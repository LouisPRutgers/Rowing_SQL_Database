"""
Main application window for the rowing database entry system.

This module coordinates the overall application, manages the database connection,
and sets up the tabbed interface for the different workflow steps.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from Collegeite_SQL_Race_input.database import DatabaseManager
from Collegeite_SQL_Race_input.config.constants import FONT_TITLE


class RowingDatabaseApp:
    """Main application class that coordinates the GUI and database."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Rowing Database Entry")
        self.root.geometry("1200x900")  # Increased size for additional tab
        
        # Initialize database connection
        self.db = DatabaseManager()
        
        # Current workflow state - shared across tabs
        self.current_regatta_id: Optional[int] = None
        self.current_event_id: Optional[int] = None
        self.current_event_boat_class: Optional[str] = None
        
        # Setup the main UI
        self._setup_ui()
        
        # Initialize data in tabs
        self._initialize_tabs()
    
    def _setup_ui(self):
        """Set up the main user interface with tabbed layout."""
        # Create main title
        title_label = tk.Label(
            self.root, 
            text="Rowing Database Entry System", 
            font=FONT_TITLE
        )
        title_label.pack(pady=10)
        
        # Create notebook for different sections
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Import and create actual tabs
        self._create_tabs()
    
    def _create_tabs(self):
        """Create the actual tab modules."""
        from .tabs import RegattaTab, EventTab, EntriesResultsTab, ConferenceTab, D1SchoolsTab
        
        # Create tab instances in logical order
        self.regatta_tab = RegattaTab(self.notebook, self)
        self.event_tab = EventTab(self.notebook, self)
        self.entries_results_tab = EntriesResultsTab(self.notebook, self)
        self.conference_tab = ConferenceTab(self.notebook, self)
        self.d1_schools_tab = D1SchoolsTab(self.notebook, self)
    
    def _initialize_tabs(self):
        """Initialize data and state in all tabs."""
        # Initialize tab data after all tabs are created
        # Tabs handle their own initialization in their constructors
        pass
    
    # ── Tab Communication Methods ──────────────────────────────────────────
    
    def set_current_regatta(self, regatta_id: int):
        """Set the currently selected regatta (called by regatta tab)."""
        self.current_regatta_id = regatta_id
        # Notify event tab of regatta change if needed
        if hasattr(self, 'event_tab'):
            self.event_tab.on_regatta_changed(regatta_id)
    
    def set_current_event(self, event_id: int, event_boat_class: str = None):
        """Set the currently selected event (called by event/entry tabs)."""
        self.current_event_id = event_id
        self.current_event_boat_class = event_boat_class
        # Notify entries/results tab of event change if needed
        if hasattr(self, 'entries_results_tab'):
            self.entries_results_tab.on_event_changed(event_id, event_boat_class)
    
    def get_database(self) -> DatabaseManager:
        """Get the database manager instance."""
        return self.db
    
    def get_current_regatta_id(self) -> Optional[int]:
        """Get the currently selected regatta ID."""
        return self.current_regatta_id
    
    def get_current_event_id(self) -> Optional[int]:
        """Get the currently selected event ID."""
        return self.current_event_id
    
    def get_current_event_boat_class(self) -> Optional[str]:
        """Get the currently selected event boat class."""
        return self.current_event_boat_class
    
    # ── Data Refresh Methods ───────────────────────────────────────────────
    
    def refresh_all_tabs(self):
        """Refresh data in all tabs (called when data changes)."""
        # Refresh all tabs when data changes
        if hasattr(self, 'regatta_tab'):
            self.regatta_tab.refresh()
        if hasattr(self, 'event_tab'):
            self.event_tab.refresh()
        if hasattr(self, 'entries_results_tab'):
            self.entries_results_tab.refresh()
        if hasattr(self, 'conference_tab'):
            self.conference_tab.refresh()
        if hasattr(self, 'd1_schools_tab'):
            self.d1_schools_tab.refresh()
    
    def refresh_regatta_dependent_tabs(self):
        """Refresh tabs that depend on regatta data."""
        if hasattr(self, 'event_tab'):
            self.event_tab.refresh()
        if hasattr(self, 'entries_results_tab'):
            self.entries_results_tab.refresh()
    
    def refresh_event_dependent_tabs(self):
        """Refresh tabs that depend on event data."""
        if hasattr(self, 'entries_results_tab'):
            self.entries_results_tab.refresh()
    
    def refresh_team_dependent_tabs(self):
        """Refresh tabs that depend on team/school data."""
        if hasattr(self, 'conference_tab'):
            self.conference_tab.refresh()
        if hasattr(self, 'd1_schools_tab'):
            self.d1_schools_tab.refresh()
        if hasattr(self, 'entries_results_tab'):
            self.entries_results_tab.refresh()
    
    # ── Application Lifecycle Methods ──────────────────────────────────────
    
    def on_closing(self):
        """Handle application closing."""
        # Close database connection
        if self.db:
            self.db.close()
        
        # Destroy the root window
        self.root.destroy()
    
    def show_status_message(self, message: str, message_type: str = "info"):
        """
        Show a status message to the user.
        
        Args:
            message: The message to display
            message_type: Type of message ("info", "warning", "error", "success")
        """
        # For now, we'll just print to console
        # In the future, this could show a status bar message
        status_prefix = {
            "info": "ℹ️",
            "warning": "⚠️", 
            "error": "❌",
            "success": "✅"
        }
        
        prefix = status_prefix.get(message_type, "ℹ️")
        print(f"{prefix} {message}")
        
        # TODO: Implement actual status bar in the UI
    
    def confirm_action(self, title: str, message: str) -> bool:
        """
        Show a confirmation dialog to the user.
        
        Args:
            title: Dialog title
            message: Confirmation message
            
        Returns:
            True if user confirmed, False otherwise
        """
        from tkinter import messagebox
        return messagebox.askyesno(title, message)
    
    def show_error(self, title: str, message: str):
        """
        Show an error dialog to the user.
        
        Args:
            title: Dialog title
            message: Error message
        """
        from tkinter import messagebox
        messagebox.showerror(title, message)
    
    def show_info(self, title: str, message: str):
        """
        Show an info dialog to the user.
        
        Args:
            title: Dialog title
            message: Information message
        """
        from tkinter import messagebox
        messagebox.showinfo(title, message)


def create_application() -> RowingDatabaseApp:
    """
    Factory function to create and configure the main application.
    
    Returns:
        Configured RowingDatabaseApp instance
    """
    # Create root window
    root = tk.Tk()
    
    # Configure root window
    root.minsize(800, 600)
    
    # Create application
    app = RowingDatabaseApp(root)
    
    # Bind close event
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    return app