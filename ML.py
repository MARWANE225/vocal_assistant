import sqlite3
import pandas as pd

# Connect to the correct database
db_path = "instance/sensor_data.db"
conn = sqlite3.connect(db_path)

# List available tables
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:", tables)

# Fetch data from the correct table
df = pd.read_sql("SELECT * FROM sensor_data", conn)  # Use the correct table name

conn.close()

# Print first few rows
print(df.head())
