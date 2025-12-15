# workout_session.py
"""
Main workout session manager - LISTENING MODE INTEGRATED
"""
import cv2
import mediapipe as mp
import numpy as np
import time
from typing import Tuple, Optional

from ai_engine import AIEngine

class WorkoutSession:
    """Manages entire workout session state"""
    
    def __init__(self):
        from constants import (WorkoutPhase, MIN_DETECTION_CONFIDENCE, 
                              MIN_TRACKING_CONFIDENCE, WORKOUT_COUNTDOWN_TIME,
                              CALIBRATION_HOLD_TIME, SMOOTHING_WINDOW, 
                              SAFETY_MARGIN, MIN_REP_DURATION)
        from models import ArmMetrics, CalibrationData, SessionHistory
        from angle_calculator import AngleCalculator
        from pose_processor import PoseProcessor
        from calibration import CalibrationManager
        from rep_counter import RepCounter
        
        self.phase = WorkoutPhase.INACTIVE
        self.start_time = 0.0
        self.countdown_remaining = 0
        self.countdown_time = WORKOUT_COUNTDOWN_TIME
        
        self.arm_metrics = {
            'RIGHT': ArmMetrics(),
            'LEFT': ArmMetrics()
        }
        
        angle_calc = AngleCalculator(SMOOTHING_WINDOW)
        self.pose_processor = PoseProcessor(angle_calc)
        
        calibration_data = CalibrationData()
        self.calibration_manager = CalibrationManager(
            self.pose_processor, calibration_data, 
            CALIBRATION_HOLD_TIME, SAFETY_MARGIN
        )
        
        self.rep_counter = RepCounter(calibration_data, MIN_REP_DURATION)
        self.history = SessionHistory()
        
        self.holistic_model = None
        self.cap = None
        self.min_detection_conf = MIN_DETECTION_CONFIDENCE
        self.min_tracking_conf = MIN_TRACKING_CONFIDENCE

        self.last_ai_check = 0
        self.ai_interval = 0.2
        self.ai_latched_state = {'RIGHT': False, 'LEFT': False}
        self.last_feedback_text = {'RIGHT': "", 'LEFT': ""}
        
        self.gesture_detected = False
        self.listening_mode = False
    
    def start(self):
        from constants import WorkoutPhase
        from models import ArmMetrics
        
        for arm in ['RIGHT', 'LEFT']:
            self.arm_metrics[arm] = ArmMetrics()
        
        self.history.reset()
        self.pose_processor.angle_calculator.reset_buffers()
        
        self.ai_latched_state = {'RIGHT': False, 'LEFT': False}
        self.last_feedback_text = {'RIGHT': "", 'LEFT': ""}
        self.gesture_detected = False
        self.listening_mode = False
        
        self.cap = cv2.VideoCapture(0)
        self.holistic_model = mp.solutions.holistic.Holistic(
            min_detection_confidence=self.min_detection_conf,
            min_tracking_confidence=self.min_tracking_conf,
            model_complexity=1
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
        from constants import WorkoutPhase
        
        if self.cap is None or not self.cap.isOpened(): 
            return None, False
            
        success, image = self.cap.read()
        if not success: return None, False
        
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
        
        if results.pose_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(
                image, results.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
        
        image = self._draw_ui(image, results)
        return image, True
    
    def _process_calibration(self, results, current_time: float):
        from constants import WorkoutPhase
        complete = self.calibration_manager.process_frame(results, current_time)
        if complete:
            self.phase = WorkoutPhase.COUNTDOWN
            self.start_time = current_time
    
    def _process_countdown(self, current_time: float):
        from constants import WorkoutPhase
        elapsed = current_time - self.start_time
        if elapsed >= self.countdown_time:
            self.phase = WorkoutPhase.ACTIVE
            self.start_time = current_time
        else:
            self.countdown_remaining = int(self.countdown_time - elapsed)
    
    def _process_workout(self, results, current_time: float):
        from constants import ArmStage
        
        if not results.pose_landmarks:
            for arm in ['RIGHT', 'LEFT']: self.arm_metrics[arm].stage = ArmStage.LOST.value
            return
        
        if (current_time - self.last_ai_check) > self.ai_interval:
            self.last_ai_check = current_time
            self._update_ai_latch(results)

        angles = self.pose_processor.get_both_arm_angles(results)
        
        for arm in ['RIGHT', 'LEFT']:
            if angles[arm] is not None:
                self.rep_counter.process_rep(
                    arm, angles[arm], self.arm_metrics[arm], 
                    current_time, self.history
                )
                
                # [FIX] AI Feedback Override
                # If rep_counter says "Maintain Form" (default) OR empty, but AI sees bad form -> Override
                current_fb = self.arm_metrics[arm].feedback
                if (not current_fb or current_fb == "Maintain Form") and self.ai_latched_state[arm]:
                    if self.arm_metrics[arm].stage == ArmStage.UP.value:
                        self.arm_metrics[arm].feedback = "AI: Bad Form"
                
                current_text = self.arm_metrics[arm].feedback
                previous_text = self.last_feedback_text[arm]
                
                if current_text == "AI: Bad Form" and previous_text != "AI: Bad Form":
                    if arm == 'RIGHT': self.history.right_feedback_count += 1
                    else: self.history.left_feedback_count += 1
                
                self.last_feedback_text[arm] = current_text

        self.history.time.append(round(current_time - self.start_time, 2))
        self.history.right_angle.append(angles['RIGHT'] or 0)
        self.history.left_angle.append(angles['LEFT'] or 0)

    def _update_ai_latch(self, results):
        try:
            landmarks = results.pose_landmarks.landmark
            features = [
                landmarks[12].x, landmarks[12].y, landmarks[14].x, landmarks[14].y, landmarks[16].x, landmarks[16].y,
                landmarks[11].x, landmarks[11].y, landmarks[13].x, landmarks[13].y, landmarks[15].x, landmarks[15].y
            ]
            prediction = AIEngine.predict_form(features)
            self.ai_latched_state['RIGHT'] = (prediction == 0)
            self.ai_latched_state['LEFT'] = (prediction == 0)
        except Exception:
            self.ai_latched_state['RIGHT'] = False
            self.ai_latched_state['LEFT'] = False
    
    def _draw_ui(self, image: np.ndarray, results) -> np.ndarray:
        image = cv2.flip(image, 1)
        return image
    
    def get_state_dict(self) -> dict:
        return {
            'RIGHT': self.arm_metrics['RIGHT'].to_dict(),
            'LEFT': self.arm_metrics['LEFT'].to_dict(),
            'status': self.phase.value,
            'remaining': self.countdown_remaining,
            'gesture': 'V_SIGN' if self.gesture_detected else None,
            'listening': self.listening_mode,
            'calibration': {
                'active': self.calibration_manager.data.active,
                'message': self.calibration_manager.data.message,
                'progress': self.calibration_manager.data.progress
            }
        }
    
    def get_final_report(self) -> dict:
        return {
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