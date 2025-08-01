import sys
import mne
import numpy as np
import matplotlib as mpl
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QDoubleValidator, QFont, QKeySequence, QAction, QShortcut
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLineEdit, QLabel, QScrollBar, QStatusBar,
    QComboBox, QGroupBox, QMessageBox, QCheckBox, QFrame,
    QToolBar, QDialog, QListWidget, QListWidgetItem,
    QSplitter, QAbstractItemView
)
import time
import logging

# Configure Matplotlib for optimal EEG visualization performance
mpl.rcParams['path.simplify'] = True
mpl.rcParams['path.simplify_threshold'] = 1.0
mpl.rcParams['agg.path.chunksize'] = 10000

# Set up logging for critical errors that need to be tracked
logging.basicConfig(level=logging.ERROR,
                   format='%(asctime)s - %(levelname)s - %(message)s')

class ChannelSelectionDialog(QDialog):
    """Dialog for selecting and ordering EEG channels - modeled after EDFbrowser"""
    def __init__(self, raw, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Channel Selection")
        self.resize(600, 800)

        self.raw = raw
        # Initialize with currently selected channels if available, else all
        if hasattr(parent, 'channel_indices') and parent.channel_indices:
            self.selected_channels = parent.channel_indices
        else:
            self.selected_channels = list(range(len(raw.ch_names)))

        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Available channels list
        available_group = QGroupBox("Available Channels")
        available_layout = QVBoxLayout()
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        available_layout.addWidget(self.available_list)
        available_group.setLayout(available_layout)

        # Selected channels list
        selected_group = QGroupBox("Selected Channels (Drag to reorder)")
        selected_layout = QVBoxLayout()
        self.selected_list = QListWidget()
        self.selected_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.selected_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        selected_layout.addWidget(self.selected_list)
        selected_group.setLayout(selected_layout)

        # Populate lists
        selected_set = set(self.selected_channels)
        for i, ch_name in enumerate(raw.ch_names):
            item = QListWidgetItem(ch_name)
            item.setData(Qt.ItemDataRole.UserRole, i)
            if i in selected_set:
                self.selected_list.addItem(item)
            else:
                self.available_list.addItem(item)

        splitter.addWidget(available_group)
        splitter.addWidget(selected_group)
        splitter.setSizes([300, 500])

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("→ Add")
        self.remove_button = QPushButton("← Remove")
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")

        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        self.add_button.clicked.connect(self.add_channels)
        self.remove_button.clicked.connect(self.remove_channels)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        main_layout.addWidget(splitter)
        main_layout.addLayout(button_layout)

    def add_channels(self):
        """Add selected channels from available to selected list"""
        for item in self.available_list.selectedItems():
            self.selected_list.addItem(self.available_list.takeItem(self.available_list.row(item)))

    def remove_channels(self):
        """Remove selected channels from selected to available list"""
        for item in self.selected_list.selectedItems():
            self.available_list.addItem(self.selected_list.takeItem(self.selected_list.row(item)))

    def get_selected_channels(self):
        """Get list of selected channel indices in order"""
        selected_indices = []
        for i in range(self.selected_list.count()):
            item = self.selected_list.item(i)
            selected_indices.append(item.data(Qt.ItemDataRole.UserRole))
        return selected_indices

    def accept(self):
        """Override to validate that at least one channel is selected."""
        if self.selected_list.count() == 0:
            QMessageBox.warning(self, "Invalid Selection", "You must select at least one channel to continue.")
            return
        super().accept()


class EDFViewer(QMainWindow):
    """Advanced EDF Viewer for clinical EEG review with annotation workflow."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clinical EDF Viewer")
        self.setGeometry(100, 100, 1400, 900)

        # --- State Variables ---
        self.raw = None
        self.view_start_time = 0.0
        self.view_duration = 10.0
        self.min_duration = 0.5
        self.max_duration = 60.0
        self.focus_start_time = 0.0
        self.focus_duration = 1.0
        self.focus_step_time = 0.5
        self.is_auto_moving = False
        self.auto_move_timer = QTimer()
        self.auto_move_timer.timeout.connect(self.auto_move_focus)
        self.channel_indices = []
        self.channel_offset = 0
        self.visible_channels = 20
        self.popup_enabled = True
        self.zoom_factor = 1.3
        self.plot_fps = 0

        # --- GUI Setup ---
        self.setup_ui()
        self.setup_toolbar()
        self.setup_status_bar()
        self.update_button_states()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setup_ui(self):
        """Create the main user interface."""
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)

        control_layout = self.create_control_panel()
        focus_layout = self.create_focus_panel()
        navigation_layout = self.create_navigation_panel()

        self.figure = Figure(tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        plot_container = QWidget()
        plot_layout = QHBoxLayout(plot_container)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.addWidget(self.canvas, 1)

        self.vscroll = QScrollBar(Qt.Orientation.Vertical)
        self.vscroll.valueChanged.connect(self.on_channel_scroll)
        plot_layout.addWidget(self.vscroll)

        self.hscroll = QScrollBar(Qt.Orientation.Horizontal)
        self.hscroll.valueChanged.connect(self.on_time_scroll)

        main_layout.addLayout(control_layout)
        main_layout.addLayout(focus_layout)
        main_layout.addLayout(navigation_layout)
        main_layout.addWidget(plot_container, 1)
        main_layout.addWidget(self.hscroll)
        self.setCentralWidget(main_widget)

        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_click)

    def create_control_panel(self):
        """Create the file and channel control panel."""
        layout = QHBoxLayout()
        self.load_button = QPushButton("Load EDF File")
        self.load_button.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.load_button)

        layout.addWidget(QLabel("Visible Channels:"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["20", "30", "40", "50", "All"])
        self.channel_combo.setCurrentText(str(self.visible_channels))
        self.channel_combo.currentTextChanged.connect(self.on_channel_selection_changed)
        layout.addWidget(self.channel_combo)

        self.channel_button = QPushButton("Manage Channels...")
        self.channel_button.clicked.connect(self.open_channel_selection)
        layout.addWidget(self.channel_button)
        layout.addStretch()
        return layout

    def create_focus_panel(self):
        """Create the focus window control panel."""
        layout = QHBoxLayout()
        layout.addWidget(QLabel("Focus Duration (s):"))
        self.duration_input = QLineEdit(str(self.focus_duration))
        self.duration_input.setFixedWidth(60)
        self.duration_input.setValidator(QDoubleValidator(0.1, 10.0, 2))
        self.duration_input.editingFinished.connect(self.update_focus_duration)
        layout.addWidget(self.duration_input)

        layout.addWidget(QLabel("Step (s):"))
        self.step_input = QLineEdit(str(self.focus_step_time))
        self.step_input.setFixedWidth(60)
        self.step_input.setValidator(QDoubleValidator(0.1, 10.0, 2))
        self.step_input.editingFinished.connect(self.update_focus_step)
        layout.addWidget(self.step_input)
        layout.addStretch()
        return layout

    def create_navigation_panel(self):
        """Create the navigation control panel."""
        layout = QHBoxLayout()
        self.prev_focus_button = QPushButton("⏮️ Prev (G)")
        self.next_focus_button = QPushButton("Next (H) ⏭️")
        self.auto_button = QPushButton("▶ Auto (Space)")
        self.prev_focus_button.clicked.connect(self.prev_focus)
        self.next_focus_button.clicked.connect(self.next_focus)
        self.auto_button.clicked.connect(self.toggle_auto_move)
        layout.addWidget(self.prev_focus_button)
        layout.addWidget(self.next_focus_button)
        layout.addWidget(self.auto_button)

        layout.addStretch()
        self.popup_checkbox = QCheckBox("Enable Confirmation Popups")
        self.popup_checkbox.setChecked(self.popup_enabled)
        self.popup_checkbox.stateChanged.connect(lambda state: self.set_popup_enabled(state == Qt.CheckState.Checked.value))
        layout.addWidget(self.popup_checkbox)
        
        self.fps_label = QLabel("FPS: --")
        layout.addWidget(self.fps_label)

        return layout

    def setup_toolbar(self):
        """Create the main toolbar and actions."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        load_action = QAction("Load EDF", self, triggered=self.open_file_dialog)
        toolbar.addAction(load_action)
        channel_action = QAction("Manage Channels", self, triggered=self.open_channel_selection)
        toolbar.addAction(channel_action)
        toolbar.addSeparator()

        zoom_in_action = QAction("Zoom In", self, shortcut="Ctrl++", triggered=self.zoom_in)
        toolbar.addAction(zoom_in_action)
        zoom_out_action = QAction("Zoom Out", self, shortcut="Ctrl+-", triggered=self.zoom_out)
        toolbar.addAction(zoom_out_action)
        reset_action = QAction("Reset View", self, shortcut="Ctrl+0", triggered=self.reset_view)
        toolbar.addAction(reset_action)
        toolbar.addSeparator()

        # Define shortcuts on actions - THIS IS THE CORRECT WAY
        prev_action = QAction("Previous Section", self, shortcut="G", triggered=self.prev_focus)
        toolbar.addAction(prev_action)
        next_action = QAction("Next Section", self, shortcut="H", triggered=self.next_focus)
        toolbar.addAction(next_action)
        auto_action = QAction("Toggle Auto", self, shortcut="Space", triggered=self.toggle_auto_move)
        toolbar.addAction(auto_action)

    def setup_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready - Load an EDF file.")
        self.status_bar.addPermanentWidget(self.status_label)

    def open_file_dialog(self):
        """Open a file dialog to select an EDF file."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Open EDF File", "", "EDF Files (*.edf *.bdf)")
        if file_path:
            self.load_edf_file(file_path)

    def open_channel_selection(self):
        """Open the channel selection dialog."""
        if self.raw is None:
            QMessageBox.warning(self, "No Data", "Please load an EDF file first.")
            return

        dialog = ChannelSelectionDialog(self.raw, self)
        if dialog.exec():
            self.channel_indices = dialog.get_selected_channels()
            self.channel_offset = 0
            self._validate_and_plot()

    def load_edf_file(self, file_path):
        """Load an EDF file with comprehensive error handling."""
        try:
            self.status_label.setText("Loading file...")
            QApplication.processEvents()
            self.raw = mne.io.read_raw_edf(file_path, preload=True, verbose=False)

            if len(self.raw.ch_names) == 0:
                raise ValueError("The selected file contains no channels.")

            # Default to all channels
            self.channel_indices = list(range(len(self.raw.ch_names)))
            self.reset_view()

            self.status_label.setText(f"Loaded: {file_path} | Duration: {self.raw.times[-1]:.1f}s")
        except Exception as e:
            logging.error(f"Error loading file {file_path}: {e}")
            QMessageBox.critical(self, "File Error", f"Failed to load EDF file:\n{e}")
            self.raw = None
        finally:
            self.update_button_states()

    def _validate_and_plot(self):
        """Validate state parameters and trigger a plot update."""
        if self.raw is None or not self.channel_indices:
            self.figure.clear()
            self.canvas.draw()
            return

        start_time = time.time()
        max_time = self.raw.times[-1]

        self.view_duration = np.clip(self.view_duration, self.min_duration, max_time)
        self.view_start_time = np.clip(self.view_start_time, 0, max_time - self.view_duration)
        self.focus_duration = np.clip(self.focus_duration, 0.1, self.view_duration)
        self.focus_start_time = np.clip(self.focus_start_time, 0, max_time - self.focus_duration)
        
        self.channel_offset = np.clip(self.channel_offset, 0, max(0, len(self.channel_indices) - self.visible_channels))

        self.plot_eeg_data()
        self.update_scrollbars()
        self.update_status_bar()
        
        elapsed = time.time() - start_time
        if elapsed > 0:
            self.plot_fps = int(1.0 / elapsed)
            self.fps_label.setText(f"FPS: {self.plot_fps}")

    def plot_eeg_data(self):
        """Plot EEG data with clinical standards."""
        view_start, view_end = self.view_start_time, self.view_start_time + self.view_duration
        
        # FIX: Ensure start and stop are integers for MNE
        start_samp = int(self.raw.time_as_index(view_start)[0])
        stop_samp = int(self.raw.time_as_index(view_end)[0])

        end_ch = self.channel_offset + self.visible_channels
        ch_to_plot_indices = self.channel_indices[self.channel_offset:end_ch]
        ch_names = [self.raw.ch_names[i] for i in ch_to_plot_indices]

        if not ch_to_plot_indices:
            return

        data, times = self.raw.get_data(picks=ch_to_plot_indices, start=start_samp, stop=stop_samp, return_times=True)

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if data.size > 0:
            offset = (np.std(data) or 1) * 15
            tick_locs = [-i * offset for i in range(len(ch_to_plot_indices))]
            for i, channel_data in enumerate(data):
                ax.plot(times + view_start, channel_data - (i * offset), lw=0.8, color='k')
            ax.set_yticks(tick_locs)
            ax.set_yticklabels(ch_names)

        ax.axvspan(self.focus_start_time, self.focus_start_time + self.focus_duration, color='yellow', alpha=0.4, zorder=0)
        ax.set_xlim(view_start, view_end)
        ax.set_xlabel("Time (s)")
        ax.grid(True, which='major', axis='x', linestyle='--', alpha=0.5)

        self.canvas.draw()

    def keyPressEvent(self, event):
        """Handle keyboard navigation for panning."""
        if self.raw is None or self.duration_input.hasFocus() or self.step_input.hasFocus():
            super().keyPressEvent(event)
            return

        pan_amount = self.view_duration * 0.1
        if event.key() == Qt.Key.Key_Right:
            self.view_start_time += pan_amount
        elif event.key() == Qt.Key.Key_Left:
            self.view_start_time -= pan_amount
        elif event.key() == Qt.Key.Key_Up:
            self.channel_offset = max(0, self.channel_offset - 1)
        elif event.key() == Qt.Key.Key_Down:
            self.channel_offset = min(max(0, len(self.channel_indices) - self.visible_channels), self.channel_offset + 1)
        else:
            super().keyPressEvent(event)
            return
        self._validate_and_plot()

    def on_scroll(self, event):
        """Handle zooming via mouse wheel."""
        if self.raw is None or event.inaxes is None: return
        
        direction = 'up' if event.button == 'up' else 'down'
        if direction == 'up':
            new_duration = self.view_duration / self.zoom_factor
        else:
            new_duration = self.view_duration * self.zoom_factor
        
        self.view_duration = new_duration
        self._validate_and_plot()

    def on_click(self, event):
        """Position the focus window on click."""
        if self.raw is None or event.xdata is None: return
        self.focus_start_time = event.xdata - (self.focus_duration / 2.0)
        self._validate_and_plot()

    def next_focus(self):
        """Move focus window to the next position with smooth scrolling."""
        if self.raw is None: return
        if self.popup_enabled and not self.show_annotation_popup(): return

        self.focus_start_time = min(self.raw.times[-1] - self.focus_duration, self.focus_start_time + self.focus_step_time)

        # Scroll view if focus window goes past 75% of the view
        if self.focus_start_time > self.view_start_time + self.view_duration * 0.75:
            self.view_start_time = self.focus_start_time - self.view_duration * 0.25
        
        self._validate_and_plot()

    def prev_focus(self):
        """Move focus window to the previous position with smooth scrolling."""
        if self.raw is None: return
        if self.popup_enabled and not self.show_annotation_popup(): return

        self.focus_start_time = max(0, self.focus_start_time - self.focus_step_time)

        # Scroll view if focus window goes before 25% of the view
        if self.focus_start_time < self.view_start_time + self.view_duration * 0.25:
            self.view_start_time = self.focus_start_time - self.view_duration * 0.25
        
        self._validate_and_plot()
        
    def toggle_auto_move(self):
        """Toggle automatic focus window movement."""
        if self.raw is None: return
        self.is_auto_moving = not self.is_auto_moving
        if self.is_auto_moving:
            self.auto_move_timer.start(int(self.focus_step_time * 1000))
            self.auto_button.setText("⏹ Stop Auto")
        else:
            self.auto_move_timer.stop()
            self.auto_button.setText("▶ Auto (Space)")

    def auto_move_focus(self):
        """Automatically advance the focus window."""
        if not self.is_auto_moving or self.raw is None:
            self.stop_auto_move()
            return
        
        if self.focus_start_time >= self.raw.times[-1] - self.focus_duration:
            self.stop_auto_move()
            self.status_label.setText("Reached end of recording")
        else:
            self.next_focus()

    def set_popup_enabled(self, enabled):
        """Safely sets the popup enabled state and updates the UI checkbox."""
        self.popup_enabled = enabled
        self.popup_checkbox.blockSignals(True)
        self.popup_checkbox.setChecked(enabled)
        self.popup_checkbox.blockSignals(False)

    def show_annotation_popup(self):
        """Shows a confirmation popup, returning True if OK is clicked."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Annotation")
        msg_box.setText("Proceed to the next section?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        
        checkbox = QCheckBox("Disable confirmation popups")
        checkbox.setChecked(not self.popup_enabled)
        # Connect to a lambda to prevent recursion
        checkbox.stateChanged.connect(lambda state: self.set_popup_enabled(not (state == Qt.CheckState.Checked.value)))
        msg_box.setCheckBox(checkbox)
        
        return msg_box.exec() == QMessageBox.StandardButton.Ok

    # --- UI Update Methods ---
    def on_channel_scroll(self, value):
        self.channel_offset = value
        self._validate_and_plot()

    def on_time_scroll(self, value):
        self.view_start_time = value / 100.0
        self._validate_and_plot()
        
    def on_channel_selection_changed(self, text):
        if self.raw is None: return
        self.visible_channels = len(self.channel_indices) if text == "All" else int(text)
        self._validate_and_plot()

    def update_focus_duration(self):
        if self.raw is None: return
        try:
            self.focus_duration = float(self.duration_input.text())
            self._validate_and_plot()
        except ValueError:
            pass

    def update_focus_step(self):
        if self.raw is None: return
        try:
            self.focus_step_time = float(self.step_input.text())
            if self.is_auto_moving:
                self.auto_move_timer.start(int(self.focus_step_time * 1000))
        except ValueError:
            pass

    def zoom_in(self): self.on_scroll(type('event', (), {'button': 'up', 'inaxes': True})())
    def zoom_out(self): self.on_scroll(type('event', (), {'button': 'down', 'inaxes': True})())
    def reset_view(self):
        if self.raw is None: return
        self.view_start_time = 0.0
        self.view_duration = 10.0
        self.focus_start_time = 0.0
        self.focus_duration = 1.0
        self._validate_and_plot()

    def update_button_states(self):
        """Enable or disable UI elements based on whether a file is loaded."""
        is_loaded = self.raw is not None
        for widget in [self.channel_combo, self.channel_button, self.duration_input,
                       self.step_input, self.prev_focus_button, self.next_focus_button,
                       self.auto_button, self.vscroll, self.hscroll]:
            widget.setEnabled(is_loaded)

    def update_scrollbars(self):
        """Update the range and position of the scrollbars."""
        if self.raw is None: return
        
        self.hscroll.blockSignals(True)
        self.hscroll.setRange(0, int((self.raw.times[-1] - self.view_duration) * 100))
        self.hscroll.setPageStep(int(self.view_duration * 100))
        self.hscroll.setValue(int(self.view_start_time * 100))
        self.hscroll.blockSignals(False)
        # FIX: Cast to bool to avoid DeprecationWarning
        self.hscroll.setEnabled(bool(self.raw.times[-1] > self.view_duration))

        self.vscroll.blockSignals(True)
        max_offset = max(0, len(self.channel_indices) - self.visible_channels)
        self.vscroll.setRange(0, max_offset)
        self.vscroll.setPageStep(self.visible_channels)
        self.vscroll.setValue(self.channel_offset)
        self.vscroll.blockSignals(False)
        self.vscroll.setEnabled(bool(max_offset > 0))

    def update_status_bar(self):
        """Update the status bar with current view information."""
        if self.raw is None: return
        time_info = f"Time: {self.view_start_time:.2f}s - {self.view_start_time + self.view_duration:.2f}s"
        ch_info = f"Ch: {self.channel_offset + 1}-{min(self.channel_offset + self.visible_channels, len(self.channel_indices))}"
        self.status_label.setText(f"{time_info} | {ch_info}")

    def stop_auto_move(self):
        """Stops the auto-move timer."""
        self.is_auto_moving = False
        self.auto_move_timer.stop()
        self.auto_button.setText("▶ Auto (Space)")

    def closeEvent(self, event):
        """Handle the application close event."""
        self.stop_auto_move()
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    main_window = EDFViewer()
    main_window.show()
    sys.exit(app.exec())