"""
Gaze-based annotation creation engine.

Core logic for creating annotations based on gaze fixations with quality assessment,
EDF coordinate mapping, and integration with existing annotation system.

This module handles the conversion of validated fixations into meaningful
annotations within the EDF viewer's existing annotation framework.
"""

import time
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AnnotationCategory(Enum):
    """Categories of gaze-generated annotations."""
    SPIKE = "Spike"
    ARTIFACT = "Artifact"
    SEIZURE = "Seizure Activity"
    ABNORMAL = "Abnormal Activity"
    NORMAL = "Normal Variant"
    REVIEW = "Needs Review"
    CUSTOM = "Custom"


class AnnotationQuality(Enum):
    """Quality levels for gaze-generated annotations."""
    HIGH = "High"      # >90% confidence, stable fixation
    MEDIUM = "Medium"  # 70-90% confidence, good fixation
    LOW = "Low"        # 50-70% confidence, marginal fixation
    UNCERTAIN = "Uncertain"  # <50% confidence, poor fixation


@dataclass
class FixationAnalysis:
    """Analysis results for a fixation."""
    fixation_duration: float
    fixation_stability: float
    confidence_score: float
    eeg_context_score: float
    channel_relevance: float
    annotation_worthiness: float
    suggested_category: AnnotationCategory
    quality_level: AnnotationQuality


@dataclass
class GazeAnnotationMetadata:
    """Metadata for gaze-generated annotations."""
    gaze_generated: bool = True
    fixation_duration: float = 0.0
    fixation_stability: float = 0.0
    confidence_score: float = 0.0
    eeg_context_score: float = 0.0
    quality_level: str = "Medium"
    analysis_timestamp: str = ""
    processing_version: str = "1.0"


class FixationAnalyzer:
    """
    Analyzes fixations to determine annotation worthiness.
    
    Evaluates fixation characteristics, EEG context, and user patterns
    to determine if a fixation should generate an annotation.
    """
    
    def __init__(self):
        """Initialize fixation analyzer."""
        self.min_fixation_duration = 0.3  # Minimum 300ms for annotation
        self.min_stability_threshold = 0.7  # Minimum stability score
        self.min_confidence_threshold = 0.5  # Minimum confidence for annotation
        
        # Analysis weights
        self.weights = {
            'duration': 0.25,
            'stability': 0.30,
            'confidence': 0.25,
            'eeg_context': 0.20
        }
        
        logger.debug("FixationAnalyzer initialized")
    
    def analyze_fixation(self, fixation_data: Dict[str, Any], 
                        eeg_context: Dict[str, Any] = None) -> FixationAnalysis:
        """
        Analyze a fixation for annotation potential.
        
        Args:
            fixation_data: Fixation information from detector
            eeg_context: EEG data context around fixation
            
        Returns:
            FixationAnalysis with detailed analysis results
        """
        # Extract fixation characteristics
        duration = fixation_data.get('duration', 0.0)
        stability = fixation_data.get('stability', 0.0)
        confidence = fixation_data.get('confidence', 0.0)
        
        # Analyze EEG context if available
        eeg_score = self._analyze_eeg_context(eeg_context) if eeg_context else 0.5
        
        # Calculate channel relevance
        channel_relevance = self._calculate_channel_relevance(
            fixation_data.get('channel'), eeg_context
        )
        
        # Calculate overall annotation worthiness
        worthiness = self._calculate_worthiness(duration, stability, confidence, eeg_score)
        
        # Determine suggested category and quality
        category = self._suggest_category(eeg_context, worthiness)
        quality = self._determine_quality(duration, stability, confidence, worthiness)
        
        analysis = FixationAnalysis(
            fixation_duration=duration,
            fixation_stability=stability,
            confidence_score=confidence,
            eeg_context_score=eeg_score,
            channel_relevance=channel_relevance,
            annotation_worthiness=worthiness,
            suggested_category=category,
            quality_level=quality
        )
        
        logger.debug(f"Fixation analysis: worthiness={worthiness:.2f}, quality={quality.value}")
        
        return analysis
    
    def _analyze_eeg_context(self, eeg_context: Dict[str, Any]) -> float:
        """
        Analyze EEG context around fixation.
        
        Args:
            eeg_context: EEG data and characteristics
            
        Returns:
            Context relevance score (0-1)
        """
        if not eeg_context:
            return 0.5
        
        score = 0.5  # Baseline score
        
        # Check for spike activity
        if eeg_context.get('spike_detected', False):
            score += 0.3
        
        # Check for abnormal amplitude
        amplitude_z_score = eeg_context.get('amplitude_z_score', 0)
        if abs(amplitude_z_score) > 2.0:  # > 2 standard deviations
            score += 0.2
        
        # Check for frequency anomalies
        if eeg_context.get('frequency_anomaly', False):
            score += 0.2
        
        # Check for artifact presence
        if eeg_context.get('artifact_detected', False):
            score += 0.1  # Artifacts are worth noting but lower priority
        
        return min(1.0, score)
    
    def _calculate_channel_relevance(self, channel: str, 
                                   eeg_context: Dict[str, Any]) -> float:
        """
        Calculate relevance of the fixated channel.
        
        Args:
            channel: Channel name
            eeg_context: EEG context data
            
        Returns:
            Channel relevance score (0-1)
        """
        if not channel:
            return 0.5
        
        # High-value channels for clinical review
        high_value_channels = {
            'Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 
            'O1', 'O2', 'F7', 'F8', 'T3', 'T4', 'T5', 'T6'
        }
        
        base_score = 0.8 if channel in high_value_channels else 0.6
        
        # Boost score if this channel has notable activity
        if eeg_context and channel in eeg_context.get('active_channels', []):
            base_score += 0.2
        
        return min(1.0, base_score)
    
    def _calculate_worthiness(self, duration: float, stability: float, 
                            confidence: float, eeg_score: float) -> float:
        """
        Calculate overall annotation worthiness score.
        
        Args:
            duration: Fixation duration in seconds
            stability: Fixation stability score
            confidence: Gaze confidence score
            eeg_score: EEG context score
            
        Returns:
            Worthiness score (0-1)
        """
        # Normalize duration (cap at 3 seconds)
        duration_score = min(1.0, duration / 3.0)
        
        # Apply weights
        weighted_score = (
            self.weights['duration'] * duration_score +
            self.weights['stability'] * stability +
            self.weights['confidence'] * confidence +
            self.weights['eeg_context'] * eeg_score
        )
        
        return weighted_score
    
    def _suggest_category(self, eeg_context: Dict[str, Any], 
                         worthiness: float) -> AnnotationCategory:
        """
        Suggest annotation category based on context.
        
        Args:
            eeg_context: EEG context data
            worthiness: Overall worthiness score
            
        Returns:
            Suggested annotation category
        """
        if not eeg_context:
            return AnnotationCategory.REVIEW
        
        # Check for specific patterns
        if eeg_context.get('spike_detected', False):
            return AnnotationCategory.SPIKE
        
        if eeg_context.get('seizure_pattern', False):
            return AnnotationCategory.SEIZURE
        
        if eeg_context.get('artifact_detected', False):
            return AnnotationCategory.ARTIFACT
        
        # Check for abnormal activity
        amplitude_z = abs(eeg_context.get('amplitude_z_score', 0))
        if amplitude_z > 2.5:
            return AnnotationCategory.ABNORMAL
        elif amplitude_z > 1.5:
            return AnnotationCategory.NORMAL
        
        # Default based on worthiness
        if worthiness > 0.8:
            return AnnotationCategory.ABNORMAL
        elif worthiness > 0.6:
            return AnnotationCategory.REVIEW
        else:
            return AnnotationCategory.NORMAL
    
    def _determine_quality(self, duration: float, stability: float, 
                          confidence: float, worthiness: float) -> AnnotationQuality:
        """
        Determine annotation quality level.
        
        Args:
            duration: Fixation duration
            stability: Fixation stability
            confidence: Gaze confidence
            worthiness: Overall worthiness
            
        Returns:
            Quality level
        """
        # High quality: all metrics above thresholds
        if (duration >= 1.0 and stability >= 0.8 and 
            confidence >= 0.8 and worthiness >= 0.8):
            return AnnotationQuality.HIGH
        
        # Medium quality: most metrics good
        if (duration >= 0.5 and stability >= 0.6 and 
            confidence >= 0.6 and worthiness >= 0.6):
            return AnnotationQuality.MEDIUM
        
        # Low quality: meets minimum thresholds
        if (duration >= self.min_fixation_duration and 
            stability >= self.min_stability_threshold and 
            confidence >= self.min_confidence_threshold):
            return AnnotationQuality.LOW
        
        # Below thresholds
        return AnnotationQuality.UNCERTAIN


class ChannelMapper:
    """
    Maps gaze coordinates to EEG channels and time windows.
    
    Handles coordinate transformation from screen/plot coordinates
    to EDF data coordinates (time, channel).
    """
    
    def __init__(self):
        """Initialize channel mapper."""
        self.channels = []
        self.time_range = (0.0, 1.0)
        self.plot_bounds = None
        self.channel_height = 50  # Default channel height in pixels
        
        logger.debug("ChannelMapper initialized")
    
    def configure(self, channels: List[str], time_range: Tuple[float, float],
                 plot_bounds: Dict[str, float], channel_height: float):
        """
        Configure mapper with current display settings.
        
        Args:
            channels: List of channel names in display order
            time_range: (start_time, end_time) in seconds
            plot_bounds: Plot widget bounds
            channel_height: Height per channel in pixels
        """
        self.channels = channels
        self.time_range = time_range
        self.plot_bounds = plot_bounds
        self.channel_height = channel_height
        
        logger.debug(f"ChannelMapper configured: {len(channels)} channels, "
                    f"time range {time_range}")
    
    def map_coordinates(self, x: float, y: float) -> Tuple[float, str, bool]:
        """
        Map screen coordinates to EDF coordinates.
        
        Args:
            x: Screen X coordinate
            y: Screen Y coordinate
            
        Returns:
            Tuple of (time_seconds, channel_name, is_valid)
        """
        if not self.plot_bounds or not self.channels:
            return 0.0, "", False
        
        # Map X to time
        plot_width = self.plot_bounds.get('width', 800)
        plot_x_offset = self.plot_bounds.get('x', 0)
        
        relative_x = (x - plot_x_offset) / plot_width
        if relative_x < 0 or relative_x > 1:
            return 0.0, "", False
        
        time_seconds = (self.time_range[0] + 
                       relative_x * (self.time_range[1] - self.time_range[0]))
        
        # Map Y to channel
        plot_height = self.plot_bounds.get('height', 600)
        plot_y_offset = self.plot_bounds.get('y', 0)
        
        relative_y = (y - plot_y_offset) / plot_height
        if relative_y < 0 or relative_y > 1:
            return time_seconds, "", False
        
        # Calculate channel index
        channel_index = int(relative_y * len(self.channels))
        if channel_index >= len(self.channels):
            channel_index = len(self.channels) - 1
        
        channel_name = self.channels[channel_index] if self.channels else ""
        
        is_valid = (0 <= time_seconds <= self.time_range[1] and 
                   channel_name in self.channels)
        
        return time_seconds, channel_name, is_valid


class TimeWindowValidator:
    """
    Validates that annotations are within valid data ranges.
    
    Ensures annotations don't exceed EDF data bounds and have
    appropriate duration based on context.
    """
    
    def __init__(self):
        """Initialize time window validator."""
        self.data_duration = 0.0
        self.min_annotation_duration = 0.1  # 100ms minimum
        self.max_annotation_duration = 10.0  # 10s maximum
        self.default_duration = 1.0  # 1s default
        
        logger.debug("TimeWindowValidator initialized")
    
    def set_data_bounds(self, data_duration: float):
        """
        Set the total data duration for validation.
        
        Args:
            data_duration: Total EDF data duration in seconds
        """
        self.data_duration = data_duration
        logger.debug(f"Data bounds set: {data_duration}s")
    
    def validate_annotation(self, start_time: float, duration: float = None) -> Tuple[float, float, bool]:
        """
        Validate and adjust annotation timing.
        
        Args:
            start_time: Proposed start time in seconds
            duration: Proposed duration in seconds (None for default)
            
        Returns:
            Tuple of (adjusted_start_time, adjusted_duration, is_valid)
        """
        if duration is None:
            duration = self.default_duration
        
        # Validate start time
        if start_time < 0:
            start_time = 0
        elif start_time >= self.data_duration:
            return start_time, duration, False
        
        # Validate duration
        duration = max(self.min_annotation_duration, 
                      min(self.max_annotation_duration, duration))
        
        # Ensure annotation doesn't exceed data bounds
        if start_time + duration > self.data_duration:
            duration = self.data_duration - start_time
            if duration < self.min_annotation_duration:
                return start_time, duration, False
        
        is_valid = (0 <= start_time < self.data_duration and 
                   duration >= self.min_annotation_duration)
        
        return start_time, duration, is_valid


class GazeAnnotator:
    """
    Core gaze annotation creation engine.
    
    Coordinates fixation analysis, coordinate mapping, and annotation creation
    to convert gaze fixations into meaningful EDF annotations.
    """
    
    def __init__(self, annotation_manager):
        """
        Initialize gaze annotator.
        
        Args:
            annotation_manager: Existing annotation manager from main application
        """
        self.annotation_manager = annotation_manager
        
        # Component instances
        self.analyzer = FixationAnalyzer()
        self.mapper = ChannelMapper()
        self.validator = TimeWindowValidator()
        
        # Configuration
        self.config = {
            'auto_create_annotations': True,
            'min_quality_threshold': AnnotationQuality.LOW,
            'require_eeg_context': False,
            'default_annotation_duration': 1.0
        }
        
        # Statistics tracking
        self.stats = {
            'fixations_analyzed': 0,
            'annotations_created': 0,
            'annotations_rejected': 0,
            'quality_distribution': {q.value: 0 for q in AnnotationQuality}
        }
        
        logger.info("GazeAnnotator initialized")
    
    def configure(self, config: Dict[str, Any]):
        """
        Configure annotator settings.
        
        Args:
            config: Configuration dictionary
        """
        self.config.update(config)
        logger.info("GazeAnnotator configured")
    
    def set_display_context(self, channels: List[str], time_range: Tuple[float, float],
                           plot_bounds: Dict[str, float], channel_height: float,
                           data_duration: float):
        """
        Set current display context for coordinate mapping.
        
        Args:
            channels: Currently visible channels
            time_range: Current time window
            plot_bounds: Plot widget bounds
            channel_height: Height per channel
            data_duration: Total data duration
        """
        self.mapper.configure(channels, time_range, plot_bounds, channel_height)
        self.validator.set_data_bounds(data_duration)
        
        logger.debug("Display context updated")
    
    def process_fixation(self, fixation_data: Dict[str, Any], 
                        eeg_context: Dict[str, Any] = None) -> bool:
        """
        Process a fixation and potentially create an annotation.
        
        Args:
            fixation_data: Fixation information from detector
            eeg_context: EEG data context around fixation
            
        Returns:
            True if annotation was created, False otherwise
        """
        self.stats['fixations_analyzed'] += 1
        
        try:
            # Analyze fixation
            analysis = self.analyzer.analyze_fixation(fixation_data, eeg_context)
            
            # Update quality statistics
            self.stats['quality_distribution'][analysis.quality_level.value] += 1
            
            # Check if annotation should be created
            if not self._should_create_annotation(analysis):
                self.stats['annotations_rejected'] += 1
                logger.debug("Annotation rejected based on analysis")
                return False
            
            # Map coordinates to EDF space
            x = fixation_data.get('center_x', 0)
            y = fixation_data.get('center_y', 0)
            time_seconds, channel, is_valid = self.mapper.map_coordinates(x, y)
            
            if not is_valid:
                self.stats['annotations_rejected'] += 1
                logger.debug("Annotation rejected - invalid coordinates")
                return False
            
            # Validate timing
            duration = self.config.get('default_annotation_duration', 1.0)
            start_time, adj_duration, time_valid = self.validator.validate_annotation(
                time_seconds, duration)
            
            if not time_valid:
                self.stats['annotations_rejected'] += 1
                logger.debug("Annotation rejected - invalid timing")
                return False
            
            # Create annotation
            annotation_created = self._create_annotation(
                start_time, adj_duration, channel, analysis, fixation_data)
            
            if annotation_created:
                self.stats['annotations_created'] += 1
                logger.info(f"Gaze annotation created: {analysis.suggested_category.value} "
                           f"at {start_time:.1f}s on {channel}")
                return True
            else:
                self.stats['annotations_rejected'] += 1
                return False
                
        except Exception as e:
            logger.error(f"Error processing fixation: {e}")
            self.stats['annotations_rejected'] += 1
            return False
    
    def _should_create_annotation(self, analysis: FixationAnalysis) -> bool:
        """
        Determine if an annotation should be created based on analysis.
        
        Args:
            analysis: Fixation analysis results
            
        Returns:
            True if annotation should be created
        """
        # Check minimum quality threshold
        quality_levels = [AnnotationQuality.UNCERTAIN, AnnotationQuality.LOW,
                         AnnotationQuality.MEDIUM, AnnotationQuality.HIGH]
        min_quality_index = quality_levels.index(self.config['min_quality_threshold'])
        current_quality_index = quality_levels.index(analysis.quality_level)
        
        if current_quality_index < min_quality_index:
            return False
        
        # Check if auto-creation is enabled
        if not self.config.get('auto_create_annotations', True):
            return False
        
        # Check EEG context requirement
        if (self.config.get('require_eeg_context', False) and 
            analysis.eeg_context_score < 0.6):
            return False
        
        # Check minimum worthiness
        if analysis.annotation_worthiness < 0.4:
            return False
        
        return True
    
    def _create_annotation(self, start_time: float, duration: float, 
                          channel: str, analysis: FixationAnalysis,
                          fixation_data: Dict[str, Any]) -> bool:
        """
        Create annotation using existing annotation manager.
        
        Args:
            start_time: Annotation start time
            duration: Annotation duration
            channel: Target channel
            analysis: Fixation analysis results
            fixation_data: Original fixation data
            
        Returns:
            True if annotation was successfully created
        """
        try:
            # Create metadata
            metadata = GazeAnnotationMetadata(
                gaze_generated=True,
                fixation_duration=analysis.fixation_duration,
                fixation_stability=analysis.fixation_stability,
                confidence_score=analysis.confidence_score,
                eeg_context_score=analysis.eeg_context_score,
                quality_level=analysis.quality_level.value,
                analysis_timestamp=datetime.now().isoformat(),
                processing_version="1.0"
            )
            
            # Prepare annotation data
            description = f"{analysis.suggested_category.value} (Gaze)"
            color = self._get_category_color(analysis.suggested_category)
            notes = f"Quality: {analysis.quality_level.value}, " \
                   f"Confidence: {analysis.confidence_score:.2f}, " \
                   f"Worthiness: {analysis.annotation_worthiness:.2f}"
            
            # Create annotation through existing manager
            annotation = {
                'start_time': start_time,
                'duration': duration,
                'description': description,
                'color': color,
                'timestamp': datetime.now().isoformat(),
                'channel': channel,
                'notes': notes,
                'metadata': asdict(metadata)
            }
            
            # Use annotation manager to add annotation
            if hasattr(self.annotation_manager, 'add_annotation'):
                success = self.annotation_manager.add_annotation(annotation)
            else:
                # Fallback: add to annotations list directly
                if hasattr(self.annotation_manager, 'annotations'):
                    self.annotation_manager.annotations.append(annotation)
                    success = True
                else:
                    logger.error("Unable to add annotation - manager interface unknown")
                    success = False
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating annotation: {e}")
            return False
    
    def _get_category_color(self, category: AnnotationCategory) -> str:
        """
        Get color for annotation category.
        
        Args:
            category: Annotation category
            
        Returns:
            Color string
        """
        color_map = {
            AnnotationCategory.SPIKE: '#FF4444',       # Red
            AnnotationCategory.SEIZURE: '#FF0000',     # Bright red
            AnnotationCategory.ARTIFACT: '#FFAA00',    # Orange
            AnnotationCategory.ABNORMAL: '#FF6600',    # Orange-red
            AnnotationCategory.NORMAL: '#00AA00',      # Green
            AnnotationCategory.REVIEW: '#FFFF00',      # Yellow
            AnnotationCategory.CUSTOM: '#AA00AA'       # Purple
        }
        
        return color_map.get(category, '#FFFF00')
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get annotator statistics.
        
        Returns:
            Statistics dictionary
        """
        total_processed = self.stats['fixations_analyzed']
        creation_rate = (self.stats['annotations_created'] / total_processed 
                        if total_processed > 0 else 0)
        
        return {
            'fixations_analyzed': self.stats['fixations_analyzed'],
            'annotations_created': self.stats['annotations_created'],
            'annotations_rejected': self.stats['annotations_rejected'],
            'creation_rate': creation_rate,
            'quality_distribution': self.stats['quality_distribution'].copy(),
            'config': self.config.copy()
        }
    
    def reset_statistics(self):
        """Reset all statistics counters."""
        self.stats = {
            'fixations_analyzed': 0,
            'annotations_created': 0,
            'annotations_rejected': 0,
            'quality_distribution': {q.value: 0 for q in AnnotationQuality}
        }
        
        logger.debug("Statistics reset")