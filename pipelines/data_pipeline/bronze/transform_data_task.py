from pyspark.sql import SparkSession
from pyspark.sql.functions import from_unixtime, col

spark = SparkSession.builder.appName("Transform Bronze Data").getOrCreate()
bronze_table = "finnhub_mlops_dev.feature_bronze_data.cleaned_stock_data"


def etl_process(**options):
    print("This is the Bronze Transformation Data process...")

    trade_stock = spark.read.table("finnhub_mlops_dev.feature_bronze_data.kafka_ingest_data")

    time_df = trade_stock.withColumn("time_stamp", from_unixtime( (col("timestamp")/1000).cast("double") ))
    time_df = time_df.selectExpr("*", "CAST(time_stamp AS TIMESTAMP) AS time")

    time_df.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable(bronze_table)