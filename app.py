"""
Flask application with API routes
"""
from flask import Flask, Response, jsonify
import cv2
import mediapipe as mp
import numpy as np
import time
import json
import os
import random
import string
import requests
import certifi # Ensure this is imported
from collections import deque
from datetime import datetime
from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from flask_mail import Mail, Message

# --- 0. CONFIGURATION ---
load_dotenv()

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# --- 1. MAIL CONFIGURATION ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)

# --- 2. DATABASE SETUP (DOUBLE SSL FIX) ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "physiocheck_db"

try:
    # Use BOTH certifi AND allow invalid certs to be 100% sure it connects
    client = MongoClient(
        MONGO_URI, 
        serverSelectionTimeoutMS=5000, 
        tls=True,
        tlsCAFile=certifi.where(),       # Fix 1: Provide correct CA
        tlsAllowInvalidCertificates=True # Fix 2: Bypass validation if Fix 1 fails
    )
    
    # Trigger a connection check
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
    """Initialize workout session"""
    global workout_session
    from workout_session import WorkoutSession
    workout_session = WorkoutSession()

def generate_video_frames():
    """Generator for video streaming"""
    from constants import WorkoutPhase
    
    while workout_session.phase != WorkoutPhase.INACTIVE:
        frame, should_continue = workout_session.process_frame()
        
        if not should_continue or frame is None:
            break
# --- 3. MEDIA PIPE SETUP ---
mp_holistic = mp.solutions.holistic
mp_drawing = mp.solutions.drawing_utils
cap = None
holistic_model = None

# --- 4. EXERCISE SETTINGS & STATE ---
CONTRACTED_THRESHOLD = 50   
EXTENDED_THRESHOLD = 160    
SAFE_ANGLE_MIN = 30         
SAFE_ANGLE_MAX = 175        
COUNTDOWN_TIME = 5 
SMOOTHING_WINDOW = 7 

is_tracking_active = False
start_time = 0 

angle_buffers = {
    'RIGHT': deque(maxlen=SMOOTHING_WINDOW),
    'LEFT':  deque(maxlen=SMOOTHING_WINDOW)
}

global_tracking_data = {
    'RIGHT': {'rep_count': 0, 'stage': "INACTIVE", 'angle': 0, 
              'rep_time': 0.0, 'min_rep_time': 0.0, 'curr_rep_time': 0.0, 'feedback': "", 
              'draw_coords': (0, 0), 'text_color': (255, 255, 255)},
    'LEFT':  {'rep_count': 0, 'stage': "INACTIVE", 'angle': 0, 
              'rep_time': 0.0, 'min_rep_time': 0.0, 'curr_rep_time': 0.0, 'feedback': "",
              'draw_coords': (0, 0), 'text_color': (255, 255, 255)},
    'status': 'INACTIVE',
    'remaining': 0
}

session_history = {
    'time': [], 'right_angle': [], 'left_angle': [],
    'right_feedback': 0, 'left_feedback': 0
}
final_report_summary = {} 

arm_states = {
    'RIGHT': {'rep_count': 0, 'stage': "down", 'last_down_time': time.time()},
    'LEFT':  {'rep_count': 0, 'stage': "down", 'last_down_time': time.time()}
}

# --- 5. HELPER FUNCTIONS ---
def calculate_angle(a, b, c):
    a = np.array(a); b = np.array(b); c = np.array(c)
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(np.degrees(radians))
    return 360 - angle if angle > 180.0 else angle

def get_smoothed_angle(arm, new_angle):
    if len(angle_buffers[arm]) == 0:
        for _ in range(SMOOTHING_WINDOW):
            angle_buffers[arm].append(new_angle)
    angle_buffers[arm].append(new_angle)
    return int(sum(angle_buffers[arm]) / len(angle_buffers[arm]))

# --- 6. AUTHENTICATION ROUTES ---

@app.route('/api/auth/send-otp', methods=['POST'])
def send_otp():
    if users_collection is None: return jsonify({'error': 'Database unavailable'}), 503
    data = request.json
    email = data.get('email')
    
    if users_collection.find_one({'email': email}):
        return jsonify({'error': 'Email is already registered. Please login.'}), 400

    otp = ''.join(random.choices(string.digits, k=6))
    
    otp_collection.update_one(
        {'email': email}, 
        {'$set': {'otp': otp, 'created_at': time.time()}}, 
        upsert=True
    )

    try:
        msg = Message('PhysioCheck Verification Code', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f"Your verification code is: {otp}\n\nThis code expires in 10 minutes."
        mail.send(msg)
        return jsonify({'message': 'OTP sent successfully'}), 200
    except Exception as e:
        print(f"Mail Error: {e}")
        return jsonify({'error': 'Failed to send email.'}), 500

@app.route('/api/auth/signup-verify', methods=['POST'])
def signup_verify():
    if users_collection is None: return jsonify({'error': 'Database unavailable'}), 503
    data = request.json
    email = data.get('email')
    otp_input = data.get('otp')
    
    record = otp_collection.find_one({'email': email})
    if not record or record['otp'] != otp_input:
        return jsonify({'error': 'Invalid or expired OTP'}), 400
    
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = {
        'name': data['name'],
        'email': email,
        'password': hashed_password,
        'role': data.get('role', 'patient'),
        'licenseId': data.get('licenseId', None),
        'created_at': time.time(),
        'auth_method': 'email'
    }
    users_collection.insert_one(user)
    otp_collection.delete_one({'email': email}) 
    return jsonify({'message': 'User verified and created!', 'user': {'name': user['name'], 'role': user['role']}}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    if users_collection is None: return jsonify({'error': 'Database unavailable'}), 503
    data = request.json
    user = users_collection.find_one({'email': data['email']})
    
    if user and user.get('auth_method') == 'google' and not user.get('password'):
         return jsonify({'error': 'Please sign in with Google'}), 400

    if user and bcrypt.check_password_hash(user['password'], data['password']):
        return jsonify({
            'message': 'Login successful', 
            'role': user['role'],
            'name': user['name'],
            'email': user['email']
        }), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/google', methods=['POST'])
def google_auth():
    if users_collection is None: return jsonify({'error': 'Database unavailable'}), 503
    token = request.json.get('token')
    role = request.json.get('role', 'patient') 
    
    try:
        resp = requests.get(
            'https://www.googleapis.com/oauth2/v1/userinfo',
            params={'access_token': token, 'alt': 'json'}
        )
        if not resp.ok: return jsonify({'error': 'Invalid Google Token'}), 401
            
        google_user = resp.json()
        email = google_user['email']
        name = google_user['name']
        
        user = users_collection.find_one({'email': email})
        if not user:
            user = {
                'name': name, 'email': email, 'password': '', 
                'role': role, 'created_at': time.time(), 'auth_method': 'google'
            }
            users_collection.insert_one(user)
            
        return jsonify({
            'message': 'Google login successful',
            'role': user['role'], 'name': user['name'], 'email': user['email']
        }), 200
    except Exception as e:
        print(f"Google Auth Error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

# --- 7. PROFILE STATS ROUTES ---
@app.route('/api/user/stats', methods=['POST'])
def get_user_stats():
    if sessions_collection is None: return jsonify({'error': 'DB Error'}), 503
    
    email = request.json.get('email')
    if not email: return jsonify({'error': 'Email required'}), 400
    
    user_sessions = list(sessions_collection.find({'email': email}))
    
    total_workouts = len(user_sessions)
    total_reps = sum(s.get('total_reps', 0) for s in user_sessions)
    total_duration = sum(s.get('duration', 0) for s in user_sessions)
    
    total_errors = sum(s.get('total_errors', 0) for s in user_sessions)
    accuracy = 100
    if total_reps > 0:
        accuracy = max(0, 100 - int((total_errors / total_reps) * 20))

    graph_data = []
    for s in user_sessions[-7:]:
        graph_data.append({
            'date': s.get('date', 'Unknown'),
            'reps': s.get('total_reps', 0)
        })

    return jsonify({
        'total_workouts': total_workouts,
        'total_reps': total_reps,
        'total_minutes': round(total_duration / 60, 1),
        'accuracy': accuracy,
        'graph_data': graph_data
    })

# --- 8. VIDEO PROCESSING ---
def gen_frames():
    global cap, holistic_model, is_tracking_active, start_time, global_tracking_data, arm_states, session_history
    
    if not is_tracking_active or cap is None or holistic_model is None: return

    while cap.isOpened() and is_tracking_active:
        success, image = cap.read()
        if not success: break

        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = holistic_model.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        h, w, _ = image.shape
        
        current_time = time.time()
        elapsed_time = current_time - start_time
        countdown_running = elapsed_time < COUNTDOWN_TIME

        if countdown_running:
            remaining = int(COUNTDOWN_TIME - elapsed_time)
            global_tracking_data['status'] = 'COUNTDOWN'
            global_tracking_data['remaining'] = remaining
        else:
            global_tracking_data['status'] = 'ACTIVE'

        current_frame_angles = {'RIGHT': 0, 'LEFT': 0}

        if results.pose_landmarks and not countdown_running:
            landmarks = results.pose_landmarks.landmark
            arm_config = {
                'RIGHT': {'shoulder': mp_holistic.PoseLandmark.RIGHT_SHOULDER, 'elbow': mp_holistic.PoseLandmark.RIGHT_ELBOW, 'wrist': mp_holistic.PoseLandmark.RIGHT_WRIST},
                'LEFT':  {'shoulder': mp_holistic.PoseLandmark.LEFT_SHOULDER, 'elbow': mp_holistic.PoseLandmark.LEFT_ELBOW, 'wrist': mp_holistic.PoseLandmark.LEFT_WRIST}
            }

            for arm, config in arm_config.items():
                try:
                    s = [landmarks[config['shoulder']].x, landmarks[config['shoulder']].y]
                    e = [landmarks[config['elbow']].x, landmarks[config['elbow']].y]
                    w_l = [landmarks[config['wrist']].x, landmarks[config['wrist']].y]
                    
                    raw_angle = calculate_angle(s, e, w_l)
                    angle = get_smoothed_angle(arm, raw_angle)
                    
                    current_frame_angles[arm] = angle
                    global_tracking_data[arm]['angle'] = angle
                    global_tracking_data[arm]['curr_rep_time'] = current_time - arm_states[arm]['last_down_time']
                    global_tracking_data[arm]['feedback'] = ""

                    if angle < CONTRACTED_THRESHOLD:
                        arm_states[arm]['stage'] = "up"
                        global_tracking_data[arm]['stage'] = "UP"
                    
                    if angle > EXTENDED_THRESHOLD:
                        if arm_states[arm]['stage'] == "up":
                            rep_time = current_time - arm_states[arm]['last_down_time']
                            if global_tracking_data[arm]['min_rep_time'] == 0.0 or rep_time < global_tracking_data[arm]['min_rep_time']:
                                global_tracking_data[arm]['min_rep_time'] = rep_time
                            arm_states[arm]['rep_count'] += 1
                            arm_states[arm]['last_down_time'] = current_time
                            global_tracking_data[arm]['rep_count'] = arm_states[arm]['rep_count']
                            global_tracking_data[arm]['rep_time'] = rep_time
                        arm_states[arm]['stage'] = "down"
                        global_tracking_data[arm]['stage'] = "DOWN"

                    if angle < SAFE_ANGLE_MIN:
                        global_tracking_data[arm]['feedback'] = "OVER-CURLING"
                        session_history[f'{arm.lower()}_feedback'] += 1
                    elif angle > SAFE_ANGLE_MAX:
                        global_tracking_data[arm]['feedback'] = "OVER-EXTENDING"
                        session_history[f'{arm.lower()}_feedback'] += 1
                    elif angle > CONTRACTED_THRESHOLD and angle < EXTENDED_THRESHOLD:
                         if arm_states[arm]['stage'] == "down": global_tracking_data[arm]['feedback'] = "STRAIGHTEN ARM"
                         elif arm_states[arm]['stage'] == "up": global_tracking_data[arm]['feedback'] = "CURL DEEPER"

                except Exception:
                    global_tracking_data[arm]['stage'] = "LOST"

            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
            
            session_history['time'].append(round(current_time - start_time, 2))
            session_history['right_angle'].append(current_frame_angles['RIGHT'])
            session_history['left_angle'].append(current_frame_angles['LEFT'])

        image = cv2.flip(image, 1)
        if countdown_running:
             cv2.putText(image, str(global_tracking_data['remaining']), (int(w/2)-50, int(h/2)), cv2.FONT_HERSHEY_SIMPLEX, 5, (0,0,255), 5)
        
        ret, buffer = cv2.imencode('.jpg', frame)
        if ret:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.route('/start_tracking')
def start_tracking():
    """Start new workout session"""
    from constants import WorkoutPhase
    
    if workout_session and workout_session.phase != WorkoutPhase.INACTIVE:
        return jsonify({'status': 'already_active'}), 400
    
    try:
        if workout_session is None:
            init_session()
        workout_session.start()
        return jsonify({'status': 'success', 'message': 'Calibration started'})
# --- 9. TRACKING CONTROL ROUTES ---
@app.route('/start_tracking')
def start_tracking():
    global cap, holistic_model, is_tracking_active, start_time, angle_buffers
    if is_tracking_active: return jsonify({'status': 'already_active'})
    try:
        cap = cv2.VideoCapture(0)
        holistic_model = mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        is_tracking_active = True
        start_time = time.time()
        for arm in ['LEFT', 'RIGHT']:
            arm_states[arm]['rep_count'] = 0
            arm_states[arm]['stage'] = "down"
            arm_states[arm]['last_down_time'] = time.time()
            global_tracking_data[arm] = {'rep_count': 0, 'stage': "DOWN", 'angle': 0, 'rep_time': 0, 'min_rep_time': 0, 'curr_rep_time': 0, 'feedback': ""}
            angle_buffers[arm].clear() 
        
        session_history['time'] = []; session_history['right_angle'] = []; session_history['left_angle'] = []
        session_history['right_feedback'] = 0; session_history['left_feedback'] = 0
        global_tracking_data['status'] = 'COUNTDOWN'
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stop_tracking', methods=['POST'])
def stop_tracking():
    """Stop current workout session"""
    if workout_session:
        workout_session.stop()
    global cap, holistic_model, is_tracking_active, final_report_summary
    
    data = request.json
    user_email = data.get('email') if data else None

    is_tracking_active = False
    
    if cap: cap.release()
    if holistic_model: holistic_model.close(); holistic_model = None
    
    duration = time.time() - start_time
    total_reps = global_tracking_data['RIGHT']['rep_count'] + global_tracking_data['LEFT']['rep_count']
    total_errors = session_history['right_feedback'] + session_history['left_feedback']

    if user_email and sessions_collection is not None:
        session_doc = {
            'email': user_email,
            'date': datetime.now().strftime("%Y-%m-%d"),
            'timestamp': time.time(),
            'duration': duration,
            'total_reps': total_reps,
            'right_reps': global_tracking_data['RIGHT']['rep_count'],
            'left_reps': global_tracking_data['LEFT']['rep_count'],
            'total_errors': total_errors
        }
        sessions_collection.insert_one(session_doc)
        print(f"💾 Saved workout for {user_email}")

    final_report_summary = {
        'duration': round(duration, 2),
        'summary': {
            'RIGHT': {'total_reps': global_tracking_data['RIGHT']['rep_count'], 'min_time': global_tracking_data['RIGHT']['min_rep_time'], 'error_count': session_history['right_feedback']},
            'LEFT': {'total_reps': global_tracking_data['LEFT']['rep_count'], 'min_time': global_tracking_data['LEFT']['min_rep_time'], 'error_count': session_history['left_feedback']}
        }
    }
    return jsonify({'status': 'success'})

@app.route('/video_feed')
def video_feed():
    """Stream video frames"""
    return Response(generate_video_frames(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/data_feed')
def data_feed():
    """Get current workout state"""
    if workout_session:
        return jsonify(workout_session.get_state_dict())
    return jsonify({'status': 'INACTIVE'})

@app.route('/report_data')
def report_data():
    """Get final session report"""
    if workout_session:
        return jsonify(workout_session.get_final_report())
    return jsonify({'error': 'No session data available'})

if __name__ == '__main__':
    import cv2  # Import here for app.py
    init_session()
    app.run(host='0.0.0.0', port=5000, debug=True)