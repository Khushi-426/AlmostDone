"""
Calibration logic: Dynamically determines ROM thresholds
"""
import time
from typing import TYPE_CHECKING
from constants import CalibrationPhase, ExerciseConfig

if TYPE_CHECKING:
    from pose_processor import PoseProcessor
    from models import CalibrationData

class CalibrationManager:
    def __init__(self, pose_processor, data: 'CalibrationData', hold_time: int, safety_margin: int):
        self.pose_processor = pose_processor
        self.data = data
        self.hold_time = hold_time
        self.safety_margin = safety_margin
        
        self.exercise_config: ExerciseConfig = pose_processor.config
        self.joint_name = self.exercise_config.joint_to_track.value.title()
        self.exercise_name = self.exercise_config.name

        self.start_time = 0.0
        self.min_angle = 360  
        self.max_angle = 0    

    def start(self):
        self.data.active = True
        self.data.phase = CalibrationPhase.EXTEND
        # FIX: Single static message to avoid voice spam
        self.data.message = f"CALIBRATION: Fully EXTEND your {self.joint_name} joint."
        self.data.progress = 0
        self.start_time = time.time()
        self.min_angle = 360
        self.max_angle = 0
        print(f"Starting calibration for: {self.exercise_name} (Joint: {self.joint_name})")

    def process_frame(self, results, current_time: float) -> bool:
        if not self.data.active:
            return False

        angles = self.pose_processor.get_both_arm_angles(results)
        right_angle = angles.get('RIGHT')
        left_angle = angles.get('LEFT')
        
        valid_angles = [a for a in [right_angle, left_angle] if a is not None]

        if not valid_angles:
            self.data.message = f"CALIBRATION: Please ensure your {self.joint_name} joint is visible."
            self.data.progress = 0
            self.start_time = current_time 
            return False
            
        current_angle = sum(valid_angles) / len(valid_angles)
        self.min_angle = min(self.min_angle, current_angle)
        self.max_angle = max(self.max_angle, current_angle)
        
        elapsed_time = current_time - self.start_time
        
        if self.data.phase == CalibrationPhase.EXTEND:
            # Check holding extended position
            if current_angle > (self.max_angle - 5) or elapsed_time < 0.5:
                self.data.progress = int((elapsed_time / self.hold_time) * 100)
                # FIX: Static message during hold
                self.data.message = f"CALIBRATION: Hold EXTENDED {self.joint_name} position."
            else:
                self.start_time = current_time
                self.data.message = f"CALIBRATION: Please hold EXTENDED {self.joint_name} position steady."
                self.data.progress = 0

            if elapsed_time >= self.hold_time:
                self.data.extended_threshold = int(self.max_angle)
                self.data.phase = CalibrationPhase.CONTRACT
                self.start_time = current_time
                self.data.progress = 0
                # FIX: Static message for new phase
                self.data.message = f"CALIBRATION: Great! Now Fully CONTRACT your {self.joint_name} joint."
                self.min_angle = 360 
                self.max_angle = 0 
        
        elif self.data.phase == CalibrationPhase.CONTRACT:
            # Check holding contracted position
            if current_angle < (self.min_angle + 5) or elapsed_time < 0.5:
                self.data.progress = int((elapsed_time / self.hold_time) * 100)
                # FIX: Static message during hold
                self.data.message = f"CALIBRATION: Hold CONTRACTED {self.joint_name} position."
            else:
                self.start_time = current_time
                self.data.message = f"CALIBRATION: Please hold CONTRACTED {self.joint_name} position steady."
                self.data.progress = 0

            if elapsed_time >= self.hold_time:
                self.data.contracted_threshold = int(self.min_angle)
                self._finalize_calibration()
                return True
                
        return False

    def _finalize_calibration(self):
        """Calculates final thresholds and completes calibration."""
        self.data.safe_angle_min = max(20, self.data.contracted_threshold - self.safety_margin)
        self.data.safe_angle_max = min(175, self.data.extended_threshold + self.safety_margin)

        self.data.active = False
        self.data.phase = CalibrationPhase.COMPLETE
        self.data.message = f"{self.exercise_name} Calibration Complete. Start Workout!"
        self.data.progress = 100
        print(f"Calibration Finalized for {self.exercise_name}: Contracted={self.data.contracted_threshold}, Extended={self.data.extended_threshold}")

        if self.data.extended_threshold - self.data.contracted_threshold < 30:
            self.data.message = "WARNING: Small Range of Motion detected. Please try to move fully."