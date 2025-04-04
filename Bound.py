from flask import Flask, render_template, request, jsonify, Response
from flask_socketio import SocketIO
from flask_migrate import Migrate
from database import db, init_app, save_sensor_data, get_historical_data, SensorData, CriticalData
from apscheduler.schedulers.background import BackgroundScheduler
import paho.mqtt.client as mqtt
import subprocess
import json
import csv

# Flask setup
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensor_data.db?timeout=60'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
init_app(app)
migrate = Migrate(app, db)
socketio = SocketIO(app)

# MQTT Client setup
MQTT_BROKER = "192.168.53.94"
mqtt_client = mqtt.Client()

# MQTT Message Handler
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        temperature = payload.get("temperature")
        humidity = payload.get("humidity")
        co2 = payload.get("co2")

        if temperature and humidity and co2:
            with app.app_context():
                save_sensor_data(temperature, humidity, co2)
                socketio.emit('sensor_data', {'temperature': temperature, 'humidity': humidity, 'co2': co2})
    except Exception as e:
        print(f"MQTT error: {e}")

mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, 1883, 60)
mqtt_client.subscribe("home/mkr/sensors")
mqtt_client.loop_start()

# Routes
@app.route('/')
def dashboard():
    historical_data = get_historical_data()
    latest_data = historical_data[-1] if historical_data else {}

    return render_template(
        'dashboard.html',
        historical_data=historical_data,
        temperature=latest_data.get('temperature'),
        humidity=latest_data.get('humidity'),
        co2=latest_data.get('co2')
    )

@app.route('/control_relay')
def control_relay():
    return render_template('test2.html')

@app.route('/control', methods=['POST'])
def control():
    data = request.json
    action_map = {
        "fan_on": ("fan/control", "ON"),
        "fan_off": ("fan/control", "OFF"),
        "led_on": ("led/control", "ON"),
        "led_off": ("led/control", "OFF"),
        "servo": ("servo/angle", str(data.get('angle', 90)))
    }
    
    topic, message = action_map.get(data.get('action'), (None, None))
    if topic:
        mqtt_client.publish(topic, message)
        return jsonify({"status": "success", "action": data.get('action')})

    return jsonify({"status": "error", "message": "Invalid action"}), 400

@app.route('/latest-sensor-data')
def latest_sensor_data():
    latest_data = SensorData.query.order_by(SensorData.timestamp.desc()).first()
    return jsonify(latest_data.to_dict() if latest_data else {})

@app.route('/data-table')
def data_table():
    sensor_data = SensorData.query.order_by(SensorData.timestamp.desc()).all()
    critical_data = CriticalData.query.first()
    critical_value = critical_data.temperature if critical_data else float('inf')

    return render_template('data_table.html', sensor_data=sensor_data, critical_value=critical_value)

@app.route('/download-csv')
def download_csv():
    sensor_data = SensorData.query.order_by(SensorData.timestamp.desc()).all()

    def generate_csv():
        output = csv.writer()
        output.writerow(['Timestamp', 'Temperature (°C)', 'Humidity (%)', 'CO2 (ppm)'])
        for entry in sensor_data:
            output.writerow([entry.timestamp, entry.temperature, entry.humidity, entry.co2])
        return output.getvalue()

    return Response(
        generate_csv(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=sensor_data.csv'}
    )

@app.route('/update-critical-value', methods=['POST'])
def update_critical_value():
    new_value = request.form.get('critical_value')
    try:
        new_value = float(new_value)
        with app.app_context():
            critical_data = CriticalData.query.first() or CriticalData()
            critical_data.temperature = new_value
            db.session.add(critical_data)
            db.session.commit()
        return jsonify({"message": f"Critical temperature updated to {new_value}"}), 200
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid input"}), 400

@app.route('/vocal-commands-interface')
def vocal_commands_interface():
    return render_template('vocal_commands.html')

@app.route('/process_command', methods=['POST'])
def process_command():
    command = request.json.get('command', '')
    result = subprocess.run(['python3', 'commands.py', command], capture_output=True, text=True)
    return jsonify({"response": result.stdout.strip()})

# Scheduler setup
scheduler = BackgroundScheduler()

if __name__ == '__main__':
    try:
        socketio.run(app, debug=True, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
