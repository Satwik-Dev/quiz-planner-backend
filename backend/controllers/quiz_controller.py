import os
import sys
from pathlib import Path
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson.objectid import ObjectId
import pymongo
from datetime import datetime
from config import Config
import logging

logger = logging.getLogger(__name__)

# Initialize blueprint
quiz_bp = Blueprint('quiz', __name__)

# MongoDB connection
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
    logger.info("QuestionGenerator initialized successfully")
except Exception as e:
    logger.error(f"Error initializing QuestionGenerator: {e}")
    question_generator = None

def get_user_filter(user_id):
    """Create a filter that handles both string and ObjectId user_id formats"""
    user_id_str = str(user_id)
    return {"$or": [
        {"user_id": user_id_str},
        {"user_id": ObjectId(user_id_str) if ObjectId.is_valid(user_id_str) else None}
    ]}

@quiz_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_quiz():
    """Generate a quiz from study material"""
    if not question_generator:
        return jsonify({"error": "Question generator not available"}), 500
    
    user_id = get_jwt_identity()
    user_id_str = str(user_id)  # Always store as string
    
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
    user_filter = get_user_filter(user_id)
    material = db.study_materials.find_one({
        "_id": ObjectId(material_id),
        "$or": user_filter["$or"]
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
        
        # Create quiz document with string user_id and material_id
        quiz = {
            "title": data.get('title', f"Quiz on {material['title']}"),
            "description": data.get('description', f"Generated quiz based on {material['title']}"),
            "questions": questions,
            "user_id": user_id_str,  # Store as string
            "material_id": str(material_id),  # Store as string
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        quiz_id = db.quizzes.insert_one(quiz).inserted_id
        
        logger.info(f"Generated quiz {quiz_id} for user {user_id_str}")
        
        return jsonify({
            "message": "Quiz generated successfully",
            "quiz_id": str(quiz_id),
            "title": quiz["title"],
            "num_questions": len(questions)
        }), 201
    
    except Exception as e:
        logger.error(f"Failed to generate quiz: {str(e)}")
        return jsonify({"error": f"Failed to generate quiz: {str(e)}"}), 500

@quiz_bp.route('/', methods=['GET'])
@jwt_required()
def get_all_quizzes():
    """Get all quizzes for current user with pagination and filtering"""
    user_id = get_jwt_identity()
    user_filter = get_user_filter(user_id)
    
    # Pagination parameters
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    skip = (page - 1) * limit
    
    # Filtering parameters
    search_query = request.args.get('search', '')
    material_id = request.args.get('material', '')
    
    # Build query filter
    query_filter = user_filter.copy()
    
    # Add search filter if provided
    if search_query:
        query_filter["$and"] = [
            {"$or": query_filter["$or"]},
            {"$or": [
                {"title": {"$regex": search_query, "$options": "i"}},
                {"description": {"$regex": search_query, "$options": "i"}}
            ]}
        ]
        del query_filter["$or"]
    
    # Add material filter if provided
    if material_id and ObjectId.is_valid(material_id):
        if "$and" in query_filter:
            query_filter["$and"].append({"material_id": material_id})
        else:
            query_filter["$and"] = [
                {"$or": query_filter["$or"]},
                {"material_id": material_id}
            ]
            del query_filter["$or"]
    
    # Count total for pagination
    total_quizzes = db.quizzes.count_documents(query_filter)
    
    # Get quizzes with pagination
    quizzes = list(db.quizzes.find(query_filter).sort("created_at", -1).skip(skip).limit(limit))
    
    # Convert ObjectId to string and format response
    formatted_quizzes = []
    for quiz in quizzes:
        # Get related material info
        material = None
        if quiz.get('material_id'):
            material = db.study_materials.find_one({"_id": ObjectId(quiz['material_id'])})
        
        # Get attempt count
        attempt_filter = user_filter.copy()
        attempt_filter["quiz_id"] = str(quiz['_id'])
        attempt_count = db.quiz_attempts.count_documents(attempt_filter)
        
        formatted_quizzes.append({
            "id": str(quiz['_id']),
            "title": quiz.get('title', 'Untitled'),
            "description": quiz.get('description', ''),
            "num_questions": len(quiz.get('questions', [])),
            "created_at": quiz.get('created_at', datetime.now()).isoformat(),
            "material_id": str(quiz.get('material_id', '')),
            "material_title": material.get('title', 'Unknown') if material else "Unknown",
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
    user_filter = get_user_filter(user_id)
    
    logger.info(f"Getting quiz {quiz_id} for user {user_id}")
    
    if not ObjectId.is_valid(quiz_id):
        logger.warning(f"Invalid quiz ID format: {quiz_id}")
        return jsonify({"error": "Invalid quiz ID"}), 400
    
    # Find the quiz
    quiz = db.quizzes.find_one({
        "_id": ObjectId(quiz_id),
        "$or": user_filter["$or"]
    })
    
    if not quiz:
        logger.warning(f"Quiz {quiz_id} not found for user {user_id}")
        return jsonify({"error": "Quiz not found"}), 404
    
    # Get material info
    material = None
    if quiz.get('material_id'):
        material = db.study_materials.find_one({"_id": ObjectId(quiz['material_id'])})
    
    # Get attempt count
    attempt_filter = user_filter.copy()
    attempt_filter["quiz_id"] = str(quiz['_id'])
    attempt_count = db.quiz_attempts.count_documents(attempt_filter)
    
    # Convert ObjectId to string and format dates
    quiz['_id'] = str(quiz['_id'])
    quiz['material_id'] = str(quiz.get('material_id', ''))
    quiz['created_at'] = quiz.get('created_at', datetime.now()).isoformat()
    quiz['updated_at'] = quiz.get('updated_at', datetime.now()).isoformat()
    
    # Add extra info
    quiz['material_title'] = material.get('title', 'Unknown') if material else "Unknown"
    quiz['attempt_count'] = attempt_count
    
    return jsonify(quiz), 200

@quiz_bp.route('/<quiz_id>/attempt', methods=['OPTIONS'])
def quiz_attempt_options(quiz_id):
    """Handle OPTIONS request for quiz attempt endpoint"""
    response = jsonify({'status': 'ok'})
    return response

@quiz_bp.route('/<quiz_id>/attempt', methods=['POST'])
@jwt_required()
def submit_quiz_attempt(quiz_id):
    """Submit a quiz attempt"""
    logger.info(f"Quiz attempt submission for quiz {quiz_id}")
    
    try:
        user_id = get_jwt_identity()
        user_id_str = str(user_id)
        user_filter = get_user_filter(user_id)
        
        data = request.get_json()
        
        # Check if data contains answers
        if not data or 'answers' not in data:
            return jsonify({"error": "Quiz answers are required"}), 400
        
        answers = data['answers']
        
        # Validate quiz ID
        if not ObjectId.is_valid(quiz_id):
            return jsonify({"error": "Invalid quiz ID"}), 400
            
        # Get the quiz
        quiz = db.quizzes.find_one({
            "_id": ObjectId(quiz_id),
            "$or": user_filter["$or"]
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
                    "explanation": question.get('explanation', '')
                })
                continue
            
            # Check if answer is correct
            is_correct = False
            
            if question['type'] == 'multiple_choice':
                is_correct = user_answer == question['correct_answer']
            elif question['type'] == 'true_false':
                # Handle boolean conversion properly
                if isinstance(user_answer, str):
                    user_answer_bool = user_answer.lower() == 'true'
                else:
                    user_answer_bool = bool(user_answer)
                
                correct_answer_bool = question['correct_answer']
                if isinstance(correct_answer_bool, str):
                    correct_answer_bool = correct_answer_bool.lower() == 'true'
                    
                is_correct = user_answer_bool == correct_answer_bool
            elif question['type'] == 'short_answer':
                # Simple exact match for short answers (case-insensitive)
                if isinstance(user_answer, str) and isinstance(question['correct_answer'], str):
                    is_correct = user_answer.lower().strip() == question['correct_answer'].lower().strip()
                else:
                    is_correct = user_answer == question['correct_answer']
            
            if is_correct:
                score += 1
            
            results.append({
                "question_id": i,
                "correct": is_correct,
                "correct_answer": question['correct_answer'],
                "explanation": question.get('explanation', '')
            })
        
        # Calculate percentage
        total_questions = len(quiz['questions'])
        percentage = (score / total_questions) * 100 if total_questions > 0 else 0
        
        # Save attempt to database with string user_id
        attempt = {
            "quiz_id": str(quiz_id),  # Store as string
            "user_id": user_id_str,  # Store as string
            "quiz_title": quiz.get('title', 'Untitled Quiz'),
            "answers": answers,
            "score": score,
            "total_questions": total_questions,
            "percentage": percentage,
            "results": results,
            "created_at": datetime.now()
        }
        
        attempt_id = db.quiz_attempts.insert_one(attempt).inserted_id
        logger.info(f"Quiz attempt {attempt_id} submitted for user {user_id_str}")
        
        return jsonify({
            "message": "Quiz attempt submitted successfully",
            "attempt_id": str(attempt_id),
            "score": score,
            "total_questions": total_questions,
            "percentage": percentage,
            "results": results
        }), 201
        
    except Exception as e:
        logger.error(f"Error in submit_quiz_attempt: {str(e)}")
        return jsonify({"error": f"Failed to submit quiz: {str(e)}"}), 500

@quiz_bp.route('/attempts', methods=['OPTIONS'])
def quiz_attempts_options():
    """Handle OPTIONS request for quiz attempts endpoint"""
    response = jsonify({'status': 'ok'})
    return response

@quiz_bp.route('/attempts', methods=['GET'])
@jwt_required()
def get_user_attempts():
    """Get all quiz attempts for the current user with pagination and filtering"""
    user_id = get_jwt_identity()
    user_filter = get_user_filter(user_id)
    
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
    
    # Build query filter
    query_filter = user_filter.copy()
    
    # Add search filter if provided
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
    user_filter = get_user_filter(user_id)
    
    logger.info(f"Getting dashboard for user {user_id}")
    
    try:
        # Get total counts for stats
        total_materials = db.study_materials.count_documents(user_filter)
        total_quizzes = db.quizzes.count_documents(user_filter)
        total_attempts = db.quiz_attempts.count_documents(user_filter)
        
        logger.info(f"Dashboard stats - Materials: {total_materials}, Quizzes: {total_quizzes}, Attempts: {total_attempts}")
        
        # Calculate average score
        avg_score = 0
        if total_attempts > 0:
            avg_pipeline = [
                {"$match": user_filter},
                {"$group": {"_id": None, "avgScore": {"$avg": "$percentage"}}}
            ]
            avg_result = list(db.quiz_attempts.aggregate(avg_pipeline))
            avg_score = round(avg_result[0]['avgScore'], 2) if avg_result and avg_result[0].get('avgScore') else 0
        
        # Get recent materials
        formatted_materials = []
        recent_materials = list(db.study_materials.find(user_filter).sort("created_at", -1).limit(3))
        for material in recent_materials:
            formatted_materials.append({
                "id": str(material['_id']),
                "title": material.get('title', 'Untitled'),
                "description": material.get('description', ''),
                "created_at": material.get('created_at', datetime.now()).isoformat()
            })
        
        # Get recent quizzes
        formatted_quizzes = []
        recent_quizzes = list(db.quizzes.find(user_filter).sort("created_at", -1).limit(3))
        for quiz in recent_quizzes:
            formatted_quizzes.append({
                "id": str(quiz['_id']),
                "title": quiz.get('title', 'Untitled Quiz'),
                "description": quiz.get('description', ''),
                "num_questions": len(quiz.get('questions', [])),
                "created_at": quiz.get('created_at', datetime.now()).isoformat()
            })
        
        # Get recent attempts
        formatted_attempts = []
        attempts = list(db.quiz_attempts.find(user_filter).sort("created_at", -1).limit(5))
        for attempt in attempts:
            formatted_attempts.append({
                "_id": str(attempt['_id']),
                "quiz_id": attempt.get('quiz_id', ''),
                "quiz_title": attempt.get('quiz_title', 'Unknown Quiz'),
                "score": attempt.get('score', 0),
                "total_questions": attempt.get('total_questions', 0),
                "percentage": attempt.get('percentage', 0),
                "created_at": attempt.get('created_at', datetime.now()).isoformat()
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
        logger.error(f"Error in get_quiz_dashboard: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to retrieve dashboard data: {str(e)}"}), 500

@quiz_bp.route('/attempts/<quiz_id>', methods=['GET'])
@jwt_required()
def get_quiz_attempts(quiz_id):
    """Get all attempts for a specific quiz with pagination"""
    user_id = get_jwt_identity()
    user_filter = get_user_filter(user_id)
    
    # Pagination parameters
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    skip = (page - 1) * limit
    
    # Create filter combining user filter and quiz_id
    query_filter = user_filter.copy()
    query_filter["quiz_id"] = quiz_id
    
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

@quiz_bp.route('/<quiz_id>', methods=['DELETE'])
@jwt_required()
def delete_quiz(quiz_id):
    """Delete a quiz"""
    user_id = get_jwt_identity()
    user_filter = get_user_filter(user_id)
    
    if not ObjectId.is_valid(quiz_id):
        return jsonify({"error": "Invalid quiz ID"}), 400
    
    quiz_filter = {"_id": ObjectId(quiz_id)}
    quiz_filter.update(user_filter)
    
    result = db.quizzes.delete_one(quiz_filter)
    
    if result.deleted_count == 0:
        return jsonify({"error": "Quiz not found or not owned by user"}), 404
    
    # Also delete any quiz attempts
    db.quiz_attempts.delete_many({"quiz_id": str(quiz_id)})
    
    logger.info(f"Deleted quiz {quiz_id} and its attempts")
    
    return jsonify({"message": "Quiz deleted successfully"}), 200