"""
Data classes for state management - FIXED
"""
from dataclasses import dataclass, field
from typing import Dict, List
import time

@dataclass
class ArmMetrics:
    """Stores all metrics for a single arm"""
    rep_count: int = 0
    stage: str = "DOWN"
    angle: int = 0
    rep_time: float = 0.0
    min_rep_time: float = 0.0
    curr_rep_time: float = 0.0
    feedback: str = ""
    last_down_time: float = field(default_factory=time.time)
    stage_start_time: float = field(default_factory=time.time)  # ADDED: Missing field
    
    def to_dict(self) -> dict:
        return {
            'rep_count': self.rep_count,
            'stage': self.stage,
            'angle': self.angle,
            'rep_time': round(self.rep_time, 2),
            'min_rep_time': round(self.min_rep_time, 2),
            'curr_rep_time': round(self.curr_rep_time, 2),
            'feedback': self.feedback
        }

@dataclass
class CalibrationData:
    """Manages calibration state and measurements"""
    active: bool = False
    phase: 'CalibrationPhase' = None
    phase_start_time: float = 0.0
    extended_angles: Dict[str, List[float]] = field(default_factory=lambda: {'RIGHT': [], 'LEFT': []})
    contracted_angles: Dict[str, List[float]] = field(default_factory=lambda: {'RIGHT': [], 'LEFT': []})
    message: str = ""
    progress: int = 0
    
    contracted_threshold: int = 50
    extended_threshold: int = 160
    safe_angle_min: int = 30
    safe_angle_max: int = 175
    
    def reset(self):
        """Reset calibration data for new session"""
        self.extended_angles = {'RIGHT': [], 'LEFT': []}
        self.contracted_angles = {'RIGHT': [], 'LEFT': []}
        self.progress = 0

@dataclass
class SessionHistory:
    """Tracks session data for analysis"""
    time: List[float] = field(default_factory=list)
    right_angle: List[int] = field(default_factory=list)
    left_angle: List[int] = field(default_factory=list)
    right_feedback_count: int = 0
    left_feedback_count: int = 0
    
    def reset(self):
        self.time.clear()
        self.right_angle.clear()
        self.left_angle.clear()
        self.right_feedback_count = 0
        self.left_feedback_count = 0