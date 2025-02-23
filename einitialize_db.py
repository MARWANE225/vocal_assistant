from app import app, db
from database import SensorData, CriticalData  # Replace with your actual models

with app.app_context():
    # Drop all tables
    db.drop_all()

    # Create all tables
    db.create_all()

    print("Database reinitialized successfully.")