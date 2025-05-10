from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
import pymongo
from datetime import datetime

# Initialize blueprint
material_bp = Blueprint('material', __name__)

# MongoDB connection
client = pymongo.MongoClient('mongodb://localhost:27017/')
db = client.quiz_planner

# Add this function to handle CORS preflight requests
@material_bp.route('/', methods=['OPTIONS'])
def materials_options():
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

@material_bp.route('/', methods=['POST'])
@jwt_required()
def create_material():
    """Create a new study material"""
    # Print debugging info
    print("\n--- CREATE MATERIAL REQUEST ---")
    print("Headers:", dict(request.headers))
    print("Authorization:", request.headers.get('Authorization'))
    
    try:
        user_id = get_jwt_identity()
        print("User ID from JWT:", user_id)
        
        data = request.get_json()
        print("Request data:", data)
        
        # Validate input
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({"error": "Title and content are required"}), 400
        
        title = data['title'].strip()
        content = data['content']
        
        if not title or not content:
            return jsonify({"error": "Title and content cannot be empty"}), 400
        
        # Create new material
        material = {
            "title": title,
            "content": content,
            "description": data.get('description', '').strip(),
            "tags": data.get('tags', []),
            "user_id": user_id,
            "created_at": datetime.now()
        }
        
        material_id = db.study_materials.insert_one(material).inserted_id
        print("Material created with ID:", material_id)
        
        # Add CORS headers to response
        response = jsonify({
            "message": "Study material created successfully",
            "material": {
                "id": str(material_id),
                "title": title
            }
        })
        
        return response, 201
        
    except Exception as e:
        print("Error in create_material:", str(e))
        return jsonify({"error": f"Failed to create material: {str(e)}"}), 500

@material_bp.route('/', methods=['GET'])
@jwt_required()
def get_materials():
    """Get all study materials for the current user"""
    user_id = get_jwt_identity()
    
    # Get all materials for the user
    materials = list(db.study_materials.find({"user_id": user_id}))
    
    # Convert ObjectId to string for JSON serialization
    for material in materials:
        material['_id'] = str(material['_id'])
    
    return jsonify(materials), 200

@material_bp.route('/<material_id>', methods=['GET'])
@jwt_required()
def get_material(material_id):
    """Get a specific study material"""
    user_id = get_jwt_identity()
    
    # Validate ObjectId
    if not ObjectId.is_valid(material_id):
        return jsonify({"error": "Invalid material ID"}), 400
    
    material = db.study_materials.find_one({
        "_id": ObjectId(material_id),
        "user_id": user_id
    })
    
    if not material:
        return jsonify({"error": "Study material not found"}), 404
    
    # Convert ObjectId to string for JSON serialization
    material['_id'] = str(material['_id'])
    
    return jsonify(material), 200

@material_bp.route('/<material_id>', methods=['PUT'])
@jwt_required()
def update_material(material_id):
    """Update a study material"""
    user_id = get_jwt_identity()
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
        "user_id": user_id
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
    
    return jsonify({"message": "Study material updated successfully"}), 200

@material_bp.route('/<material_id>', methods=['DELETE'])
@jwt_required()
def delete_material(material_id):
    """Delete a study material"""
    user_id = get_jwt_identity()
    
    # Validate ObjectId
    if not ObjectId.is_valid(material_id):
        return jsonify({"error": "Invalid material ID"}), 400
    
    # Check if material exists and belongs to user
    material = db.study_materials.find_one({
        "_id": ObjectId(material_id),
        "user_id": user_id
    })
    
    if not material:
        return jsonify({"error": "Study material not found"}), 404
    
    # Delete material
    db.study_materials.delete_one({"_id": ObjectId(material_id)})
    
    # Also delete any quizzes related to this material
    db.quizzes.delete_many({"material_id": material_id})
    
    return jsonify({"message": "Study material deleted successfully"}), 200