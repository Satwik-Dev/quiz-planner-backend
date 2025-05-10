import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = "http://localhost:5000/api"
TEST_USER = {
    "email": "testuser@example.com",
    "password": "testpassword123",
    "name": "Test User"
}
SAMPLE_MATERIAL = {
    "title": "Python Programming Basics",
    "content": """Python is an interpreted, high-level programming language. It supports multiple programming paradigms including:
    - Procedural programming
    - Object-oriented programming
    - Functional programming
    
    Key features:
    - Dynamic typing
    - Automatic memory management
    - Large standard library""",
    "description": "Introduction to Python programming language",
    "tags": ["python", "programming"]
}

def print_response(response, description):
    print(f"\n{description}")
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

def get_auth_header(token):
    return {"Authorization": f"Bearer {token}"}

def display_quiz_questions(quiz_data):
    """Display quiz questions in a readable format"""
    print("\n" + "="*50)
    print(f"QUIZ DETAILS")
    print("="*50)
    print(f"Title: {quiz_data.get('title', 'Untitled Quiz')}")
    print(f"Description: {quiz_data.get('description', 'No description')}")
    print(f"Total Questions: {len(quiz_data.get('questions', []))}")
    print(f"Created At: {quiz_data.get('created_at', 'Unknown date')}")
    print("\n" + "="*50)
    print("QUESTIONS:")
    print("="*50)
    
    for i, question in enumerate(quiz_data.get('questions', []), 1):
        print(f"\nQuestion {i} ({question.get('type', 'unknown').upper()})")
        print("-"*50)
        print(f"{question.get('question', 'No question text')}\n")
        
        if question.get('type') == 'multiple_choice':
            print("Options:")
            for j, option in enumerate(question.get('options', []), 1):
                prefix = "✓" if option == question.get('correct_answer') else " "
                print(f"  {prefix} {j}. {option}")
        elif question.get('type') == 'true_false':
            answer = "True" if question.get('correct_answer') else "False"
            print(f"Correct Answer: {answer}")
        else:  # short_answer or other types
            print(f"Expected Answer: {question.get('correct_answer', 'No answer provided')}")
        
        print(f"\nExplanation: {question.get('explanation', 'No explanation provided')}")
        print("-"*50)

def test_auth_flow():
    print("=== TESTING AUTH FLOW ===")
    
    # Cleanup existing test user
    requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEST_USER["email"],
        "password": TEST_USER["password"]
    })
    
    # Register
    print("\n1. Registering test user")
    reg_resp = requests.post(f"{BASE_URL}/auth/register", json=TEST_USER)
    print_response(reg_resp, "Registration Response")
    
    # Login
    print("\n2. Logging in test user")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEST_USER["email"],
        "password": TEST_USER["password"]
    })
    print_response(login_resp, "Login Response")
    
    if login_resp.status_code != 200:
        print("Login failed, aborting tests")
        return None
    
    token = login_resp.json()["access_token"]
    
    # Get user info
    print("\n3. Getting current user info")
    me_resp = requests.get(f"{BASE_URL}/auth/me", headers=get_auth_header(token))
    print_response(me_resp, "Current User Response")
    
    return token

def test_material_flow(token):
    print("\n=== TESTING MATERIAL FLOW ===")
    
    # Create material
    print("\n1. Creating study material")
    create_resp = requests.post(
        f"{BASE_URL}/materials",
        headers=get_auth_header(token),
        json=SAMPLE_MATERIAL
    )
    print_response(create_resp, "Create Material Response")
    
    if create_resp.status_code != 201:
        print("Material creation failed, aborting tests")
        return None
    
    material_id = create_resp.json()["material"]["id"]
    
    # Get all materials
    print("\n2. Getting all materials")
    get_all_resp = requests.get(
        f"{BASE_URL}/materials",
        headers=get_auth_header(token)
    )
    print_response(get_all_resp, "All Materials Response")
    
    # Get single material
    print("\n3. Getting single material")
    get_one_resp = requests.get(
        f"{BASE_URL}/materials/{material_id}",
        headers=get_auth_header(token)
    )
    print_response(get_one_resp, "Single Material Response")
    
    return material_id

def test_quiz_flow(token, material_id):
    print("\n=== TESTING QUIZ FLOW ===")
    
    # Generate quiz
    print("\n1. Generating quiz from material")
    quiz_resp = requests.post(
        f"{BASE_URL}/quizzes/generate",
        headers=get_auth_header(token),
        json={
            "material_id": material_id,
            "num_questions": 3,
            "question_types": ["multiple_choice", "true_false", "short_answer"]
        }
    )
    print_response(quiz_resp, "Quiz Generation Response")
    
    if quiz_resp.status_code != 201:
        print("Quiz generation failed")
        return None
    
    quiz_id = quiz_resp.json()["quiz_id"]
    
    # Get quiz details
    print("\n2. Fetching quiz details")
    quiz_details_resp = requests.get(
        f"{BASE_URL}/quizzes/{quiz_id}",
        headers=get_auth_header(token)
    )
    print_response(quiz_details_resp, "Quiz Details Response")
    
    if quiz_details_resp.status_code == 200:
        display_quiz_questions(quiz_details_resp.json())
    
    return quiz_id

def main():
    print("=== STARTING BACKEND TEST FLOW ===")
    
    # Test authentication
    token = test_auth_flow()
    if not token:
        return
    
    # Test materials
    material_id = test_material_flow(token)
    if not material_id:
        return
    
    # Test quiz generation
    quiz_id = test_quiz_flow(token, material_id)
    
    print("\n=== TESTING COMPLETE ===")
    if quiz_id:
        print("All tests passed successfully!")
    else:
        print("Tests completed with some failures")

if __name__ == "__main__":
    main()