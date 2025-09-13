from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'message': 'Hello World! Flask server is running.',
        'status': 'success'
    })

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'Flask API'
    })

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
    app.run(debug=True, host='0.0.0.0', port=5000)
