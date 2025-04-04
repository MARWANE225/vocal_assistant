from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()

def init_app(app):
    db.init_app(app)
    migrate = Migrate(app, db)
class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    co2 = db.Column(db.Float, nullable=False)  # Add CO2 column
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'co2': self.co2,  # Include CO2 in the dictionary
            'timestamp': self.timestamp.isoformat()
        }

def save_sensor_data(temperature, humidity, co2):  # Add CO2 parameter
    sensor_data = SensorData(temperature=temperature, humidity=humidity, co2=co2)
    db.session.add(sensor_data)
    db.session.commit()
    """
def save_sensor_data(temperature, humidity):
    sensor_data = SensorData(temperature=temperature, humidity=humidity)
    db.session.add(sensor_data)
    db.session.commit()"
    """
def get_historical_data():
    historical_data = SensorData.query.order_by(SensorData.timestamp).all()
    return [data.to_dict() for data in historical_data]

class CriticalData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float, nullable=False)

from flask import session  # Assuming you're using session for login


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    profile_pic = db.Column(db.String(120), nullable=True)

    def __repr__(self):
        return f'<User {self.username}>'

# If necessary, add a function to fetch the user from the database
def get_user_by_id(user_id):
    return User.query.get(user_id)