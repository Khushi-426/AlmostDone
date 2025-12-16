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
# NOTE: 'models', 'ai_engine', 'constants', 'angle_calculator', 
# 'pose_processor', 'calibration', 'rep_counter' are assumed to exist.
from models import ArmMetrics, CalibrationData, SessionHistory, GhostPose, Landmark2D 
from ai_engine import AIEngine


class WorkoutSession:
    """Manages entire workout session state with optimized performance"""
    
    def __init__(self, exercise_name: str = "Bicep Curl"):
        from constants import (WorkoutPhase, MIN_DETECTION_CONFIDENCE, 
                               MIN_TRACKING_CONFIDENCE, WORKOUT_COUNTDOWN_TIME,
                               CALIBRATION_HOLD_TIME, SMOOTHING_WINDOW, 
                               SAFETY_MARGIN, MIN_REP_DURATION, 
                               EXERCISE_PRESETS, ArmStage, ExerciseJoint) 
        
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
            'RIGHT': ArmMetrics(), # Internal key for physical RIGHT arm
            'LEFT': ArmMetrics()  # Internal key for physical LEFT arm
        }
        
        # Keep smoothing buffers for metrics (angles, reps) but isolate them
        self.landmark_buffer = deque(maxlen=2)  # Used only by _lightweight_smooth (metrics)
        self.color_buffer = deque(maxlen=2)  # Quick color transitions
        
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
        
        # MediaPipe - Optimized for speed
        self.holistic_model = None
        self.cap = None
        self.min_detection_conf = 0.5  # Balanced for speed
        self.min_tracking_conf = 0.5  # Balanced for speed

        # AI State Management - Optimized timing
        self.last_ai_check = 0
        self.ai_interval = 0.1  # Fast checks (100ms)
        
        self.ai_latched_state = {
            'RIGHT': False,
            'LEFT': False
        }
        
        self.last_feedback_text = {
            'RIGHT': "",
            'LEFT': ""
        }

        # OPTIMIZED SKELETON - Essential connections only for speed
        self.ghost_pose = GhostPose(instruction="Initializing...") 
        
        # Streamlined connections for faster rendering
        self.ghost_connections = [
            # Arms
            (mp_pose_lm.RIGHT_SHOULDER.value, mp_pose_lm.RIGHT_ELBOW.value), 
            (mp_pose_lm.RIGHT_ELBOW.value, mp_pose_lm.RIGHT_WRIST.value),
            (mp_pose_lm.LEFT_SHOULDER.value, mp_pose_lm.LEFT_ELBOW.value), 
            (mp_pose_lm.LEFT_ELBOW.value, mp_pose_lm.LEFT_WRIST.value),
            
            # Torso
            (mp_pose_lm.RIGHT_SHOULDER.value, mp_pose_lm.LEFT_SHOULDER.value), 
            (mp_pose_lm.RIGHT_SHOULDER.value, mp_pose_lm.RIGHT_HIP.value),
            (mp_pose_lm.LEFT_SHOULDER.value, mp_pose_lm.LEFT_HIP.value),
            (mp_pose_lm.RIGHT_HIP.value, mp_pose_lm.LEFT_HIP.value), 
            
            # Legs
            (mp_pose_lm.RIGHT_HIP.value, mp_pose_lm.RIGHT_KNEE.value), 
            (mp_pose_lm.RIGHT_KNEE.value, mp_pose_lm.RIGHT_ANKLE.value),
            (mp_pose_lm.LEFT_HIP.value, mp_pose_lm.LEFT_KNEE.value), 
            (mp_pose_lm.LEFT_KNEE.value, mp_pose_lm.LEFT_ANKLE.value),
            
            # Minimal face for alignment reference
            (mp_pose_lm.NOSE.value, mp_pose_lm.RIGHT_SHOULDER.value),
            (mp_pose_lm.NOSE.value, mp_pose_lm.LEFT_SHOULDER.value),
        ]
        self.ghost_pose.connections = self.ghost_connections
        
        # Cache for performance
        self._last_ghost_update = 0
        self._ghost_update_interval = 0.0 # Update every frame
    
    def start(self):
        """Initialize new workout session - FAST START"""
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

        # Start camera with optimal settings for SPEED
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Lower res for speed
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimal buffer for low latency
        
        # Fast MediaPipe initialization
        self.holistic_model = mp.solutions.holistic.Holistic(
            min_detection_confidence=self.min_detection_conf,
            min_tracking_confidence=self.min_tracking_conf,
            model_complexity=0,  # Fastest model
            smooth_landmarks=True  # Built-in smoothing
        )
        
        self.calibration_manager.start()
        self.phase = WorkoutPhase.CALIBRATION
    
    def stop(self):
        from constants import WorkoutPhase
        
        if self.cap is not None: 
            self.cap.release()
            
        if self.holistic_model is not None:
            self.holistic_model.close()
            self.holistic_model = None
            
        self.phase = WorkoutPhase.INACTIVE

    def set_listening(self, active: bool):
        self.listening_mode = active

    def process_frame(self) -> Tuple[Optional[np.ndarray], bool]:
        """Process single frame - OPTIMIZED FOR SPEED"""
        from constants import WorkoutPhase
        
        if self.cap is None or not self.cap.isOpened(): 
            return None, False
            
        success, image = self.cap.read()
        if not success: return None, False
        
        # FIX: Ensure non-mirrored (Observer) view for correct form perception 
        image = cv2.flip(image, 1)

        # MediaPipe processing - minimal overhead
        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        results = self.holistic_model.process(image)
        
        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        if self.listening_mode:
            image = cv2.flip(image, 1)
            cv2.putText(image, "LISTENING...", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            return image, True

        current_time = time.time()
        
        self.gesture_detected = self.pose_processor.detect_v_sign(results)

        if self.phase == WorkoutPhase.CALIBRATION:
            self._process_calibration(results, current_time)
        elif self.phase == WorkoutPhase.COUNTDOWN:
            self._process_countdown(current_time)
        elif self.phase == WorkoutPhase.ACTIVE:
            self._process_workout(results, current_time)
        
        # Skip drawing user skeleton for speed (ghost is enough)
        
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

    def _lightweight_smooth(self, current_landmarks: dict) -> dict:
        """
        Ultra-light smoothing (2 frames). 
        Used only for metrics (angles, reps) where stability is paramount.
        The ghost figure bypasses this for maximum speed.
        """
        self.landmark_buffer.append(current_landmarks)
        
        if len(self.landmark_buffer) < 2:
            return current_landmarks
        
        # Simple average of last 2 frames only
        smoothed = {}
        for idx in current_landmarks.keys():
            if idx in self.landmark_buffer[0]:
                smoothed[idx] = Landmark2D(
                    x=(current_landmarks[idx].x + self.landmark_buffer[0][idx].x) / 2,
                    y=(current_landmarks[idx].y + self.landmark_buffer[0][idx].y) / 2
                )
            else:
                smoothed[idx] = current_landmarks[idx]
        
        return smoothed

    def _quick_color_smooth(self, new_color: str) -> str:
        """Fast color smoothing - minimal delay"""
        self.color_buffer.append(new_color)
        
        if len(self.color_buffer) < 2:
            return new_color
        
        # If last 2 colors agree, use it; otherwise use newest (minimal lag)
        if self.color_buffer[0] == self.color_buffer[1]:
            return self.color_buffer[1]
        return new_color

    def _calculate_ideal_pose_realtime(self, reference_landmarks) -> None:
        """
        OPTIMIZED: Real-time ghost calculation with minimal overhead.
        Uses RAW (unsmoothed) landmark data for maximum speed.
        """
        from constants import ArmStage, ExerciseJoint

        current_time = time.time()
        
        self._last_ghost_update = current_time

        metrics = self.arm_metrics['RIGHT']
        
        # 1. Determine Target Stage & Instruction
        if metrics.stage in [ArmStage.DOWN.value, ArmStage.MOVING_UP.value]:
            target_stage = ArmStage.UP.value
            instruction = "LIFT UP"
        elif metrics.stage in [ArmStage.UP.value, ArmStage.MOVING_DOWN.value]:
            target_stage = ArmStage.DOWN.value
            instruction = "LOWER DOWN"
        else:
            target_stage = ArmStage.DOWN.value
            instruction = "BEGIN"

        # 2. Color with quick smoothing
        raw_color = metrics.feedback_color
        ghost_color = self._quick_color_smooth(raw_color)
        
        if metrics.feedback:
            instruction = metrics.feedback.replace("AI: ", "")
            
        # 3. Build Full Body Ghost - DIRECT COPY (NO SMOOTHING APPLIED HERE)
        target_landmarks_2d = {}
        try:
            # Copy all detected landmarks directly from the CURRENT frame
            for idx in range(33):
                if idx < len(reference_landmarks) and reference_landmarks[idx].visibility > 0.0:
                    lm = reference_landmarks[idx]
                    target_landmarks_2d[idx] = Landmark2D(x=lm.x, y=lm.y)
        except Exception:
            self.ghost_pose.instruction = "LOST"
            self.ghost_pose.color = "GRAY"
            return

        # 4. Adjust ONLY exercise limbs to show ideal position
        R_A, R_B, R_C = self.exercise_config.right_landmarks
        L_A, L_B, L_C = self.exercise_config.left_landmarks

        target_angle = (self.calibration_manager.data.contracted_threshold 
                        if target_stage == ArmStage.UP.value 
                        else self.calibration_manager.data.extended_threshold)

        # --- OPTIMIZED IK CALCULATION (Right Side) ---
        if all(lm in target_landmarks_2d for lm in [R_A, R_B, R_C]):
            P_A = np.array([target_landmarks_2d[R_A].x, target_landmarks_2d[R_A].y])
            P_B = np.array([target_landmarks_2d[R_B].x, target_landmarks_2d[R_B].y])
            
            # Calculate limb length B->C
            orig_len_BC = np.hypot(reference_landmarks[R_C].x - reference_landmarks[R_B].x, 
                                   reference_landmarks[R_C].y - reference_landmarks[R_B].y)
            
            # Vector B -> A (Proximal segment)
            V_BA = P_A - P_B 
            angle_BA = np.arctan2(V_BA[1], V_BA[0])

            # Rotation required (Elbow/Knee joints flex *inward*)
            if self.exercise_config.joint_to_track in [ExerciseJoint.ELBOW, ExerciseJoint.KNEE]:
                rotation_angle = np.pi - np.radians(target_angle)
            else:
                rotation_angle = np.radians(target_angle)

            # Check if user is facing left or right (based on shoulder X position)
            if target_landmarks_2d[R_A].x > target_landmarks_2d[L_A].x: # Facing right/away
                 final_angle = angle_BA + rotation_angle 
            else: # Facing left/towards
                 final_angle = angle_BA - rotation_angle 
            
            # Set new position for right limb (R_C)
            target_landmarks_2d[R_C] = Landmark2D(
                x=P_B[0] + orig_len_BC * np.cos(final_angle),
                y=P_B[1] + orig_len_BC * np.sin(final_angle)
            )

        # --- OPTIMIZED IK CALCULATION (Left Side) ---
        if all(lm in target_landmarks_2d for lm in [L_A, L_B, L_C]):
            P_A_L = np.array([target_landmarks_2d[L_A].x, target_landmarks_2d[L_A].y])
            P_B_L = np.array([target_landmarks_2d[L_B].x, target_landmarks_2d[L_B].y])
            
            orig_len_BC_L = np.hypot(reference_landmarks[L_C].x - reference_landmarks[L_B].x,
                                     reference_landmarks[L_C].y - reference_landmarks[L_B].y)
            
            V_BA_L = P_A_L - P_B_L
            angle_BA_L = np.arctan2(V_BA_L[1], V_BA_L[0])

            if self.exercise_config.joint_to_track in [ExerciseJoint.ELBOW, ExerciseJoint.KNEE]:
                 rotation_angle = np.pi - np.radians(target_angle)
            else:
                 rotation_angle = np.radians(target_angle)

            # Mirror logic for the left arm
            if target_landmarks_2d[R_A].x > target_landmarks_2d[L_A].x: # Facing right/away
                 final_angle_L = angle_BA_L - rotation_angle 
            else: # Facing towards/left
                 final_angle_L = angle_BA_L + rotation_angle 

            target_landmarks_2d[L_C] = Landmark2D(
                x=P_B_L[0] + orig_len_BC_L * np.cos(final_angle_L),
                y=P_B_L[1] + orig_len_BC_L * np.sin(final_angle_L)
            )

        # 5. NO LANDMARK SMOOTHING APPLIED HERE FOR MAX SPEED
        smoothed_landmarks = target_landmarks_2d

        # Update ghost pose
        self.ghost_pose.landmarks = smoothed_landmarks
        self.ghost_pose.color = ghost_color
        self.ghost_pose.instruction = instruction

    def _process_workout(self, results, current_time: float):
        """Handle active workout phase - OPTIMIZED"""
        from constants import ArmStage 
        
        if not results.pose_landmarks:
            for arm in ['RIGHT', 'LEFT']:
                self.arm_metrics[arm].stage = ArmStage.LOST.value
                self.arm_metrics[arm].feedback_color = "GRAY"
            self.ghost_pose.instruction = "STEP IN VIEW"
            self.ghost_pose.color = "GRAY"
            return
        
        # 1. Fast AI checks (throttled to 100ms)
        if (current_time - self.last_ai_check) > self.ai_interval:
            self.last_ai_check = current_time
            self._update_ai_latch(results)

        # 2. Get Angles (Uses built-in smoothing or AngleCalculator's smoothing)
        angles = self.pose_processor.get_both_arm_angles(results)
        
        # 3. Process each arm
        for arm in ['RIGHT', 'LEFT']:
            if angles[arm] is not None:
                self.arm_metrics[arm].angle = angles[arm]
                self.rep_counter.process_rep(
                    arm, angles[arm], self.arm_metrics[arm], 
                    current_time, self.history
                )
                
                # Apply AI feedback if latched and no rep-specific feedback
                if not self.arm_metrics[arm].feedback and self.ai_latched_state[arm]:
                    if self.arm_metrics[arm].stage in [ArmStage.UP.value, ArmStage.MOVING_UP.value]:
                        self.arm_metrics[arm].feedback = "AI: Fix Form"
                
                # Fast color determination
                if self.arm_metrics[arm].feedback:
                    self.arm_metrics[arm].feedback_color = "RED"
                elif self.arm_metrics[arm].stage in [ArmStage.UP.value, ArmStage.DOWN.value]:
                     self.arm_metrics[arm].feedback_color = "GREEN"
                elif self.arm_metrics[arm].stage in [ArmStage.MOVING_UP.value, ArmStage.MOVING_DOWN.value]:
                    self.arm_metrics[arm].feedback_color = "YELLOW"
                else:
                    self.arm_metrics[arm].feedback_color = "GRAY"

                # Log AI feedback event
                current_text = self.arm_metrics[arm].feedback
                previous_text = self.last_feedback_text[arm]
                
                if current_text and current_text.startswith("AI:") and previous_text != current_text:
                    if arm == 'RIGHT':
                        self.history.right_feedback_count += 1
                    else:
                        self.history.left_feedback_count += 1
                
                self.last_feedback_text[arm] = current_text
                
            else:
                self.arm_metrics[arm].feedback_color = "GRAY"

        # 4. Update Ghost - REAL-TIME (updates every frame now)
        if results.pose_landmarks:
             self._calculate_ideal_pose_realtime(results.pose_landmarks.landmark)

        # Log history
        self.history.time.append(round(current_time - self.start_time, 2))
        self.history.right_angle.append(angles['RIGHT'] or 0)
        self.history.left_angle.append(angles['LEFT'] or 0)

    def _update_ai_latch(self, results):
        """Fast AI inference"""
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

            # Ensure the feature vector size matches the expected input for the AI model
            if len(features) != 16:
                 prediction = 1 # Treat as good form if features are incomplete
            else:
                 prediction = AIEngine.predict_form(features)
            
            is_bad_form = (prediction == 0)
            
            # Latch bad form state for both sides (assuming whole-body form check)
            self.ai_latched_state['RIGHT'] = is_bad_form
            self.ai_latched_state['LEFT'] = is_bad_form
            
        except Exception as e:
            # Safely disable AI if an error occurs
            self.ai_latched_state['RIGHT'] = False
            self.ai_latched_state['LEFT'] = False
    
    def get_state_dict(self) -> dict:
        """
        Get current state for API.
        
        FIX: Swaps the metrics output to match the non-mirrored screen display.
        The user's physical RIGHT arm appears on the LEFT of the screen, 
        and the physical LEFT arm appears on the RIGHT of the screen.
        """
        right_metrics = self.arm_metrics['RIGHT'].to_dict() # Physical RIGHT arm data
        left_metrics = self.arm_metrics['LEFT'].to_dict()   # Physical LEFT arm data

        return {
            'exercise_name': self.exercise_config.name,
            'tracked_joint_name': self.exercise_config.joint_to_track.value.title(),
            
            # SWAP: We map the physical LEFT arm's data to the 'RIGHT' screen position
            # and the physical RIGHT arm's data to the 'LEFT' screen position.
            'RIGHT': left_metrics,  # Data for the arm appearing on the RIGHT side of the screen (User's physical LEFT)
            'LEFT': right_metrics,  # Data for the arm appearing on the LEFT side of the screen (User's physical RIGHT)
            
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
                'landmarks': {
                    str(k): [v.x, v.y] for k, v in self.ghost_pose.landmarks.items()
                },
                'color': self.ghost_pose.color,
                'instruction': self.ghost_pose.instruction,
                'connections': self.ghost_connections
            }
        }
    
    def get_final_report(self) -> dict:
        """Generate final session report"""
        # The final report does not need to be swapped, as it reports physical data.
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