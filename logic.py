import time
from typing import Dict, Optional

class LogicLayer:
    def __init__(self, action_map: Dict[str, Dict[str, str]], default_duration: float = 1.0, confidence_threshold: float = 0.8):
        self.action_map = action_map
        self.default_duration = default_duration
        self.confidence_threshold = confidence_threshold
        
        self.current_symbol: Optional[str] = None
        self.symbol_start_time: float = 0
        self.triggered_symbols = set()
        self.last_cycle_time: float = 0
        self.last_trigger_times: Dict[str, float] = {} # For cooldowns

    def update(self, detections) -> Optional[Dict[str, str]]:
        if not detections:
            self.current_symbol = None
            self.triggered_symbols.clear()
            return None

        # Pick the detection with highest confidence
        best_detection = max(detections, key=lambda x: x['confidence'])
        if best_detection['confidence'] < self.confidence_threshold:
            self.current_symbol = None
            return None

        symbol = best_detection['label']
        action_cfg = self.action_map.get(symbol, {})
        required_hold = action_cfg.get('hold_duration', self.default_duration)
        cooldown = action_cfg.get('cooldown', 0)

        now = time.time()

        if symbol == self.current_symbol:
            duration = now - self.symbol_start_time
            
            if duration >= required_hold:
                if not action_cfg:
                    return None
                
                # Check cooldown for one-shot actions
                last_triggered = self.last_trigger_times.get(symbol, 0)
                if (now - last_triggered) < cooldown:
                    return None

                # Handle cycled actions (e.g. Volume)
                if action_cfg.get('behavior') == 'cycle':
                    # Special Request: Cycle back to mute once hit max (approximated by 5 seconds of hold)
                    if (now - self.symbol_start_time) > (required_hold + 5.0):
                        self.symbol_start_time = now
                        self.last_trigger_times[symbol] = now
                        return {"type": "keystroke", "command": "m"}
                    
                    if (now - self.last_cycle_time) > 0.2: # Trigger every 200ms
                        self.last_cycle_time = now
                        return action_cfg
                    return None
                
                # Handle one-shot actions (Pause, FullScreen)
                if symbol not in self.triggered_symbols:
                    self.triggered_symbols.add(symbol)
                    self.last_trigger_times[symbol] = now
                    return action_cfg
        else:
            self.current_symbol = symbol
            self.symbol_start_time = now
            self.triggered_symbols.clear()
            self.last_cycle_time = 0

        return None
