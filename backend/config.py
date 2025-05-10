# backend/config.py
import os
from datetime import timedelta

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # MongoDB settings
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/quiz_planner')
    
    # JWT settings
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Gemini settings
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')
    
    # CORS settings
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:3000')