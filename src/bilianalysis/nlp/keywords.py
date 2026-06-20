"""jieba TF-IDF keyword extraction from video titles."""
import json
import re
from pathlib import Path

import jieba.analyse
import pandas as pd
from pydantic import BaseModel


# ── Models ──

class KeywordItem(BaseModel):
    word: str
    weight: float


class WeeklyKeywords(BaseModel):
    week_number: int
    keywords: list[KeywordItem]


class CategoryKeywords(BaseModel):
    tname: str
    keywords: list[KeywordItem]


class GlobalKeywords(BaseModel):
    keywords: list[KeywordItem]


class KeywordsReport(BaseModel):
    global_: GlobalKeywords
    by_week: list[WeeklyKeywords]
    by_category: list[CategoryKeywords]


# ── Stopwords ──

def _load_stopwords() -> set[str]:
    path = Path(__file__).parent / "stopwords.txt"
    if path.exists():
        return set(path.read_text(encoding="utf-8").splitlines())
    return set()


STOPWORDS = _load_stopwords()
STOPWORDS.update({" ", "", "\n", "\r", "\t"})

# Custom dictionary additions for Bilibili domain
for w in ["鬼畜", "混剪", "VLOG", "vlog", "MAD", "MMD", "AMV",
          "翻唱", "手书", "宅舞", "国创", "新番", "测评", "开箱"]:
    jieba.add_word(w)


# ── Helpers ──

def clean_title(title: str) -> str:
    """Remove punctuation, brackets, URLs and normalize."""
    if not isinstance(title, str):
        return ""
    t = re.sub(r'[【\[（(].*?[】\]）)]', '', title)
    t = re.sub(r'(https?://\S+)', '', t)
    t = re.sub(r'[^一-鿿\w]', ' ', t)
    return t.strip()


def extract_keywords(texts: list[str], topk: int = 20) -> list[KeywordItem]:
    """Extract TF-IDF keywords from a list of texts."""
    if not texts:
        return []
    combined = " ".join(texts)
    tags = jieba.analyse.extract_tags(combined, topK=topk, withWeight=True)
    return [
        KeywordItem(word=word, weight=round(float(weight), 4))
        for word, weight in tags
        if word not in STOPWORDS and len(word) >= 2
    ]


# ── Report builder ──

def build_keywords_report(processed_dir: str | Path) -> KeywordsReport:
    """Build full keywords report from Video + Category Parquet files."""
    pp = Path(processed_dir)
    video_df = pd.read_parquet(pp / "Video.parquet")
    category_df = pd.read_parquet(pp / "Category.parquet")
    df = video_df.join(category_df[["tname"]], how="left")
    df["clean_title"] = df["title"].apply(clean_title)

    # ── Global ──
    global_items = extract_keywords(df["clean_title"].dropna().tolist(), topk=50)

    # ── By week (from dwd_fact_video if available, otherwise empty)
    by_week: list[WeeklyKeywords] = []
    try:
        dwd = pd.read_parquet(pp / "dwd_fact_video.parquet")
        for wn, group in dwd.groupby("weekly_number")["title"]:
            cleaned = group.dropna().apply(clean_title).tolist()
            items = extract_keywords(cleaned, topk=10)
            by_week.append(WeeklyKeywords(week_number=int(wn), keywords=items))
        by_week.sort(key=lambda x: x.week_number)
    except Exception:
        pass

    # ── By category ──
    by_category: list[CategoryKeywords] = []
    for tname, group in df.groupby("tname"):
        if pd.isna(tname) or not tname:
            continue
        cleaned = group["clean_title"].dropna().tolist()
        items = extract_keywords(cleaned, topk=10)
        by_category.append(CategoryKeywords(tname=str(tname), keywords=items))
    by_category.sort(key=lambda x: -sum(k.weight for k in x.keywords))

    return KeywordsReport(
        global_=GlobalKeywords(keywords=global_items),
        by_week=by_week,
        by_category=by_category,
    )
