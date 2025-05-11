import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from datetime import datetime
import logging

# Import config
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# IMPORTANT: Add this line to disable URL normalization
app.url_map.strict_slashes = False

# Enhanced CORS configuration
if Config.ENVIRONMENT == 'production':
    # Allow all Vercel deployments in production
    cors_origins = [
        "https://quiz-planner-frontend.vercel.app",
        "https://quiz-planner-frontend-*.vercel.app",
        "https://*.vercel.app"
    ]
else:
    cors_origins = Config.CORS_ALLOWED_ORIGINS.split(',')

CORS(app, 
     origins=cors_origins,
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     expose_headers=["Content-Type", "Authorization"])

# Setup JWT
jwt = JWTManager(app)

# MongoDB connection with retry logic
try:
    client = MongoClient(app.config['MONGO_URI'], 
                        serverSelectionTimeoutMS=5000,
                        connectTimeoutMS=10000)
    # Test connection
    client.server_info()
    db = client.quiz_planner
    logger.info("MongoDB connected successfully")
except Exception as e:
    logger.error(f"MongoDB connection error: {e}")
    db = None

# Import controllers
from controllers.auth_controller import auth_bp
from controllers.material_controller import material_bp
from controllers.quiz_controller import quiz_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(material_bp, url_prefix='/api/materials')
app.register_blueprint(quiz_bp, url_prefix='/api/quizzes')

@app.route('/')
def index():
    return jsonify({
        "status": "running",
        "message": "Quiz Planner API is running",
        "environment": os.environ.get('ENVIRONMENT', 'development'),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/health')
def health_check():
    health_status = {
        "status": "healthy",
        "environment": os.environ.get('ENVIRONMENT', 'development'),
        "mongodb": "connected" if db else "disconnected",
        "timestamp": datetime.now().isoformat()
    }
    
    # Test MongoDB connection
    if db:
        try:
            db.command('ping')
            health_status["mongodb"] = "connected"
        except Exception as e:
            health_status["mongodb"] = f"error: {str(e)}"
            
    return jsonify(health_status)

@app.route('/api/debug/status')
def debug_status():
    """Comprehensive debug endpoint to check all connections"""
    status = {
        "timestamp": datetime.now().isoformat(),
        "environment": os.environ.get('ENVIRONMENT', 'unknown'),
        "mongodb": "disconnected",
        "collections": {},
        "cors_origins": cors_origins,
        "api_status": "running"
    }
    
    # Test MongoDB connection
    try:
        client.server_info()
        status["mongodb"] = "connected"
        
        # Get collection stats
        collections = db.list_collection_names()
        for collection in collections:
            count = db[collection].count_documents({})
            status["collections"][collection] = count
            
    except Exception as e:
        status["mongodb_error"] = str(e)
    
    return jsonify(status)

# Global error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}")
    return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'  # Bind to all interfaces
    app.run(host=host, port=port, debug=Config.DEBUG)