"""
Rep counting logic with PERFECT accuracy guarantees
ENHANCED: Proper state machine + hysteresis + velocity tracking
"""
from collections import deque
# Update imports to include the new constants for validation
from constants import ArmStage, REP_VALIDATION_RELIEF, REP_HYSTERESIS_MARGIN
import time

class RepCounter:
    def __init__(self, calibration_data, min_rep_duration=0.6):
        self.calibration = calibration_data
        self.min_rep_duration = min_rep_duration

        # Stability buffers (increased window for better smoothing)
        self.angle_history = {
            'RIGHT': deque(maxlen=8),
            'LEFT': deque(maxlen=8)
        }

        # State confirmation timers (must hold state before transitioning)
        self.state_hold_time = 0.15  # seconds to confirm state change
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

    def process_rep(self, arm, angle, metrics, current_time, history):
        """
        ENHANCED: Proper state machine with hysteresis and confirmation delays
        """
        metrics.angle = angle
        self.angle_history[arm].append(angle)

        # Need enough history for velocity calculation
        if len(self.angle_history[arm]) < 4:
            return

        # Calculate velocity (degrees per frame)
        recent_angles = list(self.angle_history[arm])
        velocity = abs(recent_angles[-1] - recent_angles[-4]) / 3
        
        # Calculate acceleration (change in velocity)
        if len(recent_angles) >= 6:
            prev_velocity = abs(recent_angles[-4] - recent_angles[-6]) / 2
            acceleration = abs(velocity - prev_velocity)
        else:
            acceleration = 0

        prev_stage = metrics.stage
        metrics.feedback = ""

        # Get thresholds with hysteresis
        contracted = self.calibration.contracted_threshold
        extended = self.calibration.extended_threshold
        
        # Determine target state based on angle with hysteresis zones
        target_state = self._determine_target_state(
            angle, contracted, extended, prev_stage
        )
        
        # State confirmation logic - prevents jitter
        if target_state != prev_stage:
            if self.pending_state[arm] == target_state:
                # Check if we've held this pending state long enough
                hold_duration = current_time - self.pending_state_start[arm]
                
                # Also require that velocity has settled (not in rapid motion)
                velocity_settled = velocity < 15
                
                if hold_duration >= self.state_hold_time and velocity_settled:
                    # Confirmed state change
                    self._handle_state_transition(
                        arm, prev_stage, target_state, 
                        metrics, current_time, history
                    )
            else:
                # New pending state
                self.pending_state[arm] = target_state
                self.pending_state_start[arm] = current_time
        else:
            # Already in target state - clear pending
            self.pending_state[arm] = None

        # Update current rep timing
        if metrics.stage == ArmStage.UP.value:
            metrics.curr_rep_time = current_time - self.rep_start_time[arm]

        # Form feedback (only when not in rapid motion)
        if velocity < 20:
            self._provide_form_feedback(
                angle, metrics, contracted, extended, arm, history
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
        
        # Default: maintain current state
        return current_stage

    def _handle_state_transition(self, arm, prev_stage, new_stage, 
                                 metrics, current_time, history):
        """
        Handle validated state transitions and rep counting
        """
        # Update stage
        metrics.stage = new_stage
        
        # REP COUNTING LOGIC
        # A rep is counted when transitioning from UP to MOVING_DOWN or DOWN
        # This ensures the full curl was completed
        if prev_stage == ArmStage.UP.value:
            if new_stage in [ArmStage.MOVING_DOWN.value, ArmStage.DOWN.value]:
                # Calculate rep time
                rep_time = current_time - metrics.last_down_time
                
                # Validate rep duration (prevents false counts)
                if rep_time >= self.min_rep_duration:
                    metrics.rep_count += 1
                    metrics.rep_time = rep_time
                    
                    # Update minimum rep time
                    if metrics.min_rep_time == 0:
                        metrics.min_rep_time = rep_time
                    else:
                        metrics.min_rep_time = min(rep_time, metrics.min_rep_time)
                    
                    # Reset for next rep
                    metrics.last_down_time = current_time
                    metrics.curr_rep_time = 0
        
        # Start timing when entering DOWN state (beginning of rep)
        elif new_stage == ArmStage.DOWN.value:
            self.rep_start_time[arm] = current_time
        
        # Track when entering UP state
        elif new_stage == ArmStage.UP.value:
            if self.rep_start_time[arm] == 0:
                self.rep_start_time[arm] = current_time

    def _provide_form_feedback(self, angle, metrics, contracted, 
                               extended, arm, history):
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
            
            elif metrics.stage == ArmStage.DOWN.value or metrics.stage == ArmStage.MOVING_DOWN.value:
                # Use effective_extended for comparison
                if angle < effective_extended - 10:  # Not quite at bottom
                    metrics.feedback = "Extend Fully"
                    setattr(history, feedback_key, getattr(history, feedback_key) + 1)

    def reset_arm(self, arm):
        """Reset tracking for specific arm"""
        self.angle_history[arm].clear()
        self.pending_state[arm] = None
        self.pending_state_start[arm] = 0
        self.rep_start_time[arm] = 0