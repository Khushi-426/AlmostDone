"""
Configuration constants and enumerations
"""
from enum import Enum

class WorkoutPhase(Enum):
    INACTIVE = "INACTIVE"
    CALIBRATION = "CALIBRATION"
    COUNTDOWN = "COUNTDOWN"
    ACTIVE = "ACTIVE"

class CalibrationPhase(Enum):
    EXTEND = "EXTEND"
    CONTRACT = "CONTRACT"
    COMPLETE = "COMPLETE"

class ArmStage(Enum):
    # Core states (fully reached peaks)
    UP = "UP"           # Fully contracted (peak of curl)
    DOWN = "DOWN"         # Fully extended (bottom of movement)
    LOST = "LOST"         # Pose tracking lost
    
    # ENHANCEMENT: New transitional stages for granular rep counting logic (Used in rep_counter.py)
    MOVING_UP = "MOVING_UP"   # Arm is contracting (curling up)
    MOVING_DOWN = "MOVING_DOWN" # Arm is extending (going down)

# Calibration settings
# ENHANCEMENT: Increased hold time for better calibration data stability
CALIBRATION_HOLD_TIME = 5   # seconds (Increased from 3/10 for robust sampling)
WORKOUT_COUNTDOWN_TIME = 5  # seconds

# Angle processing
SMOOTHING_WINDOW = 7
SAFETY_MARGIN = 10  # degrees

# MediaPipe settings
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7

# Rep validation
# ENHANCEMENT: Increased min rep duration to enforce controlled movement (physio/rehab focus)
MIN_REP_DURATION = 0.6  # seconds - prevents false counts and forces control

# Default thresholds (overridden by calibration)
DEFAULT_CONTRACTED_THRESHOLD = 50
DEFAULT_EXTENDED_THRESHOLD = 160
DEFAULT_SAFE_ANGLE_MIN = 30
DEFAULT_SAFE_ANGLE_MAX = 175