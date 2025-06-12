"""
GUI tabs package for the rowing database application.
"""

from .regatta_tab import RegattaTab
from .event_tab import EventTab
from .entries_results_tab import EntriesResultsTab
from .conference_tab import ConferenceTab
from .d1_schools_tab import D1SchoolsTab

__all__ = [
    'RegattaTab',
    'EventTab', 
    'EntriesResultsTab',
    'ConferenceTab',
    'D1SchoolsTab'
]