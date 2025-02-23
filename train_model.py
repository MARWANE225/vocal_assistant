import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib  # To save the trained model

# Connect to database and load data
db_path = "instance/sensor_data.db"
conn = sqlite3.connect(db_path)
df = pd.read_sql("SELECT * FROM sensor_data", conn)
conn.close()

# Preprocess data
df['timestamp'] = pd.to_datetime(df['timestamp'])
df['hour'] = df['timestamp'].dt.hour
df['day'] = df['timestamp'].dt.day
df['month'] = df['timestamp'].dt.month

df['Temp_1h_ago'] = df['temperature'].shift(1)
df['Humidity_1h_ago'] = df['humidity'].shift(1)
df = df.dropna()  # Remove NaN values caused by shifting

# Define features and target variable
X = df[['temperature', 'humidity', 'Temp_1h_ago', 'Humidity_1h_ago', 'hour', 'day', 'month']]
y = df['temperature'].shift(-1).dropna()  # Predict next hour’s temperature

X = X[:-1]  # Remove last row since the target is shifted

# Split data for training
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = RandomForestRegressor(n_estimators=100)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
print(f"Mean Absolute Error: {mean_absolute_error(y_test, y_pred)}")

# Save the trained model
joblib.dump(model, "model.pkl")
print("Model saved successfully ✅")
