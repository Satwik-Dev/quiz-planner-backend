from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from bson.objectid import ObjectId
import pymongo
import re
from config import Config

# Initialize blueprint
auth_bp = Blueprint('auth', __name__)

# MongoDB connection - use config instead of hardcoded
client = pymongo.MongoClient(Config.MONGO_URI)
db = client.quiz_planner

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    # Validate input
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Email and password are required"}), 400
    
    email = data['email'].strip().lower()
    password = data['password']
    name = data.get('name', '').strip()
    
    # Validate email format
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "Invalid email format"}), 400
    
    # Validate password strength
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long"}), 400
    
    # Check if user already exists
    if db.users.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 409
    
    # Create new user
    user = {
        "email": email,
        "password": generate_password_hash(password),
        "name": name,
        "created_at": datetime.now()
    }
    
    user_id = db.users.insert_one(user).inserted_id
    
    return jsonify({
        "message": "User registered successfully",
        "user": {
            "id": str(user_id),
            "email": email,
            "name": name
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login a user"""
    data = request.get_json()
    
    # Validate input
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Email and password are required"}), 400
    
    email = data['email'].strip().lower()
    password = data['password']
    
    # Find user
    user = db.users.find_one({"email": email})
    
    if not user or not check_password_hash(user['password'], password):
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Create access token
    access_token = create_access_token(identity=str(user['_id']))
    
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "id": str(user['_id']),
            "email": user['email'],
            "name": user.get('name', '')
        }
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_user():
    """Get current user information"""
    user_id = get_jwt_identity()
    
    user = db.users.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": str(user['_id']),
        "email": user['email'],
        "name": user.get('name', '')
    }), 200

@auth_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_user():
    """Update user information"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No update data provided"}), 400
    
    # Find user
    user = db.users.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Update fields
    update_data = {}
    
    if 'name' in data:
        update_data['name'] = data['name'].strip()
    
    if 'password' in data:
        if len(data['password']) < 6:
            return jsonify({"error": "Password must be at least 6 characters long"}), 400
        update_data['password'] = generate_password_hash(data['password'])
    
    if not update_data:
        return jsonify({"message": "No fields to update"}), 200
    
    # Update user
    db.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    
    return jsonify({"message": "User updated successfully"}), 200