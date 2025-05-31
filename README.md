# Servers-Metrics-Logs-Kafka-Project
## Overview
This project simulates a cloud storage environment with 10 servers and a load balancer, collecting system metrics and logs. A Kafka cluster streams the data, with two dedicated topics. A Python consumer stores server metrics into a SQL Server database, and a Spark Structured Streaming application processes load balancer logs to compute 5-minute operational summaries, saving results into HDFS.

## pipline Architecture
![image](https://github.com/user-attachments/assets/1a8a9321-f6e6-4d24-a0be-34e1fe41f146)

## project steps

### 1. Start Kafka Broker & PostgreSQL
- Run Kafka and PostgreSQL using Docker Compose.
- Uses `docker-compose.yaml` file with Kafka (KRaft mode) and PostgreSQL images.

### 2. Create Kafka Topics
- Create two Kafka topics:
  - `test-topic3`: Receives **logs from the Load Balancer**.
  - `test-topic4`: Receives **metrics from the Servers**.

### 3. Run Java Producer Simulator
- Simulates 10 server agents and 1 load balancer agent.
- Sends data continuously to the Kafka topics.

### 4. Start Python Metrics Consumer
- **Consumes** from `test-topic4`.
- **Parses** server metrics data.
- **Batch inserts** into `server_matric` table in **PostgreSQL**:
  - Every 2 minutes **or**
  - After 1000 messages.

### 5. Start Spark Logs Processor
- **Consumes** from `test-topic3`.
- **Parses** HTTP logs (GET/POST success/failure).
- **Performs** 5-minute moving window aggregation with a 10-minute watermark.
- **Outputs** result to `HDFS`for storage or further processing.


