import os
import sys
from pathlib import Path
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
import pymongo
from datetime import datetime
from config import Config  # Fix: Import from your config module, not from Flask

# Initialize blueprint
quiz_bp = Blueprint('quiz', __name__)

# MongoDB connection - use config instead of hardcoded
client = pymongo.MongoClient(Config.MONGO_URI)
db = client.quiz_planner

# Add parent directory to path to ensure imports work properly
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.append(str(parent_dir))

# Import and initialize the question generator
try:
    from ai.question_generator import QuestionGenerator
    question_generator = QuestionGenerator()
    print("QuestionGenerator initialized successfully")
except Exception as e:
    print(f"Error initializing QuestionGenerator: {e}")
    question_generator = None

@quiz_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_quiz():
    """Generate a quiz from study material"""
    if not question_generator:
        return jsonify({"error": "Question generator not available"}), 500
    
    user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate input
    if not data or 'material_id' not in data:
        return jsonify({"error": "Material ID is required"}), 400
    
    material_id = data['material_id']
    
    # Validate ObjectId
    if not ObjectId.is_valid(material_id):
        return jsonify({"error": "Invalid material ID"}), 400
    
    # Get parameters
    num_questions = data.get('num_questions', 5)
    question_types = data.get('question_types', ["multiple_choice", "true_false", "short_answer"])
    
    # Get study material
    material = db.study_materials.find_one({
        "_id": ObjectId(material_id),
        "user_id": user_id
    })
    
    if not material:
        return jsonify({"error": "Study material not found"}), 404
    
    # Generate questions
    try:
        questions = question_generator.generate_questions(
            material['content'],
            num_questions=num_questions,
            question_types=question_types
        )
        
        # Create quiz document
        quiz = {
            "title": data.get('title', f"Quiz on {material['title']}"),
            "description": data.get('description', f"Generated quiz based on {material['title']}"),
            "questions": questions,
            "user_id": user_id,
            "material_id": material_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        quiz_id = db.quizzes.insert_one(quiz).inserted_id
        
        return jsonify({
            "message": "Quiz generated successfully",
            "quiz_id": str(quiz_id),
            "title": quiz["title"],
            "num_questions": len(questions)
        }), 201
    
    except Exception as e:
        return jsonify({"error": f"Failed to generate quiz: {str(e)}"}), 500

@quiz_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_quizzes():
    """Get all quizzes for current user with pagination and filtering"""
    user_id = get_jwt_identity()
    
    # Pagination parameters
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    skip = (page - 1) * limit
    
    # Filtering parameters
    search_query = request.args.get('search', '')
    material_id = request.args.get('material', '')
    
    # Create filter
    query_filter = {"user_id": user_id}
    
    # Add search filter if provided
    if search_query:
        query_filter["$or"] = [
            {"title": {"$regex": search_query, "$options": "i"}},
            {"description": {"$regex": search_query, "$options": "i"}}
        ]
    
    # Add material filter if provided
    if material_id and ObjectId.is_valid(material_id):
        query_filter["material_id"] = material_id
    
    # Count total for pagination
    total_quizzes = db.quizzes.count_documents(query_filter)
    
    # Get quizzes with pagination
    quizzes = list(db.quizzes.find(query_filter).sort("created_at", -1).skip(skip).limit(limit))
    
    # Convert ObjectId to string and format response
    formatted_quizzes = []
    for quiz in quizzes:
        # Get related material info
        material = None
        if ObjectId.is_valid(quiz['material_id']):
            material = db.study_materials.find_one({"_id": ObjectId(quiz['material_id'])})
        
        # Get attempt count
        attempt_count = db.quiz_attempts.count_documents({"quiz_id": str(quiz['_id']), "user_id": user_id})
        
        formatted_quizzes.append({
            "id": str(quiz['_id']),
            "title": quiz['title'],
            "description": quiz['description'],
            "num_questions": len(quiz['questions']),
            "created_at": quiz['created_at'].isoformat(),
            "material_id": str(quiz['material_id']),
            "material_title": material['title'] if material else "Unknown",
            "attempt_count": attempt_count
        })
    
    return jsonify({
        "quizzes": formatted_quizzes,
        "pagination": {
            "total": total_quizzes,
            "page": page,
            "limit": limit,
            "pages": (total_quizzes + limit - 1) // limit
        }
    }), 200

@quiz_bp.route('/<quiz_id>', methods=['GET'])
@jwt_required()
def get_quiz(quiz_id):
    """Get a specific quiz with all questions"""
    user_id = get_jwt_identity()
    
    # Add extensive debugging
    print(f"\n--- GET QUIZ REQUEST ---")
    print(f"Quiz ID: {quiz_id}")
    print(f"User ID: {user_id}")
    
    if not ObjectId.is_valid(quiz_id):
        print(f"Invalid quiz ID format: {quiz_id}")
        return jsonify({"error": "Invalid quiz ID"}), 400
    
    # Convert user_id to string if it's an ObjectId
    if isinstance(user_id, ObjectId):
        user_id = str(user_id)
    
    # Try to find the quiz
    quiz = db.quizzes.find_one({
        "_id": ObjectId(quiz_id),
        "user_id": user_id
    })
    
    if not quiz:
        print(f"Quiz not found for ID: {quiz_id}")
        
        # Check if quiz exists for any user to identify the issue
        any_quiz = db.quizzes.find_one({"_id": ObjectId(quiz_id)})
        if any_quiz:
            print(f"Quiz exists but belongs to user: {any_quiz['user_id']}")
        else:
            print(f"Quiz doesn't exist in database at all")
            
        return jsonify({"error": "Quiz not found"}), 404
    
    # Get material info
    material = None
    if ObjectId.is_valid(quiz['material_id']):
        material = db.study_materials.find_one({"_id": ObjectId(quiz['material_id'])})
    
    # Get attempt count
    attempt_count = db.quiz_attempts.count_documents({"quiz_id": str(quiz['_id']), "user_id": user_id})
    
    # Convert ObjectId to string and format dates
    quiz['_id'] = str(quiz['_id'])
    quiz['material_id'] = str(quiz['material_id'])
    quiz['created_at'] = quiz['created_at'].isoformat()
    quiz['updated_at'] = quiz['updated_at'].isoformat()
    
    # Add extra info
    quiz['material_title'] = material['title'] if material else "Unknown"
    quiz['attempt_count'] = attempt_count
    
    print(f"Quiz found and returned successfully")
    return jsonify(quiz), 200

@quiz_bp.route('/<quiz_id>', methods=['DELETE'])
@jwt_required()
def delete_quiz(quiz_id):
    """Delete a quiz"""
    user_id = get_jwt_identity()
    
    if not ObjectId.is_valid(quiz_id):
        return jsonify({"error": "Invalid quiz ID"}), 400
    
    result = db.quizzes.delete_one({
        "_id": ObjectId(quiz_id),
        "user_id": user_id
    })
    
    if result.deleted_count == 0:
        return jsonify({"error": "Quiz not found or not owned by user"}), 404
    
    # Also delete any quiz attempts
    db.quiz_attempts.delete_many({"quiz_id": quiz_id, "user_id": user_id})
    
    return jsonify({"message": "Quiz deleted successfully"}), 200

@quiz_bp.route('/<quiz_id>/attempt', methods=['OPTIONS'])
def quiz_attempt_options(quiz_id):
    """Handle OPTIONS request for quiz attempt endpoint"""
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

@quiz_bp.route('/<quiz_id>/attempt', methods=['POST'])
@jwt_required()
def submit_quiz_attempt(quiz_id):
    """Submit a quiz attempt"""
    print(f"\n--- SUBMIT QUIZ ATTEMPT ---")
    print(f"Quiz ID: {quiz_id}")
    print(f"Headers: {dict(request.headers)}")
    
    try:
        user_id = get_jwt_identity()
        print(f"User ID from JWT: {user_id}")
        
        data = request.get_json()
        print(f"Request data: {data}")
        
        # Check if data contains answers
        if not data or 'answers' not in data:
            print("Error: Missing answers in request")
            return jsonify({"error": "Quiz answers are required"}), 400
        
        answers = data['answers']
        print(f"Answers received: {answers}")
        
        # Validate quiz ID
        if not ObjectId.is_valid(quiz_id):
            return jsonify({"error": "Invalid quiz ID"}), 400
            
        # Get the quiz
        quiz = db.quizzes.find_one({
            "_id": ObjectId(quiz_id),
            "user_id": user_id
        })
        
        if not quiz:
            return jsonify({"error": "Quiz not found"}), 404
        
        # Grade the quiz
        score = 0
        results = []
        
        for i, question in enumerate(quiz['questions']):
            question_id = str(i)  # Use index as question ID
            user_answer = answers.get(question_id)
            
            # If question wasn't answered
            if user_answer is None:
                results.append({
                    "question_id": i,
                    "correct": False,
                    "correct_answer": question['correct_answer'],
                    "explanation": question['explanation']
                })
                continue
            
            # Check if answer is correct
            is_correct = False
            
            if question['type'] == 'multiple_choice':
                is_correct = user_answer == question['correct_answer']
            elif question['type'] == 'true_false':
                # Handle possible string/boolean conversion issues
                if isinstance(user_answer, str):
                    is_correct = (user_answer.lower() == 'true' and question['correct_answer'] is True) or \
                                (user_answer.lower() == 'false' and question['correct_answer'] is False)
                else:
                    is_correct = user_answer == question['correct_answer']
            elif question['type'] == 'short_answer':
                # Simple exact match for short answers
                if isinstance(user_answer, str) and isinstance(question['correct_answer'], str):
                    is_correct = user_answer.lower() == question['correct_answer'].lower()
                else:
                    is_correct = user_answer == question['correct_answer']
            
            if is_correct:
                score += 1
            
            results.append({
                "question_id": i,
                "correct": is_correct,
                "correct_answer": question['correct_answer'],
                "explanation": question['explanation']
            })
        
        # Calculate percentage
        total_questions = len(quiz['questions'])
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0
        
        # Save attempt to database
        attempt = {
            "quiz_id": quiz_id,  # Store as string
            "user_id": user_id,
            "quiz_title": quiz['title'],
            "answers": answers,
            "score": score,
            "total_questions": total_questions,
            "percentage": percentage,
            "results": results,
            "created_at": datetime.now()
        }
        
        attempt_id = db.quiz_attempts.insert_one(attempt).inserted_id
        print(f"Attempt saved with ID: {attempt_id}")
        
        # Add CORS headers to response
        response = jsonify({
            "message": "Quiz attempt submitted successfully",
            "attempt_id": str(attempt_id),
            "score": score,
            "total_questions": total_questions,
            "percentage": percentage,
            "results": results
        })
        
        return response, 201
        
    except Exception as e:
        print(f"Error in submit_quiz_attempt: {str(e)}")
        return jsonify({"error": f"Failed to submit quiz: {str(e)}"}), 500

@quiz_bp.route('/attempts', methods=['OPTIONS'])
def quiz_attempts_options():
    """Handle OPTIONS request for quiz attempts endpoint"""
    response = jsonify({'status': 'ok'})
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
    return response

@quiz_bp.route('/attempts', methods=['GET'])
@jwt_required()
def get_user_attempts():
    """Get all quiz attempts for the current user with pagination and filtering"""
    user_id = get_jwt_identity()
    
    # Pagination parameters
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    skip = (page - 1) * limit
    
    # Filtering parameters
    search_query = request.args.get('search', '')
    quiz_id = request.args.get('quiz', '')
    
    # Date range filtering
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    # Create filter
    query_filter = {"user_id": user_id}
    
    # Add search filter if provided (search by quiz title)
    if search_query:
        query_filter["quiz_title"] = {"$regex": search_query, "$options": "i"}
    
    # Add quiz filter if provided
    if quiz_id:
        query_filter["quiz_id"] = quiz_id
    
    # Add date range filter if provided
    date_filter = {}
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            date_filter["$gte"] = start_datetime
        except ValueError:
            pass
    
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            date_filter["$lte"] = end_datetime
        except ValueError:
            pass
    
    if date_filter:
        query_filter["created_at"] = date_filter
    
    # Count total for pagination
    total_attempts = db.quiz_attempts.count_documents(query_filter)
    
    # Get attempts with pagination
    attempts = list(db.quiz_attempts.find(query_filter).sort("created_at", -1).skip(skip).limit(limit))
    
    # Convert ObjectId to string for JSON serialization
    for attempt in attempts:
        attempt['_id'] = str(attempt['_id'])
        
        # Format dates
        if 'created_at' in attempt:
            attempt['created_at'] = attempt['created_at'].isoformat()
        
        # Simplify response by removing detailed results
        if 'results' in attempt:
            del attempt['results']
        
        if 'answers' in attempt:
            del attempt['answers']
    
    return jsonify({
        "attempts": attempts,
        "pagination": {
            "total": total_attempts,
            "page": page,
            "limit": limit,
            "pages": (total_attempts + limit - 1) // limit
        }
    }), 200

@quiz_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_quiz_dashboard():
    """Get quiz dashboard data for the current user"""
    user_id = get_jwt_identity()
    
    print(f"\n--- GET QUIZ DASHBOARD ---")
    print(f"User ID: {user_id}")
    
    try:
        # Get all attempts for the user (limit to last 5 for dashboard)
        attempts = list(db.quiz_attempts.find({"user_id": user_id}).sort("created_at", -1).limit(5))
        
        # Get total counts for stats
        total_attempts = db.quiz_attempts.count_documents({"user_id": user_id})
        total_quizzes = db.quizzes.count_documents({"user_id": user_id})
        
        # Get actual material count
        total_materials = db.study_materials.count_documents({"user_id": user_id})
        
        # Calculate average score
        if total_attempts > 0:
            avg_pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": None, "avgScore": {"$avg": "$percentage"}}}
            ]
            avg_result = list(db.quiz_attempts.aggregate(avg_pipeline))
            avg_score = round(avg_result[0]['avgScore'], 2) if avg_result else 0
        else:
            avg_score = 0
        
        # Format attempts for display
        formatted_attempts = []
        for attempt in attempts:
            # Convert ObjectId to string
            attempt['_id'] = str(attempt['_id'])
            
            # Format date
            if 'created_at' in attempt:
                attempt['created_at'] = attempt['created_at'].isoformat()
            
            # Remove detailed results to make the response lighter
            if 'results' in attempt:
                del attempt['results']
            
            if 'answers' in attempt:
                del attempt['answers']
            
            formatted_attempts.append(attempt)
        
        # Get recent quizzes (limit to last 3)
        recent_quizzes = list(db.quizzes.find({"user_id": user_id}).sort("created_at", -1).limit(3))
        formatted_quizzes = []
        
        for quiz in recent_quizzes:
            formatted_quizzes.append({
                "id": str(quiz['_id']),
                "title": quiz['title'],
                "description": quiz.get('description', ''),
                "num_questions": len(quiz.get('questions', [])),
                "created_at": quiz['created_at'].isoformat()
            })
        
        # Get recent materials (limit to last 3)
        recent_materials = list(db.study_materials.find({"user_id": user_id}).sort("created_at", -1).limit(3))
        formatted_materials = []
        
        for material in recent_materials:
            formatted_materials.append({
                "id": str(material['_id']),
                "title": material['title'],
                "description": material.get('description', ''),
                "created_at": material['created_at'].isoformat()
            })
        
        response = {
            "attempts": formatted_attempts,
            "recentQuizzes": formatted_quizzes,
            "recentMaterials": formatted_materials,
            "stats": {
                "total_attempts": total_attempts,
                "total_quizzes": total_quizzes,
                "total_materials": total_materials,
                "average_score": avg_score
            }
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        print(f"Error in get_quiz_dashboard: {str(e)}")
        return jsonify({"error": f"Failed to retrieve dashboard data: {str(e)}"}), 500

@quiz_bp.route('/attempts/<quiz_id>', methods=['GET'])
@jwt_required()
def get_quiz_attempts(quiz_id):
    """Get all attempts for a specific quiz with pagination"""
    user_id = get_jwt_identity()
    
    # Pagination parameters
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    skip = (page - 1) * limit
    
    # Create filter
    query_filter = {
        "quiz_id": quiz_id,
        "user_id": user_id
    }
    
    # Count total for pagination
    total_attempts = db.quiz_attempts.count_documents(query_filter)
    
    # Get attempts with pagination
    attempts = list(db.quiz_attempts.find(query_filter).sort("created_at", -1).skip(skip).limit(limit))
    
    # Convert ObjectId to string for JSON serialization
    for attempt in attempts:
        attempt['_id'] = str(attempt['_id'])
        
        # Format date
        if 'created_at' in attempt:
            attempt['created_at'] = attempt['created_at'].isoformat()
    
    return jsonify({
        "attempts": attempts,
        "pagination": {
            "total": total_attempts,
            "page": page,
            "limit": limit,
            "pages": (total_attempts + limit - 1) // limit
        }
    }), 200