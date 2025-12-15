"""
Main workout session manager - AGNOSTIC VERSION
"""
import cv2
import mediapipe as mp
import numpy as np
import time
from typing import Tuple, Optional


# Import the upgraded AI Engine
from ai_engine import AIEngine


class WorkoutSession:
    """Manages entire workout session state"""
    
    def __init__(self, exercise_name: str = "Bicep Curl"): # << MODIFIED
        # [Change] Re-import constants to ensure the new ExerciseConfig is loaded
        from constants import (WorkoutPhase, MIN_DETECTION_CONFIDENCE, 
                               MIN_TRACKING_CONFIDENCE, WORKOUT_COUNTDOWN_TIME,
                               CALIBRATION_HOLD_TIME, SMOOTHING_WINDOW, 
                               SAFETY_MARGIN, MIN_REP_DURATION, 
                               EXERCISE_PRESETS) 
        from models import ArmMetrics, CalibrationData, SessionHistory
        from angle_calculator import AngleCalculator
        from pose_processor import PoseProcessor
        from calibration import CalibrationManager
        from rep_counter import RepCounter
        
        # Load the configuration for the selected exercise
        self.exercise_config = EXERCISE_PRESETS.get(exercise_name, EXERCISE_PRESETS["Bicep Curl"])
        
        self.phase = WorkoutPhase.INACTIVE
        self.start_time = 0.0
        self.countdown_remaining = 0
        self.countdown_time = WORKOUT_COUNTDOWN_TIME
        
        self.arm_metrics = {
            'RIGHT': ArmMetrics(),
            'LEFT': ArmMetrics()
        }
        
        # Initialize components
        angle_calc = AngleCalculator(SMOOTHING_WINDOW)
        # Pass the config to PoseProcessor
        self.pose_processor = PoseProcessor(angle_calc, self.exercise_config) 
        
        calibration_data = CalibrationData()
        # The CalibrationManager needs the PoseProcessor, which holds the correct config
        self.calibration_manager = CalibrationManager(
            self.pose_processor, # PoseProcessor holds the exercise config
            calibration_data, 
            CALIBRATION_HOLD_TIME, 
            SAFETY_MARGIN
        )
        
        self.rep_counter = RepCounter(calibration_data, MIN_REP_DURATION)
        self.history = SessionHistory()
        
        # MediaPipe
        self.holistic_model = None
        self.cap = None
        self.min_detection_conf = MIN_DETECTION_CONFIDENCE
        self.min_tracking_conf = MIN_TRACKING_CONFIDENCE

        # AI State Management
        self.last_ai_check = 0
        self.ai_interval = 0.2  # Run AI check every 200ms
        
        self.ai_latched_state = {
            'RIGHT': False, # False = Good Form, True = Bad Form
            'LEFT': False
        }
        
        self.last_feedback_text = {
            'RIGHT': "",
            'LEFT': ""
        }
    
    def start(self):
        """Initialize new workout session"""
        from constants import WorkoutPhase
        from models import ArmMetrics
        
        # Reset all metrics
        for arm in ['RIGHT', 'LEFT']:
            self.arm_metrics[arm] = ArmMetrics()
        
        self.history.reset()
        self.pose_processor.angle_calculator.reset_buffers()
        
        # Reset state trackers
        self.ai_latched_state = {'RIGHT': False, 'LEFT': False}
        self.last_feedback_text = {'RIGHT': "", 'LEFT': ""}
        
        # Start camera and model
        self.cap = cv2.VideoCapture(0)
        self.holistic_model = mp.solutions.holistic.Holistic(
            min_detection_confidence=self.min_detection_conf,
            min_tracking_confidence=self.min_tracking_conf
        )
        
        # Begin calibration
        self.calibration_manager.start()
        self.phase = WorkoutPhase.CALIBRATION
    
    def stop(self):
        """Clean up session resources"""
        from constants import WorkoutPhase
        
        if self.cap:
            self.cap.release()
        if self.holistic_model:
            self.holistic_model.close()
            self.holistic_model = None
        
        self.phase = WorkoutPhase.INACTIVE
    
    def process_frame(self) -> Tuple[Optional[np.ndarray], bool]:
        """
        Process single frame
        Returns: (processed_frame, should_continue)
        """
        from constants import WorkoutPhase
        
        if not self.cap or not self.cap.isOpened():
            return None, False
        
        success, image = self.cap.read()
        if not success:
            return None, False
        
        # MediaPipe processing
        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.holistic_model.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        current_time = time.time()
        
        # Handle different phases
        if self.phase == WorkoutPhase.CALIBRATION:
            self._process_calibration(results, current_time)
        elif self.phase == WorkoutPhase.COUNTDOWN:
            self._process_countdown(current_time)
        elif self.phase == WorkoutPhase.ACTIVE:
            self._process_workout(results, current_time)
        
        # Draw landmarks (Skeleton Lines)
        if results.pose_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                image, results.pose_landmarks, 
                mp.solutions.pose.POSE_CONNECTIONS
            )
        
        image = self._draw_ui(image, results)
        return image, True
    
    def _process_calibration(self, results, current_time: float):
        """Handle calibration phase"""
        from constants import WorkoutPhase
        complete = self.calibration_manager.process_frame(results, current_time)
        if complete:
            self.phase = WorkoutPhase.COUNTDOWN
            self.start_time = current_time
    
    def _process_countdown(self, current_time: float):
        """Handle countdown phase"""
        from constants import WorkoutPhase
        elapsed = current_time - self.start_time
        if elapsed >= self.countdown_time:
            self.phase = WorkoutPhase.ACTIVE
            self.start_time = current_time
        else:
            self.countdown_remaining = int(self.countdown_time - elapsed)
    
    def _process_workout(self, results, current_time: float):
        """Handle active workout phase with Synchronized AI Feedback"""
        from constants import ArmStage 
        
        if not results.pose_landmarks:
            for arm in ['RIGHT', 'LEFT']:
                self.arm_metrics[arm].stage = ArmStage.LOST.value
            return
        
        # 1. Update AI Latch State (Periodic Check)
        if (current_time - self.last_ai_check) > self.ai_interval:
            self.last_ai_check = current_time
            self._update_ai_latch(results)


        # 2. Get Geometric Angles
        angles = self.pose_processor.get_both_arm_angles(results)
        
        # 3. Process each arm (Math + AI Injection)
        for arm in ['RIGHT', 'LEFT']:
            if angles[arm] is not None:
                # A. Run Math Logic (Sets 'Over Curling' etc, or clears feedback)
                self.rep_counter.process_rep(
                    arm, angles[arm], self.arm_metrics[arm], 
                    current_time, self.history
                )
                
                # B. Inject AI Feedback (If Math is silent)
                if not self.arm_metrics[arm].feedback and self.ai_latched_state[arm]:
                    # Only apply if arm is active (UP) to avoid noise at rest
                    if self.arm_metrics[arm].stage == ArmStage.UP.value:
                        self.arm_metrics[arm].feedback = "AI: Bad Form"
                
                # C. Handle Counting for AI Feedback
                current_text = self.arm_metrics[arm].feedback
                previous_text = self.last_feedback_text[arm]
                
                if current_text == "AI: Bad Form" and previous_text != "AI: Bad Form":
                    if arm == 'RIGHT':
                        self.history.right_feedback_count += 1
                    else:
                        self.history.left_feedback_count += 1
                
                # Update tracker for next frame
                self.last_feedback_text[arm] = current_text


        # Log to history
        self.history.time.append(round(current_time - self.start_time, 2))
        self.history.right_angle.append(angles['RIGHT'] or 0)
        self.history.left_angle.append(angles['LEFT'] or 0)


    def _update_ai_latch(self, results):
        """Run inference and update the latched state using the current exercise's features"""
        
        # Get the list of landmark indices to use as features from the config
        feature_indices = self.exercise_config.ai_features_landmarks
        
        if not results.pose_landmarks or len(feature_indices) == 0:
            self.ai_latched_state['RIGHT'] = False
            self.ai_latched_state['LEFT'] = False
            return
            
        try:
            landmarks = results.pose_landmarks.landmark
            features = []
            
            # Dynamically build the feature vector (X, Y for each landmark index)
            for index in feature_indices:
                features.append(landmarks[index].x)
                features.append(landmarks[index].y)

            # NOTE: The rehab_model.pkl is expected to have 16 features (8 landmarks * 2)
            if len(features) != 16:
                 # Fallback/warning if feature length does not match expected model input
                 print(f"⚠️ AI Model Feature Mismatch: Expected 16, got {len(features)}. Assuming good form.")
                 prediction = 1
            else:
                 # 0 = Bad Form, 1 = Good Form
                 prediction = AIEngine.predict_form(features)
            
            # Update the latch. True = Bad Form detected (prediction 0).
            is_bad_form = (prediction == 0)
            
            # Latch state for both arms (or relevant sides)
            self.ai_latched_state['RIGHT'] = is_bad_form
            self.ai_latched_state['LEFT'] = is_bad_form
            
        except Exception as e:
            print(f"❌ Error generating AI features: {e}")
            self.ai_latched_state['RIGHT'] = False
            self.ai_latched_state['LEFT'] = False
    
    def _draw_ui(self, image: np.ndarray, results) -> np.ndarray:
        """Draw UI overlays on image"""
        from constants import WorkoutPhase
        image = cv2.flip(image, 1)
        return image
    
    def get_state_dict(self) -> dict:
        """Get current state as dictionary for API"""
        # <<< CRITICAL FIX: Include dynamic joint name and exercise name in state dict >>>
        # This line ensures 'exercise_name' is passed to the frontend
        return {
            'exercise_name': self.exercise_config.name,
            'tracked_joint_name': self.exercise_config.joint_to_track.value.title(),
            'RIGHT': self.arm_metrics['RIGHT'].to_dict(),
            'LEFT': self.arm_metrics['LEFT'].to_dict(),
            'status': self.phase.value,
            'remaining': self.countdown_remaining,
            'calibration': {
                'active': self.calibration_manager.data.active,
                'message': self.calibration_manager.data.message,
                'progress': self.calibration_manager.data.progress
            }
        }
    
    def get_final_report(self) -> dict:
        """Generate final session report"""
        return {
            'exercise_name': self.exercise_config.name, 
            'duration': round(self.history.time[-1] if self.history.time else 0, 2),
            'summary': {
                'RIGHT': {
                    'total_reps': self.arm_metrics['RIGHT'].rep_count,
                    'min_time': round(self.arm_metrics['RIGHT'].min_rep_time, 2),
                    'error_count': self.history.right_feedback_count
                },
                'LEFT': {
                    'total_reps': self.arm_metrics['LEFT'].rep_count,
                    'min_time': round(self.arm_metrics['LEFT'].min_rep_time, 2),
                    'error_count': self.history.left_feedback_count
                }
            },
            'calibration': {
                'extended_threshold': self.calibration_manager.data.extended_threshold,
                'contracted_threshold': self.calibration_manager.data.contracted_threshold,
                'safe_min': self.calibration_manager.data.safe_angle_min,
                'safe_max': self.calibration_manager.data.safe_angle_max
            }
        }