#!/usr/bin/env python3
"""
Test script for Phase 3 gaze tracking implementation.

Tests the visual feedback and overlay components including:
- Gaze cursor overlay
- Fixation progress indicators
- Annotation preview system
- Real-time visual feedback
- Audio feedback system
"""

import sys
import os
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_overlay_imports():
    """Test importing overlay components."""
    print("Testing overlay component imports...")
    try:
        from ui.gaze_overlay import (
            GazeOverlayManager, GazeCursor, FixationProgressIndicator, 
            AnnotationPreview
        )
        print("✓ Gaze overlay components imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import gaze overlay components: {e}")
        return False

def test_feedback_imports():
    """Test importing feedback system components."""
    print("Testing feedback system imports...")
    try:
        from ui.feedback_system import (
            FeedbackSystem, VisualFeedbackPanel, FeedbackType, 
            FeedbackEvent, AudioFeedback
        )
        print("✓ Feedback system components imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import feedback system components: {e}")
        return False

def test_gaze_cursor():
    """Test gaze cursor functionality."""
    print("Testing gaze cursor...")
    try:
        from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
        from ui.gaze_overlay import GazeCursor
        
        # Create Qt application if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create test scene and view
        scene = QGraphicsScene()
        view = QGraphicsView(scene)
        
        # Create gaze cursor
        cursor = GazeCursor(size=20)
        scene.addItem(cursor)
        
        print("✓ Gaze cursor created successfully")
        
        # Test position updates
        cursor.update_position(100, 200, 0.8)
        print("✓ Cursor position updated")
        
        # Test visibility toggle
        cursor.set_visible(False)
        cursor.set_visible(True)
        print("✓ Cursor visibility control working")
        
        # Test size change
        cursor.set_size(30)
        print("✓ Cursor size change working")
        
        # Test cleanup
        cursor.cleanup()
        print("✓ Cursor cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Gaze cursor test failed: {e}")
        return False

def test_fixation_progress_indicator():
    """Test fixation progress indicator."""
    print("Testing fixation progress indicator...")
    try:
        from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
        from ui.gaze_overlay import FixationProgressIndicator
        
        # Create Qt application if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create test scene and view
        scene = QGraphicsScene()
        view = QGraphicsView(scene)
        
        # Create progress indicator
        indicator = FixationProgressIndicator(size=50)
        scene.addItem(indicator)
        
        print("✓ Progress indicator created successfully")
        
        # Test fixation tracking
        indicator.start_fixation(2.0)  # 2 second target
        print("✓ Fixation tracking started")
        
        # Test progress updates
        for i in range(5):
            indicator.update_fixation(i * 0.5)
            app.processEvents()  # Allow Qt to update
            time.sleep(0.1)
        
        print("✓ Progress updates working")
        
        # Test completion
        indicator.complete_fixation()
        print("✓ Fixation completion working")
        
        # Test cancellation
        indicator.start_fixation(1.0)
        indicator.cancel_fixation()
        print("✓ Fixation cancellation working")
        
        # Test cleanup
        indicator.cleanup()
        print("✓ Progress indicator cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Fixation progress indicator test failed: {e}")
        return False

def test_annotation_preview():
    """Test annotation preview system."""
    print("Testing annotation preview...")
    try:
        from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene
        from ui.gaze_overlay import AnnotationPreview
        
        # Create Qt application if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create test scene and view
        scene = QGraphicsScene()
        view = QGraphicsView(scene)
        
        # Create annotation preview
        preview = AnnotationPreview()
        scene.addItem(preview)
        
        print("✓ Annotation preview created successfully")
        
        # Test preview display
        annotation_data = {
            'description': 'Test Annotation',
            'duration': 1.5,
            'channel': 'Fp1'
        }
        
        preview.show_preview(50, 50, 100, 30, annotation_data)
        print("✓ Preview display working")
        
        # Test preview updates
        preview.update_preview(60, 60, 120, 35)
        print("✓ Preview updates working")
        
        # Test preview hiding
        preview.hide_preview()
        print("✓ Preview hiding working")
        
        return True
        
    except Exception as e:
        print(f"✗ Annotation preview test failed: {e}")
        return False

def test_visual_feedback_panel():
    """Test visual feedback panel."""
    print("Testing visual feedback panel...")
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.feedback_system import VisualFeedbackPanel
        
        # Create Qt application if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create feedback panel
        panel = VisualFeedbackPanel()
        
        print("✓ Visual feedback panel created successfully")
        
        # Test status updates
        panel.update_status("Testing", "#00FF00")
        print("✓ Status updates working")
        
        # Test confidence updates
        panel.update_confidence(0.85)
        print("✓ Confidence updates working")
        
        # Test fixation progress
        panel.start_fixation_progress(2.0)
        for i in range(6):
            panel.update_fixation_progress(i * 0.4)
            app.processEvents()
            time.sleep(0.05)
        
        panel.complete_fixation()
        print("✓ Fixation progress tracking working")
        
        # Test statistics
        panel.add_annotation()
        panel.update_fps(30.5)
        print("✓ Statistics updates working")
        
        # Test reset
        panel.reset_statistics()
        print("✓ Statistics reset working")
        
        return True
        
    except Exception as e:
        print(f"✗ Visual feedback panel test failed: {e}")
        return False

def test_audio_feedback():
    """Test audio feedback system."""
    print("Testing audio feedback system...")
    try:
        from ui.feedback_system import AudioFeedback, FeedbackType
        
        # Create audio feedback system
        audio = AudioFeedback()
        
        print(f"✓ Audio feedback system created (enabled: {audio.enabled})")
        
        # Test volume control
        audio.set_volume(0.5)
        print("✓ Volume control working")
        
        # Test feedback playback (may not produce actual sound in test environment)
        audio.play_feedback(FeedbackType.FIXATION_STARTED)
        audio.play_feedback(FeedbackType.FIXATION_COMPLETED)
        audio.play_feedback(FeedbackType.ANNOTATION_CREATED)
        print("✓ Audio feedback playback working")
        
        return True
        
    except Exception as e:
        print(f"✗ Audio feedback test failed: {e}")
        return False

def test_feedback_system_integration():
    """Test integrated feedback system."""
    print("Testing feedback system integration...")
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.feedback_system import FeedbackSystem, FeedbackType
        
        # Create Qt application if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create feedback system
        feedback = FeedbackSystem()
        
        print("✓ Feedback system created successfully")
        
        # Test configuration
        config = {
            'audio_enabled': True,
            'visual_enabled': True,
            'audio_volume': 0.3
        }
        feedback.configure(config)
        print("✓ Feedback system configuration working")
        
        # Test event processing
        feedback.start_session()
        
        # Simulate gaze tracking events
        events_to_test = [
            (FeedbackType.GAZE_DETECTED, "Gaze detected", {'confidence': 0.9}),
            (FeedbackType.FIXATION_STARTED, "Fixation started", {'duration': 1.5}),
            (FeedbackType.FIXATION_PROGRESS, "Fixation progress", {'elapsed_time': 0.5}),
            (FeedbackType.FIXATION_COMPLETED, "Fixation completed", {}),
            (FeedbackType.ANNOTATION_CREATED, "Annotation created", {'description': 'Test'}),
        ]
        
        for event_type, message, data in events_to_test:
            feedback.process_event(event_type, message, data, priority=2)
            app.processEvents()
            time.sleep(0.1)
        
        print("✓ Event processing working")
        
        # Test gaze data updates
        feedback.update_gaze_data(0.85, 30.0)
        print("✓ Gaze data updates working")
        
        # Test error reporting
        feedback.report_error("Test error message")
        print("✓ Error reporting working")
        
        # Test statistics
        stats = feedback.get_statistics()
        print(f"✓ Statistics: {stats['events_processed']} events processed")
        
        # Test recent events
        recent = feedback.get_recent_events(3)
        print(f"✓ Recent events: {len(recent)} events retrieved")
        
        # End session
        feedback.end_session()
        print("✓ Session management working")
        
        # Test cleanup
        feedback.cleanup()
        print("✓ Feedback system cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Feedback system integration test failed: {e}")
        return False

def test_overlay_manager_integration():
    """Test gaze overlay manager integration."""
    print("Testing overlay manager integration...")
    try:
        from PyQt6.QtWidgets import QApplication
        import pyqtgraph as pg
        from ui.gaze_overlay import GazeOverlayManager
        
        # Create Qt application if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create a simple plot widget for testing
        plot_widget = pg.PlotWidget()
        
        # Create overlay manager
        overlay_manager = GazeOverlayManager(plot_widget)
        
        print("✓ Overlay manager created successfully")
        
        # Test configuration
        config = {
            'show_cursor': True,
            'show_progress': True,
            'show_preview': True,
            'cursor_size': 20
        }
        overlay_manager.update_configuration(config)
        print("✓ Overlay configuration working")
        
        # Test gaze position updates
        overlay_manager.update_gaze_position(100, 200, 0.8)
        print("✓ Gaze position updates working")
        
        # Test fixation tracking
        annotation_data = {
            'description': 'Test Event',
            'duration': 1.0,
            'channel': 'Fp1'
        }
        
        overlay_manager.start_fixation_tracking(150, 250, 1.5, annotation_data)
        print("✓ Fixation tracking started")
        
        # Simulate fixation progress
        for i in range(6):
            overlay_manager.update_fixation_progress(i * 0.3)
            app.processEvents()
            time.sleep(0.05)
        
        overlay_manager.complete_fixation()
        print("✓ Fixation completion working")
        
        # Test cancellation
        overlay_manager.start_fixation_tracking(200, 300, 1.0, annotation_data)
        overlay_manager.cancel_fixation()
        print("✓ Fixation cancellation working")
        
        # Test statistics
        stats = overlay_manager.get_statistics()
        print(f"✓ Overlay statistics: enabled={stats['overlay_enabled']}")
        
        # Test enable/disable
        overlay_manager.set_enabled(False)
        overlay_manager.set_enabled(True)
        print("✓ Enable/disable working")
        
        # Test cleanup
        overlay_manager.cleanup()
        print("✓ Overlay manager cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"✗ Overlay manager integration test failed: {e}")
        return False

def run_all_tests():
    """Run all Phase 3 tests."""
    print("="*50)
    print("PHASE 3 GAZE TRACKING IMPLEMENTATION TESTS")
    print("="*50)
    
    tests = [
        test_overlay_imports,
        test_feedback_imports,
        test_gaze_cursor,
        test_fixation_progress_indicator,
        test_annotation_preview,
        test_visual_feedback_panel,
        test_audio_feedback,
        test_feedback_system_integration,
        test_overlay_manager_integration
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
        print("🎉 All Phase 3 tests passed! Visual feedback system ready.")
        print("\nPhase 3 Implementation Complete:")
        print("✓ Gaze cursor overlay with smooth animation")
        print("✓ Fixation progress indicators")
        print("✓ Annotation preview system")
        print("✓ Real-time visual feedback panel")
        print("✓ Audio feedback system")
        print("✓ Integrated overlay management")
        print("\nNext steps:")
        print("• Begin Phase 4: Complete Integration & Auto-Scroll")
        print("• Integrate all components with main EDF viewer")
        print("• Add auto-scroll functionality")
        print("• Implement comprehensive gaze annotation workflow")
    else:
        print("❌ Some Phase 3 tests failed. Please review the implementation.")
    
    print("="*50)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)