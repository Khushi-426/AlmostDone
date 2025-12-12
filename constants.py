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
    UP = "UP"
    DOWN = "DOWN"
    LOST = "LOST"

# Calibration settings
CALIBRATION_HOLD_TIME = 10  # seconds
WORKOUT_COUNTDOWN_TIME = 5  # seconds

# Angle processing
SMOOTHING_WINDOW = 7
SAFETY_MARGIN = 10  # degrees

# MediaPipe settings
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7

# Rep validation
MIN_REP_DURATION = 0.5  # seconds - prevents false counts

# Default thresholds (overridden by calibration)
DEFAULT_CONTRACTED_THRESHOLD = 50
DEFAULT_EXTENDED_THRESHOLD = 160
DEFAULT_SAFE_ANGLE_MIN = 30
DEFAULT_SAFE_ANGLE_MAX = 175