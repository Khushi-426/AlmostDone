"""
Flask application with API routes - THREADING MODE (No Eventlet)
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
from flask_mail import Mail, Message
from flask_socketio import SocketIO, emit
from bson.objectid import ObjectId

# --- OPTIONAL: Google Auth Library (Requested) ---
# We import this to satisfy dependencies, though we use requests 
# for Access Token validation to match the current Frontend flow.
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# --- IMPORT CUSTOM AI MODULE ---
from ai_engine import AIEngine
from constants import EXERCISE_PRESETS

# ----------------------------------------------------
# 0. CONFIGURATION
# ----------------------------------------------------
load_dotenv()

app = Flask(__name__)

# UPDATED CORS: Explicitly allow all origins and headers
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
bcrypt = Bcrypt(app)

# SWITCHED TO THREADING MODE (Removes Eventlet dependency)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ----------------------------------------------------
# 1. MAIL CONFIGURATION
# ----------------------------------------------------
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
mail = Mail(app)

# ----------------------------------------------------
# 2. DATABASE SETUP
# ----------------------------------------------------
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "physiocheck_db"

# Initialize as None to handle connection failures gracefully
client = None
db = None
users_collection = None
otp_collection = None
sessions_collection = None
exercises_collection = None
protocols_collection = None
notifications_collection = None

try:
    print("⏳ Attempting to connect to MongoDB...")
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000, # 5 second timeout
        tls=True,
        tlsCAFile=certifi.where(),
        tlsAllowInvalidCertificates=True,
    )
    # Trigger a connection verify
    client.admin.command("ping")
    db = client[DB_NAME]

    users_collection = db["users"]
    otp_collection = db["otps"]
    sessions_collection = db["sessions"]
    exercises_collection = db["exercises"]
    protocols_collection = db["protocols"]
    notifications_collection = db["notifications"]

    print(f"✅ Connected to MongoDB Cloud: {DB_NAME}")
except Exception as e:
    print(f"⚠️ DB Error: {e}")
    print("⚠️ WARNING: Application running without Database. Login/Signup will fail.")

# ----------------------------------------------------
# 3. WORKOUT SESSION MANAGEMENT
# ----------------------------------------------------
workout_session = None
last_session_report = None

def init_session(exercise_name="Bicep Curl"):
    """Initialize a new workout session, ensuring the old one is closed."""
    global workout_session, last_session_report
    
    # 1. Force close existing session
    if workout_session:
        try:
            print("🛑 Stopping previous session...")
            workout_session.stop()
        except Exception as e:
            print(f"⚠️ Error stopping previous session: {e}")
        finally:
            workout_session = None

    # Reset last report for new session
    last_session_report = None
    
    # 2. Start new session
    print(f"🎥 Initializing Camera for {exercise_name}...")
    from workout_session import WorkoutSession
    workout_session = WorkoutSession(exercise_name)

def generate_video_frames():
    """Generator function to stream video frames."""
    from constants import WorkoutPhase
    global workout_session
    
    # Capture local reference
    current_session = workout_session
    
    if current_session is None:
        return

    # Loop to capture frames
    while current_session.phase != WorkoutPhase.INACTIVE:
        try:
            if current_session is None:
                break

            frame, should_continue = current_session.process_frame()
            
            if not should_continue or frame is None:
                break

            # Emit real-time data to frontend via WebSocket
            socketio.emit("workout_update", current_session.get_state_dict())
            
            # Control frame rate (Standard time.sleep works in threading mode)
            time.sleep(0.01)

            # Encode frame for HTTP Stream
            ret, buffer = cv2.imencode(".jpg", frame)
            if ret:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + buffer.tobytes()
                    + b"\r\n"
                )
        except Exception as e:
            print(f"Stream Error: {e}")
            break

# ----------------------------------------------------
# 4. EXERCISES (FRONTEND DATA)
# ----------------------------------------------------
def _get_frontend_exercise_list():
    meta_map = {
        "Bicep Curl": {
            "category": "Strength",
            "description": "A fundamental exercise for building arm strength and definition.",
            "instructions": [
                "Stand tall with feet shoulder-width apart.",
                "Hold dumbbells with palms facing forward.",
                "Keep elbows close to your torso at all times.",
                "Curl the weights up while contracting biceps.",
                "Lower the weights slowly."
            ],
            "difficulty": "Beginner",
            "duration": "5 Mins",
            "color": "#E3F2FD",
            "iconColor": "#1565C0",
            "recommended": True
        },
        "Knee Lift": {
            "category": "Mobility",
            "description": "Improves hip mobility and balance.",
            "instructions": [
                "Stand straight with feet together.",
                "Lift one knee up towards your chest.",
                "Hold for a second.",
                "Lower slowly and switch legs."
            ],
            "difficulty": "Beginner",
            "duration": "5 Mins",
            "color": "#E8F5E9",
            "iconColor": "#2E7D32",
            "recommended": False
        },
        "Shoulder Press": {
            "category": "Strength",
            "description": "Builds shoulder and upper arm strength.",
            "instructions": [
                "Hold dumbbells at shoulder height.",
                "Press weights upwards.",
                "Lower back down with control."
            ],
            "difficulty": "Intermediate",
            "duration": "8 Mins",
            "color": "#FFF3E0",
            "iconColor": "#EF6C00",
            "recommended": True
        },
        "Squat": {
            "category": "Lower Body",
            "description": "Compound movement for legs and core.",
            "instructions": [
                "Stand with feet shoulder-width apart.",
                "Push hips back and bend knees.",
                "Keep chest up.",
                "Push through heels to return."
            ],
            "difficulty": "Intermediate",
            "duration": "10 Mins",
            "color": "#F3E5F5",
            "iconColor": "#7B1FA2",
            "recommended": False
        },
        "Standing Row": {
            "category": "Back & Core",
            "description": "Strengthens the upper back.",
            "instructions": [
                "Hinge forward slightly.",
                "Pull weights towards your waist.",
                "Squeeze shoulder blades.",
                "Lower weights with control."
            ],
            "difficulty": "Intermediate",
            "duration": "7 Mins",
            "color": "#FFEBEE",
            "iconColor": "#C62828",
            "recommended": False
        }
    }

    result = []
    for name in EXERCISE_PRESETS:
        details = meta_map.get(name, {
            "category": "General",
            "description": "Standard rehabilitation exercise.",
            "instructions": ["Maintain good form.", "Follow the visual guide."],
            "difficulty": "General",
            "duration": "5 Mins",
            "color": "#F5F5F5",
            "iconColor": "#616161",
            "recommended": False
        })
        
        result.append({
            "id": name.lower().replace(" ", "_"),
            "title": name,
            **details 
        })
    return result

# ----------------------------------------------------
# 5. SOCKET EVENTS
# ----------------------------------------------------
@socketio.on("connect")
def handle_connect():
    print("🟢 Client connected to WebSocket")

@socketio.on("disconnect")
def handle_disconnect():
    print("🔴 Client disconnected")

@socketio.on("stop_session")
def handle_stop_session(data):
    global workout_session, last_session_report
    if not workout_session:
        return

    data = data or {}
    email = data.get("email")
    exercise = data.get("exercise", "Freestyle")

    try:
        print("🛑 Stop session command received")
        # SAVE REPORT BEFORE STOPPING
        last_session_report = workout_session.get_final_report()
        
        workout_session.stop()
        workout_session = None 

        if email and sessions_collection is not None:
            r = last_session_report["summary"]["RIGHT"]
            l = last_session_report["summary"]["LEFT"]
            
            sessions_collection.insert_one({
                "email": email,
                "exercise": exercise,
                "timestamp": time.time(),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "total_reps": r["total_reps"] + l["total_reps"],
                "total_errors": r["error_count"] + l["error_count"],
            })

        emit("session_stopped", {"status": "success"})
    except Exception as e:
        print(f"Stop session error: {e}")
        emit("session_stopped", {"status": "error", "message": str(e)})

# ----------------------------------------------------
# 6. ANALYTICS & AI ROUTES
# ----------------------------------------------------
@app.route("/api/user/analytics_detailed", methods=["POST"])
def analytics_detailed():
    """Returns detailed workout history for graphs."""
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email: return jsonify({"error": "Email required"}), 400

    if sessions_collection is None:
        return jsonify({"total_sessions": 0, "history": []})

    sessions = list(sessions_collection.find({"email": email}).sort("timestamp", 1))
    
    analytics = AIEngine.get_detailed_analytics(sessions)
    return jsonify(analytics)

@app.route("/api/user/ai_prediction", methods=["POST"])
def ai_prediction():
    """Returns AI-based recovery prediction and risk analysis."""
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    if not email: return jsonify({"error": "Email required"}), 400

    if sessions_collection is None:
        return jsonify({"error": "Database unavailable"}), 500

    sessions = list(sessions_collection.find({"email": email}).sort("timestamp", 1))
    
    prediction = AIEngine.get_recovery_prediction(sessions)
    
    if not prediction:
        return jsonify({"error": "Not enough data for prediction"}), 200 

    return jsonify(prediction)

# ----------------------------------------------------
# 7. AUTH & OTHER ROUTES
# ----------------------------------------------------
@app.route("/api/auth/send-otp", methods=["POST"])
def send_otp():
    if users_collection is None:
        return jsonify({"error": "Database unavailable. Check server logs."}), 503

    data = request.get_json(silent=True) or {}
    email = data.get("email")

    if users_collection.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 400

    otp = "".join(random.choices(string.digits, k=6))
    otp_collection.update_one(
        {"email": email},
        {"$set": {"otp": otp, "created_at": time.time()}},
        upsert=True,
    )

    try:
        msg = Message("PhysioCheck OTP", sender=app.config["MAIL_USERNAME"], recipients=[email])
        msg.body = f"Your verification code is: {otp}"
        mail.send(msg)
        return jsonify({"message": "OTP sent"}), 200
    except Exception as e:
        print(f"Mail Error: {e}")
        return jsonify({"error": "Failed to send email. Check server logs."}), 500

@app.route("/api/auth/login", methods=["POST"])
def login():
    if users_collection is None:
        return jsonify({"error": "Database unavailable. Check server logs."}), 503

    data = request.get_json(silent=True) or {}
    user = users_collection.find_one({"email": data.get("email")})

    if user and bcrypt.check_password_hash(user["password"], data.get("password")):
        return jsonify({
            "email": user["email"],
            "role": user["role"],
            "name": user["name"]
        })

    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/auth/signup-verify", methods=["POST"])
def signup_verify():
    if users_collection is None:
        return jsonify({"error": "Database unavailable. Check server logs."}), 503

    data = request.get_json(silent=True) or {}
    email = data.get("email")
    otp_input = data.get("otp")
    password = data.get("password")
    name = data.get("name")
    role = data.get("role", "patient")

    if not all([email, otp_input, password, name]):
        return jsonify({"error": "Missing required fields"}), 400

    otp_record = otp_collection.find_one({"email": email})
    if not otp_record or otp_record.get("otp") != otp_input:
        return jsonify({"error": "Invalid OTP"}), 400

    if users_collection.find_one({"email": email}):
        return jsonify({"error": "User already exists"}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = {
        "email": email, 
        "password": hashed_pw, 
        "name": name, 
        "role": role, 
        "created_at": time.time()
    }
    users_collection.insert_one(new_user)
    otp_collection.delete_one({"email": email})

    return jsonify({"user": {"email": email, "name": name, "role": role}}), 201

# --- GOOGLE AUTH ROUTE ---
@app.route("/api/auth/google", methods=["POST"])
def google_auth():
    """Handles Google Login/Signup by verifying token and checking DB."""
    # EDGE CASE: DB NOT CONNECTED
    if users_collection is None:
        print("❌ Login failed: Database not connected")
        return jsonify({"error": "Database unavailable. Check server logs."}), 503

    data = request.get_json(silent=True) or {}
    token = data.get("token") # This is an ACCESS TOKEN from frontend
    role = data.get("role", "patient")

    if not token:
        return jsonify({"error": "Google token is required"}), 400

    try:
        # NOTE: Frontend sends an ACCESS TOKEN, not an ID TOKEN.
        # We must use requests.get() to verify it against Google's UserInfo API.
        # google-auth library (id_token.verify_oauth2_token) requires an ID Token (JWT).
        
        google_response = requests.get(
            f"https://www.googleapis.com/oauth2/v1/userinfo?access_token={token}",
            headers={"Accept": "application/json"}
        )
        
        if google_response.status_code != 200:
            return jsonify({"error": "Invalid Google Token"}), 401
            
        google_user = google_response.json()
        email = google_user.get("email")
        name = google_user.get("name")
        
        if not email:
            return jsonify({"error": "Email not found in Google profile"}), 400

        # Check if user exists in DB
        user = users_collection.find_one({"email": email})
        
        if user:
            # User exists -> LOGIN
            return jsonify({
                "email": user["email"],
                "role": user.get("role", "patient"),
                "name": user["name"]
            }), 200
        else:
            # User does not exist -> REGISTER
            new_user = {
                "email": email,
                "name": name,
                "role": role,
                "password": "", 
                "auth_provider": "google",
                "created_at": time.time()
            }
            users_collection.insert_one(new_user)
            
            return jsonify({
                "email": email,
                "role": role,
                "name": name
            }), 200

    except Exception as e:
        print(f"Google Auth Error: {e}")
        return jsonify({"error": "Internal Server Error during Google Auth"}), 500

@app.route("/api/exercises", methods=["GET"])
def get_exercises():
    return jsonify(_get_frontend_exercise_list())

@app.route("/api/therapist/patients", methods=["GET"])
def therapist_patients():
    if users_collection is None: return jsonify({"patients": []}), 200

    patients = list(users_collection.find({"role": "patient"}, {"_id": 0, "name": 1, "email": 1, "created_at": 1}))
    enriched = []
    for p in patients:
        last = sessions_collection.find_one({"email": p["email"]}, sort=[("timestamp", -1)])
        status = "Normal"
        if last:
            reps = last.get("total_reps", 0)
            errors = last.get("total_errors", 0)
            accuracy = max(0, 100 - int((errors / max(reps, 1)) * 20))
            if accuracy < 60: status = "High Risk"
            elif accuracy < 80: status = "Alert"
        enriched.append({
            "name": p.get("name", "Unknown"),
            "email": p["email"],
            "date_joined": datetime.fromtimestamp(p.get("created_at", time.time())).strftime("%Y-%m-%d"),
            "status": status,
            "hasActiveProtocol": False
        })
    return jsonify({"patients": enriched}), 200

@app.route("/api/therapist/notifications", methods=["GET"])
def therapist_notifications():
    if notifications_collection is None: return jsonify([]), 200
    notifs = list(notifications_collection.find({}).sort("timestamp", -1).limit(10))
    response = []
    for n in notifs:
        response.append({
            "id": str(n.get("_id")),
            "type": n.get("type", "Info"),
            "title": n.get("title", "System"),
            "message": n.get("message", ""),
            "time": n.get("time", "Recently")
        })
    return jsonify(response), 200

# ----------------------------------------------------
# 8. STREAMING ROUTES
# ----------------------------------------------------
@app.route("/start_tracking", methods=["POST"])
def start_tracking():
    data = request.get_json(silent=True) or {}
    exercise = data.get("exercise", "Bicep Curl")

    print(f"🚀 Received start_tracking request for: {exercise}")

    try:
        init_session(exercise)
        
        if workout_session:
            workout_session.start()
            return jsonify({"status": "started", "exercise": exercise})
        else:
            return jsonify({"error": "Failed to initialize workout session"}), 500
    except Exception as e:
        print(f"❌ Error in start_tracking: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/video_feed")
def video_feed():
    return Response(
        generate_video_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/report_data")
def report_data():
    global workout_session, last_session_report
    
    if workout_session:
        return jsonify(workout_session.get_final_report())
    
    if last_session_report:
        return jsonify(last_session_report)
        
    return jsonify({"error": "No session data found"})

# ----------------------------------------------------
# 9. RUN SERVER
# ----------------------------------------------------
if __name__ == "__main__":
    print("🚀 Starting Server with THREADING on Port 5001...")
    # 'allow_unsafe_werkzeug' is needed when running threading mode with socketio in some envs
    socketio.run(app, host="0.0.0.0", port=5001, debug=True, allow_unsafe_werkzeug=True)
