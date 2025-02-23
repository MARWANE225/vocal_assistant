import sys
import random
import paho.mqtt.client as mqtt
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import json
import os
from database import db, init_app, save_sensor_data, get_historical_data, SensorData, CriticalData
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler

# Check if we are on a Raspberry Pi
if "RPi" in sys.modules:
    import RPi.GPIO as GPIO
    import Adafruit_DHT
else:
    # Mock GPIO class for non-Raspberry Pi systems
    class GPIO:
        BCM = None
        OUT = None
        HIGH = None
        LOW = None
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode): pass
        @staticmethod
        def output(pin, state): pass

    # Mock Adafruit_DHT for testing purposes
    class Adafruit_DHT:
        DHT22 = None
        @staticmethod
        def read_retry(sensor, pin):
            # Generate random sensor data for testing
            humidity = random.uniform(30.0, 90.0)  # Random humidity between 30% and 90%
            temperature = random.uniform(15.0, 35.0)  # Random temperature between 15°C and 35°C
            return humidity, temperature

# Setup Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensor_data.db?timeout=60'  # Increased timeout to 60 seconds
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
init_app(app)
migrate = Migrate(app, db)

# Initialize Flask-SocketIO
socketio = SocketIO(app)

# GPIO pin configuration (doesn't affect testing on Fedora)
relay_pin = 17  # Example pin for relay control

# Setup your sensor (assuming you're using the DHT22 sensor)
sensor = Adafruit_DHT.DHT22 if "RPi" in sys.modules else Adafruit_DHT.DHT22  # Mocked for testing
sensor_pin = 4

# MQTT configuration
MQTT_BROKER = "test.mosquitto.org"  # Public MQTT broker for testing
MQTT_PORT = 1883
MQTT_TOPIC = "home/dht11"

# Initialize MQTT client
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code " + str(rc))
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    print(f"Received message: {msg.topic} {msg.payload}")

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

def read_and_store_sensor_data():
    with app.app_context():
        humidity, temperature = Adafruit_DHT.read_retry(sensor, sensor_pin)
        if humidity is not None and temperature is not None:
            # Publish sensor data to MQTT topic
            mqtt_client.publish(MQTT_TOPIC, f"Temperature: {temperature}°C, Humidity: {humidity}%")

            # Save data to database
            save_sensor_data(temperature, humidity)
            print(f"Data saved: Temperature: {temperature}°C, Humidity: {humidity}%")

            # Emit data to connected clients
            socketio.emit('sensor_data', {'temperature': temperature, 'humidity': humidity})
        else:
            print("Failed to retrieve data from sensor.")

# Initialize the scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=read_and_store_sensor_data, trigger="interval", seconds=60)  # Adjust the interval as needed
scheduler.start()

@app.route('/')
def dashboard():
    # Read historical data from database
    historical_data = get_historical_data()

    # Retrieve the latest sensor data
    latest_data = SensorData.query.order_by(SensorData.timestamp.desc()).first()
    if (latest_data):
        temperature = latest_data.temperature
        humidity = latest_data.humidity
    else:
        # Initialize temperature and humidity with default values if no data is available
        temperature = 0.0
        humidity = 0.0

    return render_template('dashboard.html', temperature=temperature, humidity=humidity, historical_data=historical_data)

@app.route('/control_relay')
def control_relay():
    return render_template('control_relay.html')

@app.route('/control', methods=['POST'])
def control():
    action = request.form.get('action')
    if action == 'on':
        GPIO.output(relay_pin, GPIO.HIGH)  # Turn ON relay (mocked on Fedora)
        mqtt_client.publish(MQTT_TOPIC, "Relay turned on")
    elif action == 'off':
        GPIO.output(relay_pin, GPIO.LOW)  # Turn OFF relay (mocked on Fedora)
        mqtt_client.publish(MQTT_TOPIC, "Relay turned off")
    message = f'Relay turned {"ON" if action == "on" else "OFF"}'
    return render_template('control_relay.html', message=message)

@app.route('/latest-sensor-data')
def latest_sensor_data():
    # Fetch the latest sensor data from the database
    latest_data = SensorData.query.order_by(SensorData.timestamp.desc()).first()
    return jsonify(latest_data.to_dict())

@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

@app.route('/data-table')
def data_table():
    # Fetch all sensor data from the database
    sensor_data = SensorData.query.order_by(SensorData.timestamp.desc()).all()
    # Fetch the critical temperature value
    critical_data = CriticalData.query.first()
    critical_value = critical_data.temperature if critical_data else None
    return render_template('data_table.html', sensor_data=sensor_data, critical_value=critical_value)

if __name__ == '__main__':
    try:
        socketio.run(app, debug=True, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()