from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
import pymongo
from datetime import datetime
from config import Config
import logging

logger = logging.getLogger(__name__)

# Initialize blueprint
material_bp = Blueprint('material', __name__)

# MongoDB connection
client = pymongo.MongoClient(Config.MONGO_URI)
db = client.quiz_planner

@material_bp.route('/', methods=['POST'])
@jwt_required()
def create_material():
    """Create a new study material"""
    try:
        user_id = get_jwt_identity()
        user_id_str = str(user_id)  # Always store as string
        
        data = request.get_json()
        
        # Validate input
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({"error": "Title and content are required"}), 400
        
        title = data['title'].strip()
        content = data['content']
        
        if not title or not content:
            return jsonify({"error": "Title and content cannot be empty"}), 400
        
        # Create new material with string user_id
        material = {
            "title": title,
            "content": content,
            "description": data.get('description', '').strip(),
            "tags": data.get('tags', []),
            "user_id": user_id_str,  # Store as string consistently
            "created_at": datetime.now()
        }
        
        material_id = db.study_materials.insert_one(material).inserted_id
        
        logger.info(f"Created material {material_id} for user {user_id_str}")
        
        return jsonify({
            "message": "Study material created successfully",
            "material": {
                "id": str(material_id),
                "title": title
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error in create_material: {str(e)}")
        return jsonify({"error": f"Failed to create material: {str(e)}"}), 500

@material_bp.route('/', methods=['GET'])
@jwt_required()
def get_materials():
    """Get all study materials for the current user"""
    user_id = get_jwt_identity()
    user_id_str = str(user_id)
    
    logger.info(f"Getting materials for user: {user_id_str}")
    
    # Create query filter that works with both string and ObjectId
    user_filter = {"$or": [
        {"user_id": user_id_str},  # For string user_id
        {"user_id": {"$in": [user_id_str, ObjectId(user_id_str) if ObjectId.is_valid(user_id_str) else None]}}
    ]}
    
    # Get all materials for the user
    materials = list(db.study_materials.find(user_filter))
    
    logger.info(f"Found {len(materials)} materials")
    
    # Convert ObjectId to string for JSON serialization
    for material in materials:
        material['_id'] = str(material['_id'])
        # Ensure user_id is string in response
        if 'user_id' in material:
            material['user_id'] = str(material['user_id'])
    
    return jsonify(materials), 200

@material_bp.route('/<material_id>', methods=['GET'])
@jwt_required()
def get_material(material_id):
    """Get a specific study material"""
    user_id = get_jwt_identity()
    user_id_str = str(user_id)
    
    # Validate ObjectId
    if not ObjectId.is_valid(material_id):
        return jsonify({"error": "Invalid material ID"}), 400
    
    material = db.study_materials.find_one({
        "_id": ObjectId(material_id),
        "$or": [
            {"user_id": user_id_str},
            {"user_id": ObjectId(user_id_str) if ObjectId.is_valid(user_id_str) else None}
        ]
    })
    
    if not material:
        return jsonify({"error": "Study material not found"}), 404
    
    # Convert ObjectId to string for JSON serialization
    material['_id'] = str(material['_id'])
    if 'user_id' in material:
        material['user_id'] = str(material['user_id'])
    
    return jsonify(material), 200

@material_bp.route('/<material_id>', methods=['PUT'])
@jwt_required()
def update_material(material_id):
    """Update a study material"""
    user_id = get_jwt_identity()
    user_id_str = str(user_id)
    
    data = request.get_json()
    
    # Validate input
    if not data:
        return jsonify({"error": "No update data provided"}), 400
    
    # Validate ObjectId
    if not ObjectId.is_valid(material_id):
        return jsonify({"error": "Invalid material ID"}), 400
    
    # Check if material exists and belongs to user
    material = db.study_materials.find_one({
        "_id": ObjectId(material_id),
        "$or": [
            {"user_id": user_id_str},
            {"user_id": ObjectId(user_id_str) if ObjectId.is_valid(user_id_str) else None}
        ]
    })
    
    if not material:
        return jsonify({"error": "Study material not found"}), 404
    
    # Update fields
    update_data = {}
    
    if 'title' in data and data['title'].strip():
        update_data['title'] = data['title'].strip()
    
    if 'content' in data:
        update_data['content'] = data['content']
    
    if 'description' in data:
        update_data['description'] = data['description'].strip()
    
    if 'tags' in data:
        update_data['tags'] = data['tags']
    
    if not update_data:
        return jsonify({"message": "No fields to update"}), 200
    
    # Update material
    db.study_materials.update_one(
        {"_id": ObjectId(material_id)},
        {"$set": update_data}
    )
    
    logger.info(f"Updated material {material_id} for user {user_id_str}")
    
    return jsonify({"message": "Study material updated successfully"}), 200

@material_bp.route('/<material_id>', methods=['DELETE'])
@jwt_required()
def delete_material(material_id):
    """Delete a study material"""
    user_id = get_jwt_identity()
    user_id_str = str(user_id)
    
    # Validate ObjectId
    if not ObjectId.is_valid(material_id):
        return jsonify({"error": "Invalid material ID"}), 400
    
    # Check if material exists and belongs to user
    material = db.study_materials.find_one({
        "_id": ObjectId(material_id),
        "$or": [
            {"user_id": user_id_str},
            {"user_id": ObjectId(user_id_str) if ObjectId.is_valid(user_id_str) else None}
        ]
    })
    
    if not material:
        return jsonify({"error": "Study material not found"}), 404
    
    # Delete material
    db.study_materials.delete_one({"_id": ObjectId(material_id)})
    
    # Also delete any quizzes related to this material
    db.quizzes.delete_many({"material_id": str(material_id)})
    
    logger.info(f"Deleted material {material_id} for user {user_id_str}")
    
    return jsonify({"message": "Study material deleted successfully"}), 200