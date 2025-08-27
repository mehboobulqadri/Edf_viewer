#!/usr/bin/env python3
"""
Test script for Phase 1 gaze tracking implementation.

This script tests the basic functionality of the gaze tracking components
without requiring the full EDF viewer GUI or actual hardware.
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_gaze_tracker_import():
    """Test importing gaze tracker components."""
    print("Testing gaze tracker imports...")
    try:
        from gaze_tracking.gaze_tracker import GazeTracker, MockGazeTracker, GazePoint
        print("✓ GazeTracker imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import GazeTracker: {e}")
        return False

def test_coordinate_mapper_import():
    """Test importing coordinate mapper components."""
    print("Testing coordinate mapper imports...")
    try:
        from gaze_tracking.coordinate_mapper import CoordinateMapper, CalibrationData, EDFCoordinates
        print("✓ CoordinateMapper imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import CoordinateMapper: {e}")
        return False

def test_ui_dialog_import():
    """Test importing UI dialog components."""
    print("Testing UI dialog imports...")
    try:
        from ui.gaze_mode_dialog import GazeModeSetupDialog
        print("✓ GazeModeSetupDialog imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import GazeModeSetupDialog: {e}")
        return False

def test_mock_gaze_tracker():
    """Test mock gaze tracker functionality."""
    print("Testing mock gaze tracker functionality...")
    try:
        from PyQt6.QtWidgets import QApplication
        from gaze_tracking.gaze_tracker import MockGazeTracker, GazePoint
        
        # Create QApplication instance if not exists
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # Create mock tracker
        tracker = MockGazeTracker()
        
        # Test connection
        if tracker.connect_device():
            print("✓ Mock tracker connected successfully")
            
            # Test gaze data callback
            received_data = []
            
            def test_callback(gaze_point: GazePoint):
                received_data.append(gaze_point)
                print(f"  Received gaze point: ({gaze_point.x:.3f}, {gaze_point.y:.3f}) confidence={gaze_point.confidence:.3f}")
            
            tracker.set_gaze_callback(test_callback)
            
            # Start streaming briefly
            if tracker.start_streaming():
                print("✓ Mock streaming started")
                
                # Process Qt events to allow timer to fire
                import time
                start_time = time.time()
                while time.time() - start_time < 2.0 and len(received_data) < 5:
                    app.processEvents()
                    time.sleep(0.1)
                
                tracker.stop_streaming()
                print("✓ Mock streaming stopped")
                
                if len(received_data) > 0:
                    print(f"✓ Received {len(received_data)} gaze data points")
                    return True
                else:
                    print("✗ No gaze data received")
                    return False
            else:
                print("✗ Failed to start mock streaming")
                return False
        else:
            print("✗ Failed to connect mock tracker")
            return False
            
    except Exception as e:
        print(f"✗ Mock tracker test failed: {e}")
        return False

def test_coordinate_mapper():
    """Test coordinate mapper functionality."""
    print("Testing coordinate mapper functionality...")
    try:
        from gaze_tracking.coordinate_mapper import CoordinateMapper, CalibrationData, CoordinateBounds
        
        # Create coordinate mapper
        mapper = CoordinateMapper()
        
        # Set up mock bounds
        mapper.bounds = CoordinateBounds(
            screen_width=1920,
            screen_height=1080,
            widget_x=100,
            widget_y=100,
            widget_width=800,
            widget_height=600
        )
        
        # Test calibration data
        calibration = CalibrationData(offset_x=10, offset_y=15, scale_x=1.1, scale_y=0.9)
        if calibration.is_valid():
            print("✓ Calibration data validation works")
            mapper.set_calibration_data(calibration)
            print("✓ Calibration data set successfully")
        else:
            print("✗ Calibration data validation failed")
            return False
        
        # Test coordinate transformation
        screen_x, screen_y = mapper.map_gaze_to_screen(0.5, 0.5)
        print(f"✓ Gaze to screen mapping: (0.5, 0.5) → ({screen_x}, {screen_y})")
        
        # Test EDF context
        test_channels = ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2"]
        mapper.set_edf_context(test_channels, 0.0, 10.0, 10, 0)
        print("✓ EDF context set successfully")
        
        # Test full coordinate transformation
        edf_coords = mapper.map_gaze_to_edf(0.5, 0.5)
        print(f"✓ Full gaze to EDF mapping: time={edf_coords.time_seconds:.2f}s, channel={edf_coords.channel_name}")
        
        return True
        
    except Exception as e:
        print(f"✗ Coordinate mapper test failed: {e}")
        return False

def test_main_integration():
    """Test main application integration."""
    print("Testing main application integration...")
    try:
        # Test that main.py can be imported without errors
        import main
        print("✓ Main application imports without errors")
        
        # Check that gaze tracking flag is set
        if hasattr(main, 'GAZE_TRACKING_AVAILABLE'):
            print(f"✓ Gaze tracking availability flag: {main.GAZE_TRACKING_AVAILABLE}")
        else:
            print("✗ Gaze tracking availability flag not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Main integration test failed: {e}")
        return False

def run_all_tests():
    """Run all Phase 1 tests."""
    print("="*50)
    print("PHASE 1 GAZE TRACKING IMPLEMENTATION TESTS")
    print("="*50)
    
    tests = [
        test_gaze_tracker_import,
        test_coordinate_mapper_import,
        test_ui_dialog_import,
        test_mock_gaze_tracker,
        test_coordinate_mapper,
        test_main_integration
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
        print("🎉 All Phase 1 tests passed! Implementation is ready.")
        print("\nNext steps:")
        print("• Install Tobii Pro SDK for hardware integration")
        print("• Begin Phase 2: Gaze Data Processing & Fixation Detection")
        print("• Test with actual eye tracking hardware")
    else:
        print("❌ Some tests failed. Please review the implementation.")
    
    print("="*50)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)