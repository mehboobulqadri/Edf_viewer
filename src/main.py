import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget

# All our application's GUI components will go inside this class
class EDFViewer(QMainWindow):
    def __init__(self):
        # This calls the constructor of the parent class (QMainWindow)
        super().__init__()

        # --- Window Properties ---
        self.setWindowTitle("EDF Viewer v0.1")
        # Set the initial size of the window (width, height in pixels)
        self.setGeometry(100, 100, 1200, 800) # x-pos, y-pos, width, height

        # --- Central Widget ---
        # QMainWindow needs a "central widget" to hold all other elements.
        # We'll create a simple QWidget for this for now.
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # In the next steps, we will add layouts and other widgets
        # (like buttons and plots) to this central_widget.

# This is the standard boilerplate for running a PyQt application
if __name__ == '__main__':
    # 1. Create the Application object.
    #    sys.argv allows passing command-line arguments to the application.
    app = QApplication(sys.argv)

    # 2. Create an instance of our main window.
    main_window = EDFViewer()

    # 3. Show the window.
    main_window.show()

    # 4. Start the application's event loop.
    #    This loop waits for user actions (like clicks) and stops the script
    #    from exiting immediately. The window will stay open until you close it.
    #    The sys.exit() ensures a clean exit.
    sys.exit(app.exec())

