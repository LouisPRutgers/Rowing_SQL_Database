#!/usr/bin/env python3
"""
Rowing Database Entry Application - Main Entry Point
===================================================

Launch the rowing database GUI application.

Prerequisites:
- Run database_initializer.py first to set up schools and teams data
- pip install tkcalendar

Usage:
    python -m Collegeite_SQL_Race_input.main
    OR
    cd Collegeite_SQL_Race_input && python main.py
"""

import tkinter as tk
from tkinter import messagebox

def check_dependencies():
    """Check if required dependencies are available."""
    try:
        import tkcalendar
    except ImportError:
        messagebox.showerror(
            "Missing Dependency", 
            "Required package 'tkcalendar' is not installed.\n\n"
            "Please run: pip install tkcalendar"
        )
        exit(1)

def main():
    """Launch the rowing database application."""
    check_dependencies()
    
    # Use absolute imports
    from Collegeite_SQL_Race_input.gui.main_window import RowingDatabaseApp
    
    root = tk.Tk()
    app = RowingDatabaseApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()