"""
Gaze overlay components for visual feedback.

Provides real-time visual feedback for gaze tracking including:
- Gaze cursor showing current eye position
- Fixation progress indicators
- Annotation previews
- Visual feedback for gaze-based interactions

This module handles the overlay graphics that are displayed on top
of the EDF plot to provide immediate visual feedback to users.
"""

import math
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, pyqtSignal, QObject
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QFont
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsTextItem
import pyqtgraph as pg

logger = logging.getLogger(__name__)


class GazeCursor(QGraphicsEllipseItem):
    """
    Animated cursor showing current gaze position.
    
    Displays a smooth, animated cursor that follows the user's gaze
    with confidence-based visual feedback and smooth movement.
    """
    
    def __init__(self, size: int = 15):
        """
        Initialize gaze cursor.
        
        Args:
            size: Cursor size in pixels
        """
        super().__init__(-size/2, -size/2, size, size)
        
        self.cursor_size = size
        self.confidence = 1.0
        self.is_visible = True
        self.smooth_factor = 0.7  # For smooth movement
        self.target_x = 0.0
        self.target_y = 0.0
        self.current_x = 0.0
        self.current_y = 0.0
        
        # Animation timer for smooth movement
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate_position)
        self.animation_timer.start(16)  # ~60 FPS
        
        # Pulsing animation for visibility
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._pulse_animation)
        self.pulse_timer.start(50)  # 20 FPS for pulse
        self.pulse_phase = 0.0
        
        self._update_appearance()
        
        logger.debug("GazeCursor initialized")
    
    def update_position(self, x: float, y: float, confidence: float = 1.0):
        """
        Update cursor target position and confidence.
        
        Args:
            x: Target X coordinate in widget coordinates
            y: Target Y coordinate in widget coordinates
            confidence: Gaze confidence (0-1)
        """
        self.target_x = x
        self.target_y = y
        self.confidence = max(0.0, min(1.0, confidence))
        self._update_appearance()
    
    def _animate_position(self):
        """Animate smooth movement to target position."""
        if not self.is_visible:
            return
        
        # Smooth interpolation to target
        dx = self.target_x - self.current_x
        dy = self.target_y - self.current_y
        
        self.current_x += dx * self.smooth_factor
        self.current_y += dy * self.smooth_factor
        
        # Update position
        self.setPos(self.current_x, self.current_y)
    
    def _pulse_animation(self):
        """Animate pulsing effect based on confidence."""
        if not self.is_visible:
            return
        
        self.pulse_phase += 0.2
        if self.pulse_phase > 2 * math.pi:
            self.pulse_phase = 0.0
        
        self._update_appearance()
    
    def _update_appearance(self):
        """Update cursor appearance based on confidence and animation state."""
        # Calculate alpha based on confidence
        base_alpha = int(255 * self.confidence * 0.8)  # Max 80% opacity
        
        # Add pulsing effect
        pulse_factor = 1.0 + 0.3 * math.sin(self.pulse_phase)
        pulse_alpha = int(base_alpha * pulse_factor)
        pulse_alpha = max(50, min(255, pulse_alpha))
        
        # Color based on confidence
        if self.confidence > 0.8:
            color = QColor(0, 255, 0, pulse_alpha)  # Green for high confidence
        elif self.confidence > 0.5:
            color = QColor(255, 255, 0, pulse_alpha)  # Yellow for medium confidence
        else:
            color = QColor(255, 0, 0, pulse_alpha)  # Red for low confidence
        
        # Update pen and brush
        pen = QPen(color)
        pen.setWidth(2)
        brush = QBrush(QColor(color.red(), color.green(), color.blue(), pulse_alpha // 3))
        
        self.setPen(pen)
        self.setBrush(brush)
        
        # Scale based on confidence
        scale_factor = 0.5 + 0.5 * self.confidence
        self.setScale(scale_factor)
    
    def set_visible(self, visible: bool):
        """
        Set cursor visibility.
        
        Args:
            visible: Whether cursor should be visible
        """
        self.is_visible = visible
        self.setVisible(visible)
        
        if visible:
            self.animation_timer.start()
            self.pulse_timer.start()
        else:
            self.animation_timer.stop()
            self.pulse_timer.stop()
    
    def set_size(self, size: int):
        """
        Set cursor size.
        
        Args:
            size: New cursor size in pixels
        """
        self.cursor_size = size
        self.setRect(-size/2, -size/2, size, size)
    
    def cleanup(self):
        """Clean up timers and resources."""
        self.animation_timer.stop()
        self.pulse_timer.stop()


class FixationProgressIndicator(QGraphicsItem):
    """
    Progress indicator showing fixation detection progress.
    
    Displays a circular progress indicator that fills up as the user
    maintains a fixation at a specific location.
    """
    
    def __init__(self, size: int = 40):
        """
        Initialize fixation progress indicator.
        
        Args:
            size: Indicator size in pixels
        """
        super().__init__()
        
        self.indicator_size = size
        self.progress = 0.0  # 0.0 to 1.0
        self.is_active = False
        self.target_duration = 1.0  # Target fixation duration
        self.current_duration = 0.0
        
        # Animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_progress)
        self.animation_timer.start(50)  # 20 FPS
        
        self.setZValue(10)  # Above other items
        
        logger.debug("FixationProgressIndicator initialized")
    
    def boundingRect(self) -> QRectF:
        """Return bounding rectangle for the indicator."""
        return QRectF(-self.indicator_size/2, -self.indicator_size/2, 
                      self.indicator_size, self.indicator_size)
    
    def paint(self, painter: QPainter, option, widget):
        """Paint the progress indicator."""
        if not self.is_active:
            return
        
        # Set up painter
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background circle
        background_pen = QPen(QColor(255, 255, 255, 100))
        background_pen.setWidth(3)
        painter.setPen(background_pen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 50)))
        
        radius = self.indicator_size / 2 - 5
        painter.drawEllipse(QPointF(0, 0), radius, radius)
        
        # Progress arc
        if self.progress > 0:
            progress_pen = QPen(QColor(0, 255, 0, 200))
            progress_pen.setWidth(4)
            painter.setPen(progress_pen)
            
            # Calculate arc span (in 16ths of a degree)
            start_angle = 90 * 16  # Start at top
            span_angle = int(-360 * 16 * self.progress)  # Clockwise
            
            rect = QRectF(-radius, -radius, radius * 2, radius * 2)
            painter.drawArc(rect, start_angle, span_angle)
        
        # Center dot
        center_brush = QBrush(QColor(255, 255, 255, 150))
        painter.setBrush(center_brush)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(0, 0), 3, 3)
    
    def start_fixation(self, duration: float):
        """
        Start fixation progress tracking.
        
        Args:
            duration: Target fixation duration in seconds
        """
        self.target_duration = duration
        self.current_duration = 0.0
        self.progress = 0.0
        self.is_active = True
        self.setVisible(True)
        
        logger.debug(f"Fixation progress started, target duration: {duration}s")
    
    def update_fixation(self, elapsed_time: float):
        """
        Update fixation progress.
        
        Args:
            elapsed_time: Time elapsed since fixation start in seconds
        """
        if not self.is_active:
            return
        
        self.current_duration = elapsed_time
        self.progress = min(1.0, elapsed_time / self.target_duration)
        
        # Trigger update
        self.update()
    
    def complete_fixation(self):
        """Mark fixation as complete."""
        self.progress = 1.0
        self.is_active = False
        
        # Brief completion animation
        QTimer.singleShot(200, self._hide_indicator)
        
        logger.debug("Fixation completed")
    
    def cancel_fixation(self):
        """Cancel current fixation progress."""
        self.is_active = False
        self.progress = 0.0
        self.setVisible(False)
        
        logger.debug("Fixation cancelled")
    
    def _update_progress(self):
        """Update progress animation."""
        if self.is_active:
            self.update()  # Trigger repaint
    
    def _hide_indicator(self):
        """Hide the indicator after completion."""
        self.setVisible(False)
    
    def cleanup(self):
        """Clean up timers and resources."""
        self.animation_timer.stop()


class AnnotationPreview(QGraphicsRectItem):
    """
    Preview of annotation that will be created.
    
    Shows a semi-transparent preview of the annotation region
    that will be created when the fixation is complete.
    """
    
    def __init__(self):
        """Initialize annotation preview."""
        super().__init__()
        
        self.preview_active = False
        self.annotation_data = {}
        
        # Styling
        self.setPen(QPen(QColor(255, 255, 0, 150), 2, Qt.PenStyle.DashLine))
        self.setBrush(QBrush(QColor(255, 255, 0, 30)))
        
        # Text label
        self.text_item = QGraphicsTextItem()
        self.text_item.setParentItem(self)
        self.text_item.setFont(QFont("Arial", 10))
        self.text_item.setDefaultTextColor(QColor(255, 255, 255, 200))
        
        self.setZValue(5)  # Below progress indicator but above plot
        self.setVisible(False)
        
        logger.debug("AnnotationPreview initialized")
    
    def show_preview(self, x: float, y: float, width: float, height: float, 
                    annotation_data: Dict[str, Any]):
        """
        Show annotation preview.
        
        Args:
            x: Preview X position
            y: Preview Y position  
            width: Preview width
            height: Preview height
            annotation_data: Annotation information
        """
        self.setRect(x, y, width, height)
        self.annotation_data = annotation_data
        
        # Update text label
        description = annotation_data.get('description', 'Annotation')
        duration = annotation_data.get('duration', 1.0)
        self.text_item.setPlainText(f"{description}\n({duration:.1f}s)")
        
        # Position text at top of preview
        text_rect = self.text_item.boundingRect()
        self.text_item.setPos(x, y - text_rect.height() - 5)
        
        self.preview_active = True
        self.setVisible(True)
        
        logger.debug(f"Annotation preview shown: {description}")
    
    def hide_preview(self):
        """Hide annotation preview."""
        self.preview_active = False
        self.setVisible(False)
        self.text_item.setVisible(False)
    
    def update_preview(self, x: float, y: float, width: float, height: float):
        """
        Update preview position and size.
        
        Args:
            x: New X position
            y: New Y position
            width: New width
            height: New height
        """
        if self.preview_active:
            self.setRect(x, y, width, height)
            
            # Update text position
            text_rect = self.text_item.boundingRect()
            self.text_item.setPos(x, y - text_rect.height() - 5)


class GazeOverlayManager(QObject):
    """
    Manager for all gaze overlay components.
    
    Coordinates the display and animation of gaze cursor, fixation indicators,
    annotation previews, and other visual feedback elements.
    """
    
    # Signals for feedback events
    fixation_completed = pyqtSignal(dict)  # Fixation completion data
    annotation_previewed = pyqtSignal(dict)  # Annotation preview data
    
    def __init__(self, plot_widget):
        """
        Initialize gaze overlay manager.
        
        Args:
            plot_widget: PyQtGraph plot widget to add overlays to
        """
        super().__init__()
        
        self.plot_widget = plot_widget
        self.plot_item = plot_widget.getPlotItem()
        
        # Overlay components
        self.gaze_cursor = None
        self.fixation_indicator = None
        self.annotation_preview = None
        
        # State tracking
        self.current_fixation_start = None
        self.current_fixation_data = {}
        self.overlay_enabled = True
        
        # Configuration
        self.config = {
            'show_cursor': True,
            'show_progress': True,
            'show_preview': True,
            'cursor_size': 15,
            'animation_speed': 0.7
        }
        
        self._setup_overlays()
        
        logger.info("GazeOverlayManager initialized")
    
    def _setup_overlays(self):
        """Set up all overlay components."""
        # Add gaze cursor
        self.gaze_cursor = GazeCursor(self.config['cursor_size'])
        self.plot_item.addItem(self.gaze_cursor)
        self.gaze_cursor.set_visible(self.config['show_cursor'])
        
        # Add fixation progress indicator
        self.fixation_indicator = FixationProgressIndicator()
        self.plot_item.addItem(self.fixation_indicator)
        
        # Add annotation preview
        self.annotation_preview = AnnotationPreview()
        self.plot_item.addItem(self.annotation_preview)
        
        logger.debug("Overlay components setup complete")
    
    def update_gaze_position(self, x: float, y: float, confidence: float = 1.0):
        """
        Update gaze cursor position.
        
        Args:
            x: Gaze X coordinate in plot coordinates
            y: Gaze Y coordinate in plot coordinates
            confidence: Gaze confidence (0-1)
        """
        if self.overlay_enabled and self.gaze_cursor and self.config['show_cursor']:
            self.gaze_cursor.update_position(x, y, confidence)
    
    def start_fixation_tracking(self, x: float, y: float, target_duration: float,
                               annotation_data: Dict[str, Any]):
        """
        Start tracking a potential fixation.
        
        Args:
            x: Fixation center X coordinate
            y: Fixation center Y coordinate
            target_duration: Target fixation duration
            annotation_data: Data for potential annotation
        """
        if not self.overlay_enabled:
            return
        
        self.current_fixation_start = time.time()
        self.current_fixation_data = annotation_data
        
        # Position and start fixation indicator
        if self.fixation_indicator and self.config['show_progress']:
            self.fixation_indicator.setPos(x, y)
            self.fixation_indicator.start_fixation(target_duration)
        
        # Show annotation preview
        if self.annotation_preview and self.config['show_preview']:
            # Calculate preview dimensions (example: 2 seconds width, channel height)
            preview_width = 100  # This would be calculated based on time scale
            preview_height = 50  # This would be calculated based on channel height
            
            self.annotation_preview.show_preview(
                x - preview_width/2, y - preview_height/2,
                preview_width, preview_height,
                annotation_data
            )
        
        logger.debug(f"Fixation tracking started at ({x:.1f}, {y:.1f})")
    
    def update_fixation_progress(self, elapsed_time: float):
        """
        Update fixation progress.
        
        Args:
            elapsed_time: Time elapsed since fixation start
        """
        if self.fixation_indicator and self.current_fixation_start:
            self.fixation_indicator.update_fixation(elapsed_time)
    
    def complete_fixation(self):
        """Complete current fixation and trigger annotation."""
        if self.fixation_indicator:
            self.fixation_indicator.complete_fixation()
        
        if self.annotation_preview:
            self.annotation_preview.hide_preview()
        
        # Emit completion signal
        if self.current_fixation_data:
            self.fixation_completed.emit(self.current_fixation_data)
            logger.info("Fixation completed and annotation triggered")
        
        self._reset_fixation_state()
    
    def cancel_fixation(self):
        """Cancel current fixation tracking."""
        if self.fixation_indicator:
            self.fixation_indicator.cancel_fixation()
        
        if self.annotation_preview:
            self.annotation_preview.hide_preview()
        
        logger.debug("Fixation tracking cancelled")
        self._reset_fixation_state()
    
    def _reset_fixation_state(self):
        """Reset fixation tracking state."""
        self.current_fixation_start = None
        self.current_fixation_data = {}
    
    def update_configuration(self, config: Dict[str, Any]):
        """
        Update overlay configuration.
        
        Args:
            config: New configuration settings
        """
        self.config.update(config)
        
        # Apply configuration changes
        if self.gaze_cursor:
            self.gaze_cursor.set_visible(self.config.get('show_cursor', True))
            if 'cursor_size' in config:
                self.gaze_cursor.set_size(config['cursor_size'])
        
        logger.info("Overlay configuration updated")
    
    def set_enabled(self, enabled: bool):
        """
        Enable or disable all overlays.
        
        Args:
            enabled: Whether overlays should be enabled
        """
        self.overlay_enabled = enabled
        
        if self.gaze_cursor:
            self.gaze_cursor.set_visible(enabled and self.config.get('show_cursor', True))
        
        if not enabled:
            self.cancel_fixation()
        
        logger.info(f"Gaze overlays {'enabled' if enabled else 'disabled'}")
    
    def cleanup(self):
        """Clean up overlay components and resources."""
        try:
            if self.gaze_cursor:
                self.gaze_cursor.cleanup()
                self.plot_item.removeItem(self.gaze_cursor)
            
            if self.fixation_indicator:
                self.fixation_indicator.cleanup()
                self.plot_item.removeItem(self.fixation_indicator)
            
            if self.annotation_preview:
                self.plot_item.removeItem(self.annotation_preview)
            
            logger.info("Gaze overlay cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during overlay cleanup: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overlay statistics.
        
        Returns:
            Dictionary with overlay statistics
        """
        return {
            'overlay_enabled': self.overlay_enabled,
            'cursor_visible': self.gaze_cursor.is_visible if self.gaze_cursor else False,
            'fixation_active': self.fixation_indicator.is_active if self.fixation_indicator else False,
            'preview_active': self.annotation_preview.preview_active if self.annotation_preview else False,
            'current_fixation_duration': (time.time() - self.current_fixation_start) if self.current_fixation_start else 0.0
        }