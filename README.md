# 📈 Finnhub Real-Time Stock Pipeline

> **Streaming data pipeline** — from live Finnhub WebSocket trades to OHLCV candlestick Grafana dashboards, orchestrated on Databricks with full CI/CD automation.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![PySpark](https://img.shields.io/badge/PySpark-3.3-E25A1C?logo=apachespark&logoColor=white)](https://spark.apache.org)
[![Databricks](https://img.shields.io/badge/Databricks-DAB-FF3621?logo=databricks&logoColor=white)](https://databricks.com)
[![Delta Lake](https://img.shields.io/badge/Delta_Lake-Medallion-003366)](https://delta.io)
[![Kafka](https://img.shields.io/badge/Confluent_Kafka-Streaming-231F20?logo=apachekafka&logoColor=white)](https://confluent.io)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![Grafana](https://img.shields.io/badge/Grafana-Dashboard-F46800?logo=grafana&logoColor=white)](https://grafana.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🗺️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        FINNHUB REAL-TIME STOCK PIPELINE                         │
└─────────────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐     WebSocket      ┌─────────────────────────┐
  │   Finnhub    │ ─────────────────► │  Confluent Cloud Kafka  │
  │  Trade Stock │  (AMZN, BTC/USDT)  │     finnhub_topic       │
  │  (Live API)  │                    └────────────┬────────────┘
  └──────────────┘                                 │
                                     Spark Structured Streaming
                                                   │
                    ┌──────────────────────────────▼──────────────────────────────┐
                    │                   DELTA LAKE  (Databricks)                  │
                    │                                                             │
                    │  ┌─────────────┐   ┌───────────────┐   ┌────────────────┐   │
                    │  │   BRONZE    │──►│    SILVER     │──►│     GOLD       │   │
                    │  │             │   │               │   │                │   │
                    │  │ • Raw Ingest│   │ • Deduplicate │   │ • OHLCV Aggr   │   │
                    │  │ • JSON Parse│   │ • Null Filter │   │ • 1-min candle │   │
                    │  │ • Timestamp │   │ • price > 0   │   │   Per symbol   │   │
                    │  │   Convert   │   │               │   │                │   │
                    │  └─────────────┘   └───────────────┘   └────────┬───────┘   │
                    └─────────────────────────────────────────────────┼───────────┘
                                                                      │
                                                               ┌──────▼──────┐
                                                               │   Grafana   │
                                                               │ Candlestick │
                                                               │  Dashboard  │
                                                               └─────────────┘

  ┌──────────────────────────────────────────────────────────────────────────────┐
  │                         DEPLOYMENT                                           │
  │   GitHub Actions CI/CD  ──►  Databricks Asset Bundles (DAB)                  │
  └──────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Key Features

| Feature | Description |
|---|---|
| **Real-Time Streaming** | WebSocket connection to Finnhub — trades ingested within milliseconds |
| **Medallion Architecture** | RAW → Bronze → Silver → Gold Delta Lake layers for progressive data quality |
| **OHLCV Aggregation** | 1-minute tumbling windows per symbol, Grafana Candlestick-ready |
| **Spark Structured Streaming** | `availableNow` trigger pattern for serverless-compatible micro-batch processing |
| **DAB Orchestration** | Full task dependency graph managed via Databricks Asset Bundles |
| **CI/CD Automation** | GitHub Actions deploys and runs the DAB job on every trigger |
| **Multi-Environment** | `dev_feature`, `test_synthetic`, `prod_release` target isolation |

---

## 🧱 Pipeline Stages

### **RAW**: WebSocket Producer → Kafka

**File:** `pipelines/data_pipeline/raw/stream_finnhub_to_kafka.py`

Establishes WebSocket connection to the [Finnhub API](https://finnhub.io/) and publishes raw trade messages to Confluent Cloud Kafka with zero transformation — preserving the original payload for full auditability.

- Subscribes to **AMZN**, and **BINANCE:BTCUSDT** trade data
- Runs for a duration of 4 minutes per DAB job cycle, for data collection purposes
- Uses `producer.flush()` after each message for low-latency delivery
- Designed to run in a separate Databricks task, decoupled from the ingestion layer

```
Finnhub WebSocket  ──►  confluent_kafka.Producer  ──►  Confluent Cloud (finnhub_topic)
```

---

### **BRONZE**: Kafka Ingestion & Timestamp Transformation

**Files:** `bronze/kafka_bronze_ingestion.py` · `bronze/transform_data_task.py`

**Step 1 — Kafka Ingestion (`kafka_bronze_ingestion`):**  
Reads the raw Kafka topic (finnhub_topic) as a Spark Structured Streaming DataFrame, parses the nested JSON schema, explodes the `data` array, and writes trade fields (`price`, `symbol`, `timestamp`, `volume`, `conditions`) to a Delta Lake table.

- `startingOffsets: earliest` ensures no data loss between runs
- `failOnDataLoss: false` Spark will not fail if there's data loss, but will continue processing next available offset
- `trigger(availableNow=True)` processes all pending offsets then exits — compatible with Databricks Serverless which does not allow long-running streaming jobs

**Step 2 — Timestamp Transformation (`transform_data_task`):**  
Reads from the raw Bronze table and converts the Unix millisecond timestamp to a human-readable `TIMESTAMP` column (`time`), making downstream time-window operations straightforward.

```
Kafka Topic  ──►  JSON Parse & Explode  ──►  kafka_ingest_data (Delta table)
                                                       │
                                         from_unixtime(timestamp/1000)
                                                       │
                                         transformed_stock_data (Delta table)
```

---

### **SILVER**: Data Cleaning

**File:** `pipelines/data_pipeline/silver/clean_data_task.py`

Reads the transformed Bronze table as a stream and applies three quality filters to produce a trusted, analysis-ready dataset:

| Rule | Filter Logic |
|---|---|
| **Deduplication** | `dropDuplicates(["symbol", "timestamp"])` |
| **Invalid Prices** | `filter(col("price") > 0)` |
| **Null Symbols** | `filter(col("symbol").isNotNull())` |

Output is written with `mergeSchema: true` to allow safe schema evolution as new symbols or fields are introduced.

```
transformed_stock_data  ──►  Dedup + Filter  ──►  cleaned_stock_data (Delta table)
```

---

### **GOLD**: OHLCV Pre-Aggregation

**File:** `pipelines/data_pipeline/gold/ohlcv_data_task.py`

Aggregates every trade into **1-minute OHLCV candlesticks** per symbol — the standard format consumed by Grafana's Candlestick panel.

```python
.withWatermark("time", "2 minutes")
.groupBy(col("symbol"), window(col("time"), "1 minute"))
.agg(
    first("price").alias("open"),
    max("price").alias("high"),
    min("price").alias("low"),
    last("price").alias("close"),
    sum("volume").alias("volume")
)
```

- **Watermark of 2 minutes** allow Sparks to handle late-arriving events (in streaming, data doesn’t always arrive in order) and accept delayed data. 
- **Tumbling windows** guarantee that each event is grouped into exactly one fixed interval (1 minute), no overlap between candle intervals
- Output schema (`symbol`, `candle_time`, `open`, `high`, `low`, `close`, `volume`) maps directly to Grafana axes

```
cleaned_stock_data  ──►  1-min Window Agg  ──►  trades_stock_data (Delta → Grafana)
```

---

## 🗂️ Project Structure

```
finnhub-pipeline/
│
├── .github/
│   └── workflows/
│       ├── data_pipeline.yml                   # Dispatch trigger — env/space/job_type inputs
│       ├── data_pipeline_launch_workflow.yml   # Reusable: deploy DAB + run job
│
├── modules/
│   ├── kafka/                              # Terraform: Confluent Cloud Kafka config
│   └── monitoring/                         # Terraform: Grafana monitoring infra
│
├── pipelines/
│   ├── core/
│   │   ├── constant/                       # Shared constants (envs, spaces, CLI keys)
│   │   └── util/
│   │       └── configuration_util.py       # SubparserBuilder decorator pattern
│   │
│   ├── data_pipeline/
│   │   ├── raw/
│   │   │   └── stream_finnhub_to_kafka.py  # WebSocket → Kafka producer
│   │   ├── bronze/
│   │   │   ├── kafka_bronze_ingestion.py   # Kafka → Delta Lake (raw trades)
│   │   │   └── transform_data_task.py      # Unix timestamp → human-readable
│   │   ├── silver/
│   │   │   └── clean_data_task.py          # Dedup, null filter, price filter
│   │   └── gold/
│   │       └── ohlcv_data_task.py          # 1-min OHLCV candles per symbol
│   │
│   └── entry_point.py                      # Argparse dispatcher — routes to etl_process()
│
├── databricks.yml                          # DAB bundle — task graph & targets
├── setup.py                                # Python package definition & dependencies
└── README.md
```

---

## 🚀 Databricks Asset Bundle (DAB) Task Graph

The pipeline is orchestrated as a single Databricks job with a strict task dependency chain:

```
stock_subscription_task          (RAW)
        │
        ▼
data_ingestion_task              (BRONZE — Kafka → Delta)
        │
        ▼
data_transformation_task         (BRONZE — Timestamp conversion)
        │
        ▼
data_cleaning_task               (SILVER — Dedup & filter)
        │
        ▼
data_ohlcv_task                  (GOLD — OHLCV aggregation)
```

The job is **scheduled every 5 minutes** via a Quartz cron expression. Because each task uses `trigger(availableNow=True)`, each run processes only newly arrived data and exits cleanly — making it fully compatible with Databricks Serverless (which prohibits long-running streaming jobs).

### Deployment Targets

| Target | Mode | Purpose |
|---|---|---|
| `dev_feature` | `development` | Active development & iteration |
| `prod_release` | `production` | Stable production workloads |

---

## ⚙️ CI/CD Pipeline (GitHub Actions)

Deployment is fully automated via two reusable workflows.

### Trigger Workflow — `data_pipeline.yml`

Manually dispatched via `workflow_dispatch` with three inputs:

| Input | Options | Default |
|---|---|---|
| `environment` | `dev`, `test`, `prod` | `dev` |
| `space` | `feature`, `synthetic`, `release` | `feature` |
| `job_type` | `data_pipeline`, `model_training`, `model_evaluation` | `data_pipeline` |

### Deploy & Run Workflow — `data_pipeline_launch_workflow.yml`

Executes the following steps on every trigger:

```
1. Checkout code
2. Set up Python 3.11
3. Install package dependencies (pip install -e ".[dev]")
4. Install Databricks CLI (unified DAB CLI)
5. Configure Databricks CLI with host & token
6. Build Python wheel (setup.py bdist_wheel)
7. Deploy DAB bundle  →  databricks bundle deploy -t {env}_{space}
8. Run DAB job       →  databricks bundle run -t {env}_{space} finnhub-pipeline
```

Required GitHub repository secrets:

```
DATABRICKS_HOST     # Databricks workspace URL
DATABRICKS_TOKEN    # Databricks personal access token
GIT_TOKEN           # GitHub token for private repo access
```

---

## 📊 Delta Lake Table Schema

### Bronze — `kafka_ingest_data`

| Column | Type | Description |
|---|---|---|
| `conditions` | `Array[Integer]` | Trade condition codes |
| `price` | `Double` | Trade execution price |
| `symbol` | `String` | Stock ticker (e.g. `AMZN`) |
| `timestamp` | `Long` | Unix epoch in milliseconds |
| `volume` | `Double` | Number of shares traded |

### Bronze — `transformed_stock_data`

All of the above, plus:

| Column | Type | Description |
|---|---|---|
| `time_stamp` | `String` | Human-readable timestamp string |
| `time` | `Timestamp` | Parsed `TIMESTAMP` for time-window ops |

### Silver — `cleaned_stock_data`

Same schema as `transformed_stock_data`, with duplicates and invalid records removed.

### Gold — `trades_stock_data`

| Column | Type | Description |
|---|---|---|
| `symbol` | `String` | Stock ticker |
| `candle_time` | `Timestamp` | Window start — X-axis for Grafana |
| `open` | `Double` | First trade price in the 1-min window |
| `high` | `Double` | Highest trade price |
| `low` | `Double` | Lowest trade price |
| `close` | `Double` | Last trade price |
| `volume` | `Double` | Total shares traded in window |

---

## 🏗️ Design Decisions

**Why `availableNow=True` instead of `processingTime`?**  
Databricks Serverless does not support long-running streaming jobs. Using `availableNow=True` allows each task to process all pending data in the current batch and exit cleanly. The 5-minute cron schedule on the DAB job then re-triggers the next micro-batch.

**Why separate tasks for Kafka ingestion and timestamp transformation?**  
Separating raw ingestion from transformation keeps the Bronze layer append-only and auditable. The raw `kafka_ingest_data` table always holds exactly what arrived from Kafka, while `transformed_stock_data` is a derived enrichment — making rollback and reprocessing straightforward.

**Why `dropDuplicates(["symbol", "timestamp"])` in Silver?**  
The `availableNow` trigger processes overlapping offset windows between runs due to `startingOffsets: earliest` as a safety net. Deduplication at the Silver layer ensures idempotency without requiring exactly-once Kafka semantics.

**Why a 2-minute watermark in the Gold layer?**  
WebSocket delivery and Kafka lag can introduce minor event-time skew. A 2-minute watermark tolerates late arrivals without indefinitely growing streaming state, while still producing accurate 1-minute OHLCV candles for Grafana.

---

## 🔗 Links

| Resource | URL |
|---|---|
| **Portfolio** | [github.com/haziqmatlan](https://github.com/haziqmatlan) |
| **GitHub** | [github.com/haziqmatlan/finnhub-pipeline](https://github.com/haziqmatlan/finnhub-pipeline) |
| **Finnhub API Docs** | [finnhub.io/docs/api](https://finnhub.io/docs/api) |
| **Databricks Asset Bundles** | [docs.databricks.com/dev-tools/bundles](https://docs.databricks.com/dev-tools/bundles/index.html) |
| **Confluent Cloud Kafka** | [confluent.io](https://confluent.io) |

---

## 👤 Author

**Haziq Matlan**  
Data Quality Engineer → Data Engineer  
[haziq.matlan@gmail.com](mailto:haziq.matlan@gmail.com) · [GitHub](https://github.com/haziqmatlan)

---

*Built with PySpark, Confluent Cloud, Databricks, and a relentless obsession with data quality.*
