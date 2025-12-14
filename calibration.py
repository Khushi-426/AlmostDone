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
        
        # <<< NEW: Store the ExerciseConfig and Joint Name for dynamic messaging and logic >>>
        self.exercise_config: ExerciseConfig = pose_processor.config
        # Use .title() to capitalize the joint name (e.g., "ELBOW" -> "Elbow")
        self.joint_name = self.exercise_config.joint_to_track.value.title()
        self.exercise_name = self.exercise_config.name

        self.start_time = 0.0
        self.min_angle = 360  # Start with max possible angle
        self.max_angle = 0    # Start with min possible angle

    def start(self):
        self.data.active = True
        self.data.phase = CalibrationPhase.EXTEND
        # Use dynamic joint and hold time in the message
        self.data.message = f"CALIBRATION: Fully EXTEND your {self.joint_name} joint for {self.hold_time} seconds."
        self.data.progress = 0
        self.start_time = time.time()
        self.min_angle = 360
        self.max_angle = 0
        print(f"Starting calibration for: {self.exercise_name} (Joint: {self.joint_name})")

    def process_frame(self, results, current_time: float) -> bool:
        """
        Processes a single frame for calibration.
        Returns True if calibration is complete.
        """
        if not self.data.active:
            return False

        # Get angles for the joint specified in the current exercise config
        angles = self.pose_processor.get_both_arm_angles(results)
        
        # Calibration relies on consistent movement from either or both tracked sides
        right_angle = angles.get('RIGHT')
        left_angle = angles.get('LEFT')
        
        valid_angles = [a for a in [right_angle, left_angle] if a is not None]

        # Check for valid angles (only proceed if tracking is reliable)
        if not valid_angles:
            self.data.message = f"CALIBRATION: Please ensure your {self.joint_name} joint is visible."
            self.data.progress = 0
            self.start_time = current_time # Reset timer if pose is lost
            return False
            
        current_angle = sum(valid_angles) / len(valid_angles)
        
        # Update min/max angles based on motion
        self.min_angle = min(self.min_angle, current_angle)
        self.max_angle = max(self.max_angle, current_angle)
        
        elapsed_time = current_time - self.start_time
        
        if self.data.phase == CalibrationPhase.EXTEND:
            # Check if the user is holding the extended position (high angle)
            # Check if the current angle is close to the max angle found so far (within 5 degrees)
            if current_angle > (self.max_angle - 5) or elapsed_time < 0.5:
                self.data.progress = int((elapsed_time / self.hold_time) * 100)
                self.data.message = f"CALIBRATION: Hold EXTENDED {self.joint_name} position. ({self.hold_time - int(elapsed_time)}s left)"
            else:
                # Movement detected, reset timer
                self.start_time = current_time
                self.data.message = f"CALIBRATION: Please hold EXTENDED {self.joint_name} position steady."
                self.data.progress = 0

            if elapsed_time >= self.hold_time:
                # Transition to CONTRACT phase
                self.data.extended_threshold = int(self.max_angle)
                self.data.phase = CalibrationPhase.CONTRACT
                self.start_time = current_time
                self.data.progress = 0
                self.data.message = f"CALIBRATION: Great! Now Fully CONTRACT your {self.joint_name} joint for {self.hold_time} seconds."
                self.min_angle = 360 # Reset min angle for next phase
                self.max_angle = 0 # Reset max angle for next phase
        
        elif self.data.phase == CalibrationPhase.CONTRACT:
            # Check if the user is holding the contracted position (low angle)
            # Check if the current angle is close to the min angle found so far (within 5 degrees)
            if current_angle < (self.min_angle + 5) or elapsed_time < 0.5:
                self.data.progress = int((elapsed_time / self.hold_time) * 100)
                self.data.message = f"CALIBRATION: Hold CONTRACTED {self.joint_name} position. ({self.hold_time - int(elapsed_time)}s left)"
            else:
                # Movement detected, reset timer
                self.start_time = current_time
                self.data.message = f"CALIBRATION: Please hold CONTRACTED {self.joint_name} position steady."
                self.data.progress = 0

            if elapsed_time >= self.hold_time:
                # Calibration Complete
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
        # Use dynamic exercise name in the final message
        self.data.message = f"{self.exercise_name} Calibration Complete. Start Workout!"
        self.data.progress = 100
        print(f"Calibration Finalized for {self.exercise_name}: Contracted={self.data.contracted_threshold}, Extended={self.data.extended_threshold}")

        # Final check (e.g., if ROM is too small)
        if self.data.extended_threshold - self.data.contracted_threshold < 30:
            self.data.message = "WARNING: Small Range of Motion detected. Please try to move fully."