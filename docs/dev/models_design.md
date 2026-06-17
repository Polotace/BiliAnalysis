# 模型设计

## 模型设计原则
1. **简洁性**：模型应尽可能简单，避免过度复杂化。简单的模型更容易理解和维护。
2. **可解释性**：模型应具有良好的可解释性，能够清晰地说明其决策过程和结果。
3. **泛化能力**：模型应具有良好的泛化能力，能够在未见过的数据上表现良好，避免过拟合。
4. **可扩展性**：模型设计应考虑未来的扩展需求，能够方便地添加新的功能或处理新的数据类型。
5. **性能**：模型应在合理的时间内完成训练和预测，满足实际应用的性能要求。
6. **数据驱动**：模型设计应基于数据的特征和分布，充分利用数据中的信息来提高模型的性能。

## 数据模型

1. Weekly 期刊

    | 字段         | 类型           |
    |------------|--------------|
    | id         | bigint       |
    | number     | int          |
    | subject    | varchar(200) |
    | name       | varchar(100) |
    | start_time | timestamp    |
    | end_time   | timestamp    |

2. Video 视频

    | 字段        | 类型        |
    |-----------|-----------|
    | aid       | bigint    |
    | bvid      | varchar   |
    | title     | text      |
    | desc      | text      |
    | duration  | int       |
    | pubdate   | timestamp |
    | cid       | bigint    |
    | cover_url | text      |

3. Creator 用户

    | 字段   | 类型      |
    |------|---------|
    | mid  | bigint  |
    | name | varchar |
    | face | text    |

4. Category 分类

    | 字段       | 类型      |
    |----------|---------|
    | pid      | bigint  |
    | pid_name | varchar |
    | tidv2    | bigint  |
    | tnamev2  | varchar |
    | tid      | bigint  |
    | tname    | varchar |

5. VideoStat 视频统计数据

    | 字段       | 类型     |
    |----------|--------|
    | aid      | bigint |
    | view     | bigint |
    | like     | bigint |
    | coin     | bigint |
    | favorite | bigint |
    | share    | bigint |
    | reply    | bigint |
    | danmaku  | bigint |
