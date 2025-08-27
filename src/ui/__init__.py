"""
User interface extensions for gaze tracking functionality.

Phase 1: Basic gaze mode setup dialog
Phase 3: Visual feedback and overlay components
"""

from .gaze_mode_dialog import GazeModeSetupDialog
from .gaze_overlay import GazeOverlayManager, GazeCursor, FixationProgressIndicator, AnnotationPreview
from .feedback_system import FeedbackSystem, VisualFeedbackPanel, FeedbackType, FeedbackEvent

__all__ = [
    # Phase 1 components
    'GazeModeSetupDialog',
    # Phase 3 components
    'GazeOverlayManager', 'GazeCursor', 'FixationProgressIndicator', 'AnnotationPreview',
    'FeedbackSystem', 'VisualFeedbackPanel', 'FeedbackType', 'FeedbackEvent'
]