from flask import Flask
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create Flask app
app = Flask(__name__)

@app.route('/')
def hello_world():
    app.logger.info("Handling request to root endpoint")
    return 'Hello, World! This is a test Flask application for Cloud Run with Gunicorn.'

@app.route('/health')
def health():
    app.logger.info("Health check requested")
    return 'OK'

# This is used when running locally. 
# Gunicorn will import the app object directly when running in production
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 