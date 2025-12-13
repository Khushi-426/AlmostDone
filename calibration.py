"""
Calibration logic and threshold calculation - ENHANCED
"""
import numpy as np
from typing import List
import time

class CalibrationManager:
    """Manages the calibration process"""
    
    def __init__(self, pose_processor, calibration_data, 
                 hold_time: float = 5, safety_margin: int = 10):
        self.pose_processor = pose_processor
        self.data = calibration_data
        self.hold_time = hold_time
        self.safety_margin = safety_margin
        
        # ADDED: Minimum samples required for valid calibration
        self.min_samples = 20
    
    def start(self):
        """Initialize calibration"""
        from constants import CalibrationPhase
        
        self.data.reset()
        self.data.active = True
        self.data.phase = CalibrationPhase.EXTEND
        self.data.phase_start_time = time.time()
        self.data.message = "EXTEND BOTH ARMS FULLY - HOLD STEADY"
    
    def process_frame(self, results, current_time: float) -> bool:
        """
        Process calibration frame
        Returns: True if calibration complete, False otherwise
        """
        from constants import CalibrationPhase
        
        if not self.data.active:
            return True
        
        # Check for pose detection
        if not results.pose_landmarks:
            self.data.message = "STAND IN FRAME - BODY NOT DETECTED"
            return False
        
        # Update progress
        elapsed = current_time - self.data.phase_start_time
        self.data.progress = min(int((elapsed / self.hold_time) * 100), 100)
        
        # Collect angle measurements
        angles = self.pose_processor.get_both_arm_angles(results)
        
        # Track if both arms are visible
        both_visible = True
        
        for arm in ['RIGHT', 'LEFT']:
            if angles[arm] is not None:
                if self.data.phase == CalibrationPhase.EXTEND:
                    self.data.extended_angles[arm].append(angles[arm])
                elif self.data.phase == CalibrationPhase.CONTRACT:
                    self.data.contracted_angles[arm].append(angles[arm])
            else:
                both_visible = False
        
        # Update message based on visibility
        if not both_visible:
            if self.data.phase == CalibrationPhase.EXTEND:
                self.data.message = "EXTEND BOTH ARMS - KEEP ARMS VISIBLE"
            else:
                self.data.message = "CURL BOTH ARMS - KEEP ARMS VISIBLE"
        else:
            if self.data.phase == CalibrationPhase.EXTEND:
                self.data.message = "EXTEND BOTH ARMS FULLY - HOLD STEADY"
            else:
                self.data.message = "CURL BOTH ARMS COMPLETELY - HOLD STEADY"
        
        # Check for phase transition
        if elapsed >= self.hold_time:
            # Verify we have enough samples
            if self.data.phase == CalibrationPhase.EXTEND:
                samples_ok = (len(self.data.extended_angles['RIGHT']) >= self.min_samples and 
                            len(self.data.extended_angles['LEFT']) >= self.min_samples)
                if samples_ok:
                    self._transition_to_contract(current_time)
                else:
                    # Not enough data, extend the phase
                    self.data.phase_start_time = current_time
                    self.data.message = "HOLD POSITION LONGER - KEEP ARMS VISIBLE"
                    
            elif self.data.phase == CalibrationPhase.CONTRACT:
                samples_ok = (len(self.data.contracted_angles['RIGHT']) >= self.min_samples and 
                            len(self.data.contracted_angles['LEFT']) >= self.min_samples)
                if samples_ok:
                    self._finalize_calibration()
                    return True
                else:
                    # Not enough data, extend the phase
                    self.data.phase_start_time = current_time
                    self.data.message = "HOLD POSITION LONGER - KEEP ARMS VISIBLE"
        
        return False
    
    def _transition_to_contract(self, current_time: float):
        """Move to contraction phase"""
        from constants import CalibrationPhase
        
        self.data.phase = CalibrationPhase.CONTRACT
        self.data.phase_start_time = current_time
        self.data.message = "CURL BOTH ARMS COMPLETELY - HOLD STEADY"
        self.data.progress = 0
    
    def _finalize_calibration(self):
        """Calculate final thresholds with enhanced accuracy"""
        # Calculate robust averages
        right_ext = self._calculate_robust_average(self.data.extended_angles['RIGHT'])
        left_ext = self._calculate_robust_average(self.data.extended_angles['LEFT'])
        right_con = self._calculate_robust_average(self.data.contracted_angles['RIGHT'])
        left_con = self._calculate_robust_average(self.data.contracted_angles['LEFT'])

        # ENHANCED: Use more conservative thresholds
        # Extended threshold: slightly less than most extended (ensures full extension)
        self.data.extended_threshold = int(min(right_ext, left_ext) - 8)
        
        # Contracted threshold: slightly more than most contracted (ensures full contraction)
        self.data.contracted_threshold = int(max(right_con, left_con) + 8)

        # Safety ranges with larger margins
        self.data.safe_angle_min = max(15, self.data.contracted_threshold - 15)
        self.data.safe_angle_max = min(175, self.data.extended_threshold + 15)

        # Validate thresholds make sense
        if self.data.extended_threshold - self.data.contracted_threshold < 40:
            # Range too small, use defaults with warning
            self.data.contracted_threshold = 50
            self.data.extended_threshold = 160
            self.data.safe_angle_min = 30
            self.data.safe_angle_max = 175
            self.data.message = "CALIBRATION WARNING: Using default ranges"

        self.data.active = False
        self.data.message = "CALIBRATION COMPLETE"

    @staticmethod
    def _calculate_robust_average(values: List[float]) -> float:
        """Calculate average removing outliers using IQR method"""
        if not values:
            return 0
        if len(values) < 3:
            return np.mean(values)
        
        # Use interquartile range to remove outliers
        q1, q3 = np.percentile(values, [25, 75])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        filtered = [v for v in values if lower_bound <= v <= upper_bound]
        return np.mean(filtered) if filtered else np.mean(values)
    
    def get_calibration_stats(self) -> dict:
        """Get calibration statistics for debugging"""
        return {
            'extended': {
                'right_samples': len(self.data.extended_angles['RIGHT']),
                'left_samples': len(self.data.extended_angles['LEFT']),
                'right_avg': self._calculate_robust_average(self.data.extended_angles['RIGHT']),
                'left_avg': self._calculate_robust_average(self.data.extended_angles['LEFT'])
            },
            'contracted': {
                'right_samples': len(self.data.contracted_angles['RIGHT']),
                'left_samples': len(self.data.contracted_angles['LEFT']),
                'right_avg': self._calculate_robust_average(self.data.contracted_angles['RIGHT']),
                'left_avg': self._calculate_robust_average(self.data.contracted_angles['LEFT'])
            },
            'thresholds': {
                'extended': self.data.extended_threshold,
                'contracted': self.data.contracted_threshold,
                'safe_min': self.data.safe_angle_min,
                'safe_max': self.data.safe_angle_max
            }
        }