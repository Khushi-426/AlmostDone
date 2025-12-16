"""
Rep counting logic - MINUTE PRECISION, ZERO FALSE ALARMS
"""
from collections import deque
# Update imports to include the new constants for validation
from constants import ArmStage, REP_VALIDATION_RELIEF, REP_HYSTERESIS_MARGIN
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
        
        # Hysteresis margins (prevents flickering at thresholds)
        # self.hysteresis_margin = 5  # degrees <--- OLD
        self.hysteresis_margin = REP_HYSTERESIS_MARGIN # Use imported constant

        # NEW: Store the Rep Validation Relief (the +/- 2 degree error space)
        self.rep_validation_relief = REP_VALIDATION_RELIEF
        
        # FIX: Add missing initializations for compliment logic
        self.last_rep_time = {'RIGHT': 0, 'LEFT': 0}
        self.current_compliment = {'RIGHT': "Maintain Form", 'LEFT': "Maintain Form"}
        self.compliments = ["Great Rep!", "Excellent Form!", "Keep Going!", "Perfect!"]


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

                # FIX FOR STICKING ISSUE: 
                # Only require low velocity to confirm a peak (UP or DOWN).
                # When transitioning *out* of a peak (to MOVING_...), we rely only on hold_duration.
                is_peak_transition = target_state in [ArmStage.UP.value, ArmStage.DOWN.value]
                velocity_settled = velocity < 15 
                
                is_confirmed = hold_duration >= self.state_hold_time and (
                    (is_peak_transition and velocity_settled) or # Must be stable at peak
                    (not is_peak_transition)                     # Movement transition relies only on hold time
                )

                if is_confirmed:
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
        """
        Determine target state with hysteresis to prevent flickering
        ENHANCED: Incorporates REP_VALIDATION_RELIEF (e.g., +/- 2 degrees) to relax 
        the angle requirement for reaching a calibrated peak.
        """
        margin = self.hysteresis_margin
        relief = self.rep_validation_relief # +/- 2 degrees

        # Apply the required +/- 2 degree error space to the calibrated thresholds
        # Contracted is a low angle, so relief makes the threshold higher (easier to reach UP)
        effective_contracted = contracted + relief
        # Extended is a high angle, so relief makes the threshold lower (easier to reach DOWN)
        effective_extended = extended - relief

        # Fully contracted zone (with hysteresis)
        if angle <= effective_contracted - margin:
            return ArmStage.UP.value
        
        # Fully extended zone (with hysteresis)
        if angle >= effective_extended + margin:
            return ArmStage.DOWN.value
        
        # In the middle - use hysteresis based on current state (using effective thresholds)
        if current_stage == ArmStage.UP.value:
            # Stick to UP until we clearly move past contracted threshold
            if angle < effective_contracted + margin:
                return ArmStage.UP.value
            else:
                return ArmStage.MOVING_DOWN.value
        
        elif current_stage == ArmStage.DOWN.value:
            # Stick to DOWN until we clearly move past extended threshold
            if angle > effective_extended - margin:
                return ArmStage.DOWN.value
            else:
                return ArmStage.MOVING_UP.value
        
        elif current_stage == ArmStage.MOVING_UP.value:
            # Continue moving up until we reach contracted zone
            if angle <= effective_contracted - margin:
                return ArmStage.UP.value
            elif angle >= effective_extended + margin:
                return ArmStage.DOWN.value  # Moved back down
            else:
                return ArmStage.MOVING_UP.value
        
        elif current_stage == ArmStage.MOVING_DOWN.value:
            # Continue moving down until we reach extended zone
            if angle >= effective_extended + margin:
                return ArmStage.DOWN.value
            elif angle <= effective_contracted - margin:
                return ArmStage.UP.value  # Moved back up
            else:
                return ArmStage.MOVING_DOWN.value
        
        return current_stage

    def _handle_state_transition(self, arm, prev_stage, new_stage, 
                                 metrics, current_time, history):
        metrics.stage = new_stage
        
        # Count rep (End of Cycle)
        if prev_stage == ArmStage.UP.value:
            if new_stage in [ArmStage.MOVING_DOWN.value, ArmStage.DOWN.value]:
                # Calculate rep time using the stored rep_start_time
                rep_time = current_time - self.rep_start_time[arm]
                
                if rep_time >= self.min_rep_duration:
                    metrics.rep_count += 1
                    metrics.rep_time = rep_time
                    if metrics.min_rep_time == 0:
                        metrics.min_rep_time = rep_time
                    else:
                        metrics.min_rep_time = min(rep_time, metrics.min_rep_time)
                    metrics.curr_rep_time = 0
                    
                    # Reset rep_start_time for the next rep cycle
                    self.rep_start_time[arm] = 0
                    
                    # TRIGGER COMPLIMENT ON REP COMPLETE
                    self.last_rep_time[arm] = current_time
                    self.current_compliment[arm] = random.choice(self.compliments)
        
        elif new_stage == ArmStage.DOWN.value:
            # Set the start time of the rep cycle when the arm reaches the fully extended (DOWN) position
            self.rep_start_time[arm] = current_time
        
        elif new_stage == ArmStage.UP.value:
            if self.rep_start_time[arm] == 0:
                self.rep_start_time[arm] = current_time

    def _provide_form_feedback(self, angle, metrics, contracted, 
                               extended, arm, history, velocity, current_time):
        """
        Provide form feedback based on angle and stage
        ENHANCED: Range of Motion guidance uses the relaxed thresholds 
        (effective_contracted/extended) to match the rep counting logic.
        """
        safe_min = self.calibration.safe_angle_min
        safe_max = self.calibration.safe_angle_max

        # Apply the same relief to feedback thresholds for consistency
        relief = self.rep_validation_relief
        effective_contracted = contracted + relief
        effective_extended = extended - relief
        
        feedback_key = f"{arm.lower()}_feedback_count"
        
        # Critical form errors (Safety margins should NOT be relaxed)
        if angle < safe_min:
            metrics.feedback = "Over Curling"
            setattr(history, feedback_key, getattr(history, feedback_key) + 1)
        elif angle > safe_max:
            metrics.feedback = "Over Extending"
            setattr(history, feedback_key, getattr(history, feedback_key) + 1)
        
        # Range of motion guidance (using RELAXED thresholds)
        elif effective_contracted < angle < effective_extended:
            if metrics.stage == ArmStage.UP.value or metrics.stage == ArmStage.MOVING_UP.value:
                # Use effective_contracted for comparison
                if angle > effective_contracted + 10:  # Not quite at peak
                    metrics.feedback = "Curl Higher"
                    setattr(history, feedback_key, getattr(history, feedback_key) + 1)
                    return
            
            elif metrics.stage == ArmStage.DOWN.value or metrics.stage == ArmStage.MOVING_DOWN.value:
                # Use effective_extended for comparison
                if angle < effective_extended - 10:  # Not quite at bottom
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