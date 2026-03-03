import websocket, json, threading, time
from kafka import KafkaProducer


FINNHUB_TOKEN = "d683319r01qobepjs73gd683319r01qobepjs740"
KAFKA_BOOTSTRAP = "pkc-7qyr9j.ap-southeast-5.aws.confluent.cloud:9092"
KAFKA_USERNAME = "NOZOITJU6CB2DBLX"
KAFKA_PASSWORD = "cfltMmGvY52Tl+KXMD2yZS/6cmCddUAg7fhKR84KzGpFTnZ6uiUZFGXKhYPtVlbQ"

KAFKA_TOPIC = "finnhub_topic"
VOLUME_PATH = "/Volumes/finnhub_mlops_dev/feature_raw_data/trades_stock_data"   # Unity Catalog Volume
CHECKPOINT_PATH = "/Volumes/finnhub_mlops_dev/feature_raw_data/checkpoints"
symbols = []

# Bridge b/w Websocket & Kafka
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    security_protocol='SASL_SSL',   # Confluent always uses encrypted, authenticated connections
    sasl_mechanism='PLAIN',
    sasl_plain_username=KAFKA_USERNAME,
    sasl_plain_password=KAFKA_PASSWORD,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

# Websocket callback functions
def on_message(ws, message):
    data = json.loads(message)
    if data.get("type") == "trade":
        producer.send(KAFKA_TOPIC, value=data)  # Send trade data to Kafka topic
        producer.flush()  # Ensure all buffered data is sent immediately

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"Connection closed: {close_status_code}\n message: {close_msg}")

def on_open(ws):
    ws.send(' {"type": "subscribe", "symbol": "BINANCE:BTCUSDT"} ') 
    print("Subscribed to BINANCE:BTCUSDT...")


def etl_process(**options):
    ws = websocket.WebSocketApp(
        f"wss://ws.finnhub.io?token={FINNHUB_TOKEN}",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
        )

    thread = threading.Thread(target=ws.run_forever)
    thread.start()
    time.sleep(10)  # Keep the main thread alive for 10 seconds to receive messages

    ws.keep_running = False # Signal the WebSocket run_forever() to stop 
    ws.close()              # Close the WebSocket connection gracefully
    thread.join(timeout=5)  # Wait for the thread to finish, with a timeout to prevent hanging indefinitely
    print("WebSocket connection closed, thread joined...")
