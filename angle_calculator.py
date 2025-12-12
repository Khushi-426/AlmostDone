"""
Angle calculation and smoothing algorithms
"""
import numpy as np
from collections import deque
from typing import Dict, List

class AngleCalculator:
    """Handles all angle-related calculations"""
    
    def __init__(self, smoothing_window: int = 7):
        self.angle_buffers: Dict[str, deque] = {
            'RIGHT': deque(maxlen=smoothing_window),
            'LEFT': deque(maxlen=smoothing_window)
        }
    
    @staticmethod
    def calculate_angle(a: List[float], b: List[float], c: List[float]) -> float:
        """Calculate angle between three points using vectors"""
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)
        
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - \
                  np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(np.degrees(radians))
        
        return 360 - angle if angle > 180.0 else angle
    
    def get_smoothed_angle(self, arm: str, new_angle: float) -> int:
        """Apply temporal smoothing to reduce jitter"""
        buffer = self.angle_buffers[arm]
        
        # Initialize buffer on first call
        if len(buffer) == 0:
            for _ in range(buffer.maxlen):
                buffer.append(new_angle)
        
        buffer.append(new_angle)
        return int(np.median(buffer))  # Use median for better outlier resistance
    
    def reset_buffers(self):
        """Clear all angle buffers"""
        for buffer in self.angle_buffers.values():
            buffer.clear()