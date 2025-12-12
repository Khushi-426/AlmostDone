"""
Calibration logic and threshold calculation
"""
import numpy as np
from typing import List
import time

class CalibrationManager:
    """Manages the calibration process"""
    
    def __init__(self, pose_processor, calibration_data, 
                 hold_time: float = 3, safety_margin: int = 10):
        self.pose_processor = pose_processor
        self.data = calibration_data
        self.hold_time = hold_time
        self.safety_margin = safety_margin
    
    def start(self):
        """Initialize calibration"""
        from constants import CalibrationPhase
        
        self.data.reset()
        self.data.active = True
        self.data.phase = CalibrationPhase.EXTEND
        self.data.phase_start_time = time.time()
        self.data.message = "EXTEND BOTH ARMS FULLY - HOLD POSITION"
    
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
        
        for arm in ['RIGHT', 'LEFT']:
            if angles[arm] is not None:
                if self.data.phase == CalibrationPhase.EXTEND:
                    self.data.extended_angles[arm].append(angles[arm])
                elif self.data.phase == CalibrationPhase.CONTRACT:
                    self.data.contracted_angles[arm].append(angles[arm])
        
        # Check for phase transition
        if elapsed >= self.hold_time:
            if self.data.phase == CalibrationPhase.EXTEND:
                self._transition_to_contract(current_time)
            elif self.data.phase == CalibrationPhase.CONTRACT:
                self._finalize_calibration()
                return True
        
        return False
    
    def _transition_to_contract(self, current_time: float):
        """Move to contraction phase"""
        from constants import CalibrationPhase
        
        self.data.phase = CalibrationPhase.CONTRACT
        self.data.phase_start_time = current_time
        self.data.message = "CURL YOUR ARMS COMPLETELY - HOLD POSITION"
        self.data.progress = 0
    
    def _finalize_calibration(self):
        """Calculate final thresholds from collected data"""
        from constants import CalibrationPhase
        
        # Calculate averages with outlier removal
        right_extended = self._calculate_robust_average(self.data.extended_angles['RIGHT'])
        left_extended = self._calculate_robust_average(self.data.extended_angles['LEFT'])
        right_contracted = self._calculate_robust_average(self.data.contracted_angles['RIGHT'])
        left_contracted = self._calculate_robust_average(self.data.contracted_angles['LEFT'])
        
        # Average both arms
        self.data.extended_threshold = int((right_extended + left_extended) / 2)
        self.data.contracted_threshold = int((right_contracted + left_contracted) / 2)
        
        # Set safety bounds
        self.data.safe_angle_min = max(10, self.data.contracted_threshold - self.safety_margin)
        self.data.safe_angle_max = min(180, self.data.extended_threshold + self.safety_margin)
        
        self.data.phase = CalibrationPhase.COMPLETE
        self.data.message = f"CALIBRATION COMPLETE! Extended: {self.data.extended_threshold}° | Contracted: {self.data.contracted_threshold}°"
        self.data.active = False
    
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