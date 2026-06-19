# 数据仓库分层设计（DWD/DWS/ADS）

> 设计日期：2026-06-19 | 状态：已确认 | 关联文档：`docs/new-scheme.md` §5.3

## 一、设计目标

在分析引擎的 Parquet 产出之上，按 Kimball 维度建模方法论构建三层数据仓库：DWD（明细宽表）→ DWS（维度汇总）→ ADS（面向前端）。引擎本身的 5 张 Parquet 表（ODS 层）不变，仓库是增值层。

核心约束：
- 所有代码位于 `src/bilianalysis/warehouse/`，纯 Python 函数，**不接触数据库**
- 数据源：`etl/transform.py` 产出的 typed records（raw JSON → 6 组 dict）
- 构建方式：**全量重建**，每次遍历所有 raw JSON，串行产出三层 Parquet
- 维度策略：**Type 1（取最新值）**，不保留历史版本

## 二、关键决策

| # | 决策 | 理由 |
|----|------|------|
| 1 | 事实粒度 = `(weekly_number, aid)` | 视频上榜事件，对齐已有 `weekly_video` 关联表 |
| 2 | 维度属性 Type 1，嵌入 DWD 宽表 | 数据量小（每周~30视频，~280期上限），独立维度表无实际收益 |
| 3 | 全量重建 | 总数据量 < 10000 行，Pandas 秒级完成；避免增量更新的状态管理和去重逻辑 |
| 4 | 衍生率（like_rate 等）在 DWD 构建时预计算 | 不在查询时重复算，DWS/ADS 直接引用 |
| 5 | 仓库产出写入 `data/warehouse/` | 与 `data/processed/`（引擎）和 `data/reports/`（报告）分开 |
| 6 | 单文件 Parquet，不分区 | 数据量不足以支撑分区收益 |

## 三、层级架构

```
                    data/raw/week_*.json
                           │
                           ▼
              src/bilianalysis/etl/transform.py
              (纯函数：JSON → 6 组 typed records)
                           │
                           ▼
              ┌────────────────────────────┐
              │  DWD：明细宽表（1 张）       │
              │  dwd_fact_video.parquet     │
              │  粒度：(weekly_number, aid)  │
              │  维度属性全嵌入，含衍生指标   │
              └───────────┬────────────────┘
                          │
              ┌───────────┴───────────────┐
              │  DWS：汇总表（3 张）         │
              │  dws_creator.parquet       │  ← 按 up_mid 聚合
              │  dws_category.parquet      │  ← 按 category_tid 聚合
              │  dws_weekly.parquet        │  ← 按 weekly_number 聚合
              └───────────┬───────────────┘
                          │
              ┌───────────┴───────────────┐
              │  ADS：应用表（4 张）         │
              │  ads_hot_videos.parquet    │  ← 视频库页
              │  ads_top_creators.parquet  │  ← UP 主榜
              │  ads_category_trend        │  ← 分区趋势页
              │  ads_weekly_kpi.parquet    │  ← 首页 KPI + 趋势图
              └────────────────────────────┘
```

数据流严格单向：DWD 只读 transform 产物，DWS 只读 DWD，ADS 只读 DWD + DWS。无循环依赖，无跨层回写。

## 四、DWD 层：明细宽表

### 4.1 `dwd_fact_video.parquet`

一张表，粒度 `(weekly_number, aid)`，一行 = 一个视频在某一周上榜。全量重建。

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `weekly_number` | int32 | weekly_video → weekly | 期号，联合主键 |
| `aid` | int64 | video | AV 号，联合主键 |
| `bvid` | str | video | BV 号 |
| `title` | str | video | 视频标题 |
| `duration` | int32 | video | 时长（秒） |
| `pubdate` | datetime64[ns] | video | 发布时间 |
| `up_mid` | int64 | creator | UP 主 ID |
| `up_name` | str | creator | UP 主昵称，Type 1 取最新值 |
| `category_tid` | int32 | category | 三级分类 ID |
| `category_name` | str | category | 三级分类名 |
| `view` | int64 | video_stat | 播放量 |
| `like_cnt` | int64 | video_stat | 点赞数 |
| `coin` | int64 | video_stat | 投币数 |
| `favorite` | int64 | video_stat | 收藏数 |
| `share` | int64 | video_stat | 分享数 |
| `reply` | int64 | video_stat | 评论数 |
| `danmaku` | int64 | video_stat | 弹幕数 |
| `like_rate` | float64 | 衍生 | 点赞率 = like_cnt / view |
| `coin_rate` | float64 | 衍生 | 投币率 = coin / view |
| `favorite_rate` | float64 | 衍生 | 收藏率 = favorite / view |

衍生率计算：`rate = metric / view`，当 `view == 0` 时 `rate = 0.0`（不除零）。

### 4.2 构建逻辑

```python
def build_dwd(records_list: list[dict]) -> pl.DataFrame:
    """将多周 transform 产出的 records 合并为 DWD 宽表。

    Args:
        records_list: transform_week() 返回的 dict 列表，
                      每个 dict 含 "weekly", "videos", "creators",
                      "video_stats", "weekly_videos", "categories"

    Returns:
        DWD 宽表 DataFrame，含所有维度和衍生指标
    """
```

步骤：
1. 遍历 `records_list`，展开每个周的 `videos` + `video_stats` + `creators` + `categories` + `weekly_videos`
2. JOIN 维度属性（up_name, category_name, weekly_number）
3. 计算衍生率（like_rate, coin_rate, favorite_rate），`view=0` 时填 0.0
4. 类型转换：int64/int32/float64/datetime64
5. 排序 `(weekly_number, aid)` 后写入单文件 Parquet

## 五、DWS 层：维度汇总表

从 DWD 按单一维度 `groupby` 聚合，预计算常用指标。

### 5.1 `dws_creator.parquet` — UP 主汇总

粒度：`up_mid`

| 字段 | 类型 | 说明 |
|------|------|------|
| `up_mid` | int64 | PK |
| `up_name` | str | 最新昵称（取最后出现的值） |
| `total_views` | int64 | 上榜视频总播放量 |
| `total_likes` | int64 | 总点赞数 |
| `total_coins` | int64 | 总投币数 |
| `total_favorites` | int64 | 总收藏数 |
| `avg_view` | float64 | 均播放（量级指标） |
| `avg_like_rate` | float64 | 平均点赞率（质量指标） |
| `avg_coin_rate` | float64 | 平均投币率 |
| `video_count` | int32 | 上榜总次数（同一视频多周重复计数） |
| `unique_video_count` | int32 | 独立视频数 |
| `week_first` | int32 | 首次上榜期号 |
| `week_last` | int32 | 最近上榜期号 |
| `active_span` | int32 | 活跃跨度 = week_last - week_first + 1 |

### 5.2 `dws_category.parquet` — 分区汇总

粒度：`category_tid`

| 字段 | 类型 | 说明 |
|------|------|------|
| `category_tid` | int32 | PK |
| `category_name` | str | 分类名 |
| `total_views` | int64 | 总播放量 |
| `avg_view_per_video` | float64 | 均播放 |
| `avg_like_rate` | float64 | 均点赞率 |
| `video_count` | int32 | 上榜总次数 |
| `unique_creator_count` | int32 | 不同 UP 主数 |

### 5.3 `dws_weekly.parquet` — 周汇总

粒度：`weekly_number`

| 字段 | 类型 | 说明 |
|------|------|------|
| `weekly_number` | int32 | PK |
| `total_views` | int64 | 本周总播放量 |
| `avg_view_per_video` | float64 | 均播放 |
| `video_count` | int32 | 本周上榜视频数 |
| `creator_count` | int32 | 本周不同 UP 主数 |
| `category_count` | int32 | 本周不同分区数 |
| `total_likes` | int64 | 总点赞 |
| `total_coins` | int64 | 总投币 |
| `total_favorites` | int64 | 总收藏 |

### 5.4 构建逻辑

```python
def build_dws(dwd_df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """从 DWD 宽表生成三张 DWS 汇总表。

    Returns:
        {"dws_creator": df, "dws_category": df, "dws_weekly": df}
    """
```

三张表都是纯 `groupby` 聚合，无外部依赖，可并行构建。

## 六、ADS 层：应用表

ADS 是 DWD/DWS 的薄投影——排序 + 字段裁剪 + 子集筛选。唯一的例外是 `ads_category_trend`（需要对 DWD 做 `(category, week)` 交叉粒度聚合，因为 DWS 中 category 和 week 是独立聚合的，没有交叉汇总表）。

### 6.1 `ads_hot_videos.parquet` — 视频库

来源：DWD，`drop_duplicates(subset=["aid"])` 去重，每个视频取最新一期快照（最近的上榜数据）。对应前端视频库卡片网格页。

| 字段 | 说明 |
|------|------|
| `aid`, `bvid`, `title` | 基本信息 |
| `up_mid`, `up_name` | UP 主 |
| `category_name` | 分区 |
| `view`, `like_cnt`, `coin`, `favorite` | 关键指标 |
| `like_rate`, `coin_rate` | 关键衍生率 |
| `pubdate` | 发布时间 |

视频详情页所需的历史上榜记录（含 `weekly_number`）由 API 直接从 DWD 按 `aid` 过滤获取，不通过 ADS。

### 6.2 `ads_top_creators.parquet` — UP 主榜

来源：DWS creator。按 `total_views` 降序排列全量。对应前端 UP 主排行榜页 + 详情页。

| 字段 | 说明 |
|------|------|
| `up_mid`, `up_name` | |
| `total_views`, `avg_like_rate`, `avg_coin_rate` | 核心指标 |
| `video_count`, `unique_video_count` | 上榜统计 |
| `active_span` | 活跃跨度（周数） |

### 6.3 `ads_category_trend.parquet` — 分区趋势

来源：DWD 按 `(category_name, weekly_number)` 聚合。对应前端趋势分析页。

| 字段 | 说明 |
|------|------|
| `weekly_number` | |
| `category_name` | |
| `video_count` | 本周该分区上榜数 |
| `total_views` | 周播放量 |
| `avg_like_rate` | 周均点赞率 |

### 6.4 `ads_weekly_kpi.parquet` — 首页 KPI + 趋势图

来源：DWS weekly。全量，每行一周。对应前端首页卡片 + 趋势迷你图。

| 字段 | 说明 |
|------|------|
| `weekly_number` | |
| `total_views` | 周总播放 |
| `avg_view_per_video` | 周均播放 |
| `video_count`, `creator_count`, `category_count` | 规模指标 |
| `avg_like_rate`, `avg_coin_rate` | 周质量指标 |

### 6.5 构建逻辑

```python
def build_ads(dws_dict: dict[str, pl.DataFrame], dwd_df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """从 DWS + DWD 生成四张 ADS 应用表。

    Returns:
        {"ads_hot_videos": df, "ads_top_creators": df,
         "ads_category_trend": df, "ads_weekly_kpi": df}
    """
```

- `ads_hot_videos`：DWD `drop_duplicates(subset=["aid"])` 取每视频最新快照，按 view 降序
- `ads_top_creators`：DWS creator 按 total_views 降序
- `ads_category_trend`：DWD `groupby(["category_name", "weekly_number"]).agg(...)`
- `ads_weekly_kpi`：DWS weekly 直接投影（全量行数少，不裁剪）

## 七、构建编排

### 7.1 入口函数

```python
# src/bilianalysis/warehouse/__init__.py 公开导出
def build_warehouse(raw_dir: Path, warehouse_dir: Path) -> WarehouseReport:
    """全量构建数据仓库三层。

    Args:
        raw_dir:       data/raw/ 目录路径
        warehouse_dir: 产出目录，如 data/warehouse/

    Returns:
        WarehouseReport(weeks_processed, weeks_skipped, tables_written)
    """
```

### 7.2 构建流程

1. **扫描**：`raw_dir.glob("week_*.json")`，按期号排序
2. **转换**：每周围调 `transform_week()`，收集 records。单周异常记录 `(week_number, error)` 并跳过，继续处理后续周
3. **DWD**：`build_dwd()` 合并所有 records → 写 `dwd_fact_video.parquet`
4. **DWS**：`build_dws(dwd)` → 写三张表
5. **ADS**：`build_ads(dws_dicts, dwd)` → 写四张表
6. **报告**：返回 `WarehouseReport`，含处理统计和跳过的周列表

### 7.3 模块结构

```
src/bilianalysis/warehouse/
├── __init__.py           # 公开导出：build_warehouse()
├── dwd.py                # build_dwd(records_list) → pl.DataFrame
├── dws.py                # build_dws(dwd_df) → dict[str, pl.DataFrame]
├── ads.py                # build_ads(dws_dict, dwd_df) → dict[str, pl.DataFrame]
├── builder.py            # 编排入口：扫描 → 转换 → DWD → DWS → ADS → 写文件
└── report.py             # WarehouseReport 模型
```

### 7.4 报告模型

```python
class WarehouseReport(BaseModel):
    weeks_processed: int       # 成功处理的周数
    weeks_skipped: int         # 跳过的周数
    skipped_details: list[dict]  # [{"week_number": N, "error": "..."}]
    tables_written: list[str]  # 写入的 Parquet 文件名
    duration_seconds: float
```

## 八、调度集成

在现有调度框架中新增一个 `build_warehouse` Task，注册到 `scheduler/builtins/`：

```
Pipeline: analysis
  Steps: [crawl] → [build_warehouse] → [clean_data] → [statistics] → [clustering] → [prediction]
          ↑              ↑                  ↑
          已有           新增               已有
```

仓库构建位于爬虫之后、引擎清洗之前——确保引擎读取的 raw JSON 与仓库数据源一致。

也可独立触发：`POST /api/tasks/build_warehouse/run`

## 九、错误处理

| 场景 | 行为 |
|------|------|
| `transform_week` 单周异常 | 记录 `(week_number, error)` 到 skipped 列表，**继续处理后续周** |
| 所有周皆异常 | `build_warehouse` 返回 `WarehouseReport(weeks_processed=0, weeks_skipped=N)`，不写任何 Parquet |
| 数据类型不匹配（如 aid 为字符串） | `build_dwd` 做 schema 校验，类型错误抛 `TypeError` 列出不符合字段名和期望类型 |
| 除零（view=0） | 衍生率填 `0.0`，不抛异常 |
| 文件写入失败 | 先写 `{table}.tmp.parquet`，写入成功后 `os.rename` → `{table}.parquet`，中断时无脏数据残留 |
| 构建中途崩溃 | 旧 Parquet 文件保留（未被 rename 覆盖），下次全量重建自然修复 |

## 十、测试策略

所有函数均为纯函数，无需 mock 数据库。

### 10.1 单元测试

- `test_dwd.py`：假 records 输入 → 验证列名完整、衍生率计算正确、`view=0` 时 `rate=0.0`
- `test_dws.py`：固定 DWD（3 周 × 3 视频 × 2 UP 主）→ 验证 `groupby` 聚合值（sum/avg/count/nunique）
- `test_ads.py`：验证排序方向、字段子集、`ads_category_trend` 的 `groupby` 产物
- `test_builder.py`：mock `transform_week` → 验证编排流程和 `WarehouseReport` 字段

### 10.2 快照测试

固定 fixtures（3 周 × 3 视频）→ 走全链路 `build_warehouse` → 对比 8 张 Parquet 的预期 DataFrame 值。使用 `pandas.testing.assert_frame_equal`。

### 10.3 边界测试

- 空 `raw_dir`（无 week_*.json）
- 单周数据
- 单视频数据（多个 groupby 返回单行）
- `view=0` 的衍生率
- UP 主改名场景（Type 1 取最新值验证）

## 十一、数据目录

```
data/warehouse/          # ★ 新增目录
├── dwd_fact_video.parquet
├── dws_creator.parquet
├── dws_category.parquet
├── dws_weekly.parquet
├── ads_hot_videos.parquet
├── ads_top_creators.parquet
├── ads_category_trend.parquet
└── ads_weekly_kpi.parquet
```

`.gitignore` 添加 `data/warehouse/`。
