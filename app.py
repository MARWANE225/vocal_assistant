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
import io
import subprocess
import speech_recognition as sr
import threading
from flask import Flask, render_template, request, redirect, url_for
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import InputRequired
from werkzeug.utils import secure_filename

import os
import secrets
# Setup Flask
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sensor_data.db?timeout=60'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

# Initialize database
init_app(app)
migrate = Migrate(app, db)

# Initialize Flask-SocketIO
socketio = SocketIO(app)

# MQTT Setup
MQTT_BROKER = "192.168.65.94"
client = mqtt.Client()
# Assuming you have a User model already set up


# Modify get_user() to return a User object instead of a dictionary
def get_user():
    # Simulate a user with more details
    return {
        'id': 1,
        'username': 'Marwane Taleb',
        'profile_pic': 'default.jpg',
        'email': 'marwanet@example.com',  # Example email
        'phone': '123-456-7890'  # Example phone number
    }


# Define the ProfileForm with FileField to upload profile pictures
class ProfileForm(FlaskForm):
    profile_pic = FileField('Profile Picture', validators=[InputRequired()])
    submit = SubmitField('Upload')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user = get_user()  # Fetch user data using get_user()

    form = ProfileForm()
    if form.validate_on_submit():
        # Update phone and email in the user profile
        user['phone'] = form.phone.data
        user['email'] = form.email.data
        
        # Handle profile picture upload
        if form.profile_pic.data:
            file = form.profile_pic.data
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            user['profile_pic'] = filename  # Save the profile picture path

        return redirect(url_for('profile'))

    return render_template('profile.html', form=form, user=user)

def on_message(client, userdata, msg):
    """Callback executed when a message is received from MQTT"""
    try:
        payload = json.loads(msg.payload.decode())
        temperature = payload.get("temperature")
        humidity = payload.get("humidity")
        co2 = payload.get("co2")

        if temperature is not None and humidity is not None and co2 is not None:
            with app.app_context():
                save_sensor_data(temperature, humidity, co2)
                print(f"✅ MQTT Data Saved: Temp={temperature}°C, Hum={humidity}%, CO2={co2} ppm")

                socketio.emit('sensor_data', {
                    'temperature': temperature,
                    'humidity': humidity,
                    'co2': co2
                })
        else:
            print(f"⚠️ Incomplete MQTT Payload: {payload}")

    except Exception as e:
        print(f"❌ Error processing MQTT data: {e}")

client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.subscribe("home/mkr/sensors")
client.loop_start()

# ROUTES
@app.route('/')
def dashboard():
    historical_data = get_historical_data()
    latest_data = historical_data[-1] if historical_data else None

    return render_template(
        'dashboard.html',
        historical_data=historical_data,
        temperature=latest_data['temperature'] if latest_data else None,
        humidity=latest_data['humidity'] if latest_data else None,
        co2=latest_data['co2'] if latest_data else None
    )

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

def listen_microphone():
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
    
    while True:
        try:
            with microphone as source:
                audio = recognizer.listen(source)
            command = recognizer.recognize_google(audio, language="fr-FR").lower()
            
            actions = {
                "ouvrir": "servo/angle:90",
                "fermer": "servo/angle:0",
                "allumer": "fan/control:ON",
                "éteindre": "fan/control:OFF"
            }
            
            for key, topic_message in actions.items():
                if key in command:
                    topic, message = topic_message.split(":")
                    client.publish(topic, message)
                    break
        except sr.UnknownValueError:
            print("🤷 Could not understand the command")
        except sr.RequestError as e:
            print(f"🚨 Speech recognition error: {e}")

threading.Thread(target=listen_microphone, daemon=True).start()
@app.route("/IoTControl")
def index():
    return render_template("index.html")

@app.route("/voice-command", methods=["POST"])
def voice_command():
    data = request.get_json()  # Récupérer la commande envoyée par le client
    command = data.get("command", "").lower()
    print(f"Commande reçue: {command}")

    try:
        if "ouvrir" in command:
            angle = 90  # Valeur par défaut
            client.publish("servo/angle", str(angle))

        elif "fermer" in command:
            angle = 0  # Valeur par défaut
            client.publish("servo/angle", str(angle))

        elif "allumer" in command:
            client.publish("fan/control", "ON")

        elif "éteindre" in command:
            client.publish("fan/control", "OFF")

        else:
            return jsonify({"status": "Commande non reconnue"}), 400

        return jsonify({"status": "Commande envoyée"})

    except Exception as e:
        print(f"Erreur: {str(e)}")
        return jsonify({"error": str(e)}), 500


    except sr.RequestError as e:
        return jsonify({"error": f"Erreur de connexion avec l'API Google: {e}"}), 500
    except sr.UnknownValueError:
        return jsonify({"error": "Commande non comprise"}), 400
@app.route('/latest-sensor-data')
def latest_sensor_data():
    latest_data = SensorData.query.order_by(SensorData.timestamp.desc()).first()
    return jsonify(latest_data.to_dict())

@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

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
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Timestamp', 'Temperature (°C)', 'Humidity (%)', 'CO2 (ppm)'])

        for entry in sensor_data:
            writer.writerow([entry.timestamp, entry.temperature, entry.humidity, entry.co2])

        return output.getvalue()

    csv_data = generate_csv()
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sensor_data.csv'}
    )

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
                return jsonify({"message": f"Critical temperature value updated to: {new_value}"}), 200
        except ValueError:
            return jsonify({"error": "Invalid temperature value"}), 400
    return jsonify({"error": "No temperature value provided"}), 400

@app.route('/vocal-commands-interface')
def vocal_commands_interface():
    return render_template('vocal_commands.html')


@app.route('/process_command', methods=['POST'])
def process_command():
    data = request.get_json()
    command = data.get('command', '')
    print(f"Received command: {command}")
    print(command)
    try:
        result = subprocess.run(
            ['python3', 'commands.py', command],
            capture_output=True,
            text=True
        )
        response = result.stdout.strip()
        return jsonify({"response": response})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"response": f"Error: {str(e)}"})
if __name__ == '__main__':
    try:
        socketio.run(app, debug=True, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        print("Shutting down gracefully...")
