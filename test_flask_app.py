from flask import Flask
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/')
def hello_world():
    app.logger.info("Handling request to root endpoint")
    return 'Hello, World! This is a test Flask application for Cloud Run.'

@app.route('/health')
def health():
    app.logger.info("Health check requested")
    return 'OK'

if __name__ == '__main__':
    # Get port from environment variable
    port = int(os.environ.get('PORT', 8080))
    app.logger.info(f"Starting Flask app on port {port}")
    
    # Run the Flask application
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True) 