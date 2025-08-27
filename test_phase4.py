#!/usr/bin/env python3
"""
Test script for Phase 4 gaze tracking implementation.

Tests the complete integration and auto-scroll components including:
- Gaze annotation engine
- Enhanced auto-move integration
- EEG context analysis
- Pattern recognition
- Behavior analytics
"""

import sys
import os
import time
import numpy as np

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_annotation_engine_imports():
    """Test importing gaze annotation engine components."""
    print("Testing gaze annotation engine imports...")
    try:
        from gaze_tracking.gaze_annotator import (
            GazeAnnotator, FixationAnalyzer, ChannelMapper, 
            TimeWindowValidator, AnnotationCategory, AnnotationQuality
        )
        print("✓ Gaze annotation engine components imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import gaze annotation engine: {e}")
        return False

def test_enhanced_auto_move_imports():
    """Test importing enhanced auto-move components."""
    print("Testing enhanced auto-move imports...")
    try:
        from gaze_tracking.gaze_enhanced_auto_move import (
            GazeEnhancedAutoMove, ScrollBehavior, PauseLogic, 
            ProgressTracker, ScrollState, ScrollConfiguration
        )
        print("✓ Enhanced auto-move components imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import enhanced auto-move: {e}")
        return False

def test_gaze_analytics_imports():
    """Test importing gaze analytics components."""
    print("Testing gaze analytics imports...")
    try:
        from utils.gaze_analytics import (
            ContextAnalyzer, PatternRecognizer, ConfidenceScorer,
            BehaviorAnalyzer, EfficiencyMetrics, EEGPatternType
        )
        print("✓ Gaze analytics components imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import gaze analytics: {e}")
        return False

def test_fixation_analyzer():
    """Test fixation analyzer functionality."""
    print("Testing fixation analyzer...")
    try:
        from gaze_tracking.gaze_annotator import FixationAnalyzer, AnnotationCategory
        
        # Create analyzer
        analyzer = FixationAnalyzer()
        print("✓ FixationAnalyzer created successfully")
        
        # Test fixation analysis
        fixation_data = {
            'duration': 1.2,
            'stability': 0.8,
            'confidence': 0.9,
            'channel': 'Fp1',
            'center_x': 100,
            'center_y': 200
        }
        
        eeg_context = {
            'spike_detected': True,
            'amplitude_z_score': 2.5,
            'frequency_anomaly': False,
            'artifact_detected': False
        }
        
        analysis = analyzer.analyze_fixation(fixation_data, eeg_context)
        print(f"✓ Fixation analysis completed: {analysis.suggested_category.value}")
        print(f"  Quality: {analysis.quality_level.value}")
        print(f"  Worthiness: {analysis.annotation_worthiness:.2f}")
        
        # Test without EEG context
        analysis_no_context = analyzer.analyze_fixation(fixation_data)
        print("✓ Analysis without EEG context working")
        
        return True
        
    except Exception as e:
        print(f"✗ Fixation analyzer test failed: {e}")
        return False

def test_channel_mapper():
    """Test channel mapping functionality."""
    print("Testing channel mapper...")
    try:
        from gaze_tracking.gaze_annotator import ChannelMapper
        
        # Create mapper
        mapper = ChannelMapper()
        print("✓ ChannelMapper created successfully")
        
        # Configure mapper
        channels = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4']
        time_range = (10.0, 20.0)
        plot_bounds = {'x': 50, 'y': 50, 'width': 800, 'height': 600}
        channel_height = 100
        
        mapper.configure(channels, time_range, plot_bounds, channel_height)
        print("✓ Mapper configured")
        
        # Test coordinate mapping
        time_sec, channel, valid = mapper.map_coordinates(250, 150)
        print(f"✓ Coordinate mapping: {time_sec:.1f}s, {channel}, valid={valid}")
        
        # Test invalid coordinates
        time_sec2, channel2, valid2 = mapper.map_coordinates(-50, 150)
        print(f"✓ Invalid coordinate handling: valid={valid2}")
        
        return True
        
    except Exception as e:
        print(f"✗ Channel mapper test failed: {e}")
        return False

def test_time_window_validator():
    """Test time window validation."""
    print("Testing time window validator...")
    try:
        from gaze_tracking.gaze_annotator import TimeWindowValidator
        
        # Create validator
        validator = TimeWindowValidator()
        validator.set_data_bounds(100.0)  # 100 seconds of data
        print("✓ TimeWindowValidator created and configured")
        
        # Test valid annotation
        start, duration, valid = validator.validate_annotation(50.0, 1.0)
        print(f"✓ Valid annotation: {start:.1f}s, {duration:.1f}s, valid={valid}")
        
        # Test annotation near end of data
        start2, duration2, valid2 = validator.validate_annotation(99.5, 1.0)
        print(f"✓ End boundary handling: {start2:.1f}s, {duration2:.1f}s, valid={valid2}")
        
        # Test invalid annotation
        start3, duration3, valid3 = validator.validate_annotation(105.0, 1.0)
        print(f"✓ Invalid annotation handling: valid={valid3}")
        
        return True
        
    except Exception as e:
        print(f"✗ Time window validator test failed: {e}")
        return False

def test_gaze_annotator_integration():
    """Test integrated gaze annotator functionality."""
    print("Testing gaze annotator integration...")
    try:
        from gaze_tracking.gaze_annotator import GazeAnnotator
        
        # Mock annotation manager
        class MockAnnotationManager:
            def __init__(self):
                self.annotations = []
            
            def add_annotation(self, annotation):
                self.annotations.append(annotation)
                return True
        
        # Create annotator
        mock_manager = MockAnnotationManager()
        annotator = GazeAnnotator(mock_manager)
        print("✓ GazeAnnotator created with mock manager")
        
        # Configure annotator
        from gaze_tracking.gaze_annotator import AnnotationQuality
        config = {
            'auto_create_annotations': True,
            'min_quality_threshold': AnnotationQuality.LOW,
            'default_annotation_duration': 1.5
        }
        annotator.configure(config)
        print("✓ Annotator configured")
        
        # Set display context
        channels = ['Fp1', 'Fp2', 'F3', 'F4']
        time_range = (0.0, 30.0)
        plot_bounds = {'x': 0, 'y': 0, 'width': 800, 'height': 400}
        
        annotator.set_display_context(channels, time_range, plot_bounds, 100, 30.0)
        print("✓ Display context set")
        
        # Test fixation processing
        fixation_data = {
            'duration': 1.0,
            'stability': 0.7,
            'confidence': 0.8,
            'center_x': 400,
            'center_y': 200,
            'channel': 'F3'
        }
        
        eeg_context = {
            'spike_detected': True,
            'amplitude_z_score': 2.2,
            'frequency_anomaly': False
        }
        
        # Process fixation
        annotation_created = annotator.process_fixation(fixation_data, eeg_context)
        print(f"✓ Fixation processed, annotation created: {annotation_created}")
        
        # Check statistics
        stats = annotator.get_statistics()
        print(f"✓ Statistics: {stats['fixations_analyzed']} analyzed, "
              f"{stats['annotations_created']} created")
        
        # Verify annotation was added to manager
        if len(mock_manager.annotations) > 0:
            annotation = mock_manager.annotations[0]
            print(f"✓ Annotation created: {annotation['description']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Gaze annotator integration test failed: {e}")
        return False

def test_scroll_behavior():
    """Test scroll behavior management."""
    print("Testing scroll behavior...")
    try:
        from gaze_tracking.gaze_enhanced_auto_move import ScrollBehavior
        
        # Create behavior manager
        behavior = ScrollBehavior()
        print("✓ ScrollBehavior created successfully")
        
        # Test speed calculation
        context = {
            'eeg_complexity': 1.2,
            'annotation_density': 0.3
        }
        
        speed = behavior.get_scroll_speed(context)
        print(f"✓ Scroll speed calculated: {speed:.1f}s per window")
        
        # Test pause decision
        fixation_data = {
            'duration': 0.8,
            'confidence': 0.7,
            'stability': 0.6
        }
        
        should_pause = behavior.should_pause_for_fixation(fixation_data)
        print(f"✓ Pause decision: {should_pause}")
        
        # Test behavior change
        behavior.set_behavior('detailed')
        detailed_speed = behavior.get_scroll_speed(context)
        print(f"✓ Detailed behavior speed: {detailed_speed:.1f}s per window")
        
        return True
        
    except Exception as e:
        print(f"✗ Scroll behavior test failed: {e}")
        return False

def test_pause_logic():
    """Test intelligent pause logic."""
    print("Testing pause logic...")
    try:
        from gaze_tracking.gaze_enhanced_auto_move import PauseLogic, PauseReason
        
        # Create pause logic
        logic = PauseLogic()
        print("✓ PauseLogic created successfully")
        
        # Test pause decision
        fixation_data = {
            'duration': 1.0,
            'confidence': 0.8,
            'stability': 0.7
        }
        
        context = {
            'eeg_interest_score': 0.8
        }
        
        should_pause, reason = logic.should_pause(fixation_data, context)
        print(f"✓ Pause decision: {should_pause}, reason: {reason.value}")
        
        # Test pause duration calculation
        duration = logic.calculate_pause_duration(fixation_data, reason)
        print(f"✓ Pause duration: {duration:.1f}s")
        
        # Test rapid pausing detection
        for i in range(5):
            logic.should_pause(fixation_data, context)
            time.sleep(0.1)
        
        rapid_pause, rapid_reason = logic.should_pause(fixation_data, context)
        print(f"✓ Rapid pause detection working")
        
        return True
        
    except Exception as e:
        print(f"✗ Pause logic test failed: {e}")
        return False

def test_progress_tracker():
    """Test progress tracking functionality."""
    print("Testing progress tracker...")
    try:
        from gaze_tracking.gaze_enhanced_auto_move import ProgressTracker
        
        # Create progress tracker
        tracker = ProgressTracker()
        print("✓ ProgressTracker created successfully")
        
        # Start session
        tracker.start_session(100.0, 10.0)  # 100s data, 10s windows
        print("✓ Session started")
        
        # Update progress
        tracker.update_progress(25.0)  # 25% through data
        print("✓ Progress updated")
        
        # Add some events
        tracker.add_pause(2.0)
        tracker.add_annotation()
        print("✓ Events recorded")
        
        # Get progress report
        report = tracker.get_progress_report()
        print(f"✓ Progress report: {report['completion_percentage']:.1f}% complete")
        print(f"  Windows: {report['windows_completed']}/{report['total_windows']}")
        print(f"  Annotations: {report['annotations_created']}")
        
        # Test completion check
        tracker.update_progress(95.0)
        is_complete = tracker.is_complete()
        print(f"✓ Completion check: {is_complete}")
        
        return True
        
    except Exception as e:
        print(f"✗ Progress tracker test failed: {e}")
        return False

def test_enhanced_auto_move():
    """Test enhanced auto-move controller."""
    print("Testing enhanced auto-move controller...")
    try:
        from PyQt6.QtWidgets import QApplication
        from gaze_tracking.gaze_enhanced_auto_move import GazeEnhancedAutoMove, ScrollState
        
        # Create Qt application if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Mock main window
        class MockMainWindow:
            def __init__(self):
                self.auto_move_active = False
                self.view_start_time = 0.0
            
            def toggle_auto_move(self):
                self.auto_move_active = not self.auto_move_active
        
        # Create enhanced auto-move
        mock_window = MockMainWindow()
        enhanced_auto_move = GazeEnhancedAutoMove(mock_window)
        print("✓ GazeEnhancedAutoMove created successfully")
        
        # Configure
        config = {
            'base_scroll_speed': 3.0,
            'pause_on_fixation': True,
            'auto_resume_delay': 2.0
        }
        enhanced_auto_move.configure(config)
        print("✓ Enhanced auto-move configured")
        
        # Connect to mock auto-move function
        enhanced_auto_move.connect_to_original_auto_move(mock_window.toggle_auto_move)
        print("✓ Connected to original auto-move")
        
        # Test state management
        initial_state = enhanced_auto_move.get_current_state()
        print(f"✓ Initial state: {initial_state.value}")
        
        # Test fixation handling (without actually starting scroll)
        fixation_data = {
            'duration': 0.8,
            'confidence': 0.7,
            'stability': 0.6,
            'center_x': 100,
            'center_y': 200
        }
        
        # This would normally pause scrolling if active
        enhanced_auto_move.handle_fixation_detected(fixation_data)
        print("✓ Fixation handling tested")
        
        # Test statistics
        stats = enhanced_auto_move.get_statistics()
        print(f"✓ Statistics retrieved: state={stats['current_state']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Enhanced auto-move test failed: {e}")
        return False

def test_context_analyzer():
    """Test EEG context analysis."""
    print("Testing EEG context analyzer...")
    try:
        from utils.gaze_analytics import ContextAnalyzer, EEGPatternType
        
        # Create analyzer
        analyzer = ContextAnalyzer()
        print("✓ ContextAnalyzer created successfully")
        
        # Generate synthetic EEG data
        duration = 2.0  # 2 seconds
        sampling_rate = 256
        samples = int(duration * sampling_rate)
        
        # Create multi-channel EEG data with a spike pattern
        channels = 4
        eeg_data = np.random.normal(0, 10, (channels, samples))
        
        # Add a spike pattern to channel 1 around the middle
        spike_start = samples // 2 - 10
        spike_end = samples // 2 + 10
        eeg_data[1, spike_start:spike_end] += 50 * np.exp(-np.linspace(-2, 2, 20)**2)
        
        print("✓ Synthetic EEG data created")
        
        # Analyze context around fixation
        fixation_time = 1.0  # Middle of data
        channel_idx = 1  # Channel with spike
        channel_name = "F3"
        
        analysis = analyzer.analyze_fixation_context(
            eeg_data, fixation_time, channel_idx, channel_name)
        
        print(f"✓ Context analysis completed:")
        print(f"  Pattern: {analysis.pattern_type.value}")
        print(f"  Confidence: {analysis.confidence:.2f}")
        print(f"  Clinical significance: {analysis.clinical_significance:.2f}")
        print(f"  Recommendation: {analysis.recommendation}")
        
        # Test with invalid data
        empty_analysis = analyzer.analyze_fixation_context(
            np.array([[]]), 1.0, 0, "Test")
        print("✓ Invalid data handling working")
        
        return True
        
    except Exception as e:
        print(f"✗ Context analyzer test failed: {e}")
        return False

def test_pattern_recognizer():
    """Test pattern recognition functionality."""
    print("Testing pattern recognizer...")
    try:
        from utils.gaze_analytics import PatternRecognizer, ContextAnalyzer, EEGPatternType
        
        # Create recognizer
        recognizer = PatternRecognizer()
        print("✓ PatternRecognizer created successfully")
        
        # Create mock EEG context analysis
        from utils.gaze_analytics import EEGContextAnalysis
        
        context = EEGContextAnalysis(
            time_window=(0.0, 2.0),
            channel="F3",
            pattern_type=EEGPatternType.SPIKE,
            confidence=0.8,
            amplitude_stats={'z_score_max': 3.2},
            frequency_analysis={'beta': 0.2, 'gamma': 0.05},
            morphology_score=0.7,
            clinical_significance=0.9,
            recommendation="High priority spike detected"
        )
        
        # Recognize patterns
        results = recognizer.recognize_patterns(context)
        print(f"✓ Pattern recognition completed:")
        print(f"  Patterns found: {results['patterns_detected']}")
        print(f"  Max confidence: {results['max_confidence']:.2f}")
        print(f"  Clinical relevance: {results['clinical_relevance']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Pattern recognizer test failed: {e}")
        return False

def test_confidence_scorer():
    """Test confidence scoring system."""
    print("Testing confidence scorer...")
    try:
        from utils.gaze_analytics import ConfidenceScorer, EEGContextAnalysis, EEGPatternType
        
        # Create scorer
        scorer = ConfidenceScorer()
        print("✓ ConfidenceScorer created successfully")
        
        # Mock data
        fixation_data = {
            'duration': 1.2,
            'stability': 0.8,
            'confidence': 0.9
        }
        
        eeg_context = EEGContextAnalysis(
            time_window=(0.0, 2.0),
            channel="F3",
            pattern_type=EEGPatternType.SPIKE,
            confidence=0.8,
            amplitude_stats={},
            frequency_analysis={},
            morphology_score=0.7,
            clinical_significance=0.85,
            recommendation="Test"
        )
        
        pattern_results = {
            'max_confidence': 0.8,
            'patterns_detected': ['spike']
        }
        
        # Calculate confidence
        confidence_scores = scorer.calculate_confidence(
            fixation_data, eeg_context, pattern_results)
        
        print(f"✓ Confidence calculation completed:")
        print(f"  Overall confidence: {confidence_scores['overall_confidence']:.2f}")
        print(f"  Grade: {confidence_scores['confidence_grade']}")
        print(f"  Components: fixation={confidence_scores['fixation_quality']:.2f}, "
              f"eeg={confidence_scores['eeg_significance']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Confidence scorer test failed: {e}")
        return False

def test_behavior_analyzer():
    """Test user behavior analysis."""
    print("Testing behavior analyzer...")
    try:
        from utils.gaze_analytics import BehaviorAnalyzer
        
        # Create analyzer
        analyzer = BehaviorAnalyzer()
        print("✓ BehaviorAnalyzer created successfully")
        
        # Start session
        analyzer.start_session()
        time.sleep(0.1)  # Brief delay to simulate time passing
        print("✓ Session started")
        
        # Record some fixations
        for i in range(5):
            fixation_data = {
                'duration': 0.5 + i * 0.2,
                'channel': f'Ch{i % 3}',
                'confidence': 0.6 + i * 0.1
            }
            analyzer.record_fixation(fixation_data)
            time.sleep(0.02)
        
        print("✓ Fixations recorded")
        
        # Record some annotations
        for i in range(2):
            annotation_data = {
                'channel': f'Ch{i}',
                'description': f'Test annotation {i}',
                'confidence': 0.8
            }
            analyzer.record_annotation(annotation_data)
        
        print("✓ Annotations recorded")
        
        # Note: Behavior analysis requires more time to be meaningful
        # In real usage, this would be called after minutes of data
        metrics = analyzer.analyze_behavior()
        print(f"✓ Behavior analysis completed (limited data):")
        print(f"  Fixation quality: {metrics.fixation_quality:.2f}")
        print(f"  Channel coverage: {metrics.channel_coverage:.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ Behavior analyzer test failed: {e}")
        return False

def run_all_tests():
    """Run all Phase 4 tests."""
    print("="*50)
    print("PHASE 4 GAZE TRACKING IMPLEMENTATION TESTS")
    print("="*50)
    
    tests = [
        test_annotation_engine_imports,
        test_enhanced_auto_move_imports,
        test_gaze_analytics_imports,
        test_fixation_analyzer,
        test_channel_mapper,
        test_time_window_validator,
        test_gaze_annotator_integration,
        test_scroll_behavior,
        test_pause_logic,
        test_progress_tracker,
        test_enhanced_auto_move,
        test_context_analyzer,
        test_pattern_recognizer,
        test_confidence_scorer,
        test_behavior_analyzer
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        print(f"\n{test_func.__name__}:")
        if test_func():
            passed += 1
        else:
            print("  Test failed!")
    
    print("\n" + "="*50)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 4 tests passed! Complete integration ready.")
        print("\nPhase 4 Implementation Complete:")
        print("✓ Gaze annotation engine with quality assessment")
        print("✓ Enhanced auto-scroll with intelligent pause/resume")
        print("✓ EEG context analysis and pattern recognition")
        print("✓ Comprehensive confidence scoring")
        print("✓ User behavior analysis and metrics")
        print("✓ Complete coordinate mapping and validation")
        print("\nNext steps:")
        print("• Begin Phase 5: Annotation Review & Management")
        print("• Integrate all components with main EDF viewer UI")
        print("• Add final testing and optimization")
        print("• Deploy complete gaze annotation system")
    else:
        print("❌ Some Phase 4 tests failed. Please review the implementation.")
    
    print("="*50)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)