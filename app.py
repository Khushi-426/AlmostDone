"""
Flask application with API routes - OPTIMIZED & AGNOSTIC VERSION
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


# --- IMPORT CUSTOM AI MODULE (CRITICAL FOR ACCURACY) ---
from ai_engine import AIEngine
from constants import EXERCISE_PRESETS 


# --- 0. CONFIGURATION ---
load_dotenv()


app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)


# [Change] Initialize SocketIO with async_mode to ensure non-blocking behavior
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


# [Change] Modified to accept exercise_name
def init_session(exercise_name="Bicep Curl"): 
    """Initialize workout session logic"""
    global workout_session
    from workout_session import WorkoutSession
    # Pass the exercise name to WorkoutSession
    workout_session = WorkoutSession(exercise_name) 

def generate_video_frames():
    """Generator for video streaming & WebSocket Data Push"""
    from constants import WorkoutPhase
    
    if workout_session is None: return
    
    while workout_session.phase != WorkoutPhase.INACTIVE:
        # process_frame handles MediaPipe inference and UI drawing
        frame, should_continue = workout_session.process_frame() 
        
        if not should_continue or frame is None:
            break
        
        # [Critical Fix] Emit data and SLEEP to allow other requests (like Stop) to process
        socketio.emit('workout_update', workout_session.get_state_dict())
        socketio.sleep(0.01) # Yield control for 10ms


        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


# --- HELPER: EXERCISE DATA FOR FRONTEND (FIXED) ---
def _get_frontend_exercise_list():
    """Generates a list of exercises with mock data for the frontend UI."""
    # Mock data for UI presentation properties (category, instructions, etc.)
    # The exercise keys must match the keys in EXERCISE_PRESETS from constants.py
    exercise_map = {
        "Bicep Curl": {"id": "bicep_curl", "category": "Strength • Arms", "duration": "5 Mins", "difficulty": "Beginner", "recommended": True, "description": "A fundamental exercise for building upper arm strength and stability.", "instructions": ["Stand with feet shoulder-width apart.", "Keep elbows close to your torso at all times.", "Contract biceps to curl weights upwards.", "Lower slowly to starting position.", "Avoid swinging your body."], "color": '#E8F5E9', "iconColor": '#2C5D31', "video": "/bicep_demo.mp4"},
        "Knee Lift": {"id": "knee_lift", "category": "Core • Legs", "duration": "5 Mins", "difficulty": "Beginner", "recommended": False, "description": "Strengthens core and hip flexors for better stability.", "instructions": ["Stand tall, lift one knee to waist height.", "Hold for 3 seconds.", "Return slowly and repeat on the other side.", "Maintain an upright posture."], "color": '#E3F2FD', "iconColor": '#1E88E5', "video": "/knee_lift_demo.mp4"},
        "Shoulder Press": {"id": "shoulder_press", "category": "Mobility • Shoulders", "duration": "8 Mins", "difficulty": "Intermediate", "recommended": False, "description": "Overhead press to improve shoulder mobility and strength.", "instructions": ["Hold weights at shoulder level with palms facing forward.", "Push weights up until arms are fully extended.", "Lower back down slowly to the starting position.", "Keep your back straight throughout."], "color": '#FFF3E0', "iconColor": '#EF6C00', "video": "/shoulder_press_demo.mp4"},
        "Squat": {"id": "squat", "category": "Strength • Legs", "duration": "10 Mins", "difficulty": "Intermediate", "recommended": True, "description": "A full-body exercise for lower body strength and depth control.", "instructions": ["Stand with feet shoulder-width apart.", "Lower hips as if sitting in a chair.", "Keep your chest up and back straight.", "Ensure knees track over your toes."], "color": '#FBEFF5', "iconColor": '#AD1457', "video": "/squat_demo.mp4"},
        "Standing Row": {"id": "standing_row", "category": "Strength • Back", "duration": "7 Mins", "difficulty": "Intermediate", "recommended": False, "description": "Targets the upper back and lats for improved posture and pulling strength.", "instructions": ["Stand with slight knee bend and hinge at the hips.", "Pull arms back, squeezing shoulder blades together.", "Keep elbows close to the body.", "Slowly extend arms to the starting position."], "color": '#F3E5F5', "iconColor": '#6A1B9A', "video": "/standing_row_demo.mp4"},
    }

    exercise_list = []
    # Loop through the list of exercises defined in your constants.py file
    for name in EXERCISE_PRESETS:
        ui_data = exercise_map.get(name, {})
        # Create a combined object for the frontend
        exercise_list.append({
            'id': name.lower().replace(' ', '_'),
            'title': name, 
            **ui_data
        })
    return [e for e in exercise_list if 'title' in e]


# --- 3. SOCKET EVENTS (NEW) ---


@socketio.on('connect')
def handle_connect():
    print('Client connected')


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


# [Change] Socket-based Stop command 
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


@app.route('/api/exercises', methods=['GET']) 
def get_exercises():
    """Returns the list of configured exercises for the frontend."""
    return jsonify(_get_frontend_exercise_list()), 200


@app.route('/start_tracking', methods=['GET', 'POST']) 
def start_tracking():
    global workout_session
    
    exercise_name = 'Bicep Curl' # Default exercise
    
    # Try to get exercise name from JSON body if it's a POST request
    if request.method == 'POST':
        try:
            # CRITICAL: Retrieve the 'exercise' name sent from the frontend
            exercise_name = request.json.get('exercise', 'Bicep Curl') 
        except:
            # If JSON is invalid or missing, stick with default
            pass
    
    if workout_session:
        try: workout_session.stop()
        except: pass
    try:
        # Pass the specific exercise name to initialization
        init_session(exercise_name=exercise_name) 
        workout_session.start()
        return jsonify({'status': 'success', 'message': f'Session started for {exercise_name}'}), 200
    except Exception as e:
        # Log the full exception for debugging
        print(f"Exception during start_tracking: {e}")
        return jsonify({'status': 'error', 'message': f'Failed to start: {e}'}), 500


# Keep this for backward compatibility, but we use Socket for stopping now
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
    # Initial session setup (using default name)
    init_session()
    # [Critical] Use socketio.run
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)