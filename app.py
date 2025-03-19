from flask import Flask, render_template, request, jsonify, Response
import sys
import random
import paho.mqtt.client as mqtt
from flask_socketio import SocketIO, emit
import json
import os
from database import db, init_app, save_sensor_data, get_historical_data, SensorData, CriticalData
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
import csv
from flask import request
"""
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
"""
# Setup Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensor_data.db?timeout=60'  # Increased timeout to 60 seconds
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
init_app(app)
migrate = Migrate(app, db)

# Initialize Flask-SocketIO
socketio = SocketIO(app)

MQTT_BROKER = "192.168.53.94"  # IP du broker Mosquitto
client = mqtt.Client()
client.connect(MQTT_BROKER, 1883, 60)
""""
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
"""
def on_message(client, userdata, msg):
    """Callback exécuté lorsqu'un message est reçu sur MQTT"""
    try:
        payload = json.loads(msg.payload.decode())  # Décoder le message JSON
        temperature = payload.get("temperature")
        humidity = payload.get("humidity")

        if temperature is not None and humidity is not None:
            with app.app_context():  # Créer un contexte Flask ✅
                # Sauvegarder les données dans la base de données
                save_sensor_data(temperature, humidity)
                print(f"🔹 Données reçues et enregistrées : Temp={temperature}°C, Hum={humidity}%")

                # Émettre les données aux clients via WebSocket
                socketio.emit('sensor_data', {'temperature': temperature, 'humidity': humidity})

    except Exception as e:
        print(f"⚠️ Erreur de traitement des données MQTT : {e}")

# Initialiser la connexion MQTT
client = mqtt.Client()
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.subscribe("home/mkr/sensors")  # Écouter le topic MQTT
client.loop_start()  # Démarrer la boucle MQTT

# Routes
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
    return render_template('test2.html')
@app.route('/control', methods=['POST'])
def control():
    data = request.json
    action = data.get('action')

    if action == "fan_on":
        client.publish("fan/control", "ON")
    elif action == "fan_off":
        client.publish("fan/control", "OFF")
    elif action == "led_on":
        client.publish("led/control", "ON")
    elif action == "led_off":
        client.publish("led/control", "OFF")
    elif action == "servo":
        angle = data.get('angle', 90)
        client.publish("servo/angle", str(angle))

    return jsonify({"status": "success", "action": action})
""""
@app.route('/control', methods=['POST'])
def control():
    device = request.form['device']
    action = request.form['action']
    topic = f"home/{device}"
    mqtt_client.publish(topic, action)
    return "OK", 200
"""

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
    critical_value = critical_data.temperature if critical_data else float('inf')  # Set a default value if critical_data is None
    print(f"Critical Value: {critical_value}")
    for data in sensor_data:
        print(f"Timestamp: {data.timestamp}, Temperature: {data.temperature}, Critical: {data.temperature > critical_value}")
    return render_template('data_table.html', sensor_data=sensor_data, critical_value=critical_value)

@app.route('/download-csv')
def download_csv():
    # Fetch all sensor data from the database
    sensor_data = SensorData.query.order_by(SensorData.timestamp.desc()).all()

    # Create a CSV file in memory
    def generate():
        data = csv.writer()
        data.writerow(['Timestamp', 'Temperature (°C)', 'Humidity (%)'])
        for data in sensor_data:
            data.writerow([data.timestamp, data.temperature, data.humidity])
        yield data.getvalue()

    # Return the CSV file as a response
    return Response(generate(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=sensor_data.csv'})
@app.route('/update-critical-value', methods=['POST'])
def update_critical_value():
    new_value = request.form.get('critical_value')
    if new_value is not None:
        try:
            new_value = float(new_value)
            with app.app_context():
                critical_data = CriticalData.query.first()
                if critical_data is None:
                    critical_data = CriticalData(temperature=new_value)
                    db.session.add(critical_data)
                else:
                    critical_data.temperature = new_value
                db.session.commit()
                # Clear previous warning messages and return only the new one
                return jsonify({"message": f"Critical temperature value updated to: {new_value}"}), 200
        except ValueError:
            return jsonify({"error": "Invalid temperature value"}), 400
    return jsonify({"error": "No temperature value provided"}), 400
@app.route('/vocal-commands-interface')
def vocal_commands_interface():
    return render_template('vocal_commands.html')

import subprocess  # Add this line
@app.route('/process_command', methods=['POST'])
def process_command():
    data = request.get_json()
    command = data.get('command', '')

    try:
        result = subprocess.run(
            ['python3', 'commands.py', command],
            capture_output=True,
            text=True
        )
        response = result.stdout.strip()
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"})
if __name__ == '__main__':
    try:
        socketio.run(app, debug=True, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()