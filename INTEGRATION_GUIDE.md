# 🚀 Gaze Tracking Integration & Testing Guide

## 📋 **Phase-by-Phase Integration Steps**

### **Step 1: Basic Integration Check**

Run this to ensure all components are properly imported:

```bash
python test_integration.py
```

### **Step 2: Add Gaze Menu to EDFViewer**

Add this method to your `EDFViewer` class in `main.py`:

```python
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
```

### **Step 3: Add Gaze Tracking Methods**

Add these methods to your `EDFViewer` class:

```python
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
        self.gaze_overlay = GazeOverlay()
        self.feedback_system = FeedbackSystem()
        
        # Configure components
        self.gaze_tracker.configure(config)
        self.gaze_processor.configure(config)
        self.gaze_annotator.configure(config)
        
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
        if self.gaze_overlay:
            self.gaze_overlay.update_fixation(fixation_data)
        
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
            plot_bounds = self.plot_widget.getViewBox().screenGeometry()
            
            self.gaze_annotator.set_display_context(
                channels, time_range, plot_bounds.toDict(), 
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
        
        layout = QVBoxLayout()
        
        # Add metrics display
        metrics_text = f"""
        Review Speed: {metrics.review_speed:.1f} windows/min
        Annotation Rate: {metrics.annotation_rate:.1f} annotations/min
        Fixation Quality: {metrics.fixation_quality:.2f}
        Channel Coverage: {metrics.channel_coverage:.1%}
        Efficiency Score: {metrics.efficiency_score:.2f}
        """
        
        text_widget = QTextEdit()
        text_widget.setPlainText(metrics_text)
        text_widget.setReadOnly(True)
        layout.addWidget(text_widget)
        
        # Add statistics from annotator
        if self.gaze_annotator:
            stats = self.gaze_annotator.get_statistics()
            stats_text = f"""
            
        Annotation Statistics:
        Fixations Analyzed: {stats['fixations_analyzed']}
        Annotations Created: {stats['annotations_created']}
        Success Rate: {stats['success_rate']:.1%}
        """
            text_widget.append(stats_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()
        
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to show analytics: {e}")
```

### **Step 4: Update setup_menus() Method**

In your `setup_menus()` method, add:

```python
# Add this line at the end of setup_menus()
self.setup_gaze_menu()
```

## 🧪 **Testing Guide**

### **Method 1: Mock Testing (No Hardware Required)**

Create and run this test script:

```bash
python test_integration.py
```

This will test:
- ✅ All component imports
- ✅ Mock gaze data processing
- ✅ Annotation creation
- ✅ Enhanced auto-scroll
- ✅ Analytics generation

### **Method 2: Live Testing with Real Data**

1. **Load EDF File:**
   ```
   File → Open EDF/BDF → Select your test file
   ```

2. **Setup Gaze Tracking:**
   ```
   Gaze → Setup Gaze Tracking
   - Choose "Mock Eye Tracker" for testing
   - Configure settings and click OK
   ```

3. **Test Basic Gaze Mode:**
   ```
   Gaze → Toggle Gaze Mode (Ctrl+Shift+G)
   - Move mouse around the EEG plot
   - Should see gaze cursor and feedback
   ```

4. **Test Enhanced Auto-Scroll:**
   ```
   Gaze → Enhanced Auto-Scroll (Ctrl+Shift+A)
   - Should start intelligent scrolling
   - Will pause on "fixations" (when mouse stops)
   - Resumes automatically after delay
   ```

5. **Test Analytics:**
   ```
   Gaze → View Analytics
   - Shows behavior metrics and statistics
   ```

### **Method 3: Hardware Testing (Tobii/SR Research)**

1. **Install eye tracker drivers**
2. **Update tracker_config in GazeModeSetupDialog:**
   ```python
   # Change from 'mock' to your tracker type
   tracker_config['tracker_type'] = 'tobii'  # or 'sr_research'
   ```
3. **Follow calibration procedures**
4. **Test with real eye movements**

## 🔧 **Troubleshooting**

### Common Issues:

**Import Errors:**
```bash
# Run this to check imports:
python -c "from gaze_tracking.gaze_tracker import GazeTracker; print('✓ Imports OK')"
```

**Qt Application Errors:**
```bash
# Ensure PyQt6 is installed:
pip install PyQt6
```

**Performance Issues:**
- Reduce `max_fixations_stored` in FixationDetector
- Increase `min_fixation_duration` to reduce false positives
- Disable audio feedback if causing lag

**Missing Dependencies:**
```bash
pip install numpy scipy pyqtgraph PyQt6
```

## 📊 **Performance Monitoring**

The system includes built-in performance monitoring:

- **FPS tracking** in gaze processor
- **Memory usage** monitoring
- **Cache hit rates** for data access
- **Processing latency** measurements

Check the status bar for real-time performance metrics.

## 🎯 **What to Test**

### Core Functionality:
- [ ] Gaze cursor follows eye/mouse movements
- [ ] Fixations are detected correctly
- [ ] Annotations are created from fixations
- [ ] Enhanced auto-scroll pauses and resumes
- [ ] Analytics show meaningful data

### Integration:
- [ ] Works with existing EDF viewer features
- [ ] Annotations appear in annotation manager
- [ ] Performance remains smooth
- [ ] No crashes or freezes

### User Experience:
- [ ] Setup dialog is intuitive
- [ ] Visual feedback is clear
- [ ] Audio feedback works (if enabled)
- [ ] Keyboard shortcuts work
- [ ] Menu items are responsive

## 🚀 **Next Steps**

Once basic integration is working:

1. **Phase 5: Review & Management**
   - Batch annotation review
   - Quality scoring display
   - Export/import functionality

2. **Performance Optimization**
   - Profile bottlenecks
   - Optimize rendering
   - Tune detection parameters

3. **Clinical Validation**
   - Test with neurologists
   - Validate annotation accuracy
   - Gather user feedback

## 📝 **Configuration Tips**

### For Fast Review:
```python
config = {
    'min_fixation_duration': 0.3,  # Shorter fixations
    'auto_create_annotations': True,
    'pause_on_fixation': True,
    'auto_resume_delay': 1.5  # Quick resume
}
```

### For Detailed Analysis:
```python
config = {
    'min_fixation_duration': 0.8,  # Longer fixations
    'min_quality_threshold': AnnotationQuality.MEDIUM,
    'pause_on_fixation': True,
    'auto_resume_delay': 3.0  # More time to review
}
```

### For Training Mode:
```python
config = {
    'auto_create_annotations': False,  # Manual creation
    'show_confidence_feedback': True,
    'audio_feedback_enabled': True
}
```