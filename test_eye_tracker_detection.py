#!/usr/bin/env python3
"""
Test script for eye tracker detection functionality.

This script tests the enhanced eye tracker detection methods
to verify they work correctly on systems with or without eye trackers.
"""

import sys
import logging
from pathlib import Path

# Add the src directory to the path so we can import gaze_tracking modules
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

try:
    from gaze_tracking.gaze_tracker import GazeTracker, MockGazeTracker
    print("✓ Successfully imported gaze tracking modules")
except ImportError as e:
    print(f"✗ Failed to import gaze tracking modules: {e}")
    sys.exit(1)

def test_eye_tracker_detection():
    """Test eye tracker detection methods."""
    print("\n" + "="*60)
    print("TESTING EYE TRACKER DETECTION")
    print("="*60)
    
    # Test 1: Mock Eye Tracker
    print("\n1. Testing Mock Eye Tracker:")
    try:
        mock_tracker = MockGazeTracker()
        devices = mock_tracker.discover_devices()
        print(f"   Mock devices found: {len(devices)}")
        for device in devices:
            print(f"   - {device['device_name']} ({device['type']})")
    except Exception as e:
        print(f"   ✗ Mock tracker test failed: {e}")
    
    # Test 2: Real Eye Tracker Detection
    print("\n2. Testing Real Eye Tracker Detection:")
    try:
        real_tracker = GazeTracker()
        devices = real_tracker.discover_devices()
        print(f"   Real devices found: {len(devices)}")
        
        if devices:
            for device in devices:
                print(f"   - {device['device_name']} ({device['type']})")
                print(f"     Address: {device.get('address', 'N/A')}")
                print(f"     Model: {device.get('model', 'N/A')}")
                print(f"     Serial: {device.get('serial_number', 'N/A')}")
        else:
            print("   No real eye tracking devices detected")
            
    except Exception as e:
        print(f"   ✗ Real tracker detection failed: {e}")
    
    # Test 3: Connection Test (if devices found)
    print("\n3. Testing Eye Tracker Connection:")
    try:
        tracker = GazeTracker()
        devices = tracker.discover_devices()
        
        if devices:
            print("   Attempting to connect to first device...")
            if tracker.connect_device():
                print("   ✓ Connection successful!")
                
                # Get device info
                device_info = tracker.get_device_info()
                if device_info:
                    print(f"   Device info: {device_info}")
                else:
                    print("   Device connected but info unavailable")
                    
                # Disconnect
                tracker.disconnect_device()
                print("   ✓ Disconnected successfully")
            else:
                print("   ✗ Connection failed")
        else:
            print("   No devices available to test connection")
            
    except Exception as e:
        print(f"   ✗ Connection test failed: {e}")

def test_hardware_detection_methods():
    """Test individual hardware detection methods."""
    print("\n" + "="*60)
    print("TESTING INDIVIDUAL DETECTION METHODS")
    print("="*60)
    
    # Test USB detection
    print("\n1. Testing USB Device Detection:")
    try:
        import subprocess
        import re
        
        result = subprocess.run(['wmic', 'path', 'win32_pnpentity', 'get', 'name'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            usb_devices = result.stdout.lower()
            print("   ✓ USB enumeration successful")
            
            # Check for known eye tracker patterns
            eye_tracker_patterns = [
                (r'tobii', 'Tobii Eye Tracker'),
                (r'eyetech', 'EyeTech Digital Systems'),
                (r'gazepoint', 'GazePoint Eye Tracker'),
                (r'sr research', 'SR Research EyeLink'),
                (r'smart eye', 'Smart Eye Tracker'),
            ]
            
            found_patterns = []
            for pattern, name in eye_tracker_patterns:
                if re.search(pattern, usb_devices):
                    found_patterns.append(name)
            
            if found_patterns:
                print(f"   Found eye tracker patterns: {found_patterns}")
            else:
                print("   No eye tracker patterns found in USB devices")
        else:
            print(f"   ✗ USB enumeration failed with return code: {result.returncode}")
            
    except Exception as e:
        print(f"   ✗ USB detection test failed: {e}")
    
    # Test process detection
    print("\n2. Testing Process Detection:")
    try:
        import psutil
        
        eye_tracker_processes = [
            ('tobii', 'Tobii Eye Tracker Service'),
            ('eyetech', 'EyeTech TM5'),
            ('gazepoint', 'GazePoint GP3'),
            ('eyelink', 'SR Research EyeLink'),
        ]
        
        running_processes = [p.name().lower() for p in psutil.process_iter()]
        print(f"   ✓ Found {len(running_processes)} running processes")
        
        found_eye_trackers = []
        for process_name, device_name in eye_tracker_processes:
            if any(process_name in proc for proc in running_processes):
                found_eye_trackers.append(device_name)
        
        if found_eye_trackers:
            print(f"   Found eye tracker processes: {found_eye_trackers}")
        else:
            print("   No eye tracker processes found")
            
    except Exception as e:
        print(f"   ✗ Process detection test failed: {e}")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("Eye Tracker Detection Test")
    print("This script tests the enhanced eye tracker detection functionality.")
    
    test_eye_tracker_detection()
    test_hardware_detection_methods()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("\nIf no real eye trackers were found, this is normal if you don't have")
    print("eye tracking hardware connected. The mock tracker should always work.")
    print("\nFor testing the gaze annotation mode in the main application,")
    print("you can use the 'Use mock data for testing' option in the Hardware Test tab.")