"""
Rep counting logic with form validation
"""

class RepCounter:
    """Handles rep counting logic with form validation"""
    
    def __init__(self, calibration_data, min_rep_duration: float = 0.5):
        self.calibration = calibration_data
        self.min_rep_duration = min_rep_duration
    
    def process_rep(self, arm: str, angle: int, metrics, 
                   current_time: float, history) -> None:
        """Process rep counting and form feedback for one arm"""
        from constants import ArmStage
        
        # Update current rep time
        metrics.curr_rep_time = current_time - metrics.last_down_time
        metrics.angle = angle
        metrics.feedback = ""
        
        # Stage transitions
        if angle < self.calibration.contracted_threshold:
            metrics.stage = ArmStage.UP.value
        
        if angle > self.calibration.extended_threshold:
            # Count rep only if coming from UP stage and minimum duration met
            if metrics.stage == ArmStage.UP.value and metrics.curr_rep_time >= self.min_rep_duration:
                rep_time = current_time - metrics.last_down_time
                
                # Update metrics
                if metrics.min_rep_time == 0.0 or rep_time < metrics.min_rep_time:
                    metrics.min_rep_time = rep_time
                
                metrics.rep_count += 1
                metrics.rep_time = rep_time
                metrics.last_down_time = current_time
            
            metrics.stage = ArmStage.DOWN.value
        
        # Form feedback
        feedback_key = f'{arm.lower()}_feedback_count'
        
        if angle < self.calibration.safe_angle_min:
            metrics.feedback = "OVER-CURLING"
            setattr(history, feedback_key, getattr(history, feedback_key) + 1)
        elif angle > self.calibration.safe_angle_max:
            metrics.feedback = "OVER-EXTENDING"
            setattr(history, feedback_key, getattr(history, feedback_key) + 1)
        elif self.calibration.contracted_threshold < angle < self.calibration.extended_threshold:
            if metrics.stage == ArmStage.DOWN.value:
                metrics.feedback = "STRAIGHTEN ARM"
            elif metrics.stage == ArmStage.UP.value:
                metrics.feedback = "CURL DEEPER"