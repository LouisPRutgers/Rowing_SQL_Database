"""
Collegeite SQL Race Input Application
====================================

A modular GUI application for managing rowing competition data.
"""

__version__ = "1.0.0"

"""
Rowing_SQL_Database/
├──Run.py
├──database_initializer.py
├──rowing_database.db
├──Collegeite_SQL_Race_input/
    ├── __init__.py
    ├── main.py                 # Entry point (10-20 lines)
    ├── config/
    │   ├── __init__.py
    │   └── constants.py        # All constants (BOAT_TYPES, FONTS, etc.)
    ├── database/
    │   ├── __init__.py
    │   ├── manager.py          # DatabaseManager class
    │   └── models.py           # Data classes/schemas
    ├── widgets/
    │   ├── __init__.py
    │   ├── time_entries.py     # TimeEntry, ScheduleTimeEntry
    │   └── custom_widgets.py   # Any other custom widgets
    ├── gui/
    │   ├── __init__.py
    │   ├── main_window.py      # Main app window setup
    │   └── tabs/
    │       ├── __init__.py
    │       ├── regatta_tab.py
    │       ├── event_tab.py
    │       └── entries_results_tab.py
    │       └── conference_results_tab.py
    └── utils/
        ├── __init__.py
        └── helpers.py          # Utility functions
    
"""