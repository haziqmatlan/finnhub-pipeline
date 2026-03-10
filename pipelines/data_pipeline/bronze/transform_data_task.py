from pyspark.sql import SparkSession
from pyspark.sql.functions import from_unixtime, col

'''
Transforms ingested data (to a readable format).
    - Transformations involve such as: converting timestamp to human-readable format & extracting relevant fields.
'''

spark = SparkSession.builder.appName("Transform Bronze Data").getOrCreate()

CHECKPOINT_PATH = "/Volumes/finnhub_mlops_dev/checkpoints/transform_data_task"
bronze_table = "finnhub_mlops_dev.feature_bronze_data.transformed_stock_data"


def etl_process(**options):
    print("Triggering Bronze Transformation Data process...")

    kafka_df = spark.readStream \
        .format("delta") \
        .table("finnhub_mlops_dev.feature_bronze_data.kafka_ingest_data")

    time_df = kafka_df.withColumn("time_stamp", from_unixtime( (col("timestamp")/1000).cast("double") ))
    time_df = time_df.selectExpr("*", "CAST(time_stamp AS TIMESTAMP) AS time")

    query = (
        time_df.writeStream \
            .format("delta") \
            .option("checkpointLocation", CHECKPOINT_PATH) \
            .option("mergeSchema", "true") \
            .outputMode("append") \
            .trigger(availableNow=True) \
            .toTable(bronze_table)
    )

    # Wait until AvailableNow finishes processing its current batch, then let the job exit cleanly.
    query.awaitTermination()