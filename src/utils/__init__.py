"""
Utility modules for gaze tracking system.

Phase 4: Advanced gaze analytics and EEG context analysis
"""

from .gaze_analytics import (
    ContextAnalyzer, PatternRecognizer, ConfidenceScorer, 
    BehaviorAnalyzer, EfficiencyMetrics,
    EEGPatternType, EEGContextAnalysis, FixationPattern, BehaviorMetrics
)

__all__ = [
    # Phase 4 analytics components
    'ContextAnalyzer', 'PatternRecognizer', 'ConfidenceScorer',
    'BehaviorAnalyzer', 'EfficiencyMetrics',
    'EEGPatternType', 'EEGContextAnalysis', 'FixationPattern', 'BehaviorMetrics'
]