"""
Angle calculation with ZERO jitter
"""
import numpy as np
from collections import deque

class AngleCalculator:
    def __init__(self, smoothing_window=7):
        self.buffers = {
            'RIGHT': deque(maxlen=smoothing_window),
            'LEFT': deque(maxlen=smoothing_window)
        }
        self.ema = {'RIGHT': None, 'LEFT': None}
        self.alpha = 0.5

    @staticmethod
    def calculate_angle(a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - \
                  np.arctan2(a[1]-b[1], a[0]-b[0])
        angle = abs(np.degrees(radians))
        return 360 - angle if angle > 180 else angle

    def get_smoothed_angle(self, arm, angle):
        buf = self.buffers[arm]
        buf.append(angle)

        median = np.median(buf)

        if self.ema[arm] is None:
            self.ema[arm] = median
        else:
            self.ema[arm] = self.alpha * median + (1 - self.alpha) * self.ema[arm]

        return int(self.ema[arm])

    def reset_buffers(self):
        for buf in self.buffers.values():
            buf.clear()
        self.ema = {'RIGHT': None, 'LEFT': None}
