import time
import requests
from app import app, db
from database import SensorData, CriticalData  # Ensure these models are correctly defined in database.py

# Telegram bot configuration
bot_token = '7642667540:AAGvb77u-RvTxxQeILLwDBHH0w9Ub5S69qI'
chat_id = '1677969873'

def check_temperature():
    with app.app_context():
        critical_data = CriticalData.query.first()
        if critical_data is None:
            print("No critical temperature value found in the database.")
            return
        critical_value = critical_data.temperature
        latest_sensor_data = SensorData.query.order_by(SensorData.timestamp.desc()).first()
        if latest_sensor_data and latest_sensor_data.temperature > critical_value:
            send_warning_message(latest_sensor_data.temperature)

def send_warning_message(temperature):
    message = f"Warning! The temperature has reached {temperature}°C."
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Warning message sent successfully.")
    else:
        print(f"Failed to send message. Status code: {response.status_code}")

def start_background_task():
    while True:
        check_temperature()
        time.sleep(60)  # Check every 60 seconds

if __name__ == "__main__":
    start_background_task()
