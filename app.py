"""
Flask application with API routes - HIGH SPEED CONFIGURATION (Lite Model First)
"""
from flask import Flask, Response, jsonify, request
import cv2
import mediapipe as mp
import numpy as np
import time
import json
import os
import random
import string
import requests
import certifi 
from collections import deque
from datetime import datetime
from flask_cors import CORS
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit 

from ai_engine import AIEngine

# --- 0. CONFIGURATION ---
load_dotenv()

app = Flask(__name__)
# Allow CORS for all domains to prevent frontend connection issues
CORS(app, resources={r"/*": {"origins": "*"}})
bcrypt = Bcrypt(app)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# --- 1. MAIL CONFIGURATION ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)

# --- 2. DATABASE SETUP ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "physiocheck_db"

try:
    client = MongoClient(
        MONGO_URI, 
        serverSelectionTimeoutMS=5000, 
        tls=True,
        tlsCAFile=certifi.where(),       
        tlsAllowInvalidCertificates=True 
    )
    client.admin.command('ping') 
    db = client[DB_NAME]
    users_collection = db['users']
    otp_collection = db['otps']
    sessions_collection = db['sessions']
    print(f"✅ Connected to MongoDB Cloud: {DB_NAME}")
except Exception as e:
    print(f"⚠️ DB Error: {e}")
    db = None
    users_collection = None
    otp_collection = None
    sessions_collection = None

# Global session instance
workout_session = None

def init_session():
    """Initialize workout session logic"""
    global workout_session
    from workout_session import WorkoutSession
    workout_session = WorkoutSession()

def generate_video_frames():
    """Generator for video streaming & WebSocket Data Push"""
    from constants import WorkoutPhase
    
    if workout_session is None: return
    
    while workout_session.phase != WorkoutPhase.INACTIVE:
        frame, should_continue = workout_session.process_frame() 
        
        if not should_continue or frame is None:
            break
        
        socketio.emit('workout_update', workout_session.get_state_dict())
        socketio.sleep(0.01) 

        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# --- 3. SOCKET EVENTS ---

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

@socketio.on('toggle_listening')
def handle_toggle_listening(data):
    """
    Toggles the listening mode.
    data['active'] = True -> Stop Dots (Pause Analysis)
    data['active'] = False -> Resume Dots (Resume Analysis)
    """
    active = data.get('active', False)
    global workout_session
    if workout_session:
        workout_session.set_listening(active)

@socketio.on('stop_session')
def handle_stop_session(data):
    print("Received stop command via Socket")
    global workout_session
    if not workout_session: return
    
    user_email = data.get('email')
    exercise_name = data.get('exercise', 'Freestyle')
    
    try:
        report = workout_session.get_final_report()
        workout_session.stop()
        
        # [CRITICAL FIX] Check if collection exists securely for PyMongo 4+
        if user_email and sessions_collection is not None:
            right_summary = report['summary']['RIGHT']
            left_summary = report['summary']['LEFT']
            
            session_doc = {
                'email': user_email,
                'date': datetime.now().strftime("%Y-%m-%d"),
                'timestamp': time.time(),
                'exercise': exercise_name,
                'duration': report.get('duration', 0),
                'total_reps': right_summary['total_reps'] + left_summary['total_reps'],
                'right_reps': right_summary['total_reps'],
                'left_reps': left_summary['total_reps'],
                'total_errors': right_summary['error_count'] + left_summary['error_count']
            }
            sessions_collection.insert_one(session_doc)
            print(f"💾 Saved '{exercise_name}' for {user_email}")
            
        emit('session_stopped', {'status': 'success'})
    except Exception as e:
        print(f"Error stopping session: {e}")

# --- 4. HTTP ROUTES ---

@app.route('/api/auth/send-otp', methods=['POST'])
def send_otp():
    if users_collection is None: return jsonify({'error': 'Database unavailable'}), 503
    data = request.json
    email = data.get('email')
    if users_collection.find_one({'email': email}):
        return jsonify({'error': 'Email is already registered. Please login.'}), 400
    otp = ''.join(random.choices(string.digits, k=6))
    otp_collection.update_one({'email': email}, {'$set': {'otp': otp, 'created_at': time.time()}}, upsert=True)
    try:
        msg = Message('PhysioCheck Verification Code', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"Your verification code is: {otp}"
        mail.send(msg)
        return jsonify({'message': 'OTP sent successfully'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to send email.'}), 500

@app.route('/api/auth/signup-verify', methods=['POST'])
def signup_verify():
    if users_collection is None: return jsonify({'error': 'Database unavailable'}), 503
    data = request.json
    record = otp_collection.find_one({'email': data.get('email')})
    if not record or record['otp'] != data.get('otp'):
        return jsonify({'error': 'Invalid or expired OTP'}), 400
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = {'name': data['name'], 'email': data['email'], 'password': hashed_password, 'role': data.get('role', 'patient'), 'created_at': time.time(), 'auth_method': 'email'}
    users_collection.insert_one(user)
    otp_collection.delete_one({'email': data['email']}) 
    return jsonify({'message': 'User verified', 'user': {'name': user['name'], 'role': user['role']}}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    if users_collection is None: return jsonify({'error': 'Database unavailable'}), 503
    data = request.json
    user = users_collection.find_one({'email': data['email']})
    if user and bcrypt.check_password_hash(user['password'], data['password']):
        return jsonify({'message': 'Login successful', 'role': user['role'], 'name': user['name'], 'email': user['email']}), 200
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    if users_collection is None: return jsonify({'error': 'Database unavailable'}), 503
    token = request.json.get('token')
    try:
        resp = requests.get('https://www.googleapis.com/oauth2/v1/userinfo', params={'access_token': token, 'alt': 'json'})
        if not resp.ok: return jsonify({'error': 'Invalid Google Token'}), 401
        google_user = resp.json()
        email = google_user['email']
        user = users_collection.find_one({'email': email})
        if not user:
            user = {'name': google_user['name'], 'email': email, 'password': '', 'role': 'patient', 'created_at': time.time(), 'auth_method': 'google'}
            users_collection.insert_one(user)
        return jsonify({'message': 'Google login successful', 'role': user['role'], 'name': user['name'], 'email': user['email']}), 200
    except Exception as e:
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/api/user/stats', methods=['POST'])
def get_user_stats():
    if sessions_collection is None: return jsonify({'error': 'DB Error'}), 503
    email = request.json.get('email')
    user_sessions = list(sessions_collection.find({'email': email}))
    total_reps = sum(s.get('total_reps', 0) for s in user_sessions)
    accuracy = 100
    if total_reps > 0: accuracy = max(0, 100 - int((sum(s.get('total_errors', 0) for s in user_sessions) / total_reps) * 20))
    return jsonify({'total_workouts': len(user_sessions), 'total_reps': total_reps, 'accuracy': accuracy, 'graph_data': [{'date': s.get('date'), 'reps': s.get('total_reps', 0)} for s in user_sessions[-7:]]})

@app.route('/api/user/analytics_detailed', methods=['POST'])
def get_analytics_detailed():
    if sessions_collection is None: return jsonify({'error': 'DB Error'}), 503
    return jsonify(AIEngine.get_detailed_analytics(list(sessions_collection.find({'email': request.json.get('email')}).sort('timestamp', 1))))

@app.route('/api/user/ai_prediction', methods=['POST'])
def get_ai_prediction():
    if sessions_collection is None: return jsonify({'error': 'DB Error'}), 503
    sessions = list(sessions_collection.find({'email': request.json.get('email')}).sort('timestamp', 1))
    return jsonify(AIEngine.get_recovery_prediction(sessions) if sessions else {'error': 'No data'})

# --- AI COACH ROUTE (LOW LATENCY CONFIG) ---
@app.route('/api/ai_coach', methods=['POST'])
def ai_coach_chat():
    """Handles chatbot logic with DB access"""
    data = request.json
    user_query = data.get('query', '')
    context = data.get('context', {})
    
    # 1. Load Key
    raw_key = os.getenv('GEMINI_API_KEY')
    if not raw_key:
        return jsonify({'response': 'System Error: Server API Key is missing.'}), 500
    
    api_key = raw_key.strip()

    # 2. FETCH HISTORY FROM DB
    email = context.get('email')
    history_prompt = ""
    
    if email and sessions_collection is not None:
        try:
            # Stats: Total Reps, Total Sessions
            pipeline = [
                {'$match': {'email': email}},
                {'$group': {'_id': None, 'total_reps': {'$sum': '$total_reps'}, 'count': {'$sum': 1}}}
            ]
            stats = list(sessions_collection.aggregate(pipeline))
            
            # Personal Best
            best_session = sessions_collection.find_one({'email': email}, sort=[('total_reps', -1)])
            best_reps = best_session.get('total_reps', 0) if best_session else 0

            # Recent Sessions
            recent = list(sessions_collection.find({'email': email}).sort('timestamp', -1).limit(3))
            
            if stats:
                total_reps = stats[0]['total_reps']
                total_sessions = stats[0]['count']
                history_prompt = f"\nUSER DATABASE HISTORY:\n- Total Workouts: {total_sessions}\n- Total Reps: {total_reps}\n- Personal Best Reps in a Session: {best_reps}\n- Recent Activity:"
                for s in recent:
                    history_prompt += f"\n  * {s.get('date', 'N/A')}: {s.get('exercise', 'Unknown')} ({s.get('total_reps', 0)} reps)"
            else:
                history_prompt = "\nUSER DATABASE HISTORY: New user (no past sessions found)."
        except Exception as e:
            print(f"DB Fetch Error: {e}")
            history_prompt = "\nUSER DATABASE HISTORY: Error accessing records."
    
    system_prompt = f"""
    You are PhysioBot, an intelligent physiotherapy coach.
    You have access to the user's database history below.
    
    Rules:
    - If recalibration intent → return: ACTION: RECALIBRATE
    - If stop intent → return: ACTION: STOP
    - If asked about history/bests, USE THE DATABASE HISTORY provided below.
    - Otherwise respond naturally, max 20 words, motivational and exercise-aware.
    """

    full_prompt = f"""
    {system_prompt}
    {history_prompt}
    CURRENT SESSION CONTEXT: {json.dumps(context)}
    USER QUERY: {user_query}
    """
    
    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    headers = {'Content-Type': 'application/json'}

    # [OPTIMIZATION] PRIORITIZE LITE MODEL FOR SPEED
    models_to_try = [
        "gemini-2.0-flash-lite-preview-02-05", # FASTEST (New Lite Model)
        "gemini-flash-lite-latest",             # FAST BACKUP
        "gemini-2.5-flash",                     # SMART BACKUP
    ]

    for model_name in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            
            print(f"🤖 Connecting to {model_name}...")
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                ai_text = response.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'Thinking...').strip()
                print(f"✅ Success with {model_name}")
                return jsonify({'response': ai_text})
            
            elif response.status_code == 404:
                # Silently skip if model not found
                continue
            else:
                print(f"❌ {model_name} Error {response.status_code}: {response.text}")
                continue

        except Exception as e:
            print(f"💥 Exception with {model_name}: {e}")
            continue

    print("🛑 ALL MODELS FAILED.")
    return jsonify({'response': "I cannot access my brain right now. Please check server logs."})

# --- WORKOUT ROUTES ---

@app.route('/start_tracking')
def start_tracking():
    global workout_session
    if workout_session:
        try: workout_session.stop()
        except: pass
    try:
        init_session()
        workout_session.start()
        return jsonify({'status': 'success', 'message': 'Session started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to start: {e}'}), 500

@app.route('/stop_tracking', methods=['POST'])
def stop_tracking_http():
    global workout_session
    if not workout_session: return jsonify({'status': 'inactive'})
    try:
        workout_session.stop()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error'}), 500

@app.route('/video_feed')
def video_feed():
    return Response(generate_video_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/report_data')
def report_data():
    if workout_session: return jsonify(workout_session.get_final_report())
    return jsonify({'error': 'No session data available'})

if __name__ == '__main__':
    init_session()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)