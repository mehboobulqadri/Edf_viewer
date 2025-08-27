#!/usr/bin/env python3
"""
Test specifically for the click-drag zoom reset issue.

This will test:
1. Setting a custom zoom
2. Simulating click-drag operations that would trigger channel reordering
3. Simulating click-drag operations that would trigger annotation creation
4. Verifying zoom preservation in both cases
"""

import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

def patch_drag_tracking():
    """Add tracking to drag operations"""
    
    from main import EDFViewer
    
    # Store original methods
    original_reorder = EDFViewer.reorder_channels
    original_annotation = EDFViewer.add_annotation_popup
    original_highlight = EDFViewer.show_highlight_creation_dialog
    
    def tracked_reorder(self, from_index, to_index):
        print(f"🔍 reorder_channels({from_index}, {to_index}) called")
        before_duration = self.view_duration
        print(f"🔍 Before reorder - view_duration: {before_duration}")
        
        result = original_reorder(self, from_index, to_index)
        
        after_duration = self.view_duration
        if abs(before_duration - after_duration) < 0.01:
            print(f"✅ reorder_channels preserved zoom: {after_duration}")
        else:
            print(f"❌ reorder_channels CHANGED zoom: {before_duration} → {after_duration}")
        
        return result
    
    def tracked_annotation(self, start_time=None, duration=None):
        print(f"🔍 add_annotation_popup({start_time}, {duration}) called")
        before_duration = self.view_duration
        print(f"🔍 Before annotation - view_duration: {before_duration}")
        
        result = original_annotation(self, start_time, duration)
        
        after_duration = self.view_duration
        if abs(before_duration - after_duration) < 0.01:
            print(f"✅ add_annotation_popup preserved zoom: {after_duration}")
        else:
            print(f"❌ add_annotation_popup CHANGED zoom: {before_duration} → {after_duration}")
        
        return result
    
    def tracked_highlight(self, start_time, duration, channel=None):
        print(f"🔍 show_highlight_creation_dialog({start_time}, {duration}, {channel}) called")
        before_duration = self.view_duration
        print(f"🔍 Before highlight - view_duration: {before_duration}")
        
        result = original_highlight(self, start_time, duration, channel)
        
        after_duration = self.view_duration
        if abs(before_duration - after_duration) < 0.01:
            print(f"✅ show_highlight_creation_dialog preserved zoom: {after_duration}")
        else:
            print(f"❌ show_highlight_creation_dialog CHANGED zoom: {before_duration} → {after_duration}")
        
        return result
    
    # Apply patches
    EDFViewer.reorder_channels = tracked_reorder
    EDFViewer.add_annotation_popup = tracked_annotation
    EDFViewer.show_highlight_creation_dialog = tracked_highlight
    
    print("✅ Drag operation tracking applied")

def test_click_drag_zoom_preservation():
    """Test that click-drag operations preserve zoom"""
    
    from main import EDFViewer, AnnotationManager
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import QPointF
    import numpy as np
    
    print("="*60)
    print("CLICK-DRAG ZOOM PRESERVATION TEST")
    print("="*60)
    
    # Create QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(['test'])
    
    print("\n1. Creating EDFViewer...")
    viewer = EDFViewer()
    
    print("\n2. Setting up mock data...")
    # Simulate having loaded data
    class MockRaw:
        def __init__(self):
            self.info = {'sfreq': 256.0}
            self.n_times = 256000  # 1000 seconds of data
            self.ch_names = ['C3', 'C4', 'F3', 'F4', 'O1', 'O2']
            self.filenames = ['test.edf']  # Add this to prevent auto_export_csv errors
        
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
    
    # Set up annotation manager
    viewer.annotation_manager = AnnotationManager(viewer.raw)
    
    print("   ✅ Mock data loaded")
    
    print("\n3. Setting custom zoom...")
    viewer.view_duration = 2.5  # Zoom to 2.5 seconds
    print(f"   Set view_duration to: {viewer.view_duration}")
    
    print("\n4. Testing channel reordering (simulates click-drag on channels)...")
    # This simulates what happens when user drags a channel to reorder
    viewer.reorder_channels(0, 2)  # Move first channel to third position
    
    print(f"   After channel reorder: {viewer.view_duration} seconds")
    
    print("\n5. Testing annotation creation (simulates click-drag for annotation)...")
    # This simulates what happens when user drags to create an annotation
    # We'll mock the dialog to auto-accept
    
    class MockAnnotationDialog:
        def __init__(self, *args, **kwargs):
            pass
        def exec(self):
            return 1  # QDialog.DialogCode.Accepted
        def get_annotation_info(self):
            return (10.0, 2.0, "Test annotation", "#ff0000")
    
    # Temporarily replace the dialog
    import main
    original_dialog = main.AnnotationDialog
    main.AnnotationDialog = MockAnnotationDialog
    
    try:
        viewer.add_annotation_popup(10.0, 2.0)
        print(f"   After annotation creation: {viewer.view_duration} seconds")
    finally:
        # Restore original dialog
        main.AnnotationDialog = original_dialog
    
    print("\n6. Testing highlight creation (simulates click-drag on specific channel)...")
    # This simulates what happens when user drags on a specific channel to create highlight
    
    class MockHighlightDialog:
        def __init__(self, *args, **kwargs):
            pass
        def exec(self):
            return 1  # QDialog.DialogCode.Accepted
        def get_highlight_info(self):
            return ("C3", 15.0, 1.5, "#00ff00", "Test highlight")
    
    # Temporarily replace the dialog
    original_highlight_dialog = getattr(main, 'HighlightSectionDialog', None)
    main.HighlightSectionDialog = MockHighlightDialog
    
    try:
        viewer.show_highlight_creation_dialog(15.0, 1.5, "C3")
        print(f"   After highlight creation: {viewer.view_duration} seconds")
    finally:
        # Restore original dialog if it existed
        if original_highlight_dialog:
            main.HighlightSectionDialog = original_highlight_dialog
    
    print("\n7. Final zoom verification...")
    final_duration = viewer.view_duration
    if abs(final_duration - 2.5) < 0.01:
        print(f"✅ SUCCESS: Zoom preserved at {final_duration} seconds")
        print("✅ Click-drag operations do NOT reset zoom anymore!")
    else:
        print(f"❌ FAILURE: Zoom changed to {final_duration} seconds (expected 2.5)")
        print("❌ Click-drag operations still reset zoom")
    
    viewer.close()
    
    print("\n" + "="*60)
    print("CLICK-DRAG TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    print("Click-Drag Zoom Preservation Test")
    print("This tests whether click-drag operations (channel reorder, annotations) preserve zoom.")
    
    # Apply tracking patches
    patch_drag_tracking()
    
    # Run the test
    test_click_drag_zoom_preservation()