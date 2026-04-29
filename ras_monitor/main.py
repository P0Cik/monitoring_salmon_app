# [FILE: ras_monitor/main.py]
"""
Main entry point for RAS Monitor application.
Initializes QApplication and launches the main window.
"""

import sys
import os

# Add parent directory to path for imports when running as script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.main_window import MainWindow


def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to resource, works for dev and PyInstaller bundle.
    
    Args:
        relative_path: Relative path to the resource
        
    Returns:
        Absolute path to the resource
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Development mode
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


def main():
    """
    Main function to run the RAS Monitor application.
    """
    # Enable high DPI scaling
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        pass  # Older PyQt6 versions may not have this
    
    # Create application
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("RAS Monitor")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("RAS Monitoring System")
    
    # Set default font
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
