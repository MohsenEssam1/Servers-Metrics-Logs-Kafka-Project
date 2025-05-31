from kafka import KafkaConsumer
import psycopg2
import re

# Connect to Kafka
consumer = KafkaConsumer(
    'test-topic4',
    bootstrap_servers='localhost:9092',
    auto_offset_reset='earliest',
    value_deserializer=lambda v: v.decode('utf-8')
)

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="metricsdb",
    user="myuser",
    password="mypassword"
)
cursor = conn.cursor()

# Create table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS server_metrics (
        id SERIAL PRIMARY KEY,
        server_id INT NOT NULL,
        cpu_usage INT NOT NULL,
        mem_usage INT NOT NULL,
        disk_usage INT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

print("Waiting for messages from Kafka...")

for message in consumer:
    raw_message = message.value.strip()
    print(f"Received: {raw_message}")

    try:
        # Extract values using regex
        sid = int(re.search(r'id:\s*(\d+)', raw_message).group(1))
        cpu = int(re.search(r'cpu:\s*(\d+)', raw_message).group(1))
        mem = int(re.search(r'mem:\s*(\d+)', raw_message).group(1))
        disk = int(re.search(r'disk:\s*(\d+)', raw_message).group(1))

        # Insert into Postgres
        cursor.execute(
            "INSERT INTO server_metrics (server_id, cpu_usage, mem_usage, disk_usage) VALUES (%s, %s, %s, %s)",
            (sid, cpu, mem, disk)
        )
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()