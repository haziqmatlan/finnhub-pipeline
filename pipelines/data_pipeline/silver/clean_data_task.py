from pyspark.sql import SparkSession
from pyspark.sql.functions import col

'''
Prepare readable data to a trusted, useful and analysis-ready dataset:
    - Deduplication, null filtering, and enrichment logic.
'''

spark = SparkSession.builder.appName("Cleaning Silver Data").getOrCreate()

CHECKPOINT_PATH = "/Volumes/finnhub_mlops_dev/checkpoints/clean_data_task"
silver_table = "finnhub_mlops_dev.feature_silver_data.cleaned_stock_data"


def etl_process(**options):
    print("Triggering Silver Cleaning Data process...")

    bronze_df = spark.readStream \
        .format("delta") \
        .table("finnhub_mlops_dev.feature_bronze_data.transformed_stock_data")
    
    # Remove duplicates, clear bad prices, and filter out records with null symbols
    clean_df = bronze_df \
        .dropDuplicates(["symbol", "timestamp"]) \
        .filter( col("price") > 0 ) \
        .filter( col("symbol").isNotNull() ) \

    query = (
        clean_df.writeStream \
            .format("delta") \
            .option("checkpointLocation", CHECKPOINT_PATH) \
            .option("mergeSchema", "true") \
            .outputMode("append") \
            .trigger(availableNow=True) \
            .toTable(silver_table)
    )

    query.awaitTermination()