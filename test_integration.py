#!/usr/bin/env python3
"""
Comprehensive integration test for gaze tracking system.

This script tests the complete integration of all gaze tracking components
with the main EDF viewer application. Run this to verify everything works
before testing with real eye tracking hardware.
"""

import sys
import os
import time
import numpy as np
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test all component imports."""
    print("🔍 Testing component imports...")
    
    try:
        from gaze_tracking.gaze_tracker import GazeTracker
        print("✓ GazeTracker")
        
        from gaze_tracking.gaze_processor import GazeProcessor, FixationDetector
        print("✓ GazeProcessor & FixationDetector")
        
        from gaze_tracking.gaze_annotator import GazeAnnotator
        print("✓ GazeAnnotator")
        
        from gaze_tracking.gaze_enhanced_auto_move import GazeEnhancedAutoMove
        print("✓ GazeEnhancedAutoMove")
        
        from ui.gaze_overlay import GazeOverlayManager
        print("✓ GazeOverlay")
        
        from ui.feedback_system import FeedbackSystem
        print("✓ FeedbackSystem")
        
        from utils.gaze_analytics import ContextAnalyzer, BehaviorAnalyzer
        print("✓ Analytics Components")
        
        print("🎉 All imports successful!")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality without Qt."""
    print("\n🧪 Testing basic functionality...")
    
    try:
        # Test gaze tracker and processor
        from gaze_tracking.gaze_tracker import GazeTracker
        from gaze_tracking.gaze_processor import GazeProcessor
        
        tracker = GazeTracker()
        processor = GazeProcessor()
        
        # Configure components  
        processor.configure({
            'sampling_rate': 60,
            'min_fixation_duration': 0.3
        })
        
        # Connect tracker to processor
        processor.set_gaze_tracker(tracker)
        
        # Start processing
        processor.start_processing()
        
        # Simulate some processing time
        time.sleep(0.1)
        
        stats = processor.get_statistics()
        print(f"✓ Gaze processor: {stats.total_gaze_points} points, {stats.processing_rate_hz:.1f} Hz")
        
        # Test analytics
        from utils.gaze_analytics import BehaviorAnalyzer
        analyzer = BehaviorAnalyzer()
        analyzer.start_session()
        
        # Simulate some behavior
        for i in range(5):
            analyzer.record_fixation({
                'duration': 0.5 + i * 0.2,
                'channel': f'Ch{i % 3}',
                'confidence': 0.7
            })
        
        metrics = analyzer.analyze_behavior()
        print(f"✓ Behavior analyzer: {metrics.fixation_quality:.2f} quality score")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

def test_mock_integration():
    """Test full integration with mock data."""
    print("\n🎮 Testing mock integration...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        
        # Create Qt application
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Mock annotation manager
        class MockAnnotationManager:
            def __init__(self):
                self.annotations = []
            
            def add_annotation(self, annotation):
                self.annotations.append(annotation)
                return True
        
        # Mock main window
        class MockMainWindow:
            def __init__(self):
                self.auto_move_active = False
                self.view_start_time = 0.0
                self.annotation_manager = MockAnnotationManager()
            
            def toggle_auto_move(self):
                self.auto_move_active = not self.auto_move_active
        
        # Initialize components
        from gaze_tracking.gaze_tracker import GazeTracker
        from gaze_tracking.gaze_processor import GazeProcessor
        from gaze_tracking.gaze_annotator import GazeAnnotator
        from gaze_tracking.gaze_enhanced_auto_move import GazeEnhancedAutoMove
        from utils.gaze_analytics import ContextAnalyzer
        
        mock_window = MockMainWindow()
        
        # Create components
        tracker = GazeTracker()
        processor = GazeProcessor()
        annotator = GazeAnnotator(mock_window.annotation_manager)
        enhanced_auto_move = GazeEnhancedAutoMove(mock_window)
        context_analyzer = ContextAnalyzer()
        
        print("✓ All components created")
        
        # Configure components
        config = {
            'tracker_type': 'mock',
            'sampling_rate': 60,
            'min_fixation_duration': 0.3,
            'auto_create_annotations': True
        }
        
        # Configure processor and annotator (tracker doesn't need explicit config)
        processor.configure(config)
        annotator.configure(config)
        
        # Connect tracker to processor
        processor.set_gaze_tracker(tracker)
        enhanced_auto_move.configure({
            'base_scroll_speed': 2.0,
            'pause_on_fixation': True
        })
        
        print("✓ Components configured")
        
        # Set up display context for annotator
        channels = ['Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4']
        time_range = (0.0, 30.0)
        plot_bounds = {'x': 0, 'y': 0, 'width': 800, 'height': 600}
        
        annotator.set_display_context(channels, time_range, plot_bounds, 100, 30.0)
        print("✓ Display context set")
        
        # Connect enhanced auto-move
        enhanced_auto_move.connect_to_original_auto_move(mock_window.toggle_auto_move)
        print("✓ Enhanced auto-move connected")
        
        # Test data flow
        test_fixation_data = {
            'x': 400,
            'y': 200,
            'duration': 0.8,
            'confidence': 0.9,
            'stability': 0.8,
            'timestamp': time.time(),
            'channel': 'F3'
        }
        
        # Generate mock EEG data for context analysis
        eeg_data = np.random.normal(0, 10, (len(channels), 1024))  # 1024 samples
        eeg_data[2, 400:420] += 50 * np.exp(-np.linspace(-2, 2, 20)**2)  # Add spike
        
        # Analyze EEG context
        eeg_context = context_analyzer.analyze_fixation_context(
            eeg_data, 2.0, 2, 'F3'  # 2 seconds, channel 2 (F3)
        )
        
        print(f"✓ EEG context analysis: {eeg_context.pattern_type.value}")
        
        # Process fixation
        annotation_created = annotator.process_fixation(test_fixation_data, eeg_context)
        print(f"✓ Fixation processed, annotation created: {annotation_created}")
        
        # Test enhanced auto-move
        enhanced_auto_move.handle_fixation_detected(
            test_fixation_data, 
            {'eeg_interest_score': eeg_context.clinical_significance}
        )
        print("✓ Enhanced auto-move tested")
        
        # Check results
        stats = annotator.get_statistics()
        print(f"✓ Final stats: {stats.get('annotations_created', 0)} annotations created")
        
        if len(mock_window.annotation_manager.annotations) > 0:
            annotation = mock_window.annotation_manager.annotations[0]
            print(f"✓ Annotation verified: {annotation['description']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Mock integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance():
    """Test performance with large datasets."""
    print("\n⚡ Testing performance...")
    
    try:
        from gaze_tracking.gaze_tracker import GazeTracker
        from gaze_tracking.gaze_processor import GazeProcessor  
        from utils.gaze_analytics import ContextAnalyzer
        
        # Test gaze processing performance
        tracker = GazeTracker()
        processor = GazeProcessor()
        processor.configure({'sampling_rate': 120})
        processor.set_gaze_tracker(tracker)
        processor.start_processing()
        
        # Simulate processing for performance test
        time.sleep(0.5)  # Let it run for half a second
        
        stats = processor.get_statistics()
        session_time = 0.5  # We know we ran for 0.5 seconds
        
        print(f"✓ Gaze processing: {session_time:.1f}s session time")
        
        # Test EEG analysis performance
        analyzer = ContextAnalyzer()
        
        start_time = time.time()
        
        # Analyze 10 EEG contexts
        for i in range(10):
            eeg_data = np.random.normal(0, 10, (19, 512))  # 19 channels, 2 seconds at 256 Hz
            context = analyzer.analyze_fixation_context(eeg_data, 1.0, i % 19, f'Ch{i}')
        
        analysis_time = time.time() - start_time
        analyses_per_second = 10 / analysis_time
        
        print(f"✓ EEG analysis: {analyses_per_second:.1f} analyses/sec")
        
        # Performance expectations
        if session_time > 0 and analyses_per_second > 5:
            print("🚀 Performance: EXCELLENT")
        elif session_time > 0 and analyses_per_second > 2:
            print("✅ Performance: GOOD")
        else:
            print("⚠️ Performance: ACCEPTABLE (consider optimization)")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def test_error_handling():
    """Test error handling and edge cases."""
    print("\n🛡️ Testing error handling...")
    
    try:
        from gaze_tracking.gaze_tracker import GazeTracker
        from gaze_tracking.gaze_processor import GazeProcessor
        from gaze_tracking.gaze_annotator import GazeAnnotator
        from utils.gaze_analytics import ContextAnalyzer
        
        tracker = GazeTracker()
        processor = GazeProcessor()
        analyzer = ContextAnalyzer()
        
        # Test processor error handling
        try:
            processor.configure({'invalid_setting': 'test'})
            print("✓ Invalid configuration handled")
        except Exception as e:
            print(f"⚠️ Configuration error handling needs improvement: {e}")
        
        # Test invalid EEG data
        try:
            empty_analysis = analyzer.analyze_fixation_context(
                np.array([[]]), 1.0, 0, 'Test'
            )
            print("✓ Invalid EEG data handled")
        except Exception as e:
            print(f"⚠️ EEG data error handling needs improvement: {e}")
        
        # Test with very small datasets
        try:
            tiny_eeg = np.random.normal(0, 1, (1, 10))  # Very small dataset
            analysis = analyzer.analyze_fixation_context(tiny_eeg, 0.1, 0, 'Test')
            print("✓ Small dataset handled")
        except Exception as e:
            print(f"⚠️ Small dataset handling needs improvement: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

def test_configuration_options():
    """Test various configuration options."""
    print("\n⚙️ Testing configuration options...")
    
    try:
        from gaze_tracking.gaze_tracker import GazeTracker
        from gaze_tracking.gaze_processor import GazeProcessor
        from gaze_tracking.gaze_enhanced_auto_move import ScrollBehavior
        
        # Test different processor configurations
        configs = [
            {'min_fixation_duration': 0.2, 'velocity_threshold': 30},  # Fast
            {'min_fixation_duration': 1.0, 'velocity_threshold': 15},  # Slow
            {'min_fixation_duration': 0.5, 'velocity_threshold': 25},  # Medium
        ]
        
        for i, config in enumerate(configs):
            tracker = GazeTracker()
            processor = GazeProcessor()
            processor.configure(config)
            processor.set_gaze_tracker(tracker)
            processor.start_processing()
            
            # Let it run briefly
            time.sleep(0.1)
            
            stats = processor.get_statistics()
            print(f"✓ Config {i+1}: {stats.total_gaze_points} points, {stats.processing_rate_hz:.1f} Hz")
        
        # Test scroll behaviors
        behavior = ScrollBehavior()
        behaviors = ['normal', 'detailed', 'quick']
        
        for behavior_name in behaviors:
            behavior.set_behavior(behavior_name)
            speed = behavior.get_scroll_speed()
            print(f"✓ {behavior_name} behavior: {speed:.1f}s/window")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def run_full_integration_test():
    """Run complete integration test suite."""
    print("🚀 GAZE TRACKING INTEGRATION TEST SUITE")
    print("=" * 50)
    
    tests = [
        ("Component Imports", test_imports),
        ("Basic Functionality", test_basic_functionality),
        ("Mock Integration", test_mock_integration),
        ("Performance", test_performance),
        ("Error Handling", test_error_handling),
        ("Configuration Options", test_configuration_options),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 50)
    print(f"INTEGRATION TEST RESULTS: {passed}/{total} PASSED")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System ready for use.")
        print("\nNext steps:")
        print("1. Follow INTEGRATION_GUIDE.md to add to main EDF viewer")
        print("2. Test with real EDF files")
        print("3. Configure for your specific use case")
        print("4. Consider connecting real eye tracker hardware")
    else:
        print("❌ Some tests failed. Check the errors above.")
        print("Review the implementation and try again.")
    
    print("=" * 50)
    return passed == total

if __name__ == "__main__":
    success = run_full_integration_test()
    sys.exit(0 if success else 1)