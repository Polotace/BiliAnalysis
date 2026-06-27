"""Analysis functions: statistics, clustering, prediction."""
import time

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, lit, avg, count, sum as spark_sum
from pyspark.ml.feature import VectorAssembler, StandardScaler, PCA
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator, RegressionEvaluator
from pyspark.ml.regression import LinearRegression as SparkLR

from bilianalysis.engine.base import (
    StatReport, ClusterReport, PredictionReport,
    OverallStats, CategoryStats, CreatorStats, WeeklyTrend,
    ClusterGroup, ClusterResult, PredictionResult,
)


def compute_statistics(spark: SparkSession, processed_path: str) -> StatReport:
    """HDFS Parquet → JOIN → groupBy 聚合 → StatReport."""
    weekly = spark.read.parquet(f"{processed_path}/Weekly")
    video = spark.read.parquet(f"{processed_path}/Video")
    stat = spark.read.parquet(f"{processed_path}/VideoStat")
    creator = spark.read.parquet(f"{processed_path}/Creator")
    category = spark.read.parquet(f"{processed_path}/Category")

    df = video.join(stat, "aid", "inner")
    df = df.join(creator, "row_id", "left")
    df = df.join(category, "row_id", "left")
    # Only bring week_number from weekly — avoid column name conflicts (name, etc.)
    df = df.join(weekly.select(col("number").alias("week_number")),
                 "week_number", "inner")

    df = df.withColumn("like_rate",
                       col("like") / when(col("view") == 0, lit(1)).otherwise(col("view")))
    df = df.withColumn("coin_rate",
                       col("coin") / when(col("view") == 0, lit(1)).otherwise(col("view")))
    df = df.withColumn("favorite_rate",
                       col("favorite") / when(col("view") == 0, lit(1)).otherwise(col("view")))

    overall_row = df.agg(
        count("aid").alias("total_videos"), count("mid").alias("total_creators"),
        avg("view").alias("avg_view"), avg("like").alias("avg_like"),
        avg("coin").alias("avg_coin"), avg("favorite").alias("avg_favorite"),
        avg("share").alias("avg_share"), avg("danmaku").alias("avg_danmaku"),
        avg("like_rate").alias("avg_like_rate"),
        avg("coin_rate").alias("avg_coin_rate"),
        avg("favorite_rate").alias("avg_favorite_rate"),
    ).collect()[0]
    overall = OverallStats(
        total_videos=int(overall_row["total_videos"]),
        total_creators=int(overall_row["total_creators"]),
        avg_view=round(float(overall_row["avg_view"]), 2),
        avg_like=round(float(overall_row["avg_like"]), 2),
        avg_coin=round(float(overall_row["avg_coin"]), 2),
        avg_favorite=round(float(overall_row["avg_favorite"]), 2),
        avg_share=round(float(overall_row["avg_share"]), 2),
        avg_danmaku=round(float(overall_row["avg_danmaku"]), 2),
        avg_like_rate=round(float(overall_row["avg_like_rate"]), 4),
        avg_coin_rate=round(float(overall_row["avg_coin_rate"]), 4),
        avg_favorite_rate=round(float(overall_row["avg_favorite_rate"]), 4),
    )

    cat_rows = df.groupBy("tname").agg(
        count("aid").alias("video_count"),
        avg("view").alias("avg_view"), avg("like").alias("avg_like"),
        avg("like_rate").alias("avg_interaction_rate"),
    ).collect()
    by_category = [CategoryStats(
        tname=r["tname"], video_count=int(r["video_count"]),
        avg_view=round(float(r["avg_view"]), 2),
        avg_like=round(float(r["avg_like"]), 2),
        avg_interaction_rate=round(float(r["avg_interaction_rate"]), 4),
    ) for r in cat_rows]

    creator_rows = df.groupBy("mid", "name").agg(
        count("aid").alias("appearance_count"),
        spark_sum("view").alias("total_view"),
        spark_sum("like").alias("total_like"),
        spark_sum("favorite").alias("total_favorite"),
    ).orderBy(col("appearance_count").desc()).limit(10).collect()
    by_creator = [CreatorStats(
        mid=int(r["mid"]), name=r["name"],
        appearance_count=int(r["appearance_count"]),
        total_view=int(r["total_view"]),
        total_like=int(r["total_like"]),
        total_favorite=int(r["total_favorite"]),
    ) for r in creator_rows]

    week_rows = df.groupBy("week_number").agg(
        count("aid").alias("video_count"),
        avg("view").alias("avg_view"), avg("like").alias("avg_like"),
        avg("like_rate").alias("avg_interaction_rate"),
    ).orderBy("week_number").collect()
    by_week = [WeeklyTrend(
        week_number=int(r["week_number"]),
        video_count=int(r["video_count"]),
        avg_view=round(float(r["avg_view"]), 2),
        avg_like=round(float(r["avg_like"]), 2),
        avg_interaction_rate=round(float(r["avg_interaction_rate"]), 4),
    ) for r in week_rows]

    return StatReport(
        overall=overall, by_category=by_category,
        by_creator=by_creator, by_week=by_week,
    )


def compute_clustering(spark: SparkSession, processed_path: str) -> ClusterReport:
    """全 Spark ML: VectorAssembler → StandardScaler → KMeans(k=3) → PCA."""
    start_time = time.monotonic()
    stat = spark.read.parquet(f"{processed_path}/VideoStat")

    total = stat.count()
    if total < 3:
        duration = time.monotonic() - start_time
        return ClusterReport(
            clusters=ClusterResult(k=3, clusters=[], silhouette_score=0.0,
                                   feature_importance={}),
            scatter_data={"labels": [], "x": [], "y": []},
            duration_seconds=round(duration, 2),
        )

    features = ["view", "like", "coin", "favorite"]
    assembler = VectorAssembler(inputCols=features, outputCol="features")
    assembled = assembler.transform(stat)

    scaler = StandardScaler(inputCol="features", outputCol="scaled_features",
                            withStd=True, withMean=True)
    scaler_model = scaler.fit(assembled)
    scaled = scaler_model.transform(assembled)

    kmeans = KMeans(k=3, seed=42, featuresCol="scaled_features",
                    predictionCol="label")
    model = kmeans.fit(scaled)
    predictions = model.transform(scaled)

    evaluator = ClusteringEvaluator(featuresCol="scaled_features",
                                    predictionCol="label",
                                    metricName="silhouette")
    sil_score = evaluator.evaluate(predictions)

    labeled = predictions.select("aid", "label").join(stat, "aid", "inner")
    cluster_agg = labeled.groupBy("label").agg(
        count("*").alias("cnt"),
        avg("view").alias("avg_view"), avg("like").alias("avg_like"),
        avg("coin").alias("avg_coin"), avg("favorite").alias("avg_favorite"),
    ).collect()

    # Feature importance from cluster centers (variance across 3 clusters)
    def _var(vals):
        m = sum(vals) / len(vals)
        return sum((v - m) ** 2 for v in vals) / len(vals)
    importance = {}
    for f in features:
        vals = [float(r[f"avg_{f}"]) for r in cluster_agg]
        importance[f] = round(_var(vals), 4)

    label_view_rank = {row["label"]: float(row["avg_view"])
                       for row in cluster_agg}
    sorted_labels = sorted(label_view_rank, key=label_view_rank.get, reverse=True)
    tag_map = {sorted_labels[0]: "爆款视频", sorted_labels[1]: "普通热门",
               sorted_labels[2]: "潜力视频"}

    clusters = []
    for row in cluster_agg:
        label_idx = row["label"]
        sample_pd = (labeled.filter(col("label") == label_idx)
                     .select("aid").limit(20).toPandas())
        sample_ids = sample_pd["aid"].astype(int).tolist()
        clusters.append(ClusterGroup(
            label=label_idx, tag=tag_map[label_idx], count=int(row["cnt"]),
            centroid={
                "view": round(float(row["avg_view"]), 2),
                "like": round(float(row["avg_like"]), 2),
                "coin": round(float(row["avg_coin"]), 2),
                "favorite": round(float(row["avg_favorite"]), 2),
            },
            avg_view=round(float(row["avg_view"]), 2),
            avg_like=round(float(row["avg_like"]), 2),
            avg_coin=round(float(row["avg_coin"]), 2),
            avg_favorite=round(float(row["avg_favorite"]), 2),
            sample_ids=sample_ids,
        ))

    pca = PCA(k=2, inputCol="scaled_features", outputCol="pca_features")
    pca_model = pca.fit(scaled)
    pca_result = pca_model.transform(scaled)
    pca_rows = pca_result.select("pca_features").collect()
    label_rows = predictions.select("label").collect()
    scatter_data = {
        "labels": [int(r["label"]) for r in label_rows],
        "x": [round(float(r["pca_features"][0]), 4) for r in pca_rows],
        "y": [round(float(r["pca_features"][1]), 4) for r in pca_rows],
    }

    duration = time.monotonic() - start_time
    return ClusterReport(
        clusters=ClusterResult(k=3, clusters=clusters,
                               silhouette_score=round(float(sil_score), 4),
                               feature_importance=importance),
        scatter_data=scatter_data,
        duration_seconds=round(duration, 2),
    )


def compute_prediction(spark: SparkSession, processed_path: str) -> PredictionReport:
    """HDFS Parquet → 周聚合 → Spark ML LinearRegression → PredictionReport."""

    start_time = time.monotonic()
    video = spark.read.parquet(f"{processed_path}/Video")
    stat = spark.read.parquet(f"{processed_path}/VideoStat")
    weekly = spark.read.parquet(f"{processed_path}/Weekly")

    merged = video.join(stat, "aid", "inner")
    merged = merged.join(weekly.select(col("number").alias("week_number")),
                         "week_number", "inner")

    weekly_agg = merged.groupBy("week_number").agg(
        avg("view").alias("avg_view"), avg("like").alias("avg_like"),
        avg("coin").alias("avg_coin"), avg("favorite").alias("avg_favorite"),
        count("aid").alias("video_count"),
    ).orderBy("week_number")

    total_weeks = weekly_agg.count()

    def _predict(target: str) -> PredictionResult:
        if total_weeks < 6:
            return PredictionResult(
                model_type="linear_regression", target=target,
                r2_score=0.0, mae=0.0, rmse=0.0,
                train_size=0, test_size=0,
                coefficients={}, intercept=0.0, fitted=[], forecast=[],
            )

        target_col = f"avg_{target}"
        assembler = VectorAssembler(inputCols=["week_number", "video_count"],
                                    outputCol="features")
        full_df = assembler.transform(weekly_agg)

        # Train/test split (80/20, deterministic seed)
        train_df, test_df = full_df.randomSplit([0.8, 0.2], seed=42)
        n_train = train_df.count()
        n_test = test_df.count()

        lr = SparkLR(featuresCol="features", labelCol=target_col,
                     maxIter=100, regParam=0.0, elasticNetParam=0.0)
        model = lr.fit(train_df)

        summary = model.summary
        r2 = round(float(summary.r2), 4)
        mae = round(float(summary.meanAbsoluteError), 2)
        rmse = round(float(summary.rootMeanSquaredError), 2)
        coef = {"week_number": round(float(model.coefficients[0]), 4),
                "video_count": round(float(model.coefficients[1]), 4)}
        intercept = round(float(model.intercept), 2)

        # Test evaluation
        test_pred = model.transform(test_df)
        r2_eval = RegressionEvaluator(labelCol=target_col, predictionCol="prediction",
                                      metricName="r2")
        rmse_eval = RegressionEvaluator(labelCol=target_col, predictionCol="prediction",
                                        metricName="rmse")
        test_r2 = round(float(r2_eval.evaluate(test_pred)), 4)
        test_rmse = round(float(rmse_eval.evaluate(test_pred)), 2)

        # Fitted values on full data (retrain for best forecast)
        full_model = lr.fit(full_df)
        pred_df = full_model.transform(full_df) \
            .select("week_number", target_col, "prediction") \
            .orderBy("week_number").collect()
        fitted = [
            {"week_number": int(r["week_number"]),
             "actual": round(float(r[target_col]), 2),
             "predicted": round(float(r["prediction"]), 2)}
            for r in pred_df
        ]

        # Forecast future 4 weeks
        last_week = int(weekly_agg.selectExpr("max(week_number)").collect()[0][0])
        avg_vc = int(weekly_agg.selectExpr("avg(video_count)").collect()[0][0])
        future_data = [(last_week + i, avg_vc) for i in range(1, 5)]
        future_df = spark.createDataFrame(future_data, ["week_number", "video_count"])
        future_pred = full_model.transform(
            assembler.transform(future_df)).select("prediction").collect()
        forecast = [
            {"week_number": last_week + i,
             "predicted": round(float(future_pred[j]["prediction"]), 2)}
            for j, i in enumerate(range(1, 5))
        ]

        return PredictionResult(
            model_type="linear_regression", target=target,
            r2_score=r2, mae=mae, rmse=rmse,
            test_r2_score=test_r2, test_rmse=test_rmse,
            train_size=n_train, test_size=n_test,
            coefficients=coef, intercept=intercept,
            fitted=fitted, forecast=forecast,
        )

    view_result = _predict("view")
    like_result = _predict("like")
    duration = time.monotonic() - start_time
    return PredictionReport(
        view_predict=view_result, like_predict=like_result,
        duration_seconds=round(duration, 2),
    )


def compute_keywords(spark: SparkSession, processed_path: str):
    """HDFS Parquet → jieba TF-IDF → KeywordsReport (collects titles to driver)."""
    from bilianalysis.nlp.keywords import (
        KeywordsReport, GlobalKeywords, WeeklyKeywords, CategoryKeywords, KeywordItem,
        clean_title, extract_keywords,
    )

    video = spark.read.parquet(f"{processed_path}/Video")
    category = spark.read.parquet(f"{processed_path}/Category")

    # Join video + category, collect titles to driver (small data)
    df = video.join(category.select("row_id", col("tname")), "row_id", "left") \
              .select("title", "tname", "week_number") \
              .toPandas()

    df["clean_title"] = df["title"].apply(clean_title)

    # Global
    global_items = extract_keywords(list(df["clean_title"].dropna()), topk=50)

    # By week
    by_week = []
    for wn, group in df.groupby("week_number")["clean_title"]:
        titles = group.dropna()
        items = extract_keywords(list(titles), topk=10)
        by_week.append(WeeklyKeywords(week_number=int(wn), keywords=items))
    by_week.sort(key=lambda x: x.week_number)

    # By category
    by_category = []
    for tname, group in df.groupby("tname"):
        if not tname or not str(tname):
            continue
        titles = group["clean_title"].dropna()
        items = extract_keywords(list(titles), topk=10)
        by_category.append(CategoryKeywords(tname=str(tname), keywords=items))
    by_category.sort(key=lambda x: -sum(k.weight for k in x.keywords))

    return KeywordsReport(
        global_=GlobalKeywords(keywords=global_items),
        by_week=by_week,
        by_category=by_category,
    )
