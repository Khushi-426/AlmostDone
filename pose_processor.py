"""
MediaPipe pose detection and landmark extraction - AGNOSTIC
"""
import mediapipe as mp
import math
from typing import Dict, Optional
# [Change] Import the new ExerciseConfig for type hinting and configuration
from constants import ExerciseConfig 


class PoseProcessor:
    """Handles MediaPipe pose detection and landmark extraction"""
    
    # [Change] Remove hardcoded ARM_CONFIG
    
    def __init__(self, angle_calculator, exercise_config: ExerciseConfig): # << MODIFIED
        self.angle_calculator = angle_calculator
        self.config = exercise_config # Store the current exercise configuration
    
    def extract_arm_angle(self, landmarks, arm: str) -> Optional[float]:
        """Extract angle for the specified joint using the current exercise config"""
        try:
            # 1. Select the correct landmark index list based on arm/side
            if arm == 'RIGHT':
                indices = self.config.right_landmarks
            elif arm == 'LEFT':
                indices = self.config.left_landmarks
            else:
                return None
            
            # Indices are (A, B, C) where B is the vertex
            A_idx, B_idx, C_idx = indices
            
            # 2. Extract Coordinates
            A = [landmarks[A_idx].x, landmarks[A_idx].y] 
            B = [landmarks[B_idx].x, landmarks[B_idx].y] 
            C = [landmarks[C_idx].x, landmarks[C_idx].y] 
            
            # 3. Check landmark visibility
            if (landmarks[A_idx].visibility < 0.6 or
                landmarks[B_idx].visibility < 0.6 or
                landmarks[C_idx].visibility < 0.6):
                return None

            # 4. Calculate and smooth the angle
            raw_angle = self.angle_calculator.calculate_angle(A, B, C)
            return self.angle_calculator.get_smoothed_angle(arm, raw_angle)
            
        except (KeyError, IndexError, AttributeError):
            return None
    
    def get_both_arm_angles(self, results) -> Dict[str, Optional[int]]:
        """Get angles for both sides defined in the config"""
        if not results.pose_landmarks:
            return {'RIGHT': None, 'LEFT': None}
        
        landmarks = results.pose_landmarks.landmark
        return {
            'RIGHT': self.extract_arm_angle(landmarks, 'RIGHT'),
            'LEFT': self.extract_arm_angle(landmarks, 'LEFT')
        }

    def detect_v_sign(self, results) -> bool:
        """
        Strict V-Sign Detection (Peace Sign).
        Checks:
        1. Index & Middle Extended (Tip < Pip)
        2. Ring & Pinky Curled (Tip > Pip)
        3. Spread: Distance(IndexTip, MiddleTip) > Distance(IndexPip, MiddlePip)
        """
        for hand_landmarks in [results.right_hand_landmarks, results.left_hand_landmarks]:
            if hand_landmarks:
                lm = hand_landmarks.landmark
                
                # Y-coordinates (Note: Y increases downwards)
                index_tip_y, index_pip_y = lm[8].y, lm[6].y
                middle_tip_y, middle_pip_y = lm[12].y, lm[10].y
                ring_tip_y, ring_pip_y = lm[16].y, lm[14].y
                pinky_tip_y, pinky_pip_y = lm[20].y, lm[18].y
                
                # 1. Check Extensions (Index/Middle UP, Ring/Pinky DOWN)
                fingers_correct = (
                    index_tip_y < index_pip_y and
                    middle_tip_y < middle_pip_y and
                    ring_tip_y > ring_pip_y and
                    pinky_tip_y > pinky_pip_y
                )
                
                if not fingers_correct:
                    continue

                # 2. Check "V" Spread (Euclidean Distance)
                # Tips spread should be wider than knuckles
                def dist(p1, p2):
                    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

                tip_spread = dist(lm[8], lm[12])
                pip_spread = dist(lm[6], lm[10])
                
                # The spread at the tips must be significantly larger than at the base
                if tip_spread > (pip_spread * 1.5): 
                    return True
                    
        return False