#!/usr/bin/env python3
"""
Debug script to figure out exactly why zoom is still resetting.

This will add detailed logging to track what's happening with zoom during navigation.
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

def patch_zoom_tracking():
    """Patch the EDFViewer class to add detailed zoom tracking"""
    
    from main import EDFViewer
    
    # Store original methods
    original_init = EDFViewer.__init__
    original_navigate = EDFViewer._navigate_preserving_zoom
    original_update_time_scale = EDFViewer.update_time_scale
    original_update_combo_display = EDFViewer.update_time_combo_display
    original_plot_eeg_data = EDFViewer.plot_eeg_data
    
    def tracked_init(self, *args, **kwargs):
        print("🔍 EDFViewer.__init__ called")
        result = original_init(self, *args, **kwargs)
        print(f"🔍 Initial view_duration: {self.view_duration}")
        return result
    
    def tracked_navigate(self, direction):
        print(f"🔍 _navigate_preserving_zoom({direction}) called")
        print(f"🔍 Before navigation - view_duration: {self.view_duration}")
        print(f"🔍 Before navigation - _preserving_zoom: {self._preserving_zoom}")
        print(f"🔍 Before navigation - _updating_combo: {self._updating_combo}")
        
        result = original_navigate(self, direction)
        
        print(f"🔍 After navigation - view_duration: {self.view_duration}")
        print(f"🔍 After navigation - _preserving_zoom: {self._preserving_zoom}")
        print(f"🔍 After navigation - _updating_combo: {self._updating_combo}")
        return result
    
    def tracked_update_time_scale(self, value):
        print(f"🔍 update_time_scale({value}) called")
        print(f"🔍 Current view_duration: {self.view_duration}")
        print(f"🔍 _preserving_zoom: {self._preserving_zoom}")
        print(f"🔍 _updating_combo: {self._updating_combo}")
        
        # Check if we should skip
        if self._preserving_zoom:
            print("🔍 SKIPPING update_time_scale due to _preserving_zoom=True")
            return
        if self._updating_combo:
            print("🔍 SKIPPING update_time_scale due to _updating_combo=True")
            return
            
        print(f"🔍 PROCEEDING with update_time_scale - changing from {self.view_duration}")
        result = original_update_time_scale(self, value)
        print(f"🔍 AFTER update_time_scale - view_duration now: {self.view_duration}")
        return result
    
    def tracked_update_combo_display(self):
        print(f"🔍 update_time_combo_display() called")
        print(f"🔍 Current view_duration: {self.view_duration}")
        print(f"🔍 _preserving_zoom: {self._preserving_zoom}")
        print(f"🔍 _updating_combo: {self._updating_combo}")
        
        result = original_update_combo_display(self)
        
        print(f"🔍 After update_combo_display - view_duration: {self.view_duration}")
        return result
    
    def tracked_plot_eeg_data(self):
        print(f"🔍 plot_eeg_data() called")
        print(f"🔍 Current view_duration: {self.view_duration}")
        
        result = original_plot_eeg_data(self)
        
        print(f"🔍 After plot_eeg_data - view_duration: {self.view_duration}")
        return result
    
    # Apply patches
    EDFViewer.__init__ = tracked_init
    EDFViewer._navigate_preserving_zoom = tracked_navigate
    EDFViewer.update_time_scale = tracked_update_time_scale
    EDFViewer.update_time_combo_display = tracked_update_combo_display
    EDFViewer.plot_eeg_data = tracked_plot_eeg_data
    
    print("✅ Zoom tracking patches applied")

def test_zoom_issue():
    """Test the actual zoom issue with detailed tracking"""
    
    from main import EDFViewer
    from PyQt6.QtWidgets import QApplication
    
    print("="*60)
    print("DEBUGGING ZOOM RESET ISSUE")
    print("="*60)
    
    # Create QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(['debug'])
    
    print("\n1. Creating EDFViewer...")
    viewer = EDFViewer()
    
    print("\n2. Setting custom zoom level...")
    viewer.view_duration = 5.0  # Zoom to 5 seconds
    print(f"   Set view_duration to: {viewer.view_duration}")
    
    print("\n3. Testing left arrow navigation...")
    print("   *** CALLING viewer._navigate_preserving_zoom('left') ***")
    viewer._navigate_preserving_zoom('left')
    
    print(f"\n4. Final view_duration: {viewer.view_duration}")
    
    if viewer.view_duration == 5.0:
        print("✅ SUCCESS: Zoom was preserved!")
    else:
        print("❌ FAILURE: Zoom was NOT preserved!")
        print(f"   Expected: 5.0, Got: {viewer.view_duration}")
    
    print("\n5. Testing with performance manager update...")
    print("   *** CALLING viewer.perf_manager.request_update() ***")
    viewer.perf_manager.request_update()
    
    print(f"\n6. Final view_duration after perf update: {viewer.view_duration}")
    
    if viewer.view_duration == 5.0:
        print("✅ SUCCESS: Zoom preserved even after performance update!")
    else:
        print("❌ FAILURE: Performance update reset the zoom!")
        print(f"   Expected: 5.0, Got: {viewer.view_duration}")
    
    viewer.close()
    
    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)

if __name__ == "__main__":
    print("Zoom Reset Debug Tool")
    print("This will help identify exactly where and why the zoom is being reset.")
    
    # Apply tracking patches
    patch_zoom_tracking()
    
    # Run the test
    test_zoom_issue()