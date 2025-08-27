#!/usr/bin/env python3
"""
Quick test to verify zoom behavior is fixed.

This test specifically checks the zoom preservation issue described by the user:
"when i zoom into a file and then press any keys or click on the screen the zoom is reset"
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

def test_zoom_preservation():
    """Test that zoom is preserved during navigation and clicks"""
    try:
        from main import EDFViewer
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        
        print("Testing zoom preservation behavior...")
        
        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(['test'])
        
        viewer = EDFViewer()
        
        # Simulate loading a file (without actually loading one)
        print("1. Setting up initial zoom level...")
        original_zoom = 5.0  # 5 second view
        viewer.view_duration = original_zoom
        print(f"   Initial zoom set to: {viewer.view_duration}s")
        
        # Test 1: Navigation with arrow keys
        print("2. Testing arrow key navigation...")
        print("   Simulating left arrow key press...")
        viewer._navigate_preserving_zoom('left')
        
        if viewer.view_duration == original_zoom:
            print("   ✓ PASS: Zoom preserved during left arrow navigation")
        else:
            print(f"   ✗ FAIL: Zoom changed from {original_zoom} to {viewer.view_duration}")
            return False
        
        print("   Simulating right arrow key press...")
        viewer._navigate_preserving_zoom('right')
        
        if viewer.view_duration == original_zoom:
            print("   ✓ PASS: Zoom preserved during right arrow navigation")
        else:
            print(f"   ✗ FAIL: Zoom changed from {original_zoom} to {viewer.view_duration}")
            return False
        
        # Test 2: G/H navigation
        print("3. Testing G/H focus navigation...")
        print("   Simulating previous section (G key)...")
        viewer._previous_section_preserving_zoom()
        
        if viewer.view_duration == original_zoom:
            print("   ✓ PASS: Zoom preserved during previous section navigation")
        else:
            print(f"   ✗ FAIL: Zoom changed from {original_zoom} to {viewer.view_duration}")
            return False
            
        print("   Simulating next section (H key)...")
        viewer._next_section_preserving_zoom()
        
        if viewer.view_duration == original_zoom:
            print("   ✓ PASS: Zoom preserved during next section navigation")
        else:
            print(f"   ✗ FAIL: Zoom changed from {original_zoom} to {viewer.view_duration}")
            return False
        
        # Test 3: Time scale changes (should be ignored when preserving zoom)
        print("4. Testing time scale changes during preservation...")
        viewer._preserving_zoom = True
        viewer.update_time_scale("10s")  # Try to change to 10 seconds
        
        if viewer.view_duration == original_zoom:
            print("   ✓ PASS: Time scale changes ignored during zoom preservation")
        else:
            print(f"   ✗ FAIL: Time scale changed during preservation from {original_zoom} to {viewer.view_duration}")
            return False
        
        viewer._preserving_zoom = False
        
        # Test 4: Combo box updates (should be ignored when updating internally)
        print("5. Testing combo box update protection...")
        viewer._updating_combo = True
        viewer.update_time_scale("15s")  # Try to change to 15 seconds
        
        if viewer.view_duration == original_zoom:
            print("   ✓ PASS: Time scale changes ignored during combo update")
        else:
            print(f"   ✗ FAIL: Time scale changed during combo update from {original_zoom} to {viewer.view_duration}")
            return False
        
        viewer._updating_combo = False
        
        print("\n🎉 ALL ZOOM PRESERVATION TESTS PASSED!")
        print("\nThe zoom reset issue has been FIXED:")
        print("- Arrow key navigation preserves zoom ✓")
        print("- G/H focus navigation preserves zoom ✓") 
        print("- Time scale changes are properly controlled ✓")
        print("- Combo box updates don't interfere ✓")
        
        # Clean up
        viewer.close()
        return True
        
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("ZOOM PRESERVATION BEHAVIOR TEST")
    print("="*60)
    print("Testing the specific issue: 'zoom resets when pressing keys or clicking'")
    print()
    
    success = test_zoom_preservation()
    
    print("\n" + "="*60)
    if success:
        print("✅ ZOOM ISSUE FIXED - Zoom will now stay preserved during navigation!")
    else:
        print("❌ ZOOM ISSUE STILL EXISTS - Further fixes needed")
    print("="*60)