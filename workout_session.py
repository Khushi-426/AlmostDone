"""
Main workout session manager - OPTIMIZED VIDEO FEED
"""
import cv2
import mediapipe as mp
import numpy as np
import time
from typing import Tuple, Optional

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
        
        # Initialize components
        angle_calc = AngleCalculator(SMOOTHING_WINDOW)
        self.pose_processor = PoseProcessor(angle_calc)
        
        calibration_data = CalibrationData()
        self.calibration_manager = CalibrationManager(
            self.pose_processor,
            calibration_data,
            CALIBRATION_HOLD_TIME
        )

        
        self.rep_counter = RepCounter(calibration_data, MIN_REP_DURATION)
        self.history = SessionHistory()
        
        # MediaPipe
        self.holistic_model = None
        self.cap = None
        self.min_detection_conf = MIN_DETECTION_CONFIDENCE
        self.min_tracking_conf = MIN_TRACKING_CONFIDENCE
    
    def start(self):
        """Initialize new workout session"""
        from constants import WorkoutPhase
        from models import ArmMetrics
        
        # Reset all metrics
        for arm in ['RIGHT', 'LEFT']:
            self.arm_metrics[arm] = ArmMetrics()
        
        self.history.reset()
        self.pose_processor.angle_calculator.reset_buffers()
        
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
        
        # Draw UI overlays (Minimal - mostly handled by frontend now)
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
        """Handle active workout phase"""
        from constants import ArmStage
        
        if not results.pose_landmarks:
            for arm in ['RIGHT', 'LEFT']:
                self.arm_metrics[arm].stage = ArmStage.LOST.value
            return
        
        angles = self.pose_processor.get_both_arm_angles(results)
        
        for arm in ['RIGHT', 'LEFT']:
            if angles[arm] is not None:
                self.rep_counter.process_rep(
                    arm, angles[arm], self.arm_metrics[arm], 
                    current_time, self.history
                )
        
        # Log to history
        self.history.time.append(round(current_time - self.start_time, 2))
        self.history.right_angle.append(angles['RIGHT'] or 0)
        self.history.left_angle.append(angles['LEFT'] or 0)
    
    def _draw_ui(self, image: np.ndarray, results) -> np.ndarray:
        """Draw UI overlays on image (before flipping for mirror effect)"""
        from constants import WorkoutPhase
        
        h, w, _ = image.shape
        
        # Flip image first for proper orientation (Mirror Effect)
        image = cv2.flip(image, 1)
        
        # [CHANGE] Removed the RED COUNTDOWN drawing logic.
        # Frontend now handles all counters and text overlays for a cleaner look.
        
        if self.phase == WorkoutPhase.CALIBRATION:
            # Minimal backend UI for calibration (Frontend has the main overlay)
            pass
        
        return image
    
    def get_state_dict(self) -> dict:
        """Get current state as dictionary for API"""
        return {
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