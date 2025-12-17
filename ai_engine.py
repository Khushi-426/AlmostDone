"""
AI Engine & Analytics Logic
Handles data processing, statistical analysis, and recovery predictions.
NOW INTEGRATED WITH LIVE ML MODEL (rehab_model.pkl) AND GEMINI API
"""
import random
import time
import os
import joblib
import requests
import json
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

class AIEngine:
    
    # Global model cache
    _model = None
    
    @classmethod
    def load_model(cls):
        """Loads the trained Random Forest model (rehab_model.pkl)"""
        if cls._model is None:
            try:
                model_path = os.path.join(os.path.dirname(__file__), "rehab_model.pkl")
                if os.path.exists(model_path):
                    cls._model = joblib.load(model_path)
                    print(f"✅ AI Model Loaded: {model_path}")
                else:
                    print("⚠️ AI Model not found. Falling back to heuristics.")
            except Exception as e:
                print(f"❌ Error loading AI model: {e}")
                cls._model = None

    @classmethod
    def predict_form(cls, features: list) -> int:
        """
        Predicts form quality using the loaded ML model.
        Args:
            features: List of 12 floats [rx, ry, r_elb_x, ..., ly]
        Returns:
            1 for Good Form, 0 for Bad Form (or model specific class)
        """
        if cls._model is None:
            # Fallback if model is missing: Return "Good" (1) to avoid blocking
            return 1
        
        try:
            # Reshape for sklearn (1 sample, 12 features)
            input_vector = np.array(features).reshape(1, -1)
            prediction = cls._model.predict(input_vector)[0]
            return int(prediction)
        except Exception as e:
            # On prediction error, assume good form to keep app running
            return 1

    @staticmethod
    def get_detailed_analytics(sessions):
        """Processes session history for the Analytics graphs."""
        history = []
        exercise_counts = {}
        total_acc_sum = 0
        count_acc = 0

        for s in sessions:
            reps = s.get('total_reps', 0)
            errors = s.get('total_errors', 0)
            exercise = s.get('exercise', 'Freestyle') 
            
            # Calculate real accuracy based on recorded errors
            acc = 100
            if reps > 0:
                acc = max(0, int((reps - errors) / reps * 100)) 
            
            date_str = s.get('date', 'Unknown')
            history.append({
                'date': date_str,
                'date_short': date_str[5:] if len(date_str) >= 10 else date_str,
                'reps': reps,
                'accuracy': acc,
                'duration': s.get('duration', 0)
            })
            
            if exercise in exercise_counts:
                exercise_counts[exercise] += reps
            else:
                exercise_counts[exercise] = reps
                
            if reps > 0:
                total_acc_sum += acc
                count_acc += 1

        exercise_stats = [{'name': k, 'total_reps': v} for k, v in exercise_counts.items()]
        avg_accuracy = round(total_acc_sum / count_acc) if count_acc > 0 else 100

        return {
            'history': history,
            'exercise_stats': exercise_stats,
            'average_accuracy': avg_accuracy
        }

    @staticmethod
    def get_recovery_prediction(sessions):
        """Generates AI predictions for ROM, Asymmetry, Recommendations, and Session History."""
        if not sessions:
            return None

        # 1. COMPLIANCE & STREAK
        dates = [s['date'] for s in sessions]
        today = datetime.now().date()
        date_set = set(dates)
        
        loop_date = today
        current_streak = 0
        if loop_date.strftime("%Y-%m-%d") not in date_set:
             yesterday = loop_date - timedelta(days=1)
             if yesterday.strftime("%Y-%m-%d") in date_set:
                 loop_date = yesterday

        while loop_date.strftime("%Y-%m-%d") in date_set:
            current_streak += 1
            loop_date -= timedelta(days=1)
        
        last_7_days = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        days_trained = sum(1 for d in last_7_days if d in date_set)
        adherence = int((days_trained / 7) * 100)

        # 2. ASYMMETRY
        total_right = sum(s.get('right_reps', 0) for s in sessions)
        total_left = sum(s.get('left_reps', 0) for s in sessions)
        total_limb = total_right + total_left
        asymmetry = 0
        if total_limb > 0:
            asymmetry = abs(total_right - total_left) / total_limb * 100

        # 3. AI METRICS & SESSION HISTORY
        recent_sessions = sessions[-5:]
        rom_progress = []
        stability_score = 0
        session_history = []

        if len(recent_sessions) == 1:
            try:
                base_date = datetime.strptime(recent_sessions[0]['date'], "%Y-%m-%d")
                prev_date = (base_date - timedelta(days=1)).strftime("%Y-%m-%d")
                rom_progress.append({'date': prev_date[5:], 'rom': 70}) 
            except:
                pass

        for s in sessions:
            reps = s.get('total_reps', 1) or 1
            errors = s.get('total_errors', 0)
            acc = max(0, int((reps - errors) / reps * 100)) 
            base_rom = 85 + (acc * 0.5) 
            rom_val = min(145, max(60, int(base_rom))) 
            date_label = s.get('date', 'Unknown')
            
            session_history.append({
                'date': date_label,
                'accuracy': acc,
                'reps': reps,
                'rom': rom_val,
                'errors': errors
            })

        for s in recent_sessions:
            reps = s.get('total_reps', 1) or 1
            errors = s.get('total_errors', 0)
            acc = max(0, int((reps - errors) / reps * 100)) 
            base_rom = 85 + (acc * 0.5)
            rom_val = min(145, max(60, int(base_rom)))
            
            date_str = s.get('date', 'Unknown')
            short_date = date_str[5:] if len(date_str) >= 10 else date_str

            rom_progress.append({
                'date': short_date, 
                'rom': rom_val
            })
            stability_score += acc
            
        avg_stability = int(stability_score / len(recent_sessions)) if recent_sessions else 0

        # 4. RECOMMENDATIONS
        recommendations = []
        if asymmetry > 15:
            weaker = "Left" if total_right > total_left else "Right"
            recommendations.append(f"Imbalance: {weaker} side lagging by {int(asymmetry)}%. Use unilateral exercises.")
        if avg_stability < 70:
            recommendations.append("Form Correction Needed: AI detected recurring stability issues.")
        elif avg_stability > 90:
            recommendations.append("High Performance: Your form is optimal for increased resistance.")
        if adherence < 50:
            recommendations.append("Consistency: Aim for 4+ days/week to prevent regression.")

        # 5. HOTSPOTS
        severity = 100 - avg_stability
        hotspots = {
            'shoulder': int(severity * 0.7),
            'elbow': int(severity * 0.3),
            'hip': int(severity * 0.1)
        }

        session_history.reverse()

        return {
            'rom_chart': rom_progress,
            'asymmetry': {'right': total_right, 'left': total_left, 'score': int(asymmetry)},
            'stability_score': avg_stability,
            'compliance': {'streak': current_streak, 'weekly_adherence': adherence, 'days_trained': days_trained},
            'recommendations': recommendations,
            'hotspots': hotspots,
            'session_history': session_history
        }

    def generate_commentary(self, context, query, history):
        """
        Generates contextual AI feedback using Google Gemini API.
        Falls back to rule-based logic if API fails.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        
        # 1. API CALL TO GEMINI
        if api_key:
            print(f"🤖 Connecting to Gemini... Query: {query}")
            try:
                # Prepare context for the LLM
                reps = context.get('reps', 0)
                errors = context.get('errors', 0)
                feedback = context.get('feedback', 'None')
                exercise = context.get('exercise', 'Workout')
                
                system_prompt = (
                    f"You are a Physio AI Coach. The user is doing {exercise}. "
                    f"Current Stats: {reps} Reps, {errors} Errors. "
                    f"Recent Form Feedback: {feedback}. "
                    "Answer the user's question briefly (max 2 sentences) and motivatingly. "
                    "Focus on form correction if errors are high."
                )
                
                # FIX: Updated to 'gemini-2.0-flash-lite' to avoid 429 quota errors
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={api_key}"
                headers = {'Content-Type': 'application/json'}
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": f"{system_prompt}\nUser Question: {query}"
                        }]
                    }]
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    ai_text = data['candidates'][0]['content']['parts'][0]['text']
                    print("✅ Gemini Response Received")
                    return ai_text
                else:
                    print(f"⚠️ Gemini API Error {response.status_code}: {response.text}")

            except Exception as e:
                print(f"❌ Gemini Connection Failed: {e}")

        # 2. FALLBACK LOGIC (If API fails or no key)
        print("⚠️ Using Rule-Based Fallback")
        return self._rule_based_commentary(context, query)

    def _rule_based_commentary(self, context, query):
        """Internal fallback method for offline mode"""
        query = query.lower()
        reps = context.get('reps', 0)
        raw_feedback = context.get('feedback', '')
        feedback_text = str(raw_feedback) if raw_feedback else ""
        exercise = context.get('exercise', 'Exercise')

        if "form" in query or "doing" in query or "correct" in query:
            if "bad" in feedback_text.lower() or "fix" in feedback_text.lower():
                return f"I noticed some issues. {feedback_text}. Try to move slower."
            return f"Your form looks solid! You've completed {reps} reps."
            
        elif "reps" in query or "count" in query:
            return f"You have completed {reps} reps so far."
            
        elif "tired" in query or "hard" in query:
            return "You're doing great! Take a deep breath and give me 3 more perfect reps."
            
        return f"I'm tracking your {exercise}. You're at {reps} reps. Keep going!"

# Initial load when module is imported
AIEngine.load_model()