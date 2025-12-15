"""
Rep counting logic - MINUTE PRECISION, ZERO FALSE ALARMS
"""
from collections import deque
from constants import ArmStage
import time
import random

class RepCounter:
    def __init__(self, calibration_data, min_rep_duration=0.6):
        self.calibration = calibration_data
        self.min_rep_duration = min_rep_duration

        # Stability buffers
        self.angle_history = {
            'RIGHT': deque(maxlen=8),
            'LEFT': deque(maxlen=8)
        }

        # State confirmation timers
        self.state_hold_time = 0.15
        self.pending_state = {
            'RIGHT': None,
            'LEFT': None
        }
        self.pending_state_start = {
            'RIGHT': 0,
            'LEFT': 0
        }
        
        # Rep timing tracking
        self.rep_start_time = {
            'RIGHT': 0,
            'LEFT': 0
        }
        
        # Compliment System
        self.last_rep_time = {
            'RIGHT': 0,
            'LEFT': 0
        }
        self.current_compliment = {
            'RIGHT': "Maintain Form",
            'LEFT': "Maintain Form"
        }
        self.compliments = [
            "Looking Strong!", "Great Control!", "Perfect Form!", 
            "Keep Pushing!", "Solid Rep!", "Nice Pace!"
        ]
        
        # Hysteresis margins
        self.hysteresis_margin = 5  # degrees

    def process_rep(self, arm, angle, metrics, current_time, history):
        metrics.angle = angle
        self.angle_history[arm].append(angle)

        if len(self.angle_history[arm]) < 4:
            return

        # Calculate velocity
        recent_angles = list(self.angle_history[arm])
        velocity = abs(recent_angles[-1] - recent_angles[-4]) / 3
        
        prev_stage = metrics.stage
        
        # Get thresholds
        contracted = self.calibration.contracted_threshold
        extended = self.calibration.extended_threshold
        
        # Determine target state
        target_state = self._determine_target_state(
            angle, contracted, extended, prev_stage
        )
        
        # State confirmation
        if target_state != prev_stage:
            if self.pending_state[arm] == target_state:
                hold_duration = current_time - self.pending_state_start[arm]
                velocity_settled = velocity < 15
                
                if hold_duration >= self.state_hold_time and velocity_settled:
                    self._handle_state_transition(
                        arm, prev_stage, target_state, 
                        metrics, current_time, history
                    )
            else:
                self.pending_state[arm] = target_state
                self.pending_state_start[arm] = current_time
        else:
            self.pending_state[arm] = None

        # Update rep timing
        if metrics.stage == ArmStage.UP.value:
            metrics.curr_rep_time = current_time - self.rep_start_time[arm]

        # --- SMART FEEDBACK & COMPLIMENTS ---
        self._provide_form_feedback(
            angle, metrics, contracted, extended, arm, history, velocity, current_time
        )

    def _determine_target_state(self, angle, contracted, extended, current_stage):
        margin = self.hysteresis_margin
        
        if angle <= contracted - margin:
            return ArmStage.UP.value
        
        if angle >= extended + margin:
            return ArmStage.DOWN.value
        
        if current_stage == ArmStage.UP.value:
            if angle < contracted + margin: return ArmStage.UP.value
            else: return ArmStage.MOVING_DOWN.value
        
        elif current_stage == ArmStage.DOWN.value:
            if angle > extended - margin: return ArmStage.DOWN.value
            else: return ArmStage.MOVING_UP.value
        
        elif current_stage == ArmStage.MOVING_UP.value:
            if angle <= contracted - margin: return ArmStage.UP.value
            elif angle >= extended + margin: return ArmStage.DOWN.value
            else: return ArmStage.MOVING_UP.value
        
        elif current_stage == ArmStage.MOVING_DOWN.value:
            if angle >= extended + margin: return ArmStage.DOWN.value
            elif angle <= contracted - margin: return ArmStage.UP.value
            else: return ArmStage.MOVING_DOWN.value
        
        return current_stage

    def _handle_state_transition(self, arm, prev_stage, new_stage, 
                                 metrics, current_time, history):
        metrics.stage = new_stage
        
        # Count rep (End of Cycle)
        if prev_stage == ArmStage.UP.value:
            if new_stage in [ArmStage.MOVING_DOWN.value, ArmStage.DOWN.value]:
                rep_time = current_time - metrics.last_down_time
                if rep_time >= self.min_rep_duration:
                    metrics.rep_count += 1
                    metrics.rep_time = rep_time
                    if metrics.min_rep_time == 0:
                        metrics.min_rep_time = rep_time
                    else:
                        metrics.min_rep_time = min(rep_time, metrics.min_rep_time)
                    metrics.last_down_time = current_time
                    metrics.curr_rep_time = 0
                    
                    # TRIGGER COMPLIMENT ON REP COMPLETE
                    self.last_rep_time[arm] = current_time
                    self.current_compliment[arm] = random.choice(self.compliments)
        
        elif new_stage == ArmStage.DOWN.value:
            self.rep_start_time[arm] = current_time
        
        elif new_stage == ArmStage.UP.value:
            if self.rep_start_time[arm] == 0:
                self.rep_start_time[arm] = current_time

    def _provide_form_feedback(self, angle, metrics, contracted, 
                               extended, arm, history, velocity, current_time):
        """
        Feedback Philosophy:
        1. SAFETY: Only warn if exceeding EXTREME physiological limits.
        2. POSITIVITY: If moving well, show compliments.
        3. CORRECTION: Only if STALLED in wrong place.
        """
        feedback_key = f"{arm.lower()}_feedback_count"
        
        # 1. EXTREME SAFETY LIMITS (User requested minute level)
        # 2 degrees = Practically touching shoulder
        # 178 degrees = Dead straight arm
        if angle > 178: 
            metrics.feedback = "Over Extending"
            setattr(history, feedback_key, getattr(history, feedback_key) + 1)
            return

        if angle < 2:
            metrics.feedback = "Over Curling" 
            setattr(history, feedback_key, getattr(history, feedback_key) + 1)
            return

        # 2. CHECK STALLING
        # Velocity < 0.5 means user has stopped moving.
        is_stalled = velocity < 0.5

        if is_stalled:
            # Only correct if they stopped SHORT of calibration
            # (Allows 10 degree buffer)
            if metrics.stage in [ArmStage.MOVING_UP.value, ArmStage.UP.value]:
                if angle > contracted + 10: 
                    metrics.feedback = "Curl Higher"
                    setattr(history, feedback_key, getattr(history, feedback_key) + 1)
                    return
            
            elif metrics.stage in [ArmStage.MOVING_DOWN.value, ArmStage.DOWN.value]:
                if angle < extended - 10:
                    metrics.feedback = "Extend Fully"
                    setattr(history, feedback_key, getattr(history, feedback_key) + 1)
                    return

        # 3. POSITIVE REINFORCEMENT (Default)
        # Show "Great Job" for 2 seconds after a rep, otherwise "Maintain Form"
        if (current_time - self.last_rep_time[arm]) < 2.0:
            metrics.feedback = self.current_compliment[arm]
        else:
            metrics.feedback = "Maintain Form"

    def reset_arm(self, arm):
        self.angle_history[arm].clear()
        self.pending_state[arm] = None
        self.pending_state_start[arm] = 0
        self.rep_start_time[arm] = 0