import sqlite3
import pandas as pd
import numpy as np
import joblib

# Load trained model
model = joblib.load("model.pkl")

# Connect to database and fetch the latest data
db_path = "instance/sensor_data.db"
conn = sqlite3.connect(db_path)
latest_data = pd.read_sql("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 1", conn)
conn.close()

# ✅ Convert timestamp to datetime format
latest_data['timestamp'] = pd.to_datetime(latest_data['timestamp'])

# Extract latest feature values
latest_features = latest_data[['temperature', 'humidity']].values[0]

# Fetch previous record for "1 hour ago" values
conn = sqlite3.connect(db_path)
past_data = pd.read_sql("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 2", conn)
conn.close()

# If no previous record, duplicate latest values
if len(past_data) > 1:
    past_data['timestamp'] = pd.to_datetime(past_data['timestamp'])  # Ensure past timestamp is datetime
    past_features = past_data.iloc[1][['temperature', 'humidity']].values
else:
    past_features = latest_features  # Duplicate if no previous record

# ✅ Extract time-based features after datetime conversion
hour, day, month = latest_data['timestamp'].dt.hour.values[0], latest_data['timestamp'].dt.day.values[0], latest_data['timestamp'].dt.month.values[0]

# Prepare input for model
input_data = np.array([latest_features[0], latest_features[1], past_features[0], past_features[1], hour, day, month]).reshape(1, -1)

# Predict temperature
predicted_temp = model.predict(input_data)[0]

# Store prediction in database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS predictions (id INTEGER PRIMARY KEY, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, predicted_temperature REAL)")
cursor.execute("INSERT INTO predictions (predicted_temperature) VALUES (?)", (predicted_temp,))
conn.commit()
conn.close()

print(f"Predicted Temperature Stored in Database: {predicted_temp:.2f}°C ✅")
