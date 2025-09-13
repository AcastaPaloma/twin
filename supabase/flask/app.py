from flask import Flask, jsonify, request
import os
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Twilio configuration - now reads from .env file
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

@app.route('/')
def home():
    return jsonify({
        'message': 'Flask + Twilio SMS API',
        'status': 'success',
        'endpoints': {
            'send_sms': '/api/send-sms (POST)',
            'test_sms': '/api/test-sms (POST)',
            'health': '/health (GET)'
        }
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'Flask + Twilio API',
        'twilio_configured': bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER),
        'twilio_phone': TWILIO_PHONE_NUMBER
    })

<<<<<<< Updated upstream
@app.route('/api/send-sms', methods=['POST'])
def send_sms():
    try:
        # Check if Twilio is configured
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
            return jsonify({
                'error': 'Twilio credentials not configured',
                'message': 'Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER in .env'
            }), 400

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        to_number = data.get('to')
        message_body = data.get('message')

        # Validate required fields
        if not to_number or not message_body:
            return jsonify({
                'error': 'Missing required fields',
                'required': ['to', 'message'],
                'example': {
                    'to': '+1234567890',
                    'message': 'Hello from Twilio!'
                }
            }), 400

        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Send SMS
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number
        )

        return jsonify({
            'success': True,
            'message_sid': message.sid,
            'to': to_number,
            'message': message_body,
            'status': message.status,
            'from': TWILIO_PHONE_NUMBER
        })

    except Exception as e:
        return jsonify({
            'error': 'Failed to send SMS',
            'details': str(e)
        }), 500

@app.route('/api/test-sms', methods=['POST'])
def test_sms():
    """Test endpoint that simulates SMS sending without actually sending"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        to_number = data.get('to')
        message_body = data.get('message')

        if not to_number or not message_body:
            return jsonify({
                'error': 'Missing required fields',
                'required': ['to', 'message'],
                'example': {
                    'to': '+1234567890',
                    'message': 'Hello from Twilio!'
                }
            }), 400

        return jsonify({
            'success': True,
            'message': 'SMS test successful (not actually sent)',
            'to': to_number,
            'message_body': message_body,
            'from': TWILIO_PHONE_NUMBER,
            'simulated': True
        })

    except Exception as e:
        return jsonify({
            'error': 'Test failed',
            'details': str(e)
        }), 500
=======

>>>>>>> Stashed changes

@app.route('/api/test', methods=['GET', 'POST'])
def test_endpoint():
    if request.method == 'GET':
        return jsonify({
            'method': 'GET',
            'message': 'Test endpoint working!'
        })
    elif request.method == 'POST':
        data = request.get_json() if request.is_json else {}
        return jsonify({
            'method': 'POST',
            'message': 'Data received successfully',
            'received_data': data
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3067)
