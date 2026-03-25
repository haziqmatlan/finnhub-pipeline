from pyspark.sql import SparkSession
from pyspark.sql.functions import window, min, max, first, last, sum, col

'''
Pre-aggregate trade data into 1-minute OHLCV candles per symbol:
    - This involves grouping every trade into 1-minute intervals, then compute OHLCV for each stock symbol.
    - Will produce the input that Grafana's Candlestick panel expects.

Note: 
OHLCV — Open, High, Low, Close, Volume. 
Common format for representing stock price data over a specific time interval (e.g., 1 minute):
- Open: Price at the beginning of the time interval
- High: Highest price.
- Low: Lowest price.
- Close: Price at the end of the time interval.
- Volume: The total number of shares traded.
'''

spark = SparkSession.builder.appName("Pre-aggregate Gold Data").getOrCreate()

CHECKPOINT_PATH = "/Volumes/finnhub_mlops_dev/checkpoints/ohlcv_data_task"
gold_table = "finnhub_mlops_dev.feature_gold_data.trades_stock_data"


def etl_process(**options):
    print("Triggering Gold OHLCV Data process...")

    silver_df = spark.readStream \
        .format("delta") \
        .table("finnhub_mlops_dev.feature_silver_data.cleaned_stock_data")
    
    ohlcv_df = silver_df \
        .withWatermark("time", "2 minutes") \
        .groupBy(
            col("symbol"),
            window(col("time"), "1 minute")     # The tumbling window definition (Each chunk processes events that fall within its time boundaries)
        ) \
        .agg(
            first("price").alias("open"),        # First trade price in the window
            max("price").alias("high"),           # Highest trade price in the window
            min("price").alias("low"),            # Lowest trade price in the window
            last("price").alias("close"),         # Last trade price in the window
            sum("volume").alias("volume")         # Total volume traded in the window
        ) \
        .select(
            col("symbol"),
            col("window.start").alias("candle_time"),  # Grafana uses this as X-axis
            col("open"), col("high"), col("low"), col("close"), col("volume")
        )

    query = (
        ohlcv_df.writeStream
            .format("delta")
            .option("checkpointLocation", CHECKPOINT_PATH)
            .outputMode("append")
            .trigger(availableNow=True)   # Produce new candles every minute
            .toTable(gold_table)
    )
    query.awaitTermination()


