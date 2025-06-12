"""
Main application window for the rowing database entry system.

This module coordinates the overall application, manages the database connection,
and sets up the tabbed interface for the different workflow steps.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from .database import DatabaseManager
from .config.constants import FONT_TITLE


class RowingDatabaseApp:
    """Main application class that coordinates the GUI and database."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Rowing Database Entry")
        self.root.geometry("1200x800")  # Increased size for additional tab
        
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
        # Import from the correct location based on your structure
        from .gui.tabs import (
            D1SchoolsTab,           # New tab for school management
            RegattaTab, 
            EventTab, 
            EntriesResultsTab,      # Combined entries and results
            ConferenceTab           # Conference management
        )
        
        # Create tab instances in logical order
        # D1 Schools tab first for data management
        self.d1_schools_tab = D1SchoolsTab(self.notebook, self)
        
        # Then the workflow tabs
        self.regatta_tab = RegattaTab(self.notebook, self)
        self.event_tab = EventTab(self.notebook, self)
        self.entries_results_tab = EntriesResultsTab(self.notebook, self)
        self.conference_tab = ConferenceTab(self.notebook, self)
    
    def _initialize_tabs(self):
        """Initialize data and state in all tabs."""
        # Initialize tab data after all tabs are created
        # D1 Schools tab should load first as it's foundational
        if hasattr(self, 'd1_schools_tab'):
            self.d1_schools_tab.load_schools()
    
    # Methods for tabs to communicate with each other and share state
    
    def set_current_regatta(self, regatta_id: int):
        """Set the currently selected regatta (called by regatta tab)."""
        self.current_regatta_id = regatta_id
        # Notify event tab to refresh events for this regatta
        if hasattr(self, 'event_tab'):
            self.event_tab.refresh_for_regatta(regatta_id)
    
    def set_current_event(self, event_id: int, event_boat_class: str = None):
        """Set the currently selected event (called by event/entry tabs)."""
        self.current_event_id = event_id
        self.current_event_boat_class = event_boat_class
        # Notify entries/results tab (combined)
        if hasattr(self, 'entries_results_tab'):
            self.entries_results_tab.refresh_for_event(event_id)
    
    def get_database(self) -> DatabaseManager:
        """Get the database manager instance."""
        return self.db
    
    def refresh_all_tabs(self):
        """Refresh data in all tabs (called when data changes)."""
        # Refresh all tabs when data changes
        if hasattr(self, 'd1_schools_tab'):
            self.d1_schools_tab.refresh()
        if hasattr(self, 'regatta_tab'):
            self.regatta_tab.refresh()
        if hasattr(self, 'event_tab'):
            self.event_tab.refresh()
        if hasattr(self, 'entries_results_tab'):
            self.entries_results_tab.refresh()
        if hasattr(self, 'conference_tab'):
            self.conference_tab.refresh()
    
    def refresh_school_dependent_tabs(self):
        """Refresh tabs that depend on school data when CRR names change."""
        # Called when CRR names are updated to propagate changes
        if hasattr(self, 'entries_results_tab'):
            self.entries_results_tab.refresh_school_data()
        if hasattr(self, 'conference_tab'):
            self.conference_tab.refresh_school_data()
    
    def get_schools_for_event(self, event_id: int):
        """Get schools eligible for a specific event based on gender/weight."""
        # Helper method that can be used by entry tab
        try:
            # Get event details
            event = self.db.get_event_by_id(event_id)
            if not event:
                return []
            
            gender = event.get('gender')
            weight = event.get('weight')
            
            # Get teams matching the event criteria
            teams = self.db.get_teams_by_category(gender, weight)
            
            # Get school details for each team
            schools = []
            for team in teams:
                school = self.db.get_school_by_id(team['school_id'])
                if school:
                    schools.append({
                        'team_id': team['team_id'],
                        'school_id': school['school_id'],
                        'crr_name': school['crr_name'],
                        'name': school['name'],
                        'short_name': school['short_name'],
                        'color': school['color']
                    })
            
            # Sort by CRR name for consistent display
            schools.sort(key=lambda x: x['crr_name'])
            return schools
            
        except Exception as e:
            print(f"Error getting schools for event {event_id}: {e}")
            return []
    
    def get_current_conference_for_team(self, team_id: int, date_str: str = None):
        """Get the current conference for a team at a specific date."""
        # Helper method for entry tab to show conference affiliations
        try:
            if date_str is None:
                # Use current date if not specified
                from datetime import datetime
                date_str = datetime.now().strftime('%Y-%m-%d')
            
            conference = self.db.get_team_conference_at_date(team_id, date_str)
            return conference
            
        except Exception as e:
            print(f"Error getting conference for team {team_id}: {e}")
            return None
    
    def on_closing(self):
        """Handle application closing - cleanup database connections."""
        try:
            if hasattr(self, 'db'):
                self.db.close()
        except Exception as e:
            print(f"Error closing database: {e}")
        finally:
            self.root.destroy()


def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = RowingDatabaseApp(root)
    
    # Handle window closing properly
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start the main loop
    root.mainloop()


if __name__ == "__main__":
    main()