"""Tests for SparkEngine lifecycle: init, session, health checks."""
from unittest import mock
from pathlib import Path

from bilianalysis.config.model import DataSection
from bilianalysis.engine.spark_engine import SparkEngine


def test_constructor_stores_config():
    """Constructor stores data paths and spark_remote without creating session."""
    data = DataSection(raw_dir="data/raw", processed_dir="data/p",
                       reports_dir="data/r")
    with mock.patch.object(SparkEngine, '_create_session',
                           return_value=mock.MagicMock()):
        engine = SparkEngine(
            data, spark_remote="sc://test:15002",
            webhdfs_url="http://test:9870")
    assert engine._spark_remote == "sc://test:15002"
    assert engine._webhdfs_url == "http://test:9870"
    assert engine._raw_dir == Path("data/raw")
    assert engine._spark is None  # lazy


def test_get_spark_creates_on_first_call():
    """_get_spark creates a session on first call."""
    data = DataSection()
    with mock.patch.object(SparkEngine, '_create_session',
                           return_value=mock.MagicMock()):
        engine = SparkEngine(data, spark_remote="sc://x:15002",
                             webhdfs_url="http://x:9870")
    engine._create_session = mock.MagicMock(return_value=mock.MagicMock())
    spark = engine._get_spark()
    assert engine._create_session.called
    assert spark is engine._spark


def test_get_spark_reconnects_on_dead_session():
    """_get_spark reconnects when cached session is dead."""
    data = DataSection()
    with mock.patch.object(SparkEngine, '_create_session',
                           return_value=mock.MagicMock()):
        engine = SparkEngine(data, spark_remote="sc://x:15002",
                             webhdfs_url="http://x:9870")
    engine._spark_verified_at = 0  # force re-verify
    dead_spark = mock.MagicMock()
    dead_spark.sql.side_effect = Exception("dead")
    engine._spark = dead_spark
    engine._create_session = mock.MagicMock(return_value=mock.MagicMock())
    engine._get_spark()
    assert dead_spark.stop.called  # stopped old session
    assert engine._create_session.called  # created new


def test_ping_returns_true_on_success():
    """ping returns True when SELECT 1 succeeds."""
    data = DataSection()
    with mock.patch.object(SparkEngine, '_create_session',
                           return_value=mock.MagicMock()):
        engine = SparkEngine(data, spark_remote="sc://x:15002",
                             webhdfs_url="http://x:9870")
    engine._get_spark = mock.MagicMock(return_value=mock.MagicMock())
    result = engine.ping(timeout_seconds=5)
    assert result is True
