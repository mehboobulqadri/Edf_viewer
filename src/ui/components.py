"""
Modern UI Components and Theming System
Custom themed widgets and components for the EDF Viewer application.
"""

import logging
from typing import Optional, Callable, Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton, 
    QGroupBox, QApplication
)

from config import THEMES

class ThemeManager:
    """Centralized theme management system"""
    
    def __init__(self):
        self.current_theme = 'dark'
        self.themes = THEMES
        self.subscribers = []  # Widgets that need theme updates
    
    def get_theme(self) -> dict:
        """Get current theme configuration"""
        return self.themes[self.current_theme]
    
    def set_theme(self, theme_name: str):
        """Set application theme"""
        if theme_name in self.themes:
            self.current_theme = theme_name
            self.notify_theme_change()
            logging.info(f"Theme changed to: {theme_name}")
        else:
            logging.warning(f"Unknown theme: {theme_name}")
    
    def subscribe(self, callback: Callable):
        """Subscribe to theme change notifications"""
        self.subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable):
        """Unsubscribe from theme change notifications"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
    
    def notify_theme_change(self):
        """Notify all subscribers of theme change"""
        theme = self.get_theme()
        failed_callbacks = []
        
        for callback in self.subscribers:
            try:
                callback(theme)
            except Exception as e:
                logging.error(f"Theme update error: {e}")
                failed_callbacks.append(callback)
        
        # Remove failed callbacks to prevent future errors
        for callback in failed_callbacks:
            self.subscribers.remove(callback)
    
    def get_color(self, color_name: str) -> str:
        """Get color from current theme"""
        return self.get_theme()['colors'].get(color_name, '#ffffff')
    
    def get_font(self, font_name: str) -> QFont:
        """Get font from current theme"""
        font_info = self.get_theme()['fonts'].get(font_name, ('Arial', 10))
        
        if len(font_info) == 3:
            family, size, weight = font_info
            font = QFont(family, size)
            if weight == 'bold':
                font.setBold(True)
            return font
        else:
            family, size = font_info
            return QFont(family, size)

# Global theme manager instance
theme_manager = ThemeManager()

class ModernSlider(QWidget):
    """Modern themed slider with value preview"""
    
    valueChanged = pyqtSignal(int)
    
    def __init__(self, orientation: Qt.Orientation = Qt.Orientation.Horizontal, parent=None):
        super().__init__(parent)
        self.orientation = orientation
        self.minimum = 0
        self.maximum = 100
        self._value = 0
        self.tracking = True
        self.setup_ui()
        self.apply_theme(theme_manager.get_theme())
        theme_manager.subscribe(self.apply_theme)
        
    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self) if self.orientation == Qt.Orientation.Horizontal else QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Value preview label
        self.value_label = QLabel(str(self._value))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Modern slider
        self.slider = QSlider(self.orientation)
        self.slider.valueChanged.connect(self.on_value_changed)
        
        if self.orientation == Qt.Orientation.Horizontal:
            layout.addWidget(self.value_label)
            layout.addWidget(self.slider)
        else:
            layout.addWidget(self.value_label)
            layout.addWidget(self.slider)
    
    def on_value_changed(self, value: int):
        """Handle value change"""
        self._value = value
        self.value_label.setText(str(value))
        self.valueChanged.emit(value)
        
    def setRange(self, minimum: int, maximum: int):
        """Set slider range"""
        self.minimum = minimum
        self.maximum = maximum
        self.slider.setRange(minimum, maximum)
        
    def setValue(self, value: int):
        """Set slider value"""
        self._value = value
        self.slider.setValue(value)
        self.value_label.setText(str(value))
        
    def value(self) -> int:
        """Get slider value"""
        return self.slider.value()
    
    def apply_theme(self, theme: dict):
        """Apply theme to slider"""
        colors = theme['colors']
        
        self.value_label.setStyleSheet(f"""
            QLabel {{
                background: rgba(100, 181, 246, 0.1);
                border: 1px solid {colors['accent_color']};
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 9px;
                color: {colors['primary_text']};
            }}
        """)
        
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {colors['separator_color']};
                height: 4px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {colors['secondary_bg']}, stop:1 {colors['accent_bg']});
                margin: 2px 0;
                border-radius: 2px;
            }}
            
            QSlider::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['accent_color']}, stop:1 {colors['highlight_color']});
                border: 1px solid {colors['highlight_color']};
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}
            
            QSlider::handle:horizontal:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {colors['success_color']}, stop:1 {colors['success_color']});
                border: 1px solid {colors['success_color']};
            }}
            
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {colors['accent_color']}, stop:1 {colors['highlight_color']});
                border-radius: 2px;
            }}
        """)

class ModernGroupBox(QGroupBox):
    """Modern themed group box"""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(title, parent)
        self.apply_theme(theme_manager.get_theme())
        theme_manager.subscribe(self.apply_theme)
        
    def apply_theme(self, theme: dict):
        """Apply theme to group box"""
        colors = theme['colors']
        fonts = theme['fonts']
        
        self.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {colors['separator_color']};
                border-radius: 8px;
                margin-top: 1ex;
                padding: 10px;
                background: {colors['secondary_bg']};
                color: {colors['primary_text']};
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 8px;
                color: {colors['accent_color']};
                font-size: 11px;
                font-weight: bold;
            }}
        """)

class ModernButton(QPushButton):
    """Modern themed button"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.apply_theme(theme_manager.get_theme())
        theme_manager.subscribe(self.apply_theme)
        
    def apply_theme(self, theme: dict):
        """Apply theme to button"""
        colors = theme['colors']
        
        self.setStyleSheet(f"""
            QPushButton {{
                background: {colors['accent_color']};
                border: 1px solid {colors['highlight_color']};
                border-radius: 6px;
                padding: 6px 12px;
                color: white;
                font-weight: bold;
                font-size: 10px;
                min-height: 20px;
            }}
            
            QPushButton:hover {{
                background: {colors['success_color']};
                border: 1px solid {colors['success_color']};
            }}
            
            QPushButton:pressed {{
                background: {colors['highlight_color']};
                border: 1px solid {colors['highlight_color']};
            }}
            
            QPushButton:disabled {{
                background: {colors['separator_color']};
                border: 1px solid {colors['grid_color']};
                color: {colors['secondary_text']};
            }}
        """)

class ModernLabel(QLabel):
    """Modern themed label"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.apply_theme(theme_manager.get_theme())
        theme_manager.subscribe(self.apply_theme)
    
    def apply_theme(self, theme: dict):
        """Apply theme to label"""
        colors = theme['colors']
        self.setStyleSheet(f"""
            QLabel {{
                color: {colors['primary_text']};
                background: transparent;
            }}
        """)

class StatusBar(QWidget):
    """Custom status bar with themed labels"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.apply_theme(theme_manager.get_theme())
        theme_manager.subscribe(self.apply_theme)
    
    def setup_ui(self):
        """Setup status bar UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(20)
        
        # Status labels
        self.file_label = QLabel("No file loaded")
        self.position_label = QLabel("Position: 0.0s")
        self.channels_label = QLabel("Channels: 0")
        self.memory_label = QLabel("Memory: 0 MB")
        self.fps_label = QLabel("FPS: 0")
        self.cache_label = QLabel("Cache: 0%")
        
        # Add labels to layout
        layout.addWidget(self.file_label)
        layout.addStretch()
        layout.addWidget(self.position_label)
        layout.addWidget(self.channels_label)
        layout.addWidget(self.memory_label)
        layout.addWidget(self.fps_label)
        layout.addWidget(self.cache_label)
    
    def apply_theme(self, theme: dict):
        """Apply theme to status bar"""
        colors = theme['colors']
        
        self.setStyleSheet(f"""
            QWidget {{
                background: {colors['secondary_bg']};
                border-top: 1px solid {colors['separator_color']};
            }}
            
            QLabel {{
                color: {colors['secondary_text']};
                font-size: 9px;
                padding: 2px 5px;
            }}
        """)
    
    def update_file_status(self, filename: str):
        """Update file status"""
        self.file_label.setText(f"File: {filename}")
    
    def update_position(self, position: float):
        """Update position status"""
        self.position_label.setText(f"Position: {position:.1f}s")
    
    def update_channels(self, visible: int, total: int):
        """Update channels status"""
        self.channels_label.setText(f"Channels: {visible}/{total}")
    
    def update_memory(self, memory_mb: float):
        """Update memory status"""
        self.memory_label.setText(f"Memory: {memory_mb:.1f}MB")
    
    def update_fps(self, fps: float):
        """Update FPS status"""
        color = "green" if fps > 30 else "orange" if fps > 15 else "red"
        self.fps_label.setText(f"<span style='color: {color}'>FPS: {fps:.1f}</span>")
    
    def update_cache(self, hit_rate: float):
        """Update cache status"""
        color = "green" if hit_rate > 0.8 else "orange" if hit_rate > 0.5 else "red"
        self.cache_label.setText(f"<span style='color: {color}'>Cache: {hit_rate:.1%}</span>")

class ProgressWidget(QWidget):
    """Custom progress widget for long operations"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.apply_theme(theme_manager.get_theme())
        theme_manager.subscribe(self.apply_theme)
        self.hide()
    
    def setup_ui(self):
        """Setup progress widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        self.progress_label = QLabel("Loading...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.progress_bar = QWidget()
        self.progress_bar.setFixedHeight(4)
        
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)
    
    def apply_theme(self, theme: dict):
        """Apply theme to progress widget"""
        colors = theme['colors']
        
        self.setStyleSheet(f"""
            QWidget {{
                background: {colors['secondary_bg']};
                border: 1px solid {colors['accent_color']};
                border-radius: 8px;
            }}
            
            QLabel {{
                color: {colors['primary_text']};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        
        self.progress_bar.setStyleSheet(f"""
            QWidget {{
                background: {colors['accent_color']};
                border-radius: 2px;
                animation: pulse 1s ease-in-out infinite;
            }}
        """)
    
    def show_progress(self, message: str):
        """Show progress with message"""
        self.progress_label.setText(message)
        self.show()
        QApplication.processEvents()
    
    def hide_progress(self):
        """Hide progress widget"""
        self.hide()

class LoadingOverlay(QWidget):
    """Loading overlay for the main window"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.5);
            }
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.loading_label = QLabel("Loading...")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_label)
        
        self.hide()
    
    def show_loading(self, message: str = "Loading..."):
        """Show loading overlay"""
        self.loading_label.setText(message)
        self.show()
        self.raise_()
        QApplication.processEvents()
    
    def hide_loading(self):
        """Hide loading overlay"""
        self.hide()
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        if self.parent():
            self.resize(self.parent().size())

def apply_dark_theme(app: QApplication):
    """Apply dark theme to entire application"""
    colors = theme_manager.get_color
    
    app.setStyleSheet(f"""
        QMainWindow {{
            background-color: {colors('primary_bg')};
            color: {colors('primary_text')};
        }}
        
        QMenuBar {{
            background-color: {colors('secondary_bg')};
            color: {colors('primary_text')};
            border-bottom: 1px solid {colors('separator_color')};
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 4px 8px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {colors('accent_color')};
        }}
        
        QMenu {{
            background-color: {colors('secondary_bg')};
            color: {colors('primary_text')};
            border: 1px solid {colors('separator_color')};
        }}
        
        QMenu::item:selected {{
            background-color: {colors('accent_color')};
        }}
        
        QToolBar {{
            background-color: {colors('secondary_bg')};
            border: none;
            spacing: 3px;
        }}
        
        QScrollBar:vertical {{
            background: {colors('secondary_bg')};
            width: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {colors('accent_color')};
            border-radius: 6px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {colors('highlight_color')};
        }}
        
        QScrollBar:horizontal {{
            background: {colors('secondary_bg')};
            height: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background: {colors('accent_color')};
            border-radius: 6px;
            min-width: 20px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background: {colors('highlight_color')};
        }}
        
        QComboBox {{
            background: {colors('secondary_bg')};
            color: {colors('primary_text')};
            border: 1px solid {colors('separator_color')};
            border-radius: 4px;
            padding: 4px;
            min-width: 6em;
        }}
        
        QComboBox:hover {{
            border: 1px solid {colors('accent_color')};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        
        QComboBox QAbstractItemView {{
            background: {colors('secondary_bg')};
            color: {colors('primary_text')};
            selection-background-color: {colors('accent_color')};
        }}
        
        QLineEdit {{
            background: {colors('secondary_bg')};
            color: {colors('primary_text')};
            border: 1px solid {colors('separator_color')};
            border-radius: 4px;
            padding: 4px;
        }}
        
        QLineEdit:focus {{
            border: 1px solid {colors('accent_color')};
        }}
        
        QTextEdit {{
            background: {colors('secondary_bg')};
            color: {colors('primary_text')};
            border: 1px solid {colors('separator_color')};
            border-radius: 4px;
        }}
        
        QCheckBox {{
            color: {colors('primary_text')};
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors('separator_color')};
            border-radius: 3px;
            background: {colors('secondary_bg')};
        }}
        
        QCheckBox::indicator:checked {{
            background: {colors('accent_color')};
            border: 1px solid {colors('accent_color')};
        }}
        
        QRadioButton {{
            color: {colors('primary_text')};
            spacing: 8px;
        }}
        
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {colors('separator_color')};
            border-radius: 8px;
            background: {colors('secondary_bg')};
        }}
        
        QRadioButton::indicator:checked {{
            background: {colors('accent_color')};
            border: 1px solid {colors('accent_color')};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {colors('separator_color')};
            background: {colors('primary_bg')};
        }}
        
        QTabBar::tab {{
            background: {colors('secondary_bg')};
            color: {colors('secondary_text')};
            border: 1px solid {colors('separator_color')};
            padding: 8px 16px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background: {colors('accent_color')};
            color: white;
        }}
        
        QTabBar::tab:hover:!selected {{
            background: {colors('accent_bg')};
        }}
    """)

# Export theme manager instance
__all__ = ['theme_manager', 'ModernSlider', 'ModernGroupBox', 'ModernButton', 
           'ModernLabel', 'StatusBar', 'ProgressWidget', 'LoadingOverlay', 
           'apply_dark_theme']