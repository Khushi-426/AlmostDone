# workout_session.py
"""
Main workout session manager - OPTIMIZED FOR SPEED & ACCURACY
"""
import cv2
import mediapipe as mp
import numpy as np
import time
from typing import Tuple, Optional
from collections import deque

from mediapipe.python.solutions.holistic import PoseLandmark as mp_pose_lm 
from models import ArmMetrics, CalibrationData, SessionHistory, GhostPose, Landmark2D 
from ai_engine import AIEngine

# Initialize MediaPipe Drawing Utils
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_holistic = mp.solutions.holistic

class WorkoutSession:
    """Manages entire workout session state with optimized performance"""
    
    def __init__(self, exercise_name: str = "Bicep Curl"):
        from constants import (WorkoutPhase, WORKOUT_COUNTDOWN_TIME,
                               CALIBRATION_HOLD_TIME, SMOOTHING_WINDOW, 
                               SAFETY_MARGIN, MIN_REP_DURATION, 
                               EXERCISE_PRESETS) 
        
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
        
        # --- TOGGLE STATE FOR GHOST OVERLAY ---
        # DEFAULT: False (Show CV Dots first, not Ghost)
        self.show_ghost = False 
        
        self.arm_metrics = {
            'RIGHT': ArmMetrics(), 
            'LEFT': ArmMetrics() 
        }
        
        self.landmark_buffer = deque(maxlen=2)
        self.color_buffer = deque(maxlen=2)
        
        # Initialize components
        angle_calc = AngleCalculator(SMOOTHING_WINDOW)
        self.pose_processor = PoseProcessor(angle_calc, self.exercise_config) 
        
        calibration_data = CalibrationData()
        self.calibration_manager = CalibrationManager(
            self.pose_processor,
            calibration_data, 
            CALIBRATION_HOLD_TIME, 
            SAFETY_MARGIN
        )
        
        self.rep_counter = RepCounter(calibration_data, MIN_REP_DURATION)
        self.history = SessionHistory()
        
        # MediaPipe
        self.holistic_model = None
        self.cap = None
        self.min_detection_conf = 0.5 
        self.min_tracking_conf = 0.5 

        # AI State
        self.last_ai_check = 0
        self.ai_interval = 0.2  
        self.ai_latched_state = {'RIGHT': False, 'LEFT': False}
        self.listening_mode = False 
        self.last_feedback_text = {'RIGHT': "", 'LEFT': ""}

        # Ghost Skeleton Setup
        self.ghost_pose = GhostPose(instruction="Initializing...") 
        self.ghost_connections = [
            (mp_pose_lm.RIGHT_SHOULDER.value, mp_pose_lm.RIGHT_ELBOW.value), 
            (mp_pose_lm.RIGHT_ELBOW.value, mp_pose_lm.RIGHT_WRIST.value),
            (mp_pose_lm.LEFT_SHOULDER.value, mp_pose_lm.LEFT_ELBOW.value), 
            (mp_pose_lm.LEFT_ELBOW.value, mp_pose_lm.LEFT_WRIST.value),
            (mp_pose_lm.RIGHT_SHOULDER.value, mp_pose_lm.LEFT_SHOULDER.value), 
            (mp_pose_lm.RIGHT_SHOULDER.value, mp_pose_lm.RIGHT_HIP.value),
            (mp_pose_lm.LEFT_SHOULDER.value, mp_pose_lm.LEFT_HIP.value),
            (mp_pose_lm.RIGHT_HIP.value, mp_pose_lm.LEFT_HIP.value), 
            (mp_pose_lm.RIGHT_HIP.value, mp_pose_lm.RIGHT_KNEE.value), 
            (mp_pose_lm.RIGHT_KNEE.value, mp_pose_lm.RIGHT_ANKLE.value),
            (mp_pose_lm.LEFT_HIP.value, mp_pose_lm.LEFT_KNEE.value), 
            (mp_pose_lm.LEFT_KNEE.value, mp_pose_lm.LEFT_ANKLE.value),
            (mp_pose_lm.NOSE.value, mp_pose_lm.RIGHT_SHOULDER.value),
            (mp_pose_lm.NOSE.value, mp_pose_lm.LEFT_SHOULDER.value),
        ]
        self.ghost_pose.connections = self.ghost_connections
        
        # Gesture Stabilization
        self._frames_in_active = 0 
        self.gesture_active_until = 0.0 
        self.gesture_hold_duration = 2.0 
    
    def start(self):
        from constants import WorkoutPhase
        
        for arm in ['RIGHT', 'LEFT']:
            self.arm_metrics[arm] = ArmMetrics()
        
        self.history.reset()
        self.pose_processor.angle_calculator.reset_buffers()
        self.landmark_buffer.clear()
        self.color_buffer.clear()
        
        self.ai_latched_state = {'RIGHT': False, 'LEFT': False}
        self.last_feedback_text = {'RIGHT': "", 'LEFT': ""}
        self.ghost_pose = GhostPose(instruction="Ready...", connections=self.ghost_connections) 
        self._frames_in_active = 0 
        self.gesture_active_until = 0.0

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        self.holistic_model = mp.solutions.holistic.Holistic(
            min_detection_confidence=self.min_detection_conf,
            min_tracking_confidence=self.min_tracking_conf,
            model_complexity=0,
            smooth_landmarks=True
        )
        
        self.calibration_manager.start()
        self.phase = WorkoutPhase.CALIBRATION
    
    def stop(self):
        from constants import WorkoutPhase
        if self.cap is not None: self.cap.release()
        if self.holistic_model is not None: self.holistic_model.close()
        self.holistic_model = None
        self.phase = WorkoutPhase.INACTIVE

    def set_listening(self, active: bool):
        self.listening_mode = active

    def toggle_ghost(self):
        """Toggles between Ghost Skeleton and Standard CV Dots"""
        self.show_ghost = not self.show_ghost
        return self.show_ghost

    def get_cv_color(self, color_name: str) -> Tuple[int, int, int]:
        colors = { "GREEN": (0, 255, 0), "YELLOW": (0, 255, 255), "RED": (0, 0, 255), "GRAY": (150, 150, 150), "WHITE": (255, 255, 255) }
        if not color_name or not isinstance(color_name, str): return (255, 255, 255)
        return colors.get(color_name.upper(), (255, 255, 255))

    def _draw_overlay(self, image: np.ndarray, results=None):
        """
        Draws the overlay.
        - If show_ghost=True: Draws the GHOST SKELETON (Guidance).
        - If show_ghost=False: Draws the USER SKELETON (CV Dots).
        """
        h, w, _ = image.shape
        ghost_color = self.get_cv_color(self.ghost_pose.color)

        # 1. SKELETON DRAWING (Toggleable)
        if self.show_ghost:
            # Draw Ghost (Ideal Pose)
            for p1_idx, p2_idx in self.ghost_pose.connections:
                p1 = self.ghost_pose.landmarks.get(p1_idx)
                p2 = self.ghost_pose.landmarks.get(p2_idx)
                if p1 and p2:
                    p1_px = (int(p1.x * w), int(p1.y * h))
                    p2_px = (int(p2.x * w), int(p2.y * h))
                    cv2.line(image, p1_px, p2_px, ghost_color, 2)
                    cv2.circle(image, p1_px, 5, ghost_color, -1)
                    cv2.circle(image, p2_px, 5, ghost_color, -1)
        else:
            # Draw "CV Dots" (Actual User Pose) using MediaPipe utils
            if results and results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_holistic.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style()
                )

     
        # [REMOVED ALL REP COUNT AND FEEDBACK LINES AS REQUESTED] 

    def process_frame(self) -> Tuple[Optional[np.ndarray], bool]:
        """Process single frame - OPTIMIZED FOR SPEED"""
        from constants import WorkoutPhase
        
        if self.cap is None or not self.cap.isOpened(): 
            image = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(image, "CAMERA ERROR", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            return image, True
        
        success, image = self.cap.read()
        if not success: return None, False
        
        image = cv2.flip(image, 1) # Mirror view for user comfort

        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.holistic_model.process(image)
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        if self.listening_mode:
            cv2.putText(image, "LISTENING...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            self._draw_overlay(image, results) 
            return image, True

        current_time = time.time()
        
        raw_gesture_detected = self.pose_processor.detect_v_sign(results)
        if raw_gesture_detected:
            self.gesture_active_until = current_time + self.gesture_hold_duration
            self.gesture_detected = True
        else:
            self.gesture_detected = (current_time < self.gesture_active_until)

        if self.phase == WorkoutPhase.CALIBRATION:
            self._process_calibration(results, current_time)
        elif self.phase == WorkoutPhase.COUNTDOWN:
            self._process_countdown(current_time)
        elif self.phase == WorkoutPhase.ACTIVE:
            STABILIZATION_FRAMES = 5 
            if self._frames_in_active < STABILIZATION_FRAMES:
                self._frames_in_active += 1
            else:
                self._process_workout(results, current_time)

        self._draw_overlay(image, results) # Pass results for CV Dots
        
        return image, True
    
    def _process_calibration(self, results, current_time: float):
        from constants import WorkoutPhase
        complete = self.calibration_manager.process_frame(results, current_time)
        if complete:
            self.phase = WorkoutPhase.COUNTDOWN
            self.start_time = current_time
            
        if results.pose_landmarks:
             self.ghost_pose.instruction = self.calibration_manager.data.message
             self.ghost_pose.color = "GRAY"
    
    def _process_countdown(self, current_time: float):
        from constants import WorkoutPhase
        elapsed = current_time - self.start_time
        if elapsed >= self.countdown_time:
            self.phase = WorkoutPhase.ACTIVE
            self.start_time = current_time
        else:
            self.countdown_remaining = int(self.countdown_time - elapsed)
            self.ghost_pose.instruction = f"START IN {self.countdown_remaining}"
            self.ghost_pose.color = "YELLOW"

    def _quick_color_smooth(self, new_color: str) -> str:
        self.color_buffer.append(new_color)
        if len(self.color_buffer) < 2: return new_color
        if self.color_buffer[0] == self.color_buffer[1]: return self.color_buffer[1]
        return new_color

    def _calculate_ideal_pose_realtime(self, reference_landmarks) -> None:
        """OPTIMIZED: Real-time ghost calculation"""
        from constants import ArmStage, ExerciseJoint
        
        # If ghost is disabled, skip calculation to save CPU
        if not self.show_ghost:
            return

        current_time = time.time()
        metrics = self.arm_metrics['RIGHT']
        
        if metrics.stage in [ArmStage.DOWN.value, ArmStage.MOVING_UP.value]:
            target_stage = ArmStage.UP.value
            instruction = "LIFT UP"
        elif metrics.stage in [ArmStage.UP.value, ArmStage.MOVING_DOWN.value]:
            target_stage = ArmStage.DOWN.value
            instruction = "LOWER DOWN"
        else:
            target_stage = ArmStage.DOWN.value
            instruction = "BEGIN"

        raw_color = metrics.feedback_color
        ghost_color = self._quick_color_smooth(raw_color)
        if metrics.feedback: instruction = metrics.feedback.replace("AI: ", "")
            
        target_landmarks_2d = {}
        try:
            for idx in range(33):
                if idx < len(reference_landmarks) and reference_landmarks[idx].visibility > 0.0:
                    lm = reference_landmarks[idx]
                    target_landmarks_2d[idx] = Landmark2D(x=lm.x, y=lm.y)
        except Exception:
            self.ghost_pose.instruction = "LOST"
            self.ghost_pose.color = "GRAY"
            return

        R_A, R_B, R_C = self.exercise_config.right_landmarks
        L_A, L_B, L_C = self.exercise_config.left_landmarks

        target_angle = (self.calibration_manager.data.contracted_threshold 
                        if target_stage == ArmStage.UP.value 
                        else self.calibration_manager.data.extended_threshold)

        # Inverse Kinematics Logic (Same as before, omitted for brevity but preserved)
        if all(lm in target_landmarks_2d for lm in [R_A, R_B, R_C]):
            P_A = np.array([target_landmarks_2d[R_A].x, target_landmarks_2d[R_A].y])
            P_B = np.array([target_landmarks_2d[R_B].x, target_landmarks_2d[R_B].y])
            orig_len_BC = np.hypot(reference_landmarks[R_C].x - reference_landmarks[R_B].x, reference_landmarks[R_C].y - reference_landmarks[R_B].y)
            V_BA = P_A - P_B 
            angle_BA = np.arctan2(V_BA[1], V_BA[0])
            rotation_angle = np.pi - np.radians(target_angle) if self.exercise_config.joint_to_track in [ExerciseJoint.ELBOW, ExerciseJoint.KNEE] else np.radians(target_angle)
            final_angle = angle_BA + rotation_angle if target_landmarks_2d[R_A].x > target_landmarks_2d[L_A].x else angle_BA - rotation_angle 
            target_landmarks_2d[R_C] = Landmark2D(x=P_B[0] + orig_len_BC * np.cos(final_angle), y=P_B[1] + orig_len_BC * np.sin(final_angle))

        if all(lm in target_landmarks_2d for lm in [L_A, L_B, L_C]):
            P_A_L = np.array([target_landmarks_2d[L_A].x, target_landmarks_2d[L_A].y])
            P_B_L = np.array([target_landmarks_2d[L_B].x, target_landmarks_2d[L_B].y])
            orig_len_BC_L = np.hypot(reference_landmarks[L_C].x - reference_landmarks[L_B].x, reference_landmarks[L_C].y - reference_landmarks[L_B].y)
            V_BA_L = P_A_L - P_B_L
            angle_BA_L = np.arctan2(V_BA_L[1], V_BA_L[0])
            rotation_angle = np.pi - np.radians(target_angle) if self.exercise_config.joint_to_track in [ExerciseJoint.ELBOW, ExerciseJoint.KNEE] else np.radians(target_angle)
            final_angle_L = angle_BA_L - rotation_angle if target_landmarks_2d[R_A].x > target_landmarks_2d[L_A].x else angle_BA_L + rotation_angle 
            target_landmarks_2d[L_C] = Landmark2D(x=P_B_L[0] + orig_len_BC_L * np.cos(final_angle_L), y=P_B_L[1] + orig_len_BC_L * np.sin(final_angle_L))

        self.ghost_pose.landmarks = target_landmarks_2d
        self.ghost_pose.color = ghost_color
        self.ghost_pose.instruction = instruction

    def _process_workout(self, results, current_time: float):
        """Handle active workout phase"""
        from constants import ArmStage 
        
        if not results.pose_landmarks:
            self.ghost_pose.instruction = "STEP IN VIEW"
            self.ghost_pose.color = "GRAY"
            return
        
        if (current_time - self.last_ai_check) > self.ai_interval:
            self.last_ai_check = current_time
            self._update_ai_latch(results)

        angles = self.pose_processor.get_both_arm_angles(results)
        
        for arm in ['RIGHT', 'LEFT']:
            if angles[arm] is not None:
                self.arm_metrics[arm].angle = angles[arm]
                self.rep_counter.process_rep(arm, angles[arm], self.arm_metrics[arm], current_time, self.history)
                
                if not self.arm_metrics[arm].feedback and self.ai_latched_state[arm]:
                    if self.arm_metrics[arm].stage in [ArmStage.UP.value, ArmStage.MOVING_UP.value]:
                        self.arm_metrics[arm].feedback = "AI: Fix Form"
                
                if self.arm_metrics[arm].feedback:
                    self.arm_metrics[arm].feedback_color = "RED"
                elif self.arm_metrics[arm].stage in [ArmStage.UP.value, ArmStage.DOWN.value]:
                     self.arm_metrics[arm].feedback_color = "GREEN"
                elif self.arm_metrics[arm].stage in [ArmStage.MOVING_UP.value, ArmStage.MOVING_DOWN.value]:
                    self.arm_metrics[arm].feedback_color = "YELLOW"
                else:
                    self.arm_metrics[arm].feedback_color = "GRAY"

                current_text = self.arm_metrics[arm].feedback
                previous_text = self.last_feedback_text[arm]
                
                if current_text and current_text.startswith("AI:") and previous_text != current_text:
                    if arm == 'RIGHT': self.history.right_feedback_count += 1
                    else: self.history.left_feedback_count += 1
                
                self.last_feedback_text[arm] = current_text
            else:
                self.arm_metrics[arm].feedback_color = "GRAY"

        if results.pose_landmarks:
             self._calculate_ideal_pose_realtime(results.pose_landmarks.landmark)

        self.history.time.append(round(current_time - self.start_time, 2))
        self.history.right_angle.append(angles['RIGHT'] or 0)
        self.history.left_angle.append(angles['LEFT'] or 0)

    def _update_ai_latch(self, results):
        feature_indices = self.exercise_config.ai_features_landmarks
        if not results.pose_landmarks or len(feature_indices) == 0:
            self.ai_latched_state['RIGHT'] = False
            self.ai_latched_state['LEFT'] = False
            return
        try:
            landmarks = results.pose_landmarks.landmark
            features = []
            for index in feature_indices:
                features.append(landmarks[index].x)
                features.append(landmarks[index].y)
            if len(features) != 16: prediction = 1 
            else: prediction = AIEngine.predict_form(features)
            is_bad_form = (prediction == 0)
            self.ai_latched_state['RIGHT'] = is_bad_form
            self.ai_latched_state['LEFT'] = is_bad_form
        except Exception:
            self.ai_latched_state['RIGHT'] = False
            self.ai_latched_state['LEFT'] = False
    
    def get_state_dict(self) -> dict:
        right_metrics = self.arm_metrics['RIGHT'].to_dict() 
        left_metrics = self.arm_metrics['LEFT'].to_dict() 

        return {
            'exercise_name': self.exercise_config.name,
            'tracked_joint_name': self.exercise_config.joint_to_track.value.title(),
            'RIGHT': left_metrics,  
            'LEFT': right_metrics,  
            'status': self.phase.value,
            'remaining': self.countdown_remaining,
            'gesture': 'V_SIGN' if self.gesture_detected else None,
            'listening': self.listening_mode,
            'calibration': {
                'active': self.calibration_manager.data.active,
                'message': self.calibration_manager.data.message,
                'progress': self.calibration_manager.data.progress
            },
            'ghost_pose': {
                'landmarks': {str(k): [v.x, v.y] for k, v in self.ghost_pose.landmarks.items()},
                'color': self.ghost_pose.color,
                'instruction': self.ghost_pose.instruction,
                'connections': self.ghost_connections
            }
        }
    
    def get_final_report(self) -> dict:
        return {
            'exercise_name': self.exercise_config.name, 
            'duration': round(self.history.time[-1] if self.history.time else 0, 2),
            'summary': {
                'RIGHT': {'total_reps': self.arm_metrics['RIGHT'].rep_count, 'min_time': round(self.arm_metrics['RIGHT'].min_rep_time, 2), 'error_count': self.history.right_feedback_count},
                'LEFT': {'total_reps': self.arm_metrics['LEFT'].rep_count, 'min_time': round(self.arm_metrics['LEFT'].min_rep_time, 2), 'error_count': self.history.left_feedback_count}
            },
            'calibration': {
                'extended_threshold': self.calibration_manager.data.extended_threshold,
                'contracted_threshold': self.calibration_manager.data.contracted_threshold,
                'safe_min': self.calibration_manager.data.safe_angle_min,
                'safe_max': self.calibration_manager.data.safe_angle_max
            }
        }