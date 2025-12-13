# ============================================================================
# pose_processor.py
# ============================================================================
"""
MediaPipe pose detection and landmark extraction
"""
import mediapipe as mp
from typing import Dict, Optional

class PoseProcessor:
    """Handles MediaPipe pose detection and landmark extraction"""
    
    ARM_CONFIG = {
        'RIGHT': {
            'shoulder': mp.solutions.holistic.PoseLandmark.RIGHT_SHOULDER,
            'elbow': mp.solutions.holistic.PoseLandmark.RIGHT_ELBOW,
            'wrist': mp.solutions.holistic.PoseLandmark.RIGHT_WRIST
        },
        'LEFT': {
            'shoulder': mp.solutions.holistic.PoseLandmark.LEFT_SHOULDER,
            'elbow': mp.solutions.holistic.PoseLandmark.LEFT_ELBOW,
            'wrist': mp.solutions.holistic.PoseLandmark.LEFT_WRIST
        }
    }
    
    def __init__(self, angle_calculator):
        self.angle_calculator = angle_calculator
    
    def extract_arm_angle(self, landmarks, arm: str) -> Optional[float]:
        """Extract elbow angle for specified arm"""
        try:
            config = self.ARM_CONFIG[arm]
            
            shoulder = [landmarks[config['shoulder']].x, 
                       landmarks[config['shoulder']].y]
            elbow = [landmarks[config['elbow']].x, 
                    landmarks[config['elbow']].y]
            wrist = [landmarks[config['wrist']].x, 
                    landmarks[config['wrist']].y]
            
            # Check landmark visibility
            if (landmarks[config['shoulder']].visibility < 0.6 or
                landmarks[config['elbow']].visibility < 0.6 or
                landmarks[config['wrist']].visibility < 0.6):
                return None

            
            raw_angle = self.angle_calculator.calculate_angle(shoulder, elbow, wrist)
            return self.angle_calculator.get_smoothed_angle(arm, raw_angle)
            
        except (KeyError, IndexError, AttributeError):
            return None
    
    def get_both_arm_angles(self, results) -> Dict[str, Optional[int]]:
        """Get angles for both arms"""
        if not results.pose_landmarks:
            return {'RIGHT': None, 'LEFT': None}
        
        landmarks = results.pose_landmarks.landmark
        return {
            'RIGHT': self.extract_arm_angle(landmarks, 'RIGHT'),
            'LEFT': self.extract_arm_angle(landmarks, 'LEFT')
        }