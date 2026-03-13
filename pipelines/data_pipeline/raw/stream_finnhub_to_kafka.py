import websocket
import threading
import time
import json
from confluent_kafka import Producer

'''
Establishes a WebSocket connection to the Finnhub API:
    - Receiving real-time stock trade data. 
    - Then publish the data to Kafka exactly as received — no parsing, filtering & transformation.
'''

FINNHUB_TOKEN = "d683319r01qobepjs73gd683319r01qobepjs740"
KAFKA_BOOTSTRAP = "pkc-7qyr9j.ap-southeast-5.aws.confluent.cloud:9092"
KAFKA_TOPIC = "finnhub_topic"
KAFKA_USERNAME = "NOZOITJU6CB2DBLX"
KAFKA_PASSWORD = "cfltMmGvY52Tl+KXMD2yZS/6cmCddUAg7fhKR84KzGpFTnZ6uiUZFGXKhYPtVlbQ"

# ─── Kafka Producer ──────────────────────────────────────────────────────────
# Bridge b/w Websocket & Kafka
conf = {
  "bootstrap.servers": f"{KAFKA_BOOTSTRAP}",
  "security.protocol": "SASL_SSL",
  "sasl.mechanism": "PLAIN",
  "sasl.username": f"{KAFKA_USERNAME}",
  "sasl.password": f"{KAFKA_PASSWORD}"
}
producer = Producer(conf)

def delivery_report(err, msg):
    if err is not None:
        print(f"Delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()}...")

# ─── WebSocket Callback ──────────────────────────────────────────────────────
def on_message(ws, message):
    data = json.loads(message)
    print(f"Received message: {data}")
    if data.get('type') == "trade":
        producer.produce(
          KAFKA_TOPIC, 
          value=json.dumps(data).encode("utf-8"),
          callback=delivery_report
        ) # queue a message for Kafka delivery
        
        # Kafka will consider as Raw zone instead - to minimize latency
        producer.flush()    # Forces all buffered messages to deliver to Kafka right away 

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"Connection closed: {close_status_code} | {close_msg}")

#--Send all data to Kafka------------------
def on_open(ws):
    ws.send('{"type":"subscribe","symbol":"AAPL"}')
    ws.send('{"type":"subscribe","symbol":"AMZN"}')
    ws.send('{"type":"subscribe","symbol":"BINANCE:BTCUSDT"}')

def etl_process(**options):
    print("Triggering Stream Finnhub Data to Kafka process...")

    ws = websocket.WebSocketApp(f"wss://ws.finnhub.io?token={FINNHUB_TOKEN}",
                                    on_open=on_open,
                                    on_message = on_message,
                                    on_error = on_error,
                                    on_close = on_close)

    # ─── Lauch WebSocket Thread ──────────────────────────────────────────────────
    thread = threading.Thread(target=ws.run_forever)
    thread.start()
    time.sleep(240)  # Let it run for 4 minutes (240 seconds) to collect data

    ws.keep_running = False # Signal the WebSocket run_forever() to stop 
    ws.close()              # Close the WebSocket connection gracefully
    thread.join(timeout=5)  # Wait for the thread to finish, with a timeout to prevent hanging indefinitely
    print("WebSocket connection closed, thread joined...")
