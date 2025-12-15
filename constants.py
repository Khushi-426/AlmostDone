"""
Configuration constants and enumerations
"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List
import mediapipe as mp # Required for easy access to landmark indices


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
    UP = "UP"         # Fully contracted (peak of curl/lift, angle decreasing)
    DOWN = "DOWN"     # Fully extended (bottom of movement, angle increasing)
    LOST = "LOST"     # Pose tracking lost
    
    # ENHANCEMENT: New transitional stages for granular rep counting logic
    MOVING_UP = "MOVING_UP"   # Joint is contracting (angle decreasing)
    MOVING_DOWN = "MOVING_DOWN" # Joint is extending (angle increasing)


class ExerciseJoint(Enum):
    """Defines the joint type being tracked"""
    ELBOW = "ELBOW"
    KNEE = "KNEE"
    SHOULDER = "SHOULDER"
    HIP = "HIP" # Added for Squats and other torso/lower body movements
    ANKLE = "ANKLE"


@dataclass
class ExerciseConfig:
    """Stores the configuration for a specific exercise type"""
    name: str = "Bicep Curl"
    joint_to_track: ExerciseJoint = ExerciseJoint.ELBOW
    
    # Landmark definitions are (A, B, C) where B is the vertex (e.g., Elbow or Knee)
    # Uses integer indices from MediaPipe Holistic PoseLandmark
    right_landmarks: List[int] = field(default_factory=list) 
    left_landmarks: List[int] = field(default_factory=list)  
    
    # Landmarks for AI features (R_A, R_B, R_C, L_A, L_B, L_C, plus 2 stabilization points)
    # AI models require 8 landmarks (16 features) for consistency
    ai_features_landmarks: List[int] = field(default_factory=list)


# --- EXERCISE PRESETS ---

mp_pose = mp.solutions.holistic.PoseLandmark

EXERCISE_PRESETS = {
    "Bicep Curl": ExerciseConfig(
        name="Bicep Curl",
        joint_to_track=ExerciseJoint.ELBOW,
        right_landmarks=[mp_pose.RIGHT_SHOULDER.value, mp_pose.RIGHT_ELBOW.value, mp_pose.RIGHT_WRIST.value],
        left_landmarks=[mp_pose.LEFT_SHOULDER.value, mp_pose.LEFT_ELBOW.value, mp_pose.LEFT_WRIST.value],
        ai_features_landmarks=[
            mp_pose.RIGHT_SHOULDER.value, mp_pose.RIGHT_ELBOW.value, mp_pose.RIGHT_WRIST.value,
            mp_pose.LEFT_SHOULDER.value, mp_pose.LEFT_ELBOW.value, mp_pose.LEFT_WRIST.value,
            mp_pose.RIGHT_HIP.value, mp_pose.LEFT_HIP.value # Stabilization: Hips
        ]
    ),
    "Knee Lift": ExerciseConfig(
        name="Knee Lift",
        joint_to_track=ExerciseJoint.KNEE,
        right_landmarks=[mp_pose.RIGHT_HIP.value, mp_pose.RIGHT_KNEE.value, mp_pose.RIGHT_ANKLE.value],
        left_landmarks=[mp_pose.LEFT_HIP.value, mp_pose.LEFT_KNEE.value, mp_pose.LEFT_ANKLE.value],
        ai_features_landmarks=[
            mp_pose.RIGHT_HIP.value, mp_pose.RIGHT_KNEE.value, mp_pose.RIGHT_ANKLE.value,
            mp_pose.LEFT_HIP.value, mp_pose.LEFT_KNEE.value, mp_pose.LEFT_ANKLE.value,
            mp_pose.NOSE.value, mp_pose.RIGHT_HIP.value # Stabilization: Upper Body Balance/Lower Hip
        ]
    ),
    "Shoulder Press": ExerciseConfig(
        name="Shoulder Press",
        joint_to_track=ExerciseJoint.SHOULDER, 
        right_landmarks=[mp_pose.RIGHT_HIP.value, mp_pose.RIGHT_SHOULDER.value, mp_pose.RIGHT_ELBOW.value],
        left_landmarks=[mp_pose.LEFT_HIP.value, mp_pose.LEFT_SHOULDER.value, mp_pose.LEFT_ELBOW.value],
        ai_features_landmarks=[
            mp_pose.RIGHT_HIP.value, mp_pose.RIGHT_SHOULDER.value, mp_pose.RIGHT_ELBOW.value,
            mp_pose.LEFT_HIP.value, mp_pose.LEFT_SHOULDER.value, mp_pose.LEFT_ELBOW.value,
            mp_pose.RIGHT_KNEE.value, mp_pose.LEFT_KNEE.value # Stabilization: Lower body check
        ]
    ),
    "Squat": ExerciseConfig(
        name="Squat",
        joint_to_track=ExerciseJoint.HIP,
        # Measuring the Hip angle (Torso-Hip-Knee angle) to track depth
        right_landmarks=[mp_pose.RIGHT_SHOULDER.value, mp_pose.RIGHT_HIP.value, mp_pose.RIGHT_KNEE.value],
        left_landmarks=[mp_pose.LEFT_SHOULDER.value, mp_pose.LEFT_HIP.value, mp_pose.LEFT_KNEE.value],
        ai_features_landmarks=[
            mp_pose.RIGHT_SHOULDER.value, mp_pose.RIGHT_HIP.value, mp_pose.RIGHT_KNEE.value,
            mp_pose.LEFT_SHOULDER.value, mp_pose.LEFT_HIP.value, mp_pose.LEFT_KNEE.value,
            mp_pose.RIGHT_ANKLE.value, mp_pose.LEFT_ANKLE.value # Stabilization: Ankle position (foot placement)
        ]
    ),
    # <<<<<<<< NEW EXERCISE ADDED: STANDING ROW >>>>>>>>>
    "Standing Row": ExerciseConfig(
        name="Standing Row",
        joint_to_track=ExerciseJoint.SHOULDER,
        # Measuring the shoulder movement (Hip-Shoulder-Elbow)
        right_landmarks=[mp_pose.RIGHT_HIP.value, mp_pose.RIGHT_SHOULDER.value, mp_pose.RIGHT_ELBOW.value],
        left_landmarks=[mp_pose.LEFT_HIP.value, mp_pose.LEFT_SHOULDER.value, mp_pose.LEFT_ELBOW.value],
        ai_features_landmarks=[
            mp_pose.RIGHT_HIP.value, mp_pose.RIGHT_SHOULDER.value, mp_pose.RIGHT_ELBOW.value,
            mp_pose.LEFT_HIP.value, mp_pose.LEFT_SHOULDER.value, mp_pose.LEFT_ELBOW.value,
            mp_pose.RIGHT_KNEE.value, mp_pose.LEFT_KNEE.value # Stabilization: Hips/knees for torso stability
        ]
    )
}

# Calibration settings
CALIBRATION_HOLD_TIME = 5     # seconds
WORKOUT_COUNTDOWN_TIME = 5    # seconds

# Angle processing
SMOOTHING_WINDOW = 7
SAFETY_MARGIN = 10    # degrees

# MediaPipe settings
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7

# Rep validation
MIN_REP_DURATION = 0.6    # seconds - prevents false counts and forces control

# NEW: Rep validation tolerance and explicit hysteresis margin
REP_VALIDATION_RELIEF = 5   # degrees: The +/- 2 degree error space allowed for reaching a calibrated peak
REP_HYSTERESIS_MARGIN = 5   # degrees: Margin used for state transition stability (anti-flicker)

# Default thresholds (overridden by calibration)
DEFAULT_CONTRACTED_THRESHOLD = 50
DEFAULT_EXTENDED_THRESHOLD = 160
DEFAULT_SAFE_ANGLE_MIN = 30
DEFAULT_SAFE_ANGLE_MAX = 175