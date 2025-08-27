# **Gaze-Based Annotation System Implementation Plan**

## **📋 Project Overview**

### **Objective**

Implement a comprehensive gaze-based annotation system for EEG/EDF data review that allows clinicians to annotate abnormalities hands-free using eye tracking technology.

### **Core Requirements**

1. **Gaze Annotation Mode**: Dedicated mode within existing EDF viewer
2. **Auto-Scrolling Review**: Highlight window moves through EEG data automatically
3. **Fixation-Based Annotation**: Automatic annotation when user focuses on abnormalities
4. **Channel Highlighting**: Use existing channel highlight system for annotations
5. **Review & Edit Interface**: Allow user to accept/reject generated annotations
6. **Separate Calibration Tool**: Standalone calibration software for hardware setup
7. **Modular Design**: Keep main.py intact with separate modules

### **Hardware Requirements**

- **Tobii Spark Eye Tracker**: Primary hardware for gaze detection
- **Windows 10/11**: Operating system compatibility
- **Python 3.8+**: Runtime environment
- **Tobii Pro SDK**: Software development kit

---

## **🏗️ Architecture Overview**

### **File Structure**

```
src/
├── main.py                           # Original - MINIMAL CHANGES
├── gaze_tracking/                    # Core gaze functionality
│   ├── __init__.py
│   ├── gaze_tracker.py              # Tobii hardware interface
│   ├── coordinate_mapper.py         # Screen/EDF coordinate mapping
│   ├── fixation_detector.py         # Gaze analysis algorithms
│   ├── gaze_annotator.py            # Annotation creation logic
│   └── gaze_processor_thread.py     # Real-time processing thread
├── ui/                              # User interface extensions
│   ├── __init__.py
│   ├── gaze_mode_dialog.py          # Mode setup and configuration
│   ├── gaze_overlay.py              # Visual gaze feedback
│   ├── annotation_review_dialog.py  # Review generated annotations
│   └── gaze_status_widget.py        # Real-time status display
├── utils/                           # Utilities and helpers
│   ├── __init__.py
│   ├── gaze_data_processor.py       # Data filtering and smoothing
│   ├── gaze_config.py               # Configuration management
│   └── gaze_analytics.py            # Statistics and analysis
└── calibration_tool/                # Separate calibration application
    ├── __init__.py
    ├── calibration_main.py          # Main calibration application
    ├── calibration_ui.py            # Calibration interface
    └── calibration_storage.py       # Calibration data management
```

### **Integration Points with Existing System**

- **AnnotationManager**: Use existing annotation system
- **Auto-move functionality**: Extend existing auto-scroll
- **Channel highlighting**: Use existing highlight system
- **Performance monitoring**: Integrate with existing performance manager

---

## **📋 Detailed Implementation Phases**

## **Phase 1: Foundation & Hardware Integration (Week 1-2)**

### **Objectives**

- Establish Tobii Spark hardware connection
- Create basic gaze data streaming
- Implement coordinate mapping foundation
- Test hardware integration without affecting main application

### **1.1 Core Gaze Tracker Interface**

**File: `src/gaze_tracking/gaze_tracker.py`**

```python
"""
Core interface to Tobii Spark eye tracking hardware.
Handles connection, data streaming, and basic gaze data processing.
"""

Key Features:
- Hardware discovery and connection
- Real-time gaze data streaming
- Connection status monitoring
- Error handling and recovery
- PyQt6 signal integration for thread-safe communication

Main Classes:
- GazeTracker: Primary hardware interface
- GazeDataCallback: Data processing callback system
```

**Implementation Details:**

- Uses Tobii Pro SDK for hardware communication
- Implements PyQt6 signals for UI integration
- Automatic hardware discovery and connection
- Robust error handling for hardware disconnections
- Configurable streaming parameters (frequency, data types)

### **1.2 Coordinate Mapping System**

**File: `src/gaze_tracking/coordinate_mapper.py`**

```python
"""
Maps gaze coordinates between different coordinate systems:
Tobii normalized (0-1) → Screen pixels → Widget coordinates → EDF time/channel
"""

Key Features:
- Multi-stage coordinate transformation
- Calibration offset support
- Boundary validation
- EDF time and channel identification
- Real-time coordinate conversion

Main Classes:
- CoordinateMapper: Core mapping functionality
- CalibrationData: Calibration offset storage
- CoordinateBounds: Validation and bounds checking
```

**Implementation Details:**

- Chain transformation: Tobii → Screen → Widget → EDF coordinates
- Support for multi-monitor setups
- Calibration offset integration
- Channel identification based on Y-coordinate mapping
- Time identification based on X-coordinate and current view window

### **1.3 Basic Integration with Main Application**

**File: `src/main.py` - Minimal Changes**

```python
# Add imports (only addition to main.py)
from gaze_tracking import GazeTracker
from ui.gaze_mode_dialog import GazeModeSetupDialog

# Add to EDFViewer.__init__() (minimal addition)
self.gaze_tracker = None
self.gaze_mode_active = False

# Add menu item (minimal addition)
def setup_gaze_menu(self):
    gaze_menu = self.menuBar().addMenu('Gaze Tracking')
    start_gaze_action = QAction('Start Gaze Annotation Mode', self)
    start_gaze_action.triggered.connect(self.show_gaze_mode_dialog)
    gaze_menu.addAction(start_gaze_action)
```

### **Testing Phase 1**

- [ ] Tobii Spark hardware detection and connection
- [ ] Basic gaze data streaming at 30+ FPS
- [ ] Coordinate mapping accuracy (±50 pixels)
- [ ] Integration with existing EDFViewer without breaking functionality
- [ ] Error handling for hardware connection issues
- [ ] Memory usage remains stable during gaze streaming

---

## **Phase 2: Gaze Data Processing & Fixation Detection (Week 3-4)**

### **Objectives**

- Implement real-time gaze data processing
- Create robust fixation detection algorithms
- Establish smooth gaze position tracking
- Build processing thread for real-time performance

### **2.1 Gaze Data Processing Pipeline**

**File: `src/utils/gaze_data_processor.py`**

```python
"""
Advanced gaze data processing with multiple filtering stages:
1. Confidence filtering (remove low-quality data)
2. Kalman filtering (smooth trajectories)
3. Median filtering (remove noise spikes)
4. Outlier detection (identify and remove extreme values)
"""

Key Features:
- Multi-stage filtering pipeline
- Configurable filter parameters
- Real-time processing statistics
- Adaptive filtering based on data quality
- Circular buffer management for memory efficiency

Main Classes:
- GazeDataProcessor: Main processing pipeline
- KalmanFilter: Trajectory smoothing
- MedianFilter: Noise reduction
- ConfidenceFilter: Quality-based filtering
- OutlierDetector: Statistical outlier removal
```

**Implementation Details:**

- Process raw Tobii gaze data in real-time
- Apply confidence thresholding (>70% confidence required)
- Smooth gaze trajectories using Kalman filtering
- Remove noise using median filtering (5-point window)
- Detect and remove statistical outliers (2-sigma rule)
- Maintain processing statistics for performance monitoring

### **2.2 Fixation Detection Algorithm**

**File: `src/gaze_tracking/fixation_detector.py`**

```python
"""
Dispersion-based fixation detection optimized for EEG review:
- Configurable spatial and temporal thresholds
- Real-time fixation progress tracking
- Support for different fixation types (micro, macro)
- Integration with EDF viewer coordinate system
"""

Key Features:
- Dispersion-based detection algorithm
- Configurable thresholds (spatial: 50px, temporal: 1000ms)
- Real-time progress tracking
- Fixation quality assessment
- Multi-level fixation classification

Main Classes:
- FixationDetector: Core detection algorithm
- Fixation: Data structure for fixation information
- FixationProgress: Real-time progress tracking
- FixationStatistics: Analysis and metrics
```

**Implementation Details:**

- Use dispersion-based algorithm (more robust for clinical use)
- Default thresholds: 50 pixels spatial, 1000ms temporal
- Real-time progress indication for user feedback
- Quality scoring based on stability and duration
- Support for micro-fixations (<500ms) and macro-fixations (>1000ms)

### **2.3 Real-time Processing Thread**

**File: `src/gaze_tracking/gaze_processor_thread.py`**

```python
"""
Dedicated thread for gaze data processing to maintain UI responsiveness:
- Asynchronous gaze data processing
- Thread-safe communication with UI
- Performance monitoring and optimization
- Error recovery and exception handling
"""

Key Features:
- Separate thread for processing (no UI blocking)
- Thread-safe queue-based communication
- Configurable processing rates
- Performance monitoring
- Automatic error recovery

Main Classes:
- GazeProcessingThread: Main processing thread
- ThreadSafeQueue: Safe data communication
- ProcessingMonitor: Performance tracking
- ErrorRecovery: Exception handling and recovery
```

**Implementation Details:**

- Process gaze data at 60+ FPS without blocking UI
- Use thread-safe queues for data communication
- Monitor processing performance and adapt rates
- Implement graceful error recovery for hardware issues
- Provide real-time statistics to UI

### **Testing Phase 2**

- [ ] Smooth gaze tracking with <50ms latency
- [ ] Accurate fixation detection (>90% accuracy)
- [ ] Real-time processing maintains UI responsiveness
- [ ] Processing statistics show stable performance
- [ ] Error recovery works for hardware disconnections
- [ ] Memory usage remains constant during extended use

---

## **Phase 3: Gaze Annotation Mode UI (Week 5-6)**

### **Objectives**

- Create gaze mode setup dialog
- Implement visual gaze feedback overlay
- Build gaze status monitoring widget
- Integrate with existing UI without modifications

### **3.1 Gaze Mode Setup Dialog**

**File: `src/ui/gaze_mode_dialog.py`**

```python
"""
Comprehensive setup dialog for gaze annotation mode:
- Display settings (zoom, channels, sensitivity)
- Gaze detection parameters (fixation thresholds, accuracy)
- Auto-scroll configuration (speed, pause behavior)
- Annotation settings (categories, triggers)
- Visual feedback options
"""

Key Features:
- Intuitive configuration interface
- Real-time parameter validation
- Hardware connection testing
- Configuration persistence
- Integration with existing EDF viewer settings

Dialog Sections:
1. Display Settings: Time scale, channel count, sensitivity
2. Gaze Detection: Fixation duration, spatial accuracy, confidence
3. Auto-Scroll: Enable/disable, speed, pause on fixation
4. Annotations: Default categories, duration, trigger mode
5. Visual Feedback: Cursor, progress indicators, highlights

Configuration Options:
- Time Scale: 5s, 10s, 15s, 20s, 30s, 1m
- Channels: 5, 8, 10, 12, 15, 20, All
- Fixation Duration: 0.5-5.0 seconds (default: 1.0s)
- Spatial Accuracy: 20-100 pixels (default: 50px)
- Auto-scroll Speed: 0.5-10.0 seconds per window (default: 2.0s)
```

**Implementation Details:**

- Modal dialog with tabbed interface for organization
- Real-time validation of all parameters
- Test button for hardware connection verification
- Load current EDF viewer settings as defaults
- Save/load configuration profiles
- Comprehensive help tooltips for all options

### **3.2 Visual Gaze Feedback System**

**File: `src/ui/gaze_overlay.py`**

```python
"""
Real-time visual feedback system for gaze tracking:
- Gaze cursor showing current eye position
- Fixation progress indicators
- Annotation previews
- Highlight overlays for detected regions
"""

Key Features:
- Real-time gaze cursor with confidence indication
- Circular progress indicator for fixation detection
- Preview overlays for pending annotations
- Integration with PyQtGraph plotting system
- Configurable visual styles and colors

Visual Elements:
- Gaze Cursor: Small circle following eye position
- Progress Ring: Animated ring showing fixation progress
- Annotation Preview: Highlight showing annotation area
- Confidence Indicator: Color-coded gaze quality feedback
- Status Icons: Connection status, calibration quality
```

**Implementation Details:**

- Use PyQtGraph overlay system for performance
- Update at 20-30 FPS for smooth visual feedback
- Color-coded elements (blue=gaze, yellow=progress, green=annotation)
- Configurable transparency and size settings
- Automatic hiding when gaze quality is poor

### **3.3 Gaze Status Widget**

**File: `src/ui/gaze_status_widget.py`**

```python
"""
Real-time status display for gaze tracking system:
- Connection status and hardware information
- Processing statistics and performance metrics
- Current fixation information
- Annotation count and progress
"""

Key Features:
- Compact status display integrated into main UI
- Real-time updates without performance impact
- Color-coded status indicators
- Expandable detailed information
- Performance warnings and alerts

Status Information:
- Hardware: Connection status, device name, calibration quality
- Processing: FPS, latency, queue size, error rate
- Fixations: Current progress, recent count, average duration
- Annotations: Generated count, review pending, accuracy metrics
```

**Implementation Details:**

- Integrate into existing EDFViewer status bar
- Update every 1-2 seconds to avoid UI clutter
- Use icons and colors for quick status recognition
- Expandable details on hover or click
- Warning indicators for performance issues

### **Testing Phase 3**

- [ ] Setup dialog validates all parameters correctly
- [ ] Visual feedback is smooth and responsive
- [ ] Status widget provides accurate real-time information
- [ ] UI integration doesn't affect existing functionality
- [ ] Configuration persistence works correctly
- [ ] Hardware testing feature works reliably

---

## **Phase 4: Core Gaze Annotation Logic (Week 7-8)**

### **Objectives**

- Implement gaze-based annotation creation
- Integrate with existing annotation system
- Create auto-scrolling review mode
- Build annotation quality assessment

### **4.1 Gaze Annotation Engine**

**File: `src/gaze_tracking/gaze_annotator.py`**

```python
"""
Core logic for creating annotations based on gaze fixations:
- Fixation analysis and validation
- EDF coordinate mapping and validation
- Integration with existing AnnotationManager
- Annotation quality scoring and filtering
"""

Key Features:
- Automatic annotation creation from fixations
- Integration with existing annotation system
- Quality scoring and filtering
- Channel-specific annotation logic
- Time window validation and adjustment

Main Classes:
- GazeAnnotator: Core annotation creation logic
- FixationAnalyzer: Analyze fixation patterns for annotation worthiness
- AnnotationQuality: Quality assessment and scoring
- ChannelMapper: Map gaze coordinates to specific EEG channels
- TimeWindowValidator: Ensure annotations are within valid data ranges

Annotation Creation Process:
1. Receive fixation from detector
2. Map coordinates to EDF time/channel
3. Validate data quality and bounds
4. Assess annotation worthiness
5. Create annotation via existing system
6. Track annotation for later review
```

**Implementation Details:**

- Use existing AnnotationManager for all annotation operations
- Create annotations with metadata (gaze-generated, confidence score)
- Implement quality scoring based on fixation stability and duration
- Support different annotation categories based on EEG context
- Validate all coordinates are within loaded EDF data bounds

### **4.2 Enhanced Auto-Move Integration**

**File: `src/gaze_tracking/gaze_enhanced_auto_move.py`**

```python
"""
Enhancement to existing auto-move functionality:
- Gaze-aware scrolling (pause on fixations)
- Configurable scroll speeds and behaviors
- Integration with fixation detection
- Smart pause logic for annotation opportunities
"""

Key Features:
- Extends existing auto-move system
- Pause scrolling during active fixations
- Configurable pause durations and thresholds
- Resume scrolling after annotation completion
- Progress tracking through entire EDF

Main Classes:
- GazeEnhancedAutoMove: Enhanced auto-scroll controller
- ScrollBehavior: Configurable scrolling behaviors
- PauseLogic: Smart pause decisions based on gaze patterns
- ProgressTracker: Track progress through EDF data

Auto-Scroll Behavior:
- Normal speed: 2-3 seconds per time window
- Pause on fixation: Stop when fixation detected
- Resume after annotation: Continue after annotation creation
- End-of-data handling: Show review dialog when complete
```

**Implementation Details:**

- Extend existing auto_move functionality in main.py
- Use signals to communicate with fixation detector
- Implement configurable pause thresholds and durations
- Track progress through entire EDF for completion detection
- Integrate with existing focus window and time navigation

### **4.3 Annotation Context Analysis**

**File: `src/utils/gaze_analytics.py`**

```python
"""
Advanced analysis of gaze patterns for improved annotation:
- EEG context awareness (detect common abnormality patterns)
- Fixation pattern analysis
- Annotation confidence scoring
- Statistical analysis of review patterns
"""

Key Features:
- EEG-aware annotation suggestions
- Pattern recognition for common abnormalities
- User behavior analysis and adaptation
- Statistical confidence scoring
- Review efficiency metrics

Main Classes:
- ContextAnalyzer: Analyze EEG context around fixations
- PatternRecognizer: Identify common abnormality patterns
- ConfidenceScorer: Score annotation confidence
- BehaviorAnalyzer: Analyze user review patterns
- EfficiencyMetrics: Track review efficiency and accuracy

Context Analysis Features:
- Spike detection context
- Seizure pattern recognition
- Artifact identification
- Channel correlation analysis
- Temporal pattern analysis
```

**Implementation Details:**

- Analyze EEG data around fixation points
- Use statistical methods to identify abnormality patterns
- Score annotations based on EEG context and fixation quality
- Track user behavior patterns for system adaptation
- Provide efficiency metrics for workflow optimization

### **Testing Phase 4**

- [ ] Annotations created accurately from fixations
- [ ] Integration with existing annotation system works
- [ ] Auto-scroll pauses and resumes correctly
- [ ] Context analysis improves annotation quality
- [ ] Progress tracking through EDF works correctly
- [ ] Performance remains stable during annotation creation

---

## **Phase 5: Annotation Review & Management (Week 9-10)**

### **Objectives**

- Create comprehensive review interface
- Enable annotation editing and filtering
- Implement bulk operations for annotations
- Build export functionality for reviewed annotations

### **5.1 Annotation Review Dialog**

**File: `src/ui/annotation_review_dialog.py`**

```python
"""
Comprehensive review interface for gaze-generated annotations:
- List view of all generated annotations
- Preview of annotation locations in EDF data
- Accept/reject decisions for each annotation
- Bulk operations and filtering
- Edit annotation details (time, duration, description)
"""

Key Features:
- Comprehensive annotation list with previews
- Individual accept/reject decisions
- Bulk operations (accept all, reject all, filter)
- Annotation editing capabilities
- EDF data preview for context
- Statistics and quality metrics

Dialog Components:
1. Annotation List: Scrollable list with preview thumbnails
2. Detail Panel: Detailed view of selected annotation
3. EDF Preview: Mini-EDF view showing annotation context
4. Decision Buttons: Accept, reject, edit, bulk operations
5. Statistics Panel: Review progress and quality metrics

Review Features:
- Sort by time, confidence, channel, quality score
- Filter by channel, time range, confidence level
- Search annotations by description or metadata
- Batch operations with undo functionality
- Export selected annotations to various formats
```

**Implementation Details:**

- Modal dialog shown after gaze annotation mode completion
- List widget with custom items showing annotation previews
- Integrated mini-EDF viewer for annotation context
- Real-time statistics updates as decisions are made
- Support for keyboard shortcuts for efficient review
- Undo/redo functionality for decision changes

### **5.2 Enhanced Annotation Manager Integration**

**File: `src/gaze_tracking/annotation_manager_extension.py`**

```python
"""
Extensions to existing AnnotationManager for gaze-specific features:
- Gaze annotation tracking and metadata
- Quality scoring and filtering
- Batch operations and bulk editing
- Export enhancements with gaze metadata
"""

Key Features:
- Track gaze-generated vs manual annotations
- Store gaze metadata (fixation data, confidence scores)
- Batch operations for gaze annotations
- Enhanced export with gaze analytics
- Quality-based filtering and sorting

Extension Classes:
- GazeAnnotationTracker: Track gaze-specific metadata
- QualityManager: Manage annotation quality scores
- BatchOperations: Bulk operations on gaze annotations
- GazeExporter: Enhanced export with gaze data
- MetadataManager: Manage gaze-specific annotation metadata

Metadata Stored:
- Fixation duration and stability
- Gaze confidence scores
- EEG context analysis results
- User decision timestamps
- Review efficiency metrics
```

**Implementation Details:**

- Extend existing AnnotationManager without breaking changes
- Store gaze metadata in annotation custom fields
- Implement quality scoring based on multiple factors
- Create batch operation methods for efficient bulk editing
- Enhanced CSV export with gaze-specific columns

### **5.3 Annotation Statistics and Analytics**

**File: `src/utils/annotation_analytics.py`**

```python
"""
Comprehensive analytics for gaze annotation sessions:
- Review efficiency metrics
- Annotation accuracy analysis
- User behavior pattern analysis
- System performance optimization recommendations
"""

Key Features:
- Session-based analytics and reporting
- Efficiency metrics (annotations per minute, accuracy)
- Pattern analysis (common annotation locations, types)
- Performance recommendations
- Historical trend analysis

Analytics Components:
- Session Analytics: Per-session statistics and metrics
- Efficiency Tracker: Review speed and accuracy metrics
- Pattern Analyzer: Identify common annotation patterns
- Performance Monitor: System performance during review
- Trend Analysis: Historical data analysis and trends

Metrics Tracked:
- Total annotations generated vs accepted
- Average review time per annotation
- Most common annotation locations and types
- Fixation patterns and user behavior
- System performance during gaze sessions
```

**Implementation Details:**

- Collect analytics data during gaze annotation sessions
- Calculate efficiency metrics in real-time
- Store historical data for trend analysis
- Generate reports and recommendations
- Export analytics data for external analysis

### **Testing Phase 5**

- [ ] Review dialog shows all annotations correctly
- [ ] Accept/reject decisions work correctly
- [ ] Bulk operations function properly
- [ ] Annotation editing works without data loss
- [ ] Statistics and analytics provide useful insights
- [ ] Export functionality preserves all data

---

## **Phase 6: Integration & Polish (Week 11-12)**

### **Objectives**

- Complete integration with main application
- Performance optimization and testing
- Error handling and robustness
- Documentation and user guides

### **6.1 Main Application Integration**

**File: `src/main.py` - Final Integration**

```python
# Minimal additions to existing EDFViewer class

class EDFViewer(QMainWindow):
    def __init__(self):
        # ... existing initialization ...
        
        # Add gaze tracking components (minimal addition)
        self.gaze_tracker = None
        self.gaze_mode_active = False
        self.gaze_annotator = None
        self.gaze_overlay = None
        
        # Add to existing menu setup
        self.setup_gaze_menu()  # New method
    
    def setup_gaze_menu(self):
        """Add gaze tracking menu to existing menu bar"""
        gaze_menu = self.menuBar().addMenu('Gaze Tracking')
        
        start_action = QAction('Start Gaze Annotation Mode', self)
        start_action.triggered.connect(self.show_gaze_mode_dialog)
        gaze_menu.addAction(start_action)
        
        calibrate_action = QAction('Calibrate Eye Tracker', self)
        calibrate_action.triggered.connect(self.launch_calibration_tool)
        gaze_menu.addAction(calibrate_action)
    
    def show_gaze_mode_dialog(self):
        """Show gaze mode setup dialog"""
        if not self.raw:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return
        
        dialog = GazeModeSetupDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.start_gaze_annotation_mode(dialog.get_configuration())
    
    def start_gaze_annotation_mode(self, config):
        """Start gaze annotation mode with given configuration"""
        # Implementation will be added in this phase
        pass
    
    def launch_calibration_tool(self):
        """Launch separate calibration application"""
        # Implementation will be added in this phase
        pass
```

**Integration Requirements:**

- Minimal changes to main.py (only menu additions)
- All gaze functionality in separate modules
- No impact on existing functionality
- Clean integration with existing UI components

### **6.2 Performance Optimization**

**File: `src/utils/performance_optimizer.py`**

```python
"""
Performance optimization for gaze tracking system:
- Memory usage optimization
- Processing speed improvements
- GPU acceleration where applicable
- Resource management and cleanup
"""

Key Optimizations:
- Efficient memory management for gaze data buffers
- GPU acceleration for coordinate transformations
- Optimized filtering algorithms using NumPy/SciPy
- Smart resource allocation and cleanup
- Performance monitoring and automatic adjustments

Main Classes:
- MemoryManager: Efficient memory usage and cleanup
- ProcessingOptimizer: Speed improvements and algorithms
- GPUAccelerator: GPU-based processing where applicable
- ResourceManager: System resource monitoring and management
- PerformanceMonitor: Real-time performance tracking

Optimization Targets:
- <50ms latency for gaze position updates
- <100MB additional memory usage
- >60 FPS processing rate
- Stable performance over extended sessions
- Minimal impact on existing EDF viewer performance
```

**Implementation Details:**

- Profile existing performance bottlenecks
- Implement memory-efficient data structures
- Use vectorized operations where possible
- Cache frequently accessed data
- Clean up resources promptly

### **6.3 Error Handling and Robustness**

**File: `src/utils/error_handler.py`**

```python
"""
Comprehensive error handling for gaze tracking system:
- Hardware connection error handling
- Data processing error recovery
- UI error states and user feedback
- Automatic recovery mechanisms
"""

Key Features:
- Graceful hardware disconnection handling
- Data processing error recovery
- User-friendly error messages and guidance
- Automatic retry mechanisms
- System state recovery after errors

Error Handling Areas:
1. Hardware Errors: Connection failures, device not found
2. Processing Errors: Data corruption, processing failures
3. UI Errors: Dialog failures, display issues
4. Integration Errors: Annotation system failures
5. Performance Errors: Memory issues, processing slowdowns

Recovery Mechanisms:
- Automatic hardware reconnection
- Data processing queue recovery
- UI state restoration
- Graceful degradation of functionality
- User notification and guidance
```

**Implementation Details:**

- Implement try-catch blocks around all critical operations
- Create user-friendly error messages with solutions
- Automatic retry mechanisms with exponential backoff
- Fallback modes when hardware is unavailable
- Comprehensive logging for troubleshooting

### **6.4 Configuration Management**

**File: `src/utils/gaze_config.py`**

```python
"""
Centralized configuration management for gaze tracking system:
- Default configuration values
- User preference persistence
- Configuration validation
- Profile management for different use cases
"""

Configuration Categories:
1. Hardware Settings: Connection parameters, sampling rates
2. Detection Settings: Fixation thresholds, accuracy parameters
3. UI Settings: Visual feedback preferences, overlay settings
4. Performance Settings: Processing parameters, optimization settings
5. Export Settings: Default formats, metadata inclusion

Configuration Features:
- JSON-based configuration files
- User profile management
- Configuration validation and error checking
- Default value fallbacks
- Import/export configuration profiles
```

### **Testing Phase 6**

- [ ] Complete integration works without breaking existing features
- [ ] Performance meets all target metrics
- [ ] Error handling provides graceful recovery
- [ ] Configuration management works reliably
- [ ] System remains stable during extended use
- [ ] All features work together seamlessly

---

## **Phase 7: Calibration Tool (Week 13-14)**

### **Objectives**

- Create standalone calibration application
- Implement visual calibration interface
- Build calibration data storage and management
- Create calibration validation and testing

### **7.1 Standalone Calibration Application**

**File: `src/calibration_tool/calibration_main.py`**

```python
"""
Standalone calibration application for Tobii Spark eye tracker:
- Independent application separate from main EDF viewer
- Visual calibration interface with multiple calibration patterns
- Calibration validation and accuracy testing
- Calibration profile management and storage
"""

Key Features:
- Independent PyQt6 application
- Multiple calibration patterns (5-point, 9-point, custom)
- Real-time accuracy validation
- Profile management (save/load/delete)
- Integration with main application for profile loading

Application Structure:
- Main Window: Calibration interface and controls
- Calibration Canvas: Full-screen calibration display
- Accuracy Testing: Validation of calibration quality
- Profile Manager: Save/load calibration configurations
- Settings Dialog: Calibration parameters and preferences

Calibration Process:
1. Hardware connection and initialization
2. Calibration pattern selection and setup
3. Visual calibration point presentation
4. Gaze data collection and processing
5. Calibration calculation and validation
6. Accuracy testing and quality assessment
7. Profile saving and management
```

**Implementation Details:**

- Separate main() function and application entry point
- Full-screen calibration interface for accuracy
- Support for multiple monitor configurations
- Real-time feedback during calibration process
- Comprehensive calibration quality assessment

### **7.2 Visual Calibration Interface**

**File: `src/calibration_tool/calibration_ui.py`**

```python
"""
Visual calibration interface with multiple calibration patterns:
- Full-screen calibration display
- Animated calibration points
- Real-time feedback and progress indication
- User guidance and instructions
"""

Key Features:
- Full-screen calibration for maximum accuracy
- Animated calibration points with visual feedback
- Progress indication and user guidance
- Smooth transitions between calibration points
- Error state handling and retry mechanisms

Interface Components:
- Calibration Canvas: Full-screen display area
- Calibration Point: Animated target for user focus
- Progress Indicator: Show calibration progress
- Instruction Display: User guidance and feedback
- Status Bar: Connection status and quality indicators

Visual Design:
- High contrast calibration points for visibility
- Smooth animations to guide user attention
- Clear instructions and feedback messages
- Professional appearance suitable for clinical use
- Accessibility features for different users
```

**Implementation Details:**

- Use PyQt6 for cross-platform compatibility
- Full-screen window with custom calibration graphics
- Animated transitions between calibration points
- Real-time gaze feedback during calibration
- Professional visual design suitable for clinical environment

### **7.3 Calibration Data Management**

**File: `src/calibration_tool/calibration_storage.py`**

```python
"""
Calibration data storage and management system:
- Persistent storage of calibration profiles
- Profile metadata and quality metrics
- Import/export functionality for profiles
- Integration with main application
"""

Key Features:
- JSON-based profile storage
- Profile metadata (creation date, quality, user info)
- Import/export functionality
- Automatic backup and recovery
- Integration with main EDF viewer application

Data Structure:
- Calibration Points: Screen coordinates for calibration
- Gaze Offsets: Calculated offset corrections
- Quality Metrics: Accuracy measurements and statistics
- Profile Metadata: Creation info, device info, user notes
- Validation Data: Test results and accuracy measurements

Storage Features:
- Automatic profile backup
- Profile versioning and history
- Corrupted data detection and recovery
- Cross-user profile management
- Integration with main application settings
```

**Implementation Details:**

- Store calibration profiles in user application data directory
- JSON format for human-readable and cross-platform compatibility
- Automatic backup creation before profile updates
- Data validation and corruption detection
- Easy integration with main application

### **7.4 Calibration Validation and Testing**

**File: `src/calibration_tool/calibration_validator.py`**

```python
"""
Calibration validation and accuracy testing system:
- Real-time accuracy measurement during calibration
- Post-calibration validation testing
- Accuracy metrics and quality scoring
- Recommendations for calibration improvement
"""

Key Features:
- Real-time accuracy measurement
- Comprehensive validation testing
- Quality scoring and metrics
- Improvement recommendations
- Visual accuracy feedback

Validation Components:
- Accuracy Tester: Measure gaze accuracy across screen
- Quality Scorer: Calculate overall calibration quality
- Validator: Test calibration against known points
- Feedback Generator: Provide improvement suggestions
- Report Generator: Create calibration quality reports

Metrics Measured:
- Average accuracy (pixels)
- Accuracy distribution across screen
- Precision (consistency) measurements
- User-specific accuracy patterns
- Hardware-specific performance metrics
```

### **Testing Phase 7**

- [ ] Standalone calibration tool launches independently
- [ ] Calibration process is smooth and intuitive
- [ ] Calibration data saves and loads correctly
- [ ] Validation testing provides accurate results
- [ ] Integration with main application works
- [ ] Multiple user profiles are supported

---

## **Phase 8: Final Integration & Testing (Week 15-16)**

### **Objectives**

- Complete end-to-end system testing
- User acceptance testing and feedback
- Performance optimization and bug fixes
- Documentation and deployment preparation

### **8.1 End-to-End System Testing**

**Complete Workflow Testing:**

```
1. Launch EDF Viewer
2. Load EDF/BDF file
3. Access Gaze Tracking menu
4. Configure gaze annotation mode
5. Start gaze annotation session
6. Auto-scroll through EEG data
7. Generate annotations via gaze fixations
8. Complete data review or quit mode
9. Review generated annotations
10. Accept/reject annotations
11. Export final annotations
12. Verify integration with existing annotation system
```

**Test Scenarios:**

- **Normal Operation**: Complete workflow with typical EEG files
- **Edge Cases**: Very large files, poor gaze quality, hardware disconnection
- **Performance**: Extended sessions, multiple files, resource usage
- **Integration**: Existing features remain functional
- **Error Handling**: Hardware failures, data corruption, system errors

### **8.2 Performance Validation**

**Performance Targets:**

- **Latency**: <50ms gaze position updates
- **Accuracy**: >90% correct time/channel identification
- **Throughput**: Process 30-minute EEG in <45 minutes review time
- **Memory**: <200MB additional memory usage
- **CPU**: <20% additional CPU usage during gaze tracking
- **Reliability**: <1% false positive annotation rate

**Performance Testing:**

- Load testing with large EDF files (>1GB)
- Extended session testing (>2 hours continuous use)
- Memory leak detection and resource usage monitoring
- Multi-user profile testing
- Hardware compatibility testing

### **8.3 User Acceptance Testing**

**Testing Protocol:**

1. **User Training**: 15-minute introduction to gaze annotation system
2. **Practice Session**: 10-minute practice with sample data
3. **Testing Session**: 30-minute review of real EEG data
4. **Feedback Collection**: Questionnaire and interview
5. **System Metrics**: Automatic collection of usage statistics

**Evaluation Criteria:**

- **Ease of Use**: Can users complete workflow without assistance?
- **Accuracy**: Do gaze annotations match user intent?
- **Efficiency**: Is review time reduced compared to manual annotation?
- **Satisfaction**: Do users prefer gaze-based workflow?
- **Reliability**: Does system work consistently without errors?

### **8.4 Documentation and Deployment**

**User Documentation:**

- **Quick Start Guide**: Getting started with gaze annotation
- **Configuration Manual**: Detailed setup and configuration options
- **Troubleshooting Guide**: Common issues and solutions
- **Calibration Guide**: How to calibrate and maintain accuracy
- **Best Practices**: Tips for optimal gaze annotation workflow

**Technical Documentation:**

- **API Documentation**: Developer documentation for extending system
- **Architecture Guide**: System design and component interaction
- **Configuration Reference**: Complete configuration option reference
- **Performance Tuning**: Optimization recommendations
- **Integration Guide**: How to integrate with other systems

**Deployment Package:**

- **Installation Script**: Automated installation of dependencies
- **Configuration Templates**: Default configuration files
- **Sample Data**: Example EDF files for testing
- **User Guides**: PDF documentation for end users
- **Support Information**: Contact and support resources

### **Testing Phase 8**

- [ ] Complete end-to-end workflow functions correctly
- [ ] Performance meets all specified targets
- [ ] User acceptance testing shows positive results
- [ ] Documentation is complete and accurate
- [ ] Deployment package works on clean systems
- [ ] System is ready for production use

---

## **🎯 Success Metrics**

### **Technical Metrics**

- **Accuracy**: >90% correct annotation placement
- **Performance**: <50ms latency, >60 FPS processing
- **Reliability**: >99% uptime, <1% false positives
- **Memory Usage**: <200MB additional overhead
- **Processing Speed**: Real-time with no UI blocking

### **User Experience Metrics**

- **Review Efficiency**: 30-50% reduction in annotation time
- **User Satisfaction**: >80% positive feedback
- **Ease of Use**: Complete workflow without training
- **Error Recovery**: Graceful handling of all error conditions
- **Integration**: Zero impact on existing functionality

### **Clinical Workflow Metrics**

- **Workflow Integration**: Seamless integration with existing review process
- **Annotation Quality**: Matches or exceeds manual annotation accuracy
- **Time Savings**: Significant reduction in overall review time
- **User Adoption**: High acceptance rate among clinical users
- **Data Quality**: No loss of annotation data or metadata

---

## **📋 Risk Assessment and Mitigation**

### **Technical Risks**

1. **Hardware Compatibility**: Tobii Spark compatibility issues
   - *Mitigation*: Extensive testing, fallback modes, multiple hardware support
2. **Performance Issues**: Real-time processing performance
   - *Mitigation*: Performance profiling, optimization, hardware requirements
3. **Integration Complexity**: Existing codebase integration challenges
   - *Mitigation*: Minimal main.py changes, comprehensive testing

### **User Experience Risks**

1. **Calibration Difficulty**: Users struggle with eye tracker calibration
   - *Mitigation*: Comprehensive calibration tool, user training, support
2. **Accuracy Issues**: Gaze annotations not accurate enough
   - *Mitigation*: Advanced filtering, user feedback, adjustable thresholds
3. **Learning Curve**: Users find system too complex
   - *Mitigation*: Intuitive UI design, comprehensive documentation, training

### **Project Risks**

1. **Timeline Delays**: Development takes longer than expected
   - *Mitigation*: Phased approach, regular testing, scope management
2. **Scope Creep**: Requirements expansion during development
   - *Mitigation*: Clear requirements definition, change management process
3. **Resource Constraints**: Limited development or testing resources
   - *Mitigation*: Realistic planning, priority management, external support

---

## **📚 Dependencies and Requirements**

### **Software Dependencies**

```python
# Core Dependencies
tobii_research>=1.10.1
PyQt6>=6.4.0
pyqtgraph>=0.12.4
numpy>=1.21.0
scipy>=1.8.0
pandas>=1.4.0

# Optional Dependencies for Performance
numba>=0.56.0  # JIT compilation for performance
opencv-python>=4.6.0  # Advanced image processing
scikit-learn>=1.1.0  # Machine learning for pattern recognition
```

### **Hardware Requirements**

- **Eye Tracker**: Tobii Spark or compatible Tobii device
- **Operating System**: Windows 10/11 (64-bit)
- **Memory**: 8GB RAM minimum, 16GB recommended
- **CPU**: Intel i5/AMD Ryzen 5 or better
- **Graphics**: DirectX 11 compatible (for PyQtGraph OpenGL)
- **USB**: USB 3.0 port for eye tracker connection

### **Development Environment**

- **Python**: 3.8+ (3.10 recommended)
- **IDE**: Visual Studio Code or PyCharm
- **Version Control**: Git with GitHub/GitLab
- **Testing**: pytest for unit testing
- **Documentation**: Sphinx for API documentation

---

## **📋 Development Timeline**

### **Phase 1-2**: Foundation (Weeks 1-4)

- Hardware integration and basic gaze tracking
- Coordinate mapping and data processing
- **Deliverable**: Basic gaze data streaming and processing

### **Phase 3-4**: Core Features (Weeks 5-8)

- UI components and gaze annotation logic
- Auto-scroll integration and annotation creation
- **Deliverable**: Working gaze annotation mode

### **Phase 5-6**: Polish and Integration (Weeks 9-12)

- Review interface and annotation management
- Performance optimization and error handling
- **Deliverable**: Complete integrated system

### **Phase 7-8**: Advanced Features (Weeks 13-16)

- Calibration tool and final testing
- Documentation and deployment preparation
- **Deliverable**: Production-ready system with documentation

---

## **🚀 Getting Started**

### **Immediate Next Steps**

1. **Environment Setup**: Install Tobii Pro SDK and dependencies
2. **Hardware Testing**: Verify Tobii Spark connection and basic functionality
3. **Phase 1 Implementation**: Begin with gaze_tracker.py and coordinate_mapper.py
4. **Testing Framework**: Set up automated testing for each component

### **Development Approach**

- **Incremental Development**: Build and test each component individually
- **Continuous Integration**: Regular testing and integration with main application
- **User Feedback**: Early user testing and feedback incorporation
- **Documentation**: Document as you build for easier maintenance

This implementation plan provides a comprehensive roadmap for creating a professional-grade gaze-based annotation system that integrates seamlessly with your existing EDF viewer while maintaining clinical workflow efficiency and reliability.
