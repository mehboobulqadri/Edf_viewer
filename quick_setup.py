#!/usr/bin/env python3
"""
Quick setup script for gaze tracking integration.

This script automatically patches the main EDF viewer with gaze tracking
functionality. Run this to quickly integrate everything.
"""

import sys
import os
from pathlib import Path

def patch_main_edf_viewer():
    """Automatically patch the main EDF viewer with gaze tracking."""
    
    main_py_path = Path("src/main.py")
    if not main_py_path.exists():
        print("❌ Error: src/main.py not found!")
        print("   Please run this script from the Edf_viewer root directory.")
        return False
    
    print("🔧 Patching main EDF viewer...")
    
    # Read the current file
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already patched
    if "setup_gaze_menu" in content:
        print("✅ File already patched!")
        return True
    
    # Add gaze tracking methods before the last class definition
    gaze_methods = '''
    def setup_gaze_menu(self):
        """Setup gaze tracking menu items."""
        if not GAZE_TRACKING_AVAILABLE:
            return
        
        # Add Gaze menu
        gaze_menu = self.menuBar().addMenu("&Gaze")
        
        # Setup Gaze Tracking action
        setup_action = QAction("&Setup Gaze Tracking", self)
        setup_action.setShortcut("Ctrl+G")
        setup_action.triggered.connect(self.setup_gaze_tracking)
        gaze_menu.addAction(setup_action)
        
        # Toggle Gaze Mode action
        self.toggle_gaze_action = QAction("&Toggle Gaze Mode", self)
        self.toggle_gaze_action.setShortcut("Ctrl+Shift+G")
        self.toggle_gaze_action.setEnabled(False)
        self.toggle_gaze_action.triggered.connect(self.toggle_gaze_mode)
        gaze_menu.addAction(self.toggle_gaze_action)
        
        gaze_menu.addSeparator()
        
        # Enhanced Auto-Move action
        self.enhanced_auto_move_action = QAction("&Enhanced Auto-Scroll", self)
        self.enhanced_auto_move_action.setShortcut("Ctrl+Shift+A")
        self.enhanced_auto_move_action.setEnabled(False)
        self.enhanced_auto_move_action.triggered.connect(self.toggle_enhanced_auto_move)
        gaze_menu.addAction(self.enhanced_auto_move_action)
        
        # Analytics action
        analytics_action = QAction("&View Analytics", self)
        analytics_action.triggered.connect(self.show_gaze_analytics)
        gaze_menu.addAction(analytics_action)

    def setup_gaze_tracking(self):
        """Setup gaze tracking system."""
        if not GAZE_TRACKING_AVAILABLE:
            QMessageBox.warning(self, "Warning", "Gaze tracking components not available!")
            return
        
        try:
            dialog = GazeModeSetupDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                config = dialog.get_configuration()
                self.initialize_gaze_system(config)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to setup gaze tracking: {e}")

    def initialize_gaze_system(self, config):
        """Initialize complete gaze tracking system."""
        try:
            # Initialize core components
            self.gaze_tracker = GazeTracker()
            self.gaze_processor = GazeProcessor()
            self.context_analyzer = ContextAnalyzer()
            self.behavior_analyzer = BehaviorAnalyzer()
            
            # Initialize gaze annotator with annotation manager
            self.gaze_annotator = GazeAnnotator(self.annotation_manager)
            
            # Initialize enhanced auto-move
            self.enhanced_auto_move = GazeEnhancedAutoMove(self)
            self.enhanced_auto_move.connect_to_original_auto_move(self.toggle_auto_move)
            
            # Initialize visual components
            self.gaze_overlay_manager = GazeOverlayManager()
            self.feedback_system = FeedbackSystem()
            
            # Configure components
            self.gaze_processor.configure(config)
            self.gaze_annotator.configure(config)
            
            # Connect tracker to processor
            self.gaze_processor.set_gaze_tracker(self.gaze_tracker)
            
            # Connect signals
            self.connect_gaze_signals()
            
            # Enable gaze actions
            self.toggle_gaze_action.setEnabled(True)
            self.enhanced_auto_move_action.setEnabled(True)
            
            self.statusBar().showMessage("Gaze tracking system initialized successfully", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize gaze system: {e}")

    def connect_gaze_signals(self):
        """Connect all gaze tracking signals."""
        # Gaze tracker to processor
        self.gaze_tracker.gaze_data_received.connect(self.gaze_processor.process_gaze_point)
        
        # Processor to annotator
        self.gaze_processor.fixation_detected.connect(self.handle_fixation_detected)
        
        # Enhanced auto-move signals
        self.enhanced_auto_move.scroll_paused.connect(self.on_scroll_paused)
        self.enhanced_auto_move.scroll_resumed.connect(self.on_scroll_resumed)
        self.enhanced_auto_move.progress_updated.connect(self.on_progress_updated)

    def handle_fixation_detected(self, fixation_data):
        """Handle detected fixation."""
        if not self.gaze_mode_active:
            return
        
        try:
            # Get EEG context if data is loaded
            eeg_context = None
            if self.raw is not None:
                # Extract EEG data around fixation
                time_point = fixation_data.get('timestamp', 0)
                channel_idx = fixation_data.get('channel_idx', 0)
                
                # Analyze EEG context
                eeg_data = self.raw.get_data()
                eeg_context = self.context_analyzer.analyze_fixation_context(
                    eeg_data, time_point, channel_idx, 
                    self.raw.ch_names[channel_idx] if channel_idx < len(self.raw.ch_names) else 'Unknown'
                )
            
            # Process fixation with annotator
            annotation_created = self.gaze_annotator.process_fixation(fixation_data, eeg_context)
            
            # Handle enhanced auto-move
            if self.enhanced_auto_move and hasattr(self.enhanced_auto_move, 'handle_fixation_detected'):
                context = {'eeg_interest_score': eeg_context.clinical_significance if eeg_context else 0.5}
                self.enhanced_auto_move.handle_fixation_detected(fixation_data, context)
            
            # Update overlay and feedback
            if self.gaze_overlay_manager:
                # Note: Update method would need to be implemented in GazeOverlayManager
                pass
            
            if self.feedback_system and annotation_created:
                self.feedback_system.play_annotation_created_sound()
                
        except Exception as e:
            print(f"Error handling fixation: {e}")

    def toggle_gaze_mode(self):
        """Toggle gaze tracking mode."""
        if not self.gaze_tracker:
            QMessageBox.warning(self, "Warning", "Gaze tracking not initialized!")
            return
        
        self.gaze_mode_active = not self.gaze_mode_active
        
        if self.gaze_mode_active:
            self.start_gaze_tracking()
        else:
            self.stop_gaze_tracking()

    def start_gaze_tracking(self):
        """Start gaze tracking."""
        try:
            self.gaze_tracker.start_tracking()
            self.behavior_analyzer.start_session()
            
            # Set display context for annotator
            if self.raw and self.gaze_annotator:
                channels = self.raw.ch_names
                time_range = (self.view_start_time, self.view_start_time + self.view_duration)
                plot_bounds = {'x': 0, 'y': 0, 'width': 800, 'height': 600}  # Default bounds
                
                self.gaze_annotator.set_display_context(
                    channels, time_range, plot_bounds, 
                    50, self.raw.info['sfreq']  # channel_height, sampling_rate
                )
            
            self.statusBar().showMessage("Gaze tracking started", 2000)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start gaze tracking: {e}")
            self.gaze_mode_active = False

    def stop_gaze_tracking(self):
        """Stop gaze tracking."""
        try:
            if self.gaze_tracker:
                self.gaze_tracker.stop_tracking()
            
            self.statusBar().showMessage("Gaze tracking stopped", 2000)
            
        except Exception as e:
            print(f"Error stopping gaze tracking: {e}")

    def toggle_enhanced_auto_move(self):
        """Toggle enhanced auto-scroll with gaze awareness."""
        if not self.enhanced_auto_move:
            QMessageBox.warning(self, "Warning", "Enhanced auto-move not initialized!")
            return
        
        if not self.raw:
            QMessageBox.warning(self, "Warning", "No EDF data loaded!")
            return
        
        state = self.enhanced_auto_move.get_current_state()
        
        if state.value == 'stopped':
            # Start enhanced auto-scroll
            total_duration = self.raw.times[-1]
            self.enhanced_auto_move.start_enhanced_scroll(total_duration, self.view_duration)
        else:
            # Stop enhanced auto-scroll
            self.enhanced_auto_move.stop_enhanced_scroll()

    def on_scroll_paused(self, reason):
        """Handle scroll pause."""
        self.statusBar().showMessage(f"Auto-scroll paused: {reason}", 5000)

    def on_scroll_resumed(self):
        """Handle scroll resume."""
        self.statusBar().showMessage("Auto-scroll resumed", 2000)

    def on_progress_updated(self, progress_data):
        """Handle progress updates."""
        completion = progress_data.get('completion_percentage', 0)
        self.statusBar().showMessage(f"Review progress: {completion:.1f}%", 1000)

    def show_gaze_analytics(self):
        """Show gaze tracking analytics."""
        if not self.behavior_analyzer:
            QMessageBox.warning(self, "Warning", "Analytics not available!")
            return
        
        try:
            metrics = self.behavior_analyzer.analyze_behavior()
            
            # Create analytics dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Gaze Analytics")
            dialog.setModal(True)
            dialog.resize(400, 300)
            
            layout = QVBoxLayout()
            
            # Add metrics display
            metrics_text = f"""Review Speed: {metrics.review_speed:.1f} windows/min
Annotation Rate: {metrics.annotation_rate:.1f} annotations/min
Fixation Quality: {metrics.fixation_quality:.2f}
Channel Coverage: {metrics.channel_coverage:.1%}
Efficiency Score: {metrics.efficiency_score:.2f}"""
            
            if self.gaze_annotator:
                stats = self.gaze_annotator.get_statistics()
                metrics_text += f"""

Annotation Statistics:
Fixations Analyzed: {stats['fixations_analyzed']}
Annotations Created: {stats['annotations_created']}
Success Rate: {stats['success_rate']:.1%}"""
            
            text_widget = QTextEdit()
            text_widget.setPlainText(metrics_text)
            text_widget.setReadOnly(True)
            layout.addWidget(text_widget)
            
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)
            
            dialog.setLayout(layout)
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show analytics: {e}")
'''
    
    # Find where to insert the methods (before the last few lines)
    lines = content.split('\n')
    
    # Find the setup_menus method and add gaze menu call
    setup_menus_found = False
    for i, line in enumerate(lines):
        if "def setup_menus(self):" in line:
            # Find the end of this method and add gaze menu setup
            j = i + 1
            indent_level = len(line) - len(line.lstrip())
            while j < len(lines) and (lines[j].strip() == '' or len(lines[j]) - len(lines[j].lstrip()) > indent_level):
                j += 1
            
            # Insert gaze menu setup before the next method
            lines.insert(j, f"{' ' * (indent_level + 4)}self.setup_gaze_menu()")
            setup_menus_found = True
            break
    
    if not setup_menus_found:
        print("⚠️ Could not find setup_menus method. You'll need to add self.setup_gaze_menu() manually.")
    
    # Find where to insert the gaze methods (before the main execution block)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith('if __name__ == "__main__"'):
            # Insert methods before this line
            method_lines = gaze_methods.strip().split('\n')
            for method_line in reversed(method_lines):
                lines.insert(i, method_line)
            break
    
    # Write the patched file
    patched_content = '\n'.join(lines)
    
    # Create backup
    backup_path = main_py_path.with_suffix('.py.backup')
    if not backup_path.exists():
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Backup created: {backup_path}")
    
    # Write patched file
    with open(main_py_path, 'w', encoding='utf-8') as f:
        f.write(patched_content)
    
    print("✅ Main EDF viewer patched successfully!")
    return True

def run_setup():
    """Run the complete setup process."""
    print("🚀 GAZE TRACKING QUICK SETUP")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not Path("src").exists():
        print("❌ Error: Please run this script from the Edf_viewer root directory.")
        return False
    
    # Check if components exist
    required_files = [
        "src/gaze_tracking/gaze_tracker.py",
        "src/gaze_tracking/gaze_processor.py",
        "src/gaze_tracking/gaze_annotator.py",
        "src/gaze_tracking/gaze_enhanced_auto_move.py",
        "src/ui/gaze_overlay.py",
        "src/ui/feedback_system.py",
        "src/utils/gaze_analytics.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print("\nPlease ensure all gaze tracking components are properly installed.")
        return False
    
    print("✅ All required components found")
    
    # Patch main file
    if not patch_main_edf_viewer():
        return False
    
    # Run integration test
    print("\n🧪 Running integration test...")
    try:
        import subprocess
        result = subprocess.run([sys.executable, "test_integration.py"], 
                              capture_output=True, text=True, cwd=".")
        
        if result.returncode == 0:
            print("✅ Integration test passed!")
        else:
            print("⚠️ Integration test had issues:")
            print(result.stdout[-500:])  # Show last 500 chars
    except Exception as e:
        print(f"⚠️ Could not run integration test: {e}")
    
    print("\n🎉 SETUP COMPLETE!")
    print("\nNext steps:")
    print("1. Run your EDF viewer: python src/main.py")
    print("2. Open an EDF file")
    print("3. Go to Gaze → Setup Gaze Tracking")
    print("4. Choose 'Mock Eye Tracker' for testing")
    print("5. Try Gaze → Toggle Gaze Mode")
    print("\nFor help, see INTEGRATION_GUIDE.md")
    
    return True

if __name__ == "__main__":
    success = run_setup()
    sys.exit(0 if success else 1)