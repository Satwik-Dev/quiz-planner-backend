# Quiz Planner - AI-Powered Learning Management System

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)
![React](https://img.shields.io/badge/React-19.1+-61dafb.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-6.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

An intelligent full-stack learning management system that leverages Google Gemini AI to automatically generate customized quizzes from study materials, featuring real-time grading and comprehensive analytics.

🔗 **Live Demo:** [https://quiz-planner-frontend.vercel.app](https://quiz-planner-frontend.vercel.app)

---

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)
- [License](#license)

---

## ✨ Features

### AI-Powered Quiz Generation
- 🤖 **Gemini AI Integration** - Automatic question generation from study content
- 📝 **Multiple Question Types** - Multiple Choice, True/False, Short Answer
- 🎯 **Intelligent Fallback** - NLP-based question generation when API unavailable
- ✏️ **Customizable Quizzes** - Choose number of questions and types

### Learning Management
- 📚 **Study Material Management** - Upload, organize, and tag learning content
- ⚡ **Real-time Grading** - Instant feedback with detailed explanations
- 📊 **Performance Analytics** - Track progress with comprehensive dashboards
- 🔄 **Unlimited Attempts** - Retake quizzes to improve understanding
- 🔍 **Advanced Search** - Filter quizzes by material, date, and performance

### User Experience
- 🔐 **Secure Authentication** - JWT-based user management
- 📱 **Responsive Design** - Works seamlessly on desktop and mobile
- 🎨 **Modern UI** - Clean interface built with Bootstrap
- 📈 **Visual Analytics** - Charts and statistics for learning insights

---

## 🛠 Tech Stack

### Backend
- **Framework:** Flask (Python 3.11+)
- **Database:** MongoDB Atlas
- **Authentication:** Flask-JWT-Extended
- **AI Engine:** Google Gemini API (gemini-2.0-flash)
- **Password Security:** Werkzeug (bcrypt hashing)
- **CORS:** Flask-CORS

### Frontend
- **Framework:** React 19
- **Routing:** React Router v7
- **Styling:** Bootstrap 5
- **HTTP Client:** Axios
- **State Management:** React Context API
- **Build Tool:** Create React App

### DevOps & Deployment
- **Frontend Hosting:** Vercel
- **Backend Hosting:** Render
- **Database:** MongoDB Atlas (Cloud)
- **Version Control:** Git/GitHub

---

## 🏗 Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                            │
│                React + Bootstrap (Vercel)                   │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTPS/REST API
┌───────────────────────▼─────────────────────────────────────┐
│                    API Gateway Layer                        │
│                Flask + JWT Auth (Render)                    │
└─────┬──────────────────────┬────────────────────────────────┘
      │                      │
      ▼                      ▼
┌─────────────┐    ┌──────────────────┐
│  MongoDB    │    │  Google Gemini   │
│   Atlas     │    │      API         │
│             │    │  (AI Generator)  │
└─────────────┘    └──────────────────┘
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or higher
- Node.js 18+ and npm
- MongoDB Atlas account ([Sign up](https://www.mongodb.com/cloud/atlas))
- Google Gemini API key ([Get started](https://ai.google.dev/))

### Backend Setup

1. **Clone the repository**
```bash
   git clone https://github.com/yourusername/quiz-planner.git
   cd quiz-planner/backend
```

2. **Create virtual environment**
```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
   cp .env.example .env
```

   Edit `.env` with your credentials:
```env
   GEMINI_API_KEY=your_gemini_api_key
   SECRET_KEY=your_flask_secret_key
   MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/quiz_planner
   JWT_SECRET_KEY=your_jwt_secret_key
```

5. **Run the development server**
```bash
   python app.py
```

   API will be available at: `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend directory**
```bash
   cd ../frontend
```

2. **Install dependencies**
```bash
   npm install
```

3. **Configure environment**
```bash
   # Create .env file
   echo "REACT_APP_API_URL=http://localhost:5000" > .env
```

4. **Run development server**
```bash
   npm start
```

   Frontend will be available at: `http://localhost:3000`

---

## 📚 API Documentation

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | User login (returns JWT) |
| GET | `/api/auth/me` | Get current user profile |
| PUT | `/api/auth/update` | Update user information |

### Study Materials

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/materials` | Create study material |
| GET | `/api/materials` | List all materials |
| GET | `/api/materials/:id` | Get material details |
| PUT | `/api/materials/:id` | Update material |
| DELETE | `/api/materials/:id` | Delete material |

### Quiz Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/quizzes/generate` | Generate AI quiz from material |
| GET | `/api/quizzes` | List all quizzes (paginated) |
| GET | `/api/quizzes/:id` | Get quiz with questions |
| DELETE | `/api/quizzes/:id` | Delete quiz |
| POST | `/api/quizzes/:id/attempt` | Submit quiz attempt |
| GET | `/api/quizzes/attempts` | Get attempt history |
| GET | `/api/quizzes/dashboard` | Get dashboard statistics |

---

## 🔑 Key Features Explained

### AI Question Generation

The system uses Google Gemini AI with intelligent fallback:

1. **Primary:** Gemini API generates contextual questions
2. **Fallback:** NLP-based extraction if API fails
3. **Validation:** Ensures question quality and format
```python
# Example: Generate 5 questions
POST /api/quizzes/generate
{
  "material_id": "abc123",
  "num_questions": 5,
  "question_types": ["multiple_choice", "true_false", "short_answer"]
}
```

### Real-time Grading

Automatic grading with detailed feedback:
- Multiple Choice: Exact match validation
- True/False: Boolean comparison
- Short Answer: Case-insensitive matching (can be enhanced with NLP)

### Analytics Dashboard

Track learning progress with:
- Total quizzes taken
- Average score percentage
- Attempt history with filtering
- Recent materials and quizzes

---

## 🌐 Deployment

### Frontend (Vercel)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel --prod
```

### Backend (Render)

1. Create new Web Service
2. Connect GitHub repository
3. Build command: `pip install -r requirements.txt`
4. Start command: `python app.py`
5. Add environment variables
6. Deploy

### Database (MongoDB Atlas)

1. Create cluster in MongoDB Atlas
2. Whitelist IP addresses (or use 0.0.0.0/0 for Render)
3. Get connection string
4. Add to MONGO_URI environment variable

## 🎯 Future Enhancements

- [ ] Advanced NLP for short answer grading
- [ ] Collaborative study groups
- [ ] Spaced repetition algorithm
- [ ] Video/audio content support
- [ ] Mobile app (React Native)
- [ ] Integration with LMS platforms
- [ ] Multi-language support

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Satwik Alla**
- LinkedIn: [linkedin.com/in/satwik-alla](https://linkedin.com/in/satwik-alla)
- Email: allasatwik93@gmail.com
- GitHub: [@Satwik-Dev](https://github.com/Satwik-Dev)

---

## 🙏 Acknowledgments

- [Google Gemini AI](https://ai.google.dev/) - AI question generation
- [MongoDB](https://www.mongodb.com/) - Database solution
- [Flask](https://flask.palletsprojects.com/) - Backend framework
- [React](https://react.dev/) - Frontend framework

---

## 📊 Project Stats

- **Lines of Code:** ~8,000+
- **API Endpoints:** 15+
- **Question Types Supported:** 3
- **AI Model:** Google Gemini 2.0 Flash
- **Development Time:** 4 months (Feb 2025 - May 2025)

---

**⭐ Star this repo if you find it useful!**
