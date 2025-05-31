# Servers-Metrics-Logs-Kafka-Project
## Overview
This project simulates a cloud storage environment with 10 servers and a load balancer, collecting system metrics and logs. A Kafka cluster streams the data, with two dedicated topics. A Python consumer stores server metrics into a SQL Server database, and a Spark Structured Streaming application processes load balancer logs to compute 5-minute operational summaries, saving results into HDFS.

## pipline Architecture
![image](https://github.com/user-attachments/assets/1a8a9321-f6e6-4d24-a0be-34e1fe41f146)

