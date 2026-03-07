from pyspark.sql import SparkSession
from pyspark.sql.functions import from_unixtime, col

spark = SparkSession.builder.appName("Load Silver Data").getOrCreate()


silver_table = "finnhub_mlops_dev.feature_silver_data.trades_stock_data"

trade_stock = spark.read.table("finnhub_mlops_dev.feature_bronze_data.cleaned_stock_data")
trade_stock.write.format("delta").mode("append").option("mergeSchema", "true").saveAsTable(silver_table)