"""
Gaze tracking module for EDF viewer.
Provides eye tracking integration and gaze-based annotation functionality.

Phase 1: Core hardware interface and coordinate mapping
Phase 2: Gaze data processing and fixation detection
"""

from .gaze_tracker import GazeTracker, GazeDataCallback, GazePoint, MockGazeTracker
from .coordinate_mapper import CoordinateMapper, CalibrationData, EDFCoordinates, CoordinateBounds
from .fixation_detector import FixationDetector, FixationPoint, FixationConfig, FixationAlgorithm
from .gaze_processor import GazeProcessor, GazeEvent, ProcessingStats

__all__ = [
    # Phase 1 components
    'GazeTracker', 'GazeDataCallback', 'GazePoint', 'MockGazeTracker',
    'CoordinateMapper', 'CalibrationData', 'EDFCoordinates', 'CoordinateBounds',
    # Phase 2 components
    'FixationDetector', 'FixationPoint', 'FixationConfig', 'FixationAlgorithm',
    'GazeProcessor', 'GazeEvent', 'ProcessingStats'
]