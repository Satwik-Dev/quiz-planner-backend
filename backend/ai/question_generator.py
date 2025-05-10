import os
import json
import re
import random
import requests
from config import Config
from datetime import datetime

class QuestionGenerator:
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            print("Warning: GEMINI_API_KEY not configured. Only fallback questions will be available.")
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{Config.GEMINI_MODEL}:generateContent?key={Config.GEMINI_API_KEY}"
        self.headers = {'Content-Type': 'application/json'}
        print(f"QuestionGenerator initialized with model: {Config.GEMINI_MODEL}")

    def extract_key_concepts(self, text, num_concepts=10):
        """Extract key concepts from text using simple frequency analysis"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        
        stopwords = {'the', 'a', 'an', 'and', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 
                    'is', 'are', 'am', 'was', 'were', 'be', 'been', 'being', 'by', 'that', 
                    'this', 'these', 'those', 'it', 'its', 'as', 'from', 'has', 'have', 
                    'had', 'not', 'or', 'but', 'if', 'then', 'else', 'when', 'where', 'how'}
        
        filtered_words = [word for word in words if word not in stopwords and len(word) > 3]
        word_counts = {}
        
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:num_concepts]]

    def generate_questions(self, content, num_questions=5, question_types=None):
        """Generate quiz questions using Gemini API with fallback mechanism"""
        if question_types is None:
            question_types = ["multiple_choice", "true_false", "short_answer"]
        
        # Try Gemini API first if key is available
        if Config.GEMINI_API_KEY:
            try:
                questions = self._generate_with_gemini(content, num_questions, question_types)
                if questions and len(questions) >= num_questions:
                    return questions[:num_questions]
            except Exception as e:
                print(f"Gemini API failed: {str(e)}")
        
        # Fallback to rule-based generation
        print("Using fallback question generation")
        key_concepts = self.extract_key_concepts(content)
        return self._generate_fallback_questions(key_concepts, num_questions, question_types)

    def _generate_with_gemini(self, content, num_questions, question_types):
        """Generate questions using Gemini API"""
        prompt = f"""
        Generate exactly {num_questions} quiz questions based on the following content.
        Include these question types: {', '.join(question_types)}.
        Return ONLY a JSON array with this exact structure:
        
        [
            {{
                "type": "multiple_choice",
                "question": "Question text here",
                "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
                "correct_answer": "Option 1",
                "explanation": "Explanation why this is correct"
            }},
            {{
                "type": "true_false",
                "question": "Statement here",
                "correct_answer": true,
                "explanation": "Explanation here"
            }},
            {{
                "type": "short_answer",
                "question": "Question here",
                "correct_answer": "Expected answer",
                "explanation": "Explanation here"
            }}
        ]
        
        CONTENT TO BASE QUESTIONS ON:
        {content[:3000]}
        """
        
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.9,
                "topK": 40,
                "maxOutputTokens": 2048
            }
        }

        response = requests.post(self.api_url, headers=self.headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' not in result:
            raise ValueError("Invalid response format from Gemini API")
        
        generated_text = result['candidates'][0]['content']['parts'][0]['text']
        
        # Extract JSON from the response
        try:
            start = generated_text.find('[')
            end = generated_text.rfind(']') + 1
            json_str = generated_text[start:end]
            questions = json.loads(json_str)
            
            # Validate question format
            for q in questions:
                if not all(k in q for k in ['type', 'question', 'correct_answer', 'explanation']):
                    raise ValueError("Invalid question format in API response")
                if q['type'] == 'multiple_choice' and 'options' not in q:
                    raise ValueError("Missing options in multiple choice question")
            
            return questions
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse Gemini response: {str(e)}")
            raise

    def _generate_fallback_questions(self, key_concepts, num_questions, question_types):
        """Generate fallback questions when API fails"""
        questions = []
        
        if len(key_concepts) < 4:
            key_concepts = key_concepts * 4  # Duplicate if not enough concepts
        
        for i in range(num_questions):
            q_type = question_types[i % len(question_types)]
            concept = key_concepts[i % len(key_concepts)]
            
            if q_type == "multiple_choice":
                options = [concept]
                for j in range(3):
                    distractor_idx = (i + j + 1) % len(key_concepts)
                    options.append(key_concepts[distractor_idx])
                random.shuffle(options)
                
                questions.append({
                    "type": "multiple_choice",
                    "question": f"Which of these is most relevant to the study material?",
                    "options": options,
                    "correct_answer": concept,
                    "explanation": f"{concept} was identified as a key concept in the material."
                })
                
            elif q_type == "true_false":
                questions.append({
                    "type": "true_false",
                    "question": f"The concept '{concept}' is important in this context.",
                    "correct_answer": True,
                    "explanation": f"The material specifically mentions '{concept}' as important."
                })
                
            else:  # short_answer
                questions.append({
                    "type": "short_answer",
                    "question": f"Explain the significance of '{concept}' in this context.",
                    "correct_answer": f"{concept} is a key concept that...",
                    "explanation": f"A good answer would explain how {concept} relates to the main topic."
                })
        
        return questions