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

# Add debug print
print(f"MongoDB URI: {Config.MONGO_URI}")
print(f"CORS Origins: {Config.CORS_ALLOWED_ORIGINS}")

# Update CORS configuration with specific options
CORS(app, 
     resources={r"/api/*": {"origins": Config.CORS_ALLOWED_ORIGINS.split(',')}},
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Setup JWT
jwt = JWTManager(app)

# MongoDB connection
try:
    client = MongoClient(app.config['MONGO_URI'])
    db = client.quiz_planner
    print("MongoDB connected successfully")
except Exception as e:
    print(f"MongoDB connection error: {e}")
    db = None

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

@app.route('/')
def index():
    return jsonify({
        "status": "running",
        "message": "Quiz Planner API is running",
        "environment": os.environ.get('ENVIRONMENT', 'development')
    })

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy", "environment": os.environ.get('ENVIRONMENT', 'development')})

@app.route('/api/debug/env')
def debug_env():
    # Only show this in development
    if Config.ENVIRONMENT != 'production':
        return jsonify({
            "ENVIRONMENT": os.environ.get('ENVIRONMENT'),
            "CORS_ORIGINS": os.environ.get('CORS_ALLOWED_ORIGINS'),
            "MONGO_URI": "configured" if os.environ.get('MONGO_URI') else "not configured",
            "JWT_SECRET": "configured" if os.environ.get('JWT_SECRET_KEY') else "not configured",
            "GEMINI_API": "configured" if os.environ.get('GEMINI_API_KEY') else "not configured"
        })
    else:
        return jsonify({"message": "Debug info not available in production"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'  # Bind to all interfaces
    app.run(host=host, port=port, debug=Config.DEBUG)