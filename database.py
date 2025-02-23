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
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'timestamp': self.timestamp.isoformat()
        }

def save_sensor_data(temperature, humidity):
    sensor_data = SensorData(temperature=temperature, humidity=humidity)
    db.session.add(sensor_data)
    db.session.commit()

def get_historical_data():
    historical_data = SensorData.query.order_by(SensorData.timestamp).all()
    return [data.to_dict() for data in historical_data]

class CriticalData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float, nullable=False)