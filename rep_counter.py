"""
Rep counting logic - EXTREME LIMITS FEEDBACK & ROBUST COUNTING
"""
from collections import deque
from constants import ArmStage
import time
import random

class RepCounter:
    def __init__(self, calibration_data, min_rep_duration=0.5):
        self.calibration = calibration_data
        self.min_rep_duration = min_rep_duration 

        # Stability buffers
        self.angle_history = {
            'RIGHT': deque(maxlen=8),
            'LEFT': deque(maxlen=8)
        }

        # State confirmation variables
        self.state_hold_time = 0.1 
        self.pending_state = {'RIGHT': None, 'LEFT': None}
        self.pending_state_start = {'RIGHT': 0, 'LEFT': 0}
        
        self.rep_start_time = {'RIGHT': 0, 'LEFT': 0}
        self.last_rep_time = {'RIGHT': 0, 'LEFT': 0}
        
        self.compliments = ["Great Rep!", "Excellent!", "Perfect Form!", "Good Job!"]
        self.current_compliment = {'RIGHT': "Maintain Form", 'LEFT': "Maintain Form"}

    def process_rep(self, arm, angle, metrics, current_time, history):
        metrics.angle = angle
        self.angle_history[arm].append(angle)

        if len(self.angle_history[arm]) < 2:
            return

        prev_stage = metrics.stage
        
        # Get calibrated thresholds
        contracted = self.calibration.contracted_threshold
        extended = self.calibration.extended_threshold
        
        # --- 1. DETERMINE STATE (For Counting) ---
        target_state = self._determine_target_state(angle, contracted, extended, prev_stage)
        
        # --- 2. FAST STATE SWITCHING ---
        if target_state != prev_stage:
            if self.pending_state[arm] == target_state:
                if (current_time - self.pending_state_start[arm]) >= self.state_hold_time:
                    self._handle_state_transition(arm, prev_stage, target_state, metrics, current_time)
            else:
                self.pending_state[arm] = target_state
                self.pending_state_start[arm] = current_time
        else:
            self.pending_state[arm] = None

        # Update rep timing
        if metrics.stage == ArmStage.UP.value:
            metrics.curr_rep_time = current_time - self.rep_start_time[arm]

        # --- 3. FEEDBACK GENERATION (STRICT LIMITS) ---
        self._provide_form_feedback(arm, angle, metrics, current_time)

    def _determine_target_state(self, angle, contracted, extended, current_stage):
        """
        Determines state with a buffer so reps count easily.
        """
        # Buffer to make reaching targets easier
        buffer = 15 

        up_limit = contracted + buffer 
        down_limit = extended - buffer

        if angle <= up_limit:
            return ArmStage.UP.value
        elif angle >= down_limit:
            return ArmStage.DOWN.value
        
        # Hysteresis Transitions
        if current_stage == ArmStage.UP.value:
            return ArmStage.UP.value if angle < (up_limit + 5) else ArmStage.MOVING_DOWN.value
        elif current_stage == ArmStage.DOWN.value:
            return ArmStage.DOWN.value if angle > (down_limit - 5) else ArmStage.MOVING_UP.value
        elif current_stage == ArmStage.MOVING_UP.value:
            return ArmStage.UP.value if angle <= up_limit else ArmStage.MOVING_UP.value
        elif current_stage == ArmStage.MOVING_DOWN.value:
            return ArmStage.DOWN.value if angle >= down_limit else ArmStage.MOVING_DOWN.value
            
        return current_stage

    def _handle_state_transition(self, arm, prev_stage, new_stage, metrics, current_time):
        metrics.stage = new_stage
        
        # DETECT REP COMPLETION
        if prev_stage == ArmStage.UP.value and new_stage in [ArmStage.MOVING_DOWN.value, ArmStage.DOWN.value]:
            
            rep_duration = current_time - self.rep_start_time[arm]
            
            if rep_duration >= self.min_rep_duration:
                metrics.rep_count += 1
                metrics.rep_time = rep_duration
                
                self.rep_start_time[arm] = 0 
                self.last_rep_time[arm] = current_time
                self.current_compliment[arm] = random.choice(self.compliments)

        elif new_stage == ArmStage.DOWN.value:
            self.rep_start_time[arm] = current_time 
            
        elif new_stage == ArmStage.UP.value:
            if self.rep_start_time[arm] == 0:
                self.rep_start_time[arm] = current_time

    def _provide_form_feedback(self, arm, angle, metrics, current_time):
        """
        Feedback Logic:
        1. Compliment (Priority) if rep just finished.
        2. Extreme Limits ONLY (<2 or >178).
        3. Default "Maintain Form".
        """
        # 1. PRIORITY: Show compliment for 2 seconds after a rep
        if (current_time - self.last_rep_time[arm]) < 2.0:
            metrics.feedback = self.current_compliment[arm]
            return

        # 2. EXTREME LIMITS ONLY
        if angle < 2.0:
            metrics.feedback = "Over Curling"
        elif angle > 178.0:
            metrics.feedback = "Over Extending"
        
        # 3. DEFAULT
        else:
            metrics.feedback = "Maintain Form"

    def reset_arm(self, arm):
        self.angle_history[arm].clear()
        self.pending_state[arm] = None
        self.rep_start_time[arm] = 0