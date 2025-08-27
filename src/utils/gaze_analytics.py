"""
Advanced gaze pattern analysis for improved annotation quality.

Provides EEG context awareness, pattern recognition, and statistical analysis
to enhance the quality and relevance of gaze-generated annotations.

This module analyzes EEG signals around fixation points to provide
intelligent annotation suggestions and quality scoring.
"""

import numpy as np
import time
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from scipy import signal, stats
from collections import deque, defaultdict

logger = logging.getLogger(__name__)


class EEGPatternType(Enum):
    """Types of EEG patterns that can be detected."""
    SPIKE = "spike"
    SHARP_WAVE = "sharp_wave"
    SEIZURE_ACTIVITY = "seizure_activity"
    SLOW_WAVE = "slow_wave"
    ARTIFACT = "artifact"
    NORMAL_ACTIVITY = "normal_activity"
    ALPHA_RHYTHM = "alpha_rhythm"
    BETA_ACTIVITY = "beta_activity"
    THETA_ACTIVITY = "theta_activity"
    DELTA_ACTIVITY = "delta_activity"


@dataclass
class EEGContextAnalysis:
    """Results of EEG context analysis around a fixation."""
    time_window: Tuple[float, float]
    channel: str
    pattern_type: EEGPatternType
    confidence: float
    amplitude_stats: Dict[str, float]
    frequency_analysis: Dict[str, float]
    morphology_score: float
    clinical_significance: float
    recommendation: str


@dataclass
class FixationPattern:
    """Pattern analysis for fixation behavior."""
    fixation_count: int
    average_duration: float
    spatial_distribution: Dict[str, float]
    temporal_clustering: float
    channel_preferences: Dict[str, int]
    annotation_efficiency: float


@dataclass
class BehaviorMetrics:
    """User behavior analysis metrics."""
    review_speed: float  # Windows per minute
    annotation_rate: float  # Annotations per minute
    fixation_quality: float  # Average fixation quality
    channel_coverage: float  # Percentage of channels reviewed
    pattern_consistency: float  # Consistency in review patterns
    efficiency_score: float  # Overall efficiency rating


class ContextAnalyzer:
    """
    Analyzes EEG context around fixation points.
    
    Provides intelligent analysis of EEG signals to determine
    the clinical significance of fixated regions.
    """
    
    def __init__(self):
        """Initialize context analyzer."""
        self.sampling_rate = 256  # Default EEG sampling rate
        self.analysis_window = 2.0  # Seconds around fixation
        
        # Frequency band definitions (Hz)
        self.frequency_bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'beta': (13, 30),
            'gamma': (30, 100)
        }
        
        # Pattern detection thresholds
        self.thresholds = {
            'spike_amplitude': 3.0,  # Standard deviations
            'sharp_wave_duration': 0.2,  # Seconds
            'artifact_amplitude': 5.0,  # Standard deviations
            'seizure_frequency': 2.0  # Hz minimum for seizure patterns
        }
        
        logger.debug("ContextAnalyzer initialized")
    
    def analyze_fixation_context(self, eeg_data: np.ndarray, fixation_time: float,
                                channel_idx: int, channel_name: str) -> EEGContextAnalysis:
        """
        Analyze EEG context around a fixation point.
        
        Args:
            eeg_data: EEG data array (channels x samples)
            fixation_time: Time of fixation in seconds
            channel_idx: Index of fixated channel
            channel_name: Name of fixated channel
            
        Returns:
            EEGContextAnalysis with detailed analysis results
        """
        # Extract time window around fixation
        window_start = max(0, fixation_time - self.analysis_window / 2)
        window_end = min(eeg_data.shape[1] / self.sampling_rate, 
                        fixation_time + self.analysis_window / 2)
        
        start_sample = int(window_start * self.sampling_rate)
        end_sample = int(window_end * self.sampling_rate)
        
        if start_sample >= end_sample or channel_idx >= eeg_data.shape[0]:
            return self._create_empty_analysis(fixation_time, channel_name)
        
        # Extract channel data
        channel_data = eeg_data[channel_idx, start_sample:end_sample]
        
        # Perform various analyses
        amplitude_stats = self._analyze_amplitude(channel_data)
        frequency_analysis = self._analyze_frequency_content(channel_data)
        pattern_type, confidence = self._detect_pattern_type(channel_data, amplitude_stats, frequency_analysis)
        morphology_score = self._analyze_morphology(channel_data, pattern_type)
        clinical_significance = self._assess_clinical_significance(
            pattern_type, amplitude_stats, frequency_analysis, morphology_score)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            pattern_type, confidence, clinical_significance)
        
        analysis = EEGContextAnalysis(
            time_window=(window_start, window_end),
            channel=channel_name,
            pattern_type=pattern_type,
            confidence=confidence,
            amplitude_stats=amplitude_stats,
            frequency_analysis=frequency_analysis,
            morphology_score=morphology_score,
            clinical_significance=clinical_significance,
            recommendation=recommendation
        )
        
        logger.debug(f"Context analysis: {pattern_type.value} "
                    f"(confidence={confidence:.2f}, significance={clinical_significance:.2f})")
        
        return analysis
    
    def _analyze_amplitude(self, data: np.ndarray) -> Dict[str, float]:
        """Analyze amplitude characteristics of EEG signal."""
        if len(data) == 0:
            return {'mean': 0, 'std': 0, 'max': 0, 'min': 0, 'z_score_max': 0}
        
        mean_amp = np.mean(data)
        std_amp = np.std(data)
        max_amp = np.max(data)
        min_amp = np.min(data)
        
        # Calculate z-scores for extreme values
        z_score_max = (max_amp - mean_amp) / (std_amp + 1e-10)
        z_score_min = (min_amp - mean_amp) / (std_amp + 1e-10)
        
        return {
            'mean': float(mean_amp),
            'std': float(std_amp),
            'max': float(max_amp),
            'min': float(min_amp),
            'z_score_max': float(z_score_max),
            'z_score_min': float(z_score_min),
            'peak_to_peak': float(max_amp - min_amp)
        }
    
    def _analyze_frequency_content(self, data: np.ndarray) -> Dict[str, float]:
        """Analyze frequency content of EEG signal."""
        if len(data) < 64:  # Too short for reliable frequency analysis
            return {band: 0.0 for band in self.frequency_bands.keys()}
        
        try:
            # Compute power spectral density
            freqs, psd = signal.welch(data, fs=self.sampling_rate, nperseg=min(256, len(data)))
            
            # Calculate power in each frequency band
            band_powers = {}
            total_power = np.sum(psd)
            
            for band_name, (low_freq, high_freq) in self.frequency_bands.items():
                band_mask = (freqs >= low_freq) & (freqs <= high_freq)
                band_power = np.sum(psd[band_mask])
                band_powers[band_name] = float(band_power / (total_power + 1e-10))
            
            # Add dominant frequency
            dominant_freq_idx = np.argmax(psd)
            band_powers['dominant_frequency'] = float(freqs[dominant_freq_idx])
            
            return band_powers
            
        except Exception as e:
            logger.error(f"Frequency analysis error: {e}")
            return {band: 0.0 for band in self.frequency_bands.keys()}
    
    def _detect_pattern_type(self, data: np.ndarray, amplitude_stats: Dict[str, float],
                           frequency_analysis: Dict[str, float]) -> Tuple[EEGPatternType, float]:
        """Detect the type of EEG pattern present."""
        confidence = 0.5  # Base confidence
        
        # Check for spike patterns
        if amplitude_stats['z_score_max'] > self.thresholds['spike_amplitude']:
            if amplitude_stats['peak_to_peak'] > 50:  # Amplitude threshold
                return EEGPatternType.SPIKE, min(0.9, confidence + 0.4)
        
        # Check for artifact
        if amplitude_stats['z_score_max'] > self.thresholds['artifact_amplitude']:
            return EEGPatternType.ARTIFACT, min(0.9, confidence + 0.3)
        
        # Check for seizure activity (high frequency, high amplitude)
        if (frequency_analysis.get('beta', 0) > 0.3 and 
            amplitude_stats['z_score_max'] > 2.0):
            return EEGPatternType.SEIZURE_ACTIVITY, min(0.8, confidence + 0.3)
        
        # Check for slow wave activity
        if frequency_analysis.get('delta', 0) > 0.5:
            return EEGPatternType.SLOW_WAVE, confidence + 0.2
        
        # Check for normal rhythms
        if frequency_analysis.get('alpha', 0) > 0.4:
            return EEGPatternType.ALPHA_RHYTHM, confidence + 0.1
        
        if frequency_analysis.get('beta', 0) > 0.3:
            return EEGPatternType.BETA_ACTIVITY, confidence + 0.1
        
        # Default to normal activity
        return EEGPatternType.NORMAL_ACTIVITY, confidence
    
    def _analyze_morphology(self, data: np.ndarray, pattern_type: EEGPatternType) -> float:
        """Analyze morphological characteristics of the pattern."""
        if len(data) < 10:
            return 0.5
        
        try:
            # Calculate morphology features
            smoothness = self._calculate_smoothness(data)
            symmetry = self._calculate_symmetry(data)
            sharpness = self._calculate_sharpness(data)
            
            # Weight features based on pattern type
            if pattern_type in [EEGPatternType.SPIKE, EEGPatternType.SHARP_WAVE]:
                # For spikes, favor sharpness and asymmetry
                score = 0.5 * sharpness + 0.3 * (1 - symmetry) + 0.2 * smoothness
            elif pattern_type == EEGPatternType.ARTIFACT:
                # Artifacts typically have poor morphology
                score = 0.3  # Low morphology score
            else:
                # For normal patterns, favor smoothness and symmetry
                score = 0.4 * smoothness + 0.4 * symmetry + 0.2 * sharpness
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.error(f"Morphology analysis error: {e}")
            return 0.5
    
    def _calculate_smoothness(self, data: np.ndarray) -> float:
        """Calculate smoothness of signal."""
        if len(data) < 3:
            return 0.5
        
        # Calculate second derivative (measure of curvature)
        second_deriv = np.diff(data, n=2)
        smoothness = 1.0 / (1.0 + np.std(second_deriv))
        return min(1.0, smoothness)
    
    def _calculate_symmetry(self, data: np.ndarray) -> float:
        """Calculate symmetry of signal around its peak."""
        if len(data) < 5:
            return 0.5
        
        peak_idx = np.argmax(np.abs(data))
        left_half = data[:peak_idx] if peak_idx > 0 else np.array([])
        right_half = data[peak_idx+1:] if peak_idx < len(data)-1 else np.array([])
        
        if len(left_half) == 0 or len(right_half) == 0:
            return 0.5
        
        # Compare left and right halves
        min_len = min(len(left_half), len(right_half))
        if min_len == 0:
            return 0.5
        
        left_seg = left_half[-min_len:]
        right_seg = right_half[:min_len]
        
        correlation = np.corrcoef(left_seg, right_seg[::-1])[0, 1]
        symmetry = (correlation + 1) / 2  # Convert from [-1,1] to [0,1]
        
        return max(0.0, min(1.0, symmetry))
    
    def _calculate_sharpness(self, data: np.ndarray) -> float:
        """Calculate sharpness of signal peaks."""
        if len(data) < 3:
            return 0.5
        
        # Find peaks and calculate their sharpness
        peaks, _ = signal.find_peaks(np.abs(data), height=np.std(data))
        
        if len(peaks) == 0:
            return 0.3  # Low sharpness if no peaks
        
        sharpness_scores = []
        for peak in peaks:
            if peak > 0 and peak < len(data) - 1:
                # Calculate local curvature at peak
                left_slope = data[peak] - data[peak-1]
                right_slope = data[peak+1] - data[peak]
                curvature = abs(left_slope - right_slope)
                sharpness_scores.append(curvature)
        
        if not sharpness_scores:
            return 0.3
        
        avg_sharpness = np.mean(sharpness_scores)
        normalized_sharpness = avg_sharpness / (np.std(data) + 1e-10)
        
        return max(0.0, min(1.0, normalized_sharpness / 5.0))  # Normalize to [0,1]
    
    def _assess_clinical_significance(self, pattern_type: EEGPatternType,
                                    amplitude_stats: Dict[str, float],
                                    frequency_analysis: Dict[str, float],
                                    morphology_score: float) -> float:
        """Assess clinical significance of detected pattern."""
        base_significance = {
            EEGPatternType.SPIKE: 0.9,
            EEGPatternType.SHARP_WAVE: 0.8,
            EEGPatternType.SEIZURE_ACTIVITY: 0.95,
            EEGPatternType.SLOW_WAVE: 0.6,
            EEGPatternType.ARTIFACT: 0.2,
            EEGPatternType.NORMAL_ACTIVITY: 0.3,
            EEGPatternType.ALPHA_RHYTHM: 0.4,
            EEGPatternType.BETA_ACTIVITY: 0.3,
            EEGPatternType.THETA_ACTIVITY: 0.4,
            EEGPatternType.DELTA_ACTIVITY: 0.5
        }
        
        significance = base_significance.get(pattern_type, 0.3)
        
        # Adjust based on amplitude
        if amplitude_stats['z_score_max'] > 3.0:
            significance += 0.1
        elif amplitude_stats['z_score_max'] > 2.0:
            significance += 0.05
        
        # Adjust based on morphology
        significance += (morphology_score - 0.5) * 0.2
        
        return max(0.0, min(1.0, significance))
    
    def _generate_recommendation(self, pattern_type: EEGPatternType, 
                               confidence: float, significance: float) -> str:
        """Generate recommendation text for the analysis."""
        if significance > 0.8:
            urgency = "High priority"
        elif significance > 0.6:
            urgency = "Medium priority"
        else:
            urgency = "Low priority"
        
        if confidence < 0.5:
            confidence_text = "uncertain"
        elif confidence < 0.7:
            confidence_text = "moderate confidence"
        else:
            confidence_text = "high confidence"
        
        pattern_desc = {
            EEGPatternType.SPIKE: "epileptiform spike",
            EEGPatternType.SHARP_WAVE: "sharp wave",
            EEGPatternType.SEIZURE_ACTIVITY: "seizure-like activity",
            EEGPatternType.SLOW_WAVE: "slow wave activity",
            EEGPatternType.ARTIFACT: "likely artifact",
            EEGPatternType.NORMAL_ACTIVITY: "normal activity",
            EEGPatternType.ALPHA_RHYTHM: "alpha rhythm",
            EEGPatternType.BETA_ACTIVITY: "beta activity"
        }.get(pattern_type, "unknown pattern")
        
        return f"{urgency}: {pattern_desc} detected with {confidence_text} (significance: {significance:.1f})"
    
    def _create_empty_analysis(self, fixation_time: float, channel_name: str) -> EEGContextAnalysis:
        """Create empty analysis for invalid data."""
        return EEGContextAnalysis(
            time_window=(fixation_time, fixation_time),
            channel=channel_name,
            pattern_type=EEGPatternType.NORMAL_ACTIVITY,
            confidence=0.0,
            amplitude_stats={'mean': 0, 'std': 0, 'max': 0, 'min': 0, 'z_score_max': 0},
            frequency_analysis={band: 0.0 for band in self.frequency_bands.keys()},
            morphology_score=0.0,
            clinical_significance=0.0,
            recommendation="Insufficient data for analysis"
        )


class PatternRecognizer:
    """
    Recognizes common EEG patterns and abnormalities.
    
    Uses machine learning-like approaches to identify
    clinically relevant patterns in EEG data.
    """
    
    def __init__(self):
        """Initialize pattern recognizer."""
        self.pattern_templates = {}
        self.detection_history = deque(maxlen=100)
        
        logger.debug("PatternRecognizer initialized")
    
    def recognize_patterns(self, eeg_context: EEGContextAnalysis) -> Dict[str, Any]:
        """
        Recognize patterns in EEG context analysis.
        
        Args:
            eeg_context: Results of context analysis
            
        Returns:
            Pattern recognition results
        """
        patterns_found = []
        confidence_scores = []
        
        # Check for known pathological patterns
        if eeg_context.pattern_type == EEGPatternType.SPIKE:
            if eeg_context.confidence > 0.7:
                patterns_found.append("Epileptiform spike")
                confidence_scores.append(eeg_context.confidence)
        
        if eeg_context.pattern_type == EEGPatternType.SEIZURE_ACTIVITY:
            patterns_found.append("Ictal activity")
            confidence_scores.append(eeg_context.confidence)
        
        # Check for artifacts
        if eeg_context.pattern_type == EEGPatternType.ARTIFACT:
            artifact_type = self._classify_artifact(eeg_context)
            patterns_found.append(f"Artifact: {artifact_type}")
            confidence_scores.append(eeg_context.confidence * 0.8)  # Lower confidence for artifacts
        
        # Add to detection history
        detection_record = {
            'timestamp': time.time(),
            'patterns': patterns_found,
            'channel': eeg_context.channel,
            'significance': eeg_context.clinical_significance
        }
        self.detection_history.append(detection_record)
        
        return {
            'patterns_detected': patterns_found,
            'confidence_scores': confidence_scores,
            'pattern_count': len(patterns_found),
            'max_confidence': max(confidence_scores) if confidence_scores else 0.0,
            'clinical_relevance': self._assess_clinical_relevance(patterns_found, confidence_scores)
        }
    
    def _classify_artifact(self, eeg_context: EEGContextAnalysis) -> str:
        """Classify type of artifact detected."""
        amp_stats = eeg_context.amplitude_stats
        freq_analysis = eeg_context.frequency_analysis
        
        # High frequency artifact (muscle, EMG)
        if freq_analysis.get('beta', 0) > 0.4 or freq_analysis.get('gamma', 0) > 0.1:
            return "High frequency (muscle/EMG)"
        
        # Low frequency artifact (movement, eye blink)
        if freq_analysis.get('delta', 0) > 0.6:
            return "Low frequency (movement/eye)"
        
        # High amplitude artifact
        if amp_stats['z_score_max'] > 5.0:
            return "High amplitude (electrode)"
        
        return "Unspecified"
    
    def _assess_clinical_relevance(self, patterns: List[str], 
                                 confidences: List[float]) -> float:
        """Assess overall clinical relevance of detected patterns."""
        if not patterns:
            return 0.0
        
        # Weight by pattern type and confidence
        relevance_weights = {
            'spike': 0.9,
            'seizure': 0.95,
            'ictal': 0.95,
            'artifact': 0.2,
            'normal': 0.1
        }
        
        total_relevance = 0.0
        total_weight = 0.0
        
        for pattern, confidence in zip(patterns, confidences):
            pattern_lower = pattern.lower()
            weight = 0.5  # Default weight
            
            for key, value in relevance_weights.items():
                if key in pattern_lower:
                    weight = value
                    break
            
            total_relevance += weight * confidence
            total_weight += confidence
        
        return total_relevance / (total_weight + 1e-10)


class ConfidenceScorer:
    """
    Scores annotation confidence based on multiple factors.
    
    Combines fixation quality, EEG context, and pattern recognition
    to provide comprehensive confidence scoring.
    """
    
    def __init__(self):
        """Initialize confidence scorer."""
        self.weight_config = {
            'fixation_quality': 0.3,
            'eeg_significance': 0.4,
            'pattern_confidence': 0.2,
            'morphology_score': 0.1
        }
        
        logger.debug("ConfidenceScorer initialized")
    
    def calculate_confidence(self, fixation_data: Dict[str, Any],
                           eeg_context: EEGContextAnalysis,
                           pattern_results: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate comprehensive confidence score.
        
        Args:
            fixation_data: Fixation quality metrics
            eeg_context: EEG context analysis
            pattern_results: Pattern recognition results
            
        Returns:
            Dictionary with confidence scores and components
        """
        # Extract component scores
        fixation_quality = self._score_fixation_quality(fixation_data)
        eeg_significance = eeg_context.clinical_significance
        pattern_confidence = pattern_results.get('max_confidence', 0.0)
        morphology_score = eeg_context.morphology_score
        
        # Calculate weighted confidence
        weights = self.weight_config
        overall_confidence = (
            weights['fixation_quality'] * fixation_quality +
            weights['eeg_significance'] * eeg_significance +
            weights['pattern_confidence'] * pattern_confidence +
            weights['morphology_score'] * morphology_score
        )
        
        return {
            'overall_confidence': overall_confidence,
            'fixation_quality': fixation_quality,
            'eeg_significance': eeg_significance,
            'pattern_confidence': pattern_confidence,
            'morphology_score': morphology_score,
            'confidence_grade': self._grade_confidence(overall_confidence)
        }
    
    def _score_fixation_quality(self, fixation_data: Dict[str, Any]) -> float:
        """Score the quality of the fixation."""
        duration = fixation_data.get('duration', 0.0)
        stability = fixation_data.get('stability', 0.0)
        confidence = fixation_data.get('confidence', 0.0)
        
        # Normalize duration (cap at 3 seconds)
        duration_score = min(1.0, duration / 3.0)
        
        # Combine metrics
        quality_score = (0.4 * duration_score + 0.3 * stability + 0.3 * confidence)
        
        return max(0.0, min(1.0, quality_score))
    
    def _grade_confidence(self, confidence: float) -> str:
        """Convert confidence score to letter grade."""
        if confidence >= 0.9:
            return "A"
        elif confidence >= 0.8:
            return "B"
        elif confidence >= 0.7:
            return "C"
        elif confidence >= 0.6:
            return "D"
        else:
            return "F"


class BehaviorAnalyzer:
    """
    Analyzes user review patterns and behavior.
    
    Tracks user behavior to adapt system parameters
    and provide efficiency feedback.
    """
    
    def __init__(self):
        """Initialize behavior analyzer."""
        self.session_start = None
        self.fixation_history = deque(maxlen=200)
        self.annotation_history = deque(maxlen=100)
        self.channel_visits = defaultdict(int)
        
        logger.debug("BehaviorAnalyzer initialized")
    
    def start_session(self):
        """Start behavior tracking session."""
        self.session_start = time.time()
        self.fixation_history.clear()
        self.annotation_history.clear()
        self.channel_visits.clear()
        
        logger.info("Behavior analysis session started")
    
    def record_fixation(self, fixation_data: Dict[str, Any]):
        """Record a fixation for behavior analysis."""
        record = {
            'timestamp': time.time(),
            'duration': fixation_data.get('duration', 0.0),
            'channel': fixation_data.get('channel', 'unknown'),
            'quality': fixation_data.get('confidence', 0.0)
        }
        
        self.fixation_history.append(record)
        
        # Update channel visits
        channel = record['channel']
        if channel != 'unknown':
            self.channel_visits[channel] += 1
    
    def record_annotation(self, annotation_data: Dict[str, Any]):
        """Record an annotation for behavior analysis."""
        record = {
            'timestamp': time.time(),
            'channel': annotation_data.get('channel', 'unknown'),
            'type': annotation_data.get('description', 'unknown'),
            'confidence': annotation_data.get('confidence', 0.0)
        }
        
        self.annotation_history.append(record)
    
    def analyze_behavior(self) -> BehaviorMetrics:
        """
        Analyze current user behavior patterns.
        
        Returns:
            BehaviorMetrics with analysis results
        """
        if not self.session_start:
            return self._empty_metrics()
        
        session_duration = time.time() - self.session_start
        
        if session_duration < 60:  # Less than 1 minute
            return self._empty_metrics()
        
        # Calculate metrics
        review_speed = self._calculate_review_speed(session_duration)
        annotation_rate = len(self.annotation_history) / (session_duration / 60)
        fixation_quality = self._calculate_average_fixation_quality()
        channel_coverage = self._calculate_channel_coverage()
        pattern_consistency = self._calculate_pattern_consistency()
        efficiency_score = self._calculate_efficiency_score(
            review_speed, annotation_rate, fixation_quality, channel_coverage)
        
        return BehaviorMetrics(
            review_speed=review_speed,
            annotation_rate=annotation_rate,
            fixation_quality=fixation_quality,
            channel_coverage=channel_coverage,
            pattern_consistency=pattern_consistency,
            efficiency_score=efficiency_score
        )
    
    def _calculate_review_speed(self, session_duration: float) -> float:
        """Calculate review speed in windows per minute."""
        # Estimate based on fixation patterns
        if len(self.fixation_history) < 10:
            return 0.0
        
        # Assume each significant fixation represents review of a time window
        significant_fixations = [f for f in self.fixation_history 
                               if f['duration'] > 0.5 and f['quality'] > 0.6]
        
        windows_reviewed = len(significant_fixations) / 3  # Approximate
        return windows_reviewed / (session_duration / 60)
    
    def _calculate_average_fixation_quality(self) -> float:
        """Calculate average fixation quality."""
        if not self.fixation_history:
            return 0.0
        
        qualities = [f['quality'] for f in self.fixation_history]
        return np.mean(qualities)
    
    def _calculate_channel_coverage(self) -> float:
        """Calculate percentage of channels reviewed."""
        if not self.channel_visits:
            return 0.0
        
        # Assume standard 19-channel EEG setup
        total_channels = 19
        reviewed_channels = len(self.channel_visits)
        
        return min(1.0, reviewed_channels / total_channels)
    
    def _calculate_pattern_consistency(self) -> float:
        """Calculate consistency in review patterns."""
        if len(self.fixation_history) < 10:
            return 0.5
        
        # Analyze fixation duration consistency
        durations = [f['duration'] for f in self.fixation_history]
        duration_cv = np.std(durations) / (np.mean(durations) + 1e-10)
        
        # Analyze temporal consistency
        timestamps = [f['timestamp'] for f in self.fixation_history]
        intervals = np.diff(timestamps)
        interval_cv = np.std(intervals) / (np.mean(intervals) + 1e-10)
        
        # Lower coefficient of variation indicates higher consistency
        consistency = 1.0 / (1.0 + (duration_cv + interval_cv) / 2.0)
        
        return max(0.0, min(1.0, consistency))
    
    def _calculate_efficiency_score(self, review_speed: float, annotation_rate: float,
                                  fixation_quality: float, channel_coverage: float) -> float:
        """Calculate overall efficiency score."""
        # Normalize components
        speed_score = min(1.0, review_speed / 5.0)  # Normalize to 5 windows/min max
        annotation_score = min(1.0, annotation_rate / 2.0)  # Normalize to 2 annotations/min max
        
        # Weighted combination
        efficiency = (0.3 * speed_score + 0.2 * annotation_score + 
                     0.3 * fixation_quality + 0.2 * channel_coverage)
        
        return max(0.0, min(1.0, efficiency))
    
    def _empty_metrics(self) -> BehaviorMetrics:
        """Return empty metrics for insufficient data."""
        return BehaviorMetrics(
            review_speed=0.0,
            annotation_rate=0.0,
            fixation_quality=0.0,
            channel_coverage=0.0,
            pattern_consistency=0.0,
            efficiency_score=0.0
        )


class EfficiencyMetrics:
    """
    Tracks and analyzes review efficiency and accuracy.
    
    Provides metrics for workflow optimization and
    system performance evaluation.
    """
    
    def __init__(self):
        """Initialize efficiency metrics."""
        self.session_metrics = {}
        self.historical_data = deque(maxlen=50)  # Keep last 50 sessions
        
        logger.debug("EfficiencyMetrics initialized")
    
    def start_session_tracking(self, session_id: str):
        """Start tracking a new session."""
        self.session_metrics[session_id] = {
            'start_time': time.time(),
            'fixations': 0,
            'annotations': 0,
            'review_time': 0.0,
            'channels_covered': set(),
            'pattern_detections': 0
        }
    
    def update_session_metrics(self, session_id: str, metric: str, value: Any):
        """Update specific session metric."""
        if session_id in self.session_metrics:
            if metric == 'channels_covered' and isinstance(value, str):
                self.session_metrics[session_id]['channels_covered'].add(value)
            else:
                self.session_metrics[session_id][metric] = value
    
    def finalize_session(self, session_id: str) -> Dict[str, Any]:
        """Finalize session and calculate final metrics."""
        if session_id not in self.session_metrics:
            return {}
        
        session = self.session_metrics[session_id]
        end_time = time.time()
        total_time = end_time - session['start_time']
        
        final_metrics = {
            'session_duration': total_time,
            'fixations_per_minute': session['fixations'] / (total_time / 60),
            'annotations_per_minute': session['annotations'] / (total_time / 60),
            'channels_coverage': len(session['channels_covered']),
            'efficiency_ratio': session['annotations'] / max(1, session['fixations']),
            'pattern_detection_rate': session['pattern_detections'] / max(1, session['fixations'])
        }
        
        # Add to historical data
        self.historical_data.append(final_metrics)
        
        # Clean up session data
        del self.session_metrics[session_id]
        
        return final_metrics
    
    def get_performance_trends(self) -> Dict[str, Any]:
        """Get performance trends over historical sessions."""
        if len(self.historical_data) < 3:
            return {'insufficient_data': True}
        
        # Calculate trends
        recent_sessions = list(self.historical_data)[-10:]  # Last 10 sessions
        older_sessions = list(self.historical_data)[:-10] if len(self.historical_data) > 10 else []
        
        trends = {}
        
        for metric in ['fixations_per_minute', 'annotations_per_minute', 'efficiency_ratio']:
            recent_avg = np.mean([s[metric] for s in recent_sessions])
            
            if older_sessions:
                older_avg = np.mean([s[metric] for s in older_sessions])
                trend = (recent_avg - older_avg) / (older_avg + 1e-10)
                trends[f'{metric}_trend'] = trend
            else:
                trends[f'{metric}_trend'] = 0.0
            
            trends[f'{metric}_current'] = recent_avg
        
        return trends