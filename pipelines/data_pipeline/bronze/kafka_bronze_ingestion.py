from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, LongType, ArrayType
from pyspark.sql.functions import col, from_json, explode

'''
Fetching real-time stock trade data from Kafka topic:
    - Connection is established to the Kafka topic using Spark Structured Streaming.
    - Then, JSON data is parsed and relevant fields are extracted before writing to Delta Lake (append mode).
'''

spark = SparkSession.builder.appName("Kafka Bronze Ingestion").getOrCreate()

FINNHUB_TOKEN = "d683319r01qobepjs73gd683319r01qobepjs740"
KAFKA_BOOTSTRAP = "pkc-7qyr9j.ap-southeast-5.aws.confluent.cloud:9092"
KAFKA_TOPIC = "finnhub_topic"
KAFKA_USERNAME = "NOZOITJU6CB2DBLX"
KAFKA_PASSWORD = "cfltMmGvY52Tl+KXMD2yZS/6cmCddUAg7fhKR84KzGpFTnZ6uiUZFGXKhYPtVlbQ"
CHECKPOINT_PATH = "/Volumes/finnhub_mlops_dev/checkpoints/kafka_bronze_ingestion"


def etl_process(**options):
    print("Triggering Kafka Bronze Ingestion process...")

    data_schema = StructType([
        StructField("data", ArrayType(StructType([
            StructField("c", ArrayType(IntegerType()), True),
            StructField("p", DoubleType(), True),
            StructField("s", StringType(), True),
            StructField("t", LongType(), True),
            StructField("v", DoubleType(), True)
        ])))
    ])

    # Read from Kafka topic as streaming DataFrame
    kafka_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP) \
        .option("kafka.security.protocol", "SASL_SSL") \
        .option("kafka.sasl.mechanism", "PLAIN") \
        .option("kafka.sasl.jaas.config", 
            f'kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required username="{KAFKA_USERNAME}" password="{KAFKA_PASSWORD}";') \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "earliest") \
        .option("failOnDataLoss", "false") \
        .load() # Currently in format of key-value pairs, where key is null and value is the dict in string format
    
    # Parse the JSON string of the value column and extract the relevant fields
    parsed_df = kafka_df \
        .selectExpr("CAST(value AS STRING) as json_str") \
        .select(from_json(col("json_str"), data_schema).alias("json_data")) 
    
    trades_df = parsed_df \
        .select(explode(col("json_data.data")).alias("trade")) \
        .select(
            col("trade.c").alias("conditions"),
            col("trade.p").alias("price"),
            col("trade.s").alias("symbol"),
            col("trade.t").alias("timestamp"),
            col("trade.v").alias("volume")
        )
    
    # Write the streaming DataFrame to Delta Lake in append mode for every 30 seconds
    query = (
        trades_df.writeStream
            .format("delta")
            .option("checkpointLocation", CHECKPOINT_PATH)
            .option("mergeSchema", "true")
            .outputMode("append")
            .trigger(processingTime="30 seconds")
            .toTable("finnhub_mlops_dev.feature_bronze_data.kafka_ingest_data") 
    )
    
    # awaitTermination() keeps the job alive indefinitely, continuously
    # processing micro-batches (every 30 seconds). Without this, the job would exit immediately.
    query.awaitTermination()
        