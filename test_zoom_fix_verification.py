#!/usr/bin/env python3
"""
Comprehensive test to verify all zoom fixes are working.

This focuses on the core issue: navigation and clicking should preserve zoom.
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

def test_comprehensive_zoom_preservation():
    """Test all the ways zoom can be reset and verify they're now fixed"""
    
    from main import EDFViewer
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QKeyEvent, QWheelEvent
    import numpy as np
    
    print("="*70)
    print("COMPREHENSIVE ZOOM PRESERVATION VERIFICATION")
    print("="*70)
    
    # Create QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(['test'])
    
    print("\n1. Creating EDFViewer...")
    viewer = EDFViewer()
    
    print("\n2. Setting up mock data...")
    class MockRaw:
        def __init__(self):
            self.info = {'sfreq': 256.0}
            self.n_times = 256000  # 1000 seconds of data
            self.ch_names = ['C3', 'C4', 'F3', 'F4', 'O1', 'O2']
            self.filenames = ['test.edf']
        
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
    viewer.visible_ch_names = viewer.raw.ch_names[:viewer.visible_channels]
    
    print("   ✅ Mock data loaded")
    
    # Test scenarios
    test_results = []
    
    def run_test(test_name, zoom_level, test_func):
        print(f"\n{len(test_results)+3}. Testing: {test_name}")
        print(f"   Setting zoom to {zoom_level} seconds...")
        viewer.view_duration = zoom_level
        
        before_zoom = viewer.view_duration
        test_func(viewer)
        after_zoom = viewer.view_duration
        
        success = abs(before_zoom - after_zoom) < 0.01
        print(f"   Before: {before_zoom}s, After: {after_zoom}s")
        
        if success:
            print(f"   ✅ PASS: {test_name}")
            test_results.append((test_name, True))
        else:
            print(f"   ❌ FAIL: {test_name} - Zoom changed from {before_zoom} to {after_zoom}")
            test_results.append((test_name, False))
        
        return success
    
    # Test 1: Left arrow navigation
    def test_left_arrow(viewer):
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.KeyboardModifier.NoModifier)
        viewer.keyPressEvent(key_event)
    
    run_test("Left Arrow Navigation", 3.0, test_left_arrow)
    
    # Test 2: Right arrow navigation
    def test_right_arrow(viewer):
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier)
        viewer.keyPressEvent(key_event)
    
    run_test("Right Arrow Navigation", 2.5, test_right_arrow)
    
    # Test 3: Channel reordering (simulates click-drag)
    def test_channel_reorder(viewer):
        viewer.reorder_channels(0, 1)
    
    run_test("Channel Reordering (Click-Drag)", 4.0, test_channel_reorder)
    
    # Test 4: Performance manager update
    def test_perf_update(viewer):
        viewer.perf_manager.request_update()
    
    run_test("Performance Manager Update", 1.5, test_perf_update)
    
    # Test 5: Plot data refresh
    def test_plot_refresh(viewer):
        viewer.plot_eeg_data()
    
    run_test("Plot Data Refresh", 6.0, test_plot_refresh)
    
    # Test 6: Time combo display update
    def test_combo_update(viewer):
        viewer.update_time_combo_display()
    
    run_test("Time Combo Display Update", 3.5, test_combo_update)
    
    # Test 7: Scrollbar update
    def test_scrollbar_update(viewer):
        viewer.update_scrollbars()
    
    run_test("Scrollbar Update", 5.5, test_scrollbar_update)
    
    # Test 8: Up arrow (channel navigation)
    def test_up_arrow(viewer):
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
        viewer.keyPressEvent(key_event)
    
    run_test("Up Arrow (Channel Navigation)", 2.0, test_up_arrow)
    
    # Test 9: Down arrow (channel navigation)
    def test_down_arrow(viewer):
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
        viewer.keyPressEvent(key_event)
    
    run_test("Down Arrow (Channel Navigation)", 4.5, test_down_arrow)
    
    # Test 10: Create plot items (major refresh)
    def test_create_plot_items(viewer):
        viewer.create_plot_items()
    
    run_test("Create Plot Items (Major Refresh)", 7.0, test_create_plot_items)
    
    print("\n" + "="*70)
    print("ZOOM PRESERVATION TEST RESULTS")
    print("="*70)
    
    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    
    for i, (test_name, success) in enumerate(test_results, 1):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{i:2d}. {status} - {test_name}")
    
    print(f"\nSUMMARY: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL ZOOM PRESERVATION TESTS PASSED!")
        print("✅ The zoom reset issue has been COMPLETELY FIXED!")
        print("✅ Left/right arrows preserve zoom")
        print("✅ Click-drag operations preserve zoom") 
        print("✅ All plot refreshes preserve zoom")
    else:
        print(f"⚠️  {total-passed} tests still failing")
        print("❌ Zoom reset issue partially fixed")
        failed_tests = [name for name, success in test_results if not success]
        print("Failed tests:", ", ".join(failed_tests))
    
    viewer.close()
    
    print("\n" + "="*70)
    print("VERIFICATION COMPLETE")
    print("="*70)
    
    return passed == total

if __name__ == "__main__":
    print("Comprehensive Zoom Preservation Verification")
    print("This tests ALL the ways zoom could be reset to verify they're now fixed.")
    
    success = test_comprehensive_zoom_preservation()
    
    if success:
        print("\n🎯 VERDICT: The zoom reset issue is COMPLETELY RESOLVED!")
    else:
        print("\n⚠️  VERDICT: Zoom reset issue still partially exists.")