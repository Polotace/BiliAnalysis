`$SPARK_HOME/conf/spark-defaults.conf：`
```
properties
# Standalone 集群配置
spark.master                                spark://spark:7077
spark.driver.memory                         2g
spark.executor.memory                       2g
spark.executor.cores                        2
spark.cores.max                             4

# 任务优化
spark.sql.shuffle.partitions                4
spark.default.parallelism                   4
spark.serializer                            org.apache.spark.serializer.KryoSerializer
spark.sql.adaptive.enabled                  true
spark.sql.adaptive.coalescePartitions.enabled true

# Arrow 加速
spark.sql.execution.arrow.pyspark.enabled     true
spark.sql.execution.arrow.maxRecordsPerBatch 100000

# Connect Server 配置
spark.connect.grpc.binding.port             15002
spark.connect.grpc.binding.host             0.0.0.0
spark.connect.grpc.maxInboundMessageSize    512m
```

`$SPARK_HOME/conf/spark-env.sh：`
```
export SPARK_WORKER_CORES=4
export SPARK_WORKER_MEMORY=4g
export SPARK_WORKER_INSTANCES=1
```