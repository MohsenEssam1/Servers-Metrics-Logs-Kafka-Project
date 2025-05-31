import findspark
findspark.init()

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, regexp_extract, when, to_timestamp, window, coalesce, lit, sum as spark_sum

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("HTTPLogCounter") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .config("spark.sql.legacy.timeParserPolicy", "LEGACY") \
    .config("spark.sql.streaming.statefulOperator.checkCorrectness.enabled", "false") \
    .getOrCreate()

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC_NAME = "test-topic3"

# HDFS Output Path (inside Docker network)
HDFS_OUTPUT_PATH = "hdfs://172.18.0.2:9000/logs/output/windowed_counts/"

# 1. Read raw stream from Kafka
raw_kafka_stream_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
    .option("subscribe", KAFKA_TOPIC_NAME) \
    .option("startingOffsets", "earliest") \
    .load()

# 2. Extract log message value (the actual log line)
raw_logs_df = raw_kafka_stream_df.select(
    col("value").cast("string").alias("log_line")
)

# 3. Parse timestamp, operation type (GET/POST), and status code
parsed_logs_df = raw_logs_df \
    .withColumn("timestamp_str", regexp_extract(col("log_line"), r"\[(.*?)\]", 1)) \
    .withColumn("operation_type", regexp_extract(col("log_line"), r"\]\s+(GET|POST)\s+", 1)) \
    .withColumn("status_code", regexp_extract(col("log_line"), r"\s(\d{3})\s+\d+$", 1).cast("int"))

# 4. Convert string timestamp to proper timestamp type
timestamp_parsed_df = parsed_logs_df \
    .withColumn("timestamp", to_timestamp(col("timestamp_str"), "EEE, dd MMM yyyy HH:mm:ss z")) \
    .filter(
        col("timestamp").isNotNull() &
        col("operation_type").isin(["GET", "POST"]) &
        col("status_code").isNotNull()
    )

# 5. Categorize into four types
categorized_logs_df = timestamp_parsed_df \
    .withColumn("request_category",
        when((col("operation_type") == "GET") & (col("status_code").between(200, 299)), "GET_success")
        .when((col("operation_type") == "GET") & (~col("status_code").between(200, 299)), "GET_failure")
        .when((col("operation_type") == "POST") & (col("status_code").between(200, 299)), "POST_success")
        .otherwise("POST_failure")
    )

# 6. Group by 5-minute windows and request category
windowed_logs_df = categorized_logs_df \
    .withWatermark("timestamp", "10 minutes") \
    .groupBy(
        window(col("timestamp"), "5 minutes").alias("window"),
        col("request_category").alias("category")
    ) \
    .count()

# 7. Aggregate all categories per window
aggregated_windowed_counts_df = windowed_logs_df.groupBy("window") \
    .agg(
        coalesce(spark_sum(when(col("category") == "GET_success", col("count"))), lit(0)).alias("successful_get_requests"),
        coalesce(spark_sum(when(col("category") == "GET_failure", col("count"))), lit(0)).alias("failed_get_requests"),
        coalesce(spark_sum(when(col("category") == "POST_success", col("count"))), lit(0)).alias("successful_post_requests"),
        coalesce(spark_sum(when(col("category") == "POST_failure", col("count"))), lit(0)).alias("failed_post_requests")
    )

# 8. Function to write each batch to HDFS (without using rdd.isEmpty())
def write_to_hdfs(batch_df, batch_id):
    try:
        print(f"========= Batch ID: {batch_id} =========")
        batch_df.show(truncate=False)

        # Write directly without checking rdd.isEmpty()
        batch_df.write \
            .mode("append") \
            .parquet(HDFS_OUTPUT_PATH)
    except Exception as e:
        print(f" Error in batch write: {e}")

# 9. Start Streaming Query
try:
    streaming_query = aggregated_windowed_counts_df.writeStream \
        .outputMode("update") \
        .foreachBatch(write_to_hdfs) \
        .trigger(processingTime="5 minutes") \
        .start()

    print("Spark Streaming started. Waiting for messages...")
    streaming_query.awaitTermination()

except KeyboardInterrupt:
    print(" Streaming manually stopped by user (Ctrl+C)")

except Exception as e:
    print(f" An error occurred: {e}")

finally:
    print(" Stopping Spark session...")
    spark.stop()
    print("Spark session stopped.")
