"""Tests for spark/clean.py — pure logic with real local SparkSession."""
import json
import os
import sys
import pytest

from pyspark.sql import SparkSession
from bilianalysis.engine.spark.clean import extract_tables, fill_missing, convert_types


@pytest.fixture(scope="module")
def spark():
    # Spark 4.x on Windows needs PYSPARK_PYTHON to find the Python binary
    if sys.platform == "win32":
        os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
        os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)
    spark = SparkSession.builder \
        .master("local[1]") \
        .appName("test") \
        .config("spark.driver.bindAddress", "127.0.0.1") \
        .getOrCreate()
    yield spark
    spark.stop()


def test_extract_tables_structure(spark):
    """Verify 5 tables are returned with expected columns."""
    data = {
        "number": 1,
        "config": {"subject": "test", "name": "test_week",
                   "stime": 100, "etime": 200},
        "videos": [{
            "aid": 1, "bvid": "BV1", "title": "v1", "desc": "", "duration": 60,
            "pubdate": 150, "cid": 10, "pic": "",
            "owner": {"mid": 100, "name": "c", "face": ""},
            "stat": {"aid": 1, "view": 1000, "like": 100, "coin": 10,
                     "favorite": 20, "share": 5, "reply": 3, "danmaku": 8},
            "tid": 1, "tname": "game",
        }]
    }
    raw_df = spark.read.json(spark.sparkContext.parallelize([json.dumps(data)]))
    dfs = extract_tables(raw_df)
    assert set(dfs.keys()) == {"Weekly", "Video", "Creator", "Category", "VideoStat"}
    assert dfs["Video"].count() == 1
    assert dfs["Creator"].count() == 1


def test_extract_tables_fills_missing_rcmd_reason(spark):
    """When rcmd_reason is absent, tid_v2/tname_v2 are null."""
    data = {
        "number": 1,
        "config": {"subject": "t", "name": "w", "stime": 100, "etime": 200},
        "videos": [{
            "aid": 1, "bvid": "BV1", "title": "v", "desc": "", "duration": 60,
            "pubdate": 150, "cid": 10, "pic": "",
            "owner": {"mid": 100, "name": "c", "face": ""},
            "stat": {"aid": 1, "view": 1000, "like": 100, "coin": 10,
                     "favorite": 20, "share": 5, "reply": 3, "danmaku": 8},
            "tid": 1, "tname": "game",
        }]
    }
    raw_df = spark.read.json(spark.sparkContext.parallelize([json.dumps(data)]))
    dfs = extract_tables(raw_df)
    cat = dfs["Category"].collect()[0]
    assert cat["tid_v2"] is None
    assert cat["tname_v2"] is None


def test_extract_tables_row_id_consistency(spark):
    """Video, Creator, Category, VideoStat share the same row_id."""
    data = {
        "number": 1,
        "config": {"subject": "t", "name": "w", "stime": 100, "etime": 200},
        "videos": [
            {"aid": 1, "bvid": "BV1", "title": "v1", "desc": "", "duration": 60,
             "pubdate": 150, "cid": 10, "pic": "",
             "owner": {"mid": 100, "name": "c1", "face": ""},
             "stat": {"aid": 1, "view": 1000, "like": 100, "coin": 10,
                      "favorite": 20, "share": 5, "reply": 3, "danmaku": 8},
             "tid": 1, "tname": "game"},
            {"aid": 2, "bvid": "BV2", "title": "v2", "desc": "", "duration": 120,
             "pubdate": 160, "cid": 11, "pic": "",
             "owner": {"mid": 200, "name": "c2", "face": ""},
             "stat": {"aid": 2, "view": 5000, "like": 500, "coin": 50,
                      "favorite": 100, "share": 25, "reply": 15, "danmaku": 40},
             "tid": 1, "tname": "game"},
        ]
    }
    raw_df = spark.read.json(spark.sparkContext.parallelize([json.dumps(data)]))
    dfs = extract_tables(raw_df)

    video_ids = [r["row_id"] for r in dfs["Video"].select("row_id").collect()]
    creator_ids = [r["row_id"] for r in dfs["Creator"].select("row_id").collect()]
    stat_ids = [r["row_id"] for r in dfs["VideoStat"].select("row_id").collect()]
    cat_ids = [r["row_id"] for r in dfs["Category"].select("row_id").collect()]

    assert video_ids == creator_ids == stat_ids == cat_ids
    assert len(video_ids) == 2


def test_fill_missing_numeric(spark):
    """Numeric columns are filled with 0, strings with ''."""
    from pyspark.sql.types import StructType, StructField, LongType, StringType
    schema = StructType([
        StructField("aid", LongType(), True),
        StructField("view", LongType(), True),
        StructField("name", StringType(), True),
    ])
    df = spark.createDataFrame([(None, None, None)], schema)
    dfs = {"VideoStat": df}
    result = fill_missing(dfs)
    row = result["VideoStat"].collect()[0]
    assert row["aid"] == 0
    assert row["view"] == 0
    assert row["name"] == ""


def test_convert_types_casts_columns(spark):
    """Columns are cast to the correct types."""
    from pyspark.sql.types import StructType, StructField, StringType
    schema = StructType([
        StructField("aid", StringType(), True),
        StructField("view", StringType(), True),
    ])
    df = spark.createDataFrame([("1", "100")], schema)
    empty_schema = StructType([])
    dfs = {
        "VideoStat": df,
        "Video": spark.createDataFrame([], empty_schema),
        "Creator": spark.createDataFrame([], empty_schema),
        "Category": spark.createDataFrame([], empty_schema),
        "Weekly": spark.createDataFrame([], empty_schema),
    }
    result = convert_types(dfs)
    row = result["VideoStat"].collect()[0]
    assert row["aid"] == 1
    assert row["view"] == 100.0
