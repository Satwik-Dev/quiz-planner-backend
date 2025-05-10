import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from datetime import datetime

# Import config
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# IMPORTANT: Add this line to disable URL normalization
app.url_map.strict_slashes = False

# Update CORS configuration with specific options
CORS(app, 
     resources={r"/api/*": {"origins": Config.CORS_ALLOWED_ORIGINS.split(',')}},
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Setup JWT
jwt = JWTManager(app)

# MongoDB connection
client = MongoClient(app.config['MONGO_URI'])
db = client.quiz_planner

# Import controllers
from controllers.auth_controller import auth_bp
from controllers.material_controller import material_bp
from controllers.quiz_controller import quiz_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(material_bp, url_prefix='/api/materials')
app.register_blueprint(quiz_bp, url_prefix='/api/quizzes')

# Add explicit OPTIONS handler for materials endpoint
@app.route('/api/materials', methods=['OPTIONS'])
def handle_materials_options():
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', Config.CORS_ALLOWED_ORIGINS)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy", "environment": os.environ.get('ENVIRONMENT', 'development')})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'  # Bind to all interfaces
    app.run(host=host, port=port, debug=Config.DEBUG)