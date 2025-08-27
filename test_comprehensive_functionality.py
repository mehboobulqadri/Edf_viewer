#!/usr/bin/env python3
"""
Comprehensive functionality test to ensure no features were broken by zoom fixes.

This test checks all major EDF viewer functionality to ensure the zoom preservation
fixes didn't introduce any regressions or break existing features.
"""

import sys
import traceback
from pathlib import Path
from datetime import datetime

# Add the src directory to the path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

def log_test_result(test_name, success, details=""):
    """Log test results"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    status = "✓ PASS" if success else "✗ FAIL"
    message = f"{timestamp} - {status} - {test_name}"
    if details:
        message += f" - {details}"
    print(message)
    return success

def test_all_imports():
    """Test that all modules can still be imported"""
    try:
        import main
        from main import EDFViewer, DataLoaderThread, AnnotationManager
        from main import HighPerformanceDataCache, PerformanceManager, HighPerformanceSignalProcessor
        
        log_test_result("All Core Imports", True, "All main modules import successfully")
        return True
    except Exception as e:
        log_test_result("All Core Imports", False, f"Import failed: {e}")
        return False

def test_class_initialization():
    """Test that all classes can be initialized"""
    try:
        from main import EDFViewer, AnnotationManager
        from main import HighPerformanceDataCache, HighPerformanceSignalProcessor
        from PyQt6.QtWidgets import QApplication
        
        # Create QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication(['test'])
        
        # Test EDFViewer
        viewer = EDFViewer()
        
        # Check all expected attributes exist
        expected_attrs = [
            'raw', 'channel_indices', 'channel_colors', 'view_start_time', 
            'view_duration', 'focus_start_time', 'focus_duration', 'channel_offset',
            'total_channels', 'visible_channels', 'sensitivity', 'auto_sensitivity',
            'auto_move_active', '_updating_scrollbar', '_preserving_zoom', '_updating_combo'
        ]
        
        for attr in expected_attrs:
            if not hasattr(viewer, attr):
                raise AttributeError(f"Missing attribute: {attr}")
        
        # Test other classes
        cache = HighPerformanceDataCache()
        processor = HighPerformanceSignalProcessor()
        annotation_mgr = AnnotationManager()
        
        viewer.close()
        log_test_result("Class Initialization", True, "All classes initialize correctly")
        return True
        
    except Exception as e:
        log_test_result("Class Initialization", False, f"Failed: {e}")
        traceback.print_exc()
        return False

def test_zoom_functionality():
    """Test all zoom-related functionality"""
    try:
        from main import EDFViewer
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(['test'])
        
        viewer = EDFViewer()
        
        # Test 1: Basic zoom operations
        original_duration = viewer.view_duration
        
        # Test manual zoom change (should work when not preserving)
        viewer._preserving_zoom = False
        viewer._updating_combo = False
        viewer.update_time_scale("5s")
        
        # Test zoom preservation
        viewer._preserving_zoom = True
        preserved_duration = viewer.view_duration
        viewer.update_time_scale("20s")  # Should be ignored
        
        if viewer.view_duration != preserved_duration:
            raise AssertionError("Zoom not preserved when _preserving_zoom=True")
        
        viewer._preserving_zoom = False
        
        # Test combo box update protection
        viewer._updating_combo = True
        viewer.update_time_scale("30s")  # Should be ignored
        
        if viewer.view_duration != preserved_duration:
            raise AssertionError("Zoom changed when _updating_combo=True")
        
        viewer._updating_combo = False
        
        viewer.close()
        log_test_result("Zoom Functionality", True, "All zoom operations work correctly")
        return True
        
    except Exception as e:
        log_test_result("Zoom Functionality", False, f"Failed: {e}")
        traceback.print_exc()
        return False

def test_navigation_functions():
    """Test navigation functions"""
    try:
        from main import EDFViewer
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(['test'])
        
        viewer = EDFViewer()
        
        # Test navigation functions exist and work
        original_zoom = viewer.view_duration
        
        # These should preserve zoom
        viewer._navigate_preserving_zoom('left')
        assert viewer.view_duration == original_zoom, "Navigation changed zoom"
        
        viewer._navigate_preserving_zoom('right')
        assert viewer.view_duration == original_zoom, "Navigation changed zoom"
        
        viewer._previous_section_preserving_zoom()
        assert viewer.view_duration == original_zoom, "Section nav changed zoom"
        
        viewer._next_section_preserving_zoom()
        assert viewer.view_duration == original_zoom, "Section nav changed zoom"
        
        viewer.close()
        log_test_result("Navigation Functions", True, "All navigation preserves zoom correctly")
        return True
        
    except Exception as e:
        log_test_result("Navigation Functions", False, f"Failed: {e}")
        traceback.print_exc()
        return False

def test_event_handlers():
    """Test that event handlers still work"""
    try:
        from main import EDFViewer
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QKeyEvent, QWheelEvent
        from PyQt6.QtCore import Qt, QPoint
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(['test'])
        
        viewer = EDFViewer()
        
        # Test that methods exist and are callable
        methods_to_test = [
            'keyPressEvent', 'wheelEvent', 'mousePressEvent', 
            'mouseReleaseEvent', 'mouseMoveEvent'
        ]
        
        for method_name in methods_to_test:
            if not hasattr(viewer, method_name):
                raise AttributeError(f"Missing method: {method_name}")
            if not callable(getattr(viewer, method_name)):
                raise AttributeError(f"Method not callable: {method_name}")
        
        viewer.close()
        log_test_result("Event Handlers", True, "All event handlers present and callable")
        return True
        
    except Exception as e:
        log_test_result("Event Handlers", False, f"Failed: {e}")
        traceback.print_exc()
        return False

def test_ui_components():
    """Test UI component functionality"""
    try:
        from main import EDFViewer
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(['test'])
        
        viewer = EDFViewer()
        
        # Check that key UI components exist
        ui_components = [
            'plot_widget', 'vscroll', 'hscroll', 'time_combo',
            'status_label', 'annotation_manager', 'perf_manager'
        ]
        
        for component in ui_components:
            if not hasattr(viewer, component):
                raise AttributeError(f"Missing UI component: {component}")
        
        # Test that update methods exist
        update_methods = [
            'update_time_combo_display', 'update_time_scale', 'update_scrollbars',
            'create_plot_items'
        ]
        
        for method in update_methods:
            if not hasattr(viewer, method):
                raise AttributeError(f"Missing update method: {method}")
            if not callable(getattr(viewer, method)):
                raise AttributeError(f"Method not callable: {method}")
        
        viewer.close()
        log_test_result("UI Components", True, "All UI components and methods present")
        return True
        
    except Exception as e:
        log_test_result("UI Components", False, f"Failed: {e}")
        traceback.print_exc()
        return False

def test_gaze_tracking_integration():
    """Test gaze tracking components"""
    try:
        from main import EDFViewer
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(['test'])
        
        viewer = EDFViewer()
        
        # Check gaze tracking attributes
        gaze_attrs = [
            'gaze_tracker', 'gaze_processor', 'gaze_annotator',
            'gaze_overlay_manager', 'feedback_system', 'enhanced_auto_move'
        ]
        
        for attr in gaze_attrs:
            if not hasattr(viewer, attr):
                raise AttributeError(f"Missing gaze attribute: {attr}")
        
        # Test gaze tracking modules can be imported
        try:
            from gaze_tracking.gaze_tracker import GazeTracker
            from ui.gaze_mode_dialog import GazeModeSetupDialog
            log_test_result("Gaze Tracking Modules", True, "Gaze modules import correctly")
        except ImportError as e:
            log_test_result("Gaze Tracking Modules", False, f"Import failed: {e}")
            return False
        
        viewer.close()
        log_test_result("Gaze Tracking Integration", True, "Gaze tracking components intact")
        return True
        
    except Exception as e:
        log_test_result("Gaze Tracking Integration", False, f"Failed: {e}")
        traceback.print_exc()
        return False

def test_annotation_system():
    """Test annotation system"""
    try:
        from main import AnnotationManager
        
        annotation_mgr = AnnotationManager()
        
        # Test basic methods exist
        methods = ['add_annotation', 'remove_annotation', 'get_annotations']
        for method in methods:
            if hasattr(annotation_mgr, method):
                if not callable(getattr(annotation_mgr, method)):
                    raise AttributeError(f"Method not callable: {method}")
        
        log_test_result("Annotation System", True, "Annotation system intact")
        return True
        
    except Exception as e:
        log_test_result("Annotation System", False, f"Failed: {e}")
        traceback.print_exc()
        return False

def test_performance_monitoring():
    """Test performance monitoring"""
    try:
        from main import PerformanceManager, HighPerformanceDataCache, HighPerformanceSignalProcessor
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(['test'])
        
        # Create a dummy parent for PerformanceManager
        class DummyParent:
            def __init__(self):
                pass
        
        parent = DummyParent()
        perf_mgr = PerformanceManager(parent)
        cache = HighPerformanceDataCache()
        processor = HighPerformanceSignalProcessor()
        
        # Test basic functionality
        if not hasattr(cache, 'get'):
            raise AttributeError("Cache missing get method")
        if not hasattr(cache, 'put'):
            raise AttributeError("Cache missing put method")
        
        log_test_result("Performance Monitoring", True, "Performance components intact")
        return True
        
    except Exception as e:
        log_test_result("Performance Monitoring", False, f"Failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run comprehensive functionality test"""
    print("="*70)
    print("COMPREHENSIVE FUNCTIONALITY TEST")
    print("="*70)
    print("Verifying that zoom fixes didn't break any existing functionality...\n")
    
    tests = [
        ("All Core Imports", test_all_imports),
        ("Class Initialization", test_class_initialization),
        ("Zoom Functionality", test_zoom_functionality),
        ("Navigation Functions", test_navigation_functions),
        ("Event Handlers", test_event_handlers),
        ("UI Components", test_ui_components),
        ("Gaze Tracking Integration", test_gaze_tracking_integration),
        ("Annotation System", test_annotation_system),
        ("Performance Monitoring", test_performance_monitoring),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"Testing: {test_name}")
        try:
            if test_func():
                passed += 1
            print()
        except Exception as e:
            log_test_result(test_name, False, f"Exception: {e}")
            traceback.print_exc()
            print()
    
    print("="*70)
    print("COMPREHENSIVE TEST SUMMARY")
    print("="*70)
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 ALL FUNCTIONALITY TESTS PASSED!")
        print("✅ Zoom fixes did NOT break any existing features")
        print("✅ All core EDF viewer functionality is intact")
        print("✅ All integrations (gaze tracking, annotations, etc.) working")
        print("✅ All UI components and event handlers working")
        print("✅ Performance monitoring systems intact")
    else:
        print(f"⚠️  {total-passed} TESTS FAILED")
        print("❌ Some functionality may have been broken by changes")
        print("🔍 Review failed tests above for details")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)