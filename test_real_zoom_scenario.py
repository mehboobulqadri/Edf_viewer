#!/usr/bin/env python3
"""
Test the zoom issue in a more realistic scenario that simulates actual usage.

This will test:
1. Loading actual data (simulated)
2. Zooming in with mouse wheel
3. Using keyboard navigation (left/right arrows)
4. Clicking on the plot
5. Checking for any zoom resets
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

def patch_comprehensive_tracking():
    """Add comprehensive tracking to catch all zoom changes"""
    
    from main import EDFViewer
    
    # Store original methods
    originals = {}
    
    # Track all methods that might affect view_duration
    methods_to_track = [
        '__setattr__',
        'update_time_scale',
        'update_time_combo_display', 
        'wheelEvent',
        'keyPressEvent',
        'mousePressEvent',
        'mouseReleaseEvent',
        '_navigate_preserving_zoom',
        'plot_eeg_data',
        'update_scrollbars',
        'load_session',
        'on_data_loaded'
    ]
    
    for method_name in methods_to_track:
        if hasattr(EDFViewer, method_name):
            originals[method_name] = getattr(EDFViewer, method_name)
    
    def tracked_setattr(self, name, value):
        if name == 'view_duration':
            import traceback
            print(f"🚨 view_duration being set to {value}")
            print(f"🔍 Previous value: {getattr(self, 'view_duration', 'undefined')}")
            print(f"🔍 Call stack:")
            for line in traceback.format_stack()[-4:-1]:  # Show last few stack frames
                print(f"    {line.strip()}")
        return originals['__setattr__'](self, name, value)
    
    def tracked_method(method_name):
        original = originals[method_name]
        def wrapper(self, *args, **kwargs):
            before_duration = getattr(self, 'view_duration', None)
            print(f"🔍 {method_name} called - duration before: {before_duration}")
            
            result = original(self, *args, **kwargs)
            
            after_duration = getattr(self, 'view_duration', None)
            if before_duration != after_duration:
                print(f"🚨 {method_name} CHANGED view_duration: {before_duration} → {after_duration}")
            else:
                print(f"✅ {method_name} preserved view_duration: {after_duration}")
            
            return result
        return wrapper
    
    # Apply patches
    EDFViewer.__setattr__ = tracked_setattr
    
    for method_name in methods_to_track:
        if hasattr(EDFViewer, method_name) and method_name != '__setattr__':
            setattr(EDFViewer, method_name, tracked_method(method_name))
    
    print("✅ Comprehensive zoom tracking applied")

def simulate_real_usage():
    """Simulate real user interaction that causes zoom reset"""
    
    from main import EDFViewer
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QKeyEvent, QWheelEvent
    import numpy as np
    
    print("="*60)
    print("REALISTIC ZOOM RESET TEST")
    print("="*60)
    
    # Create QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(['test'])
    
    print("\n1. Creating EDFViewer...")
    viewer = EDFViewer()
    
    print("\n2. Simulating file load (setting up mock data)...")
    # Simulate having loaded data
    class MockRaw:
        def __init__(self):
            self.info = {'sfreq': 256.0}
            self.n_times = 256000  # 1000 seconds of data
            self.ch_names = ['C3', 'C4', 'F3', 'F4', 'O1', 'O2']
        
        def get_data(self, picks=None, start=0, stop=None, return_times=True):
            if stop is None:
                stop = self.n_times
            n_samples = stop - start
            n_channels = len(picks) if picks else len(self.ch_names)
            data = np.random.randn(n_channels, n_samples) * 50
            times = np.arange(start, stop) / self.info['sfreq']
            return (data, times) if return_times else data
    
    viewer.raw = MockRaw()
    viewer.channel_indices = list(range(len(viewer.raw.ch_names)))
    viewer.channel_colors = {ch: '#e0e6ed' for ch in viewer.raw.ch_names}
    viewer.total_channels = len(viewer.channel_indices)
    
    print("   ✅ Mock data loaded")
    
    print("\n3. Testing initial zoom...")
    print(f"   Initial view_duration: {viewer.view_duration}")
    
    print("\n4. Zooming in (simulating Ctrl+mouse wheel)...")
    # Simulate zooming in to 3 seconds
    viewer.view_duration = 3.0
    print(f"   Zoomed to: {viewer.view_duration} seconds")
    
    print("\n5. Testing keyboard navigation (left arrow)...")
    # Create a mock key event for left arrow
    key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.KeyboardModifier.NoModifier)
    viewer.keyPressEvent(key_event)
    print(f"   After left arrow: {viewer.view_duration} seconds")
    
    print("\n6. Testing keyboard navigation (right arrow)...")
    # Create a mock key event for right arrow  
    key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
    viewer.keyPressEvent(key_event)
    print(f"   After right arrow: {viewer.view_duration} seconds")
    
    print("\n7. Testing time combo box interaction...")
    # This might be where the problem is
    viewer.update_time_combo_display()
    print(f"   After combo update: {viewer.view_duration} seconds")
    
    print("\n8. Testing manual time scale change...")
    # Test what happens if combo box triggers time scale change
    print("   Simulating combo box selection of '10s'...")
    viewer.update_time_scale("10s")
    print(f"   After time scale update: {viewer.view_duration} seconds")
    
    print("\n9. Testing scroll bar interaction...")
    viewer.update_scrollbars()
    print(f"   After scrollbar update: {viewer.view_duration} seconds")
    
    print("\n10. Final zoom check...")
    final_duration = viewer.view_duration
    if final_duration == 3.0:
        print(f"✅ SUCCESS: Zoom preserved at {final_duration} seconds")
    else:
        print(f"❌ FAILURE: Zoom reset to {final_duration} seconds (expected 3.0)")
    
    viewer.close()
    
    print("\n" + "="*60)
    print("REALISTIC TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    print("Realistic Zoom Reset Test")
    print("This simulates actual user interaction to find the zoom reset issue.")
    
    # Apply comprehensive tracking
    patch_comprehensive_tracking()
    
    # Run realistic test
    simulate_real_usage()