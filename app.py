from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
import json
from datetime import datetime
import csv
import io
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///weather.db'
db = SQLAlchemy(app)

class WeatherRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(120), nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    start_date = db.Column(db.String(10))
    end_date = db.Column(db.String(10))
    weather_data = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'weather_data': self.weather_data,
        }

@app.before_first_request
def create_tables():
    db.create_all()

def fetch_weather(location):
    params = {
        'q': location,
        'appid': API_KEY,
        'units': 'metric'
    }
    response = requests.get('https://api.openweathermap.org/data/2.5/weather', params=params)
    print("Fetching weather for:", location)
    print("Response status:", response.status_code)
    print("Response data:", response.text)
    if response.status_code == 200:
        return response.json()
    return None

@app.route('/')
def index():
    return "Weather API is running!"

@app.route('/weather', methods=['POST'])
def create_weather():
    data = request.json
    location = data.get('location')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    weather_json = fetch_weather(location)
    if not weather_json:
        return jsonify({'error': 'Location not found or API error.'}), 404

    new_record = WeatherRecord(
        location=location,
        latitude=weather_json['coord']['lat'],
        longitude=weather_json['coord']['lon'],
        start_date=start_date,
        end_date=end_date,
        weather_data=json.dumps(weather_json)  # fixed: store JSON safely
    )
    db.session.add(new_record)
    db.session.commit()

    return jsonify(new_record.to_dict()), 201

@app.route('/weather', methods=['GET'])
def read_weather():
    records = WeatherRecord.query.all()
    return jsonify([record.to_dict() for record in records])

@app.route('/weather/<int:record_id>', methods=['PUT'])
def update_weather(record_id):
    record = WeatherRecord.query.get_or_404(record_id)
    data = request.json
    if 'location' in data:
        weather_json = fetch_weather(data['location'])
        if not weather_json:
            return jsonify({'error': 'Location not found.'}), 404
        record.location = data['location']
        record.latitude = weather_json['coord']['lat']
        record.longitude = weather_json['coord']['lon']
        record.weather_data = json.dumps(weather_json)

    if 'start_date' in data:
        record.start_date = data['start_date']
    if 'end_date' in data:
        record.end_date = data['end_date']

    db.session.commit()
    return jsonify(record.to_dict())

@app.route('/weather/<int:record_id>', methods=['DELETE'])
def delete_weather(record_id):
    record = WeatherRecord.query.get_or_404(record_id)
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': 'Record deleted successfully'})

@app.route('/export/csv', methods=['GET'])
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'location', 'latitude', 'longitude', 'start_date', 'end_date', 'weather_data'])
    for record in WeatherRecord.query.all():
        writer.writerow([
            record.id, record.location, record.latitude, record.longitude,
            record.start_date, record.end_date, record.weather_data
        ])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='weather_data.csv')

if __name__ == '__main__':
    app.run(debug=True)
