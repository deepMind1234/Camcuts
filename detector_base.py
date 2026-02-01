from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseDetector(ABC):
    @abstractmethod
    def process_frame(self, frame) -> List[Dict[str, Any]]:
        """
        Process a single frame and return a list of detected symbols.
        Each detected symbol should be a dictionary containing:
        - 'label': The name of the symbol (e.g., 'THUMBS_UP')
        - 'confidence': Confidence score (0.0 to 1.0)
        - 'landmarks': Optional list of landmark coordinates
        """
        pass

    @abstractmethod
    def release(self):
        """Release any resources used by the detector."""
        pass
