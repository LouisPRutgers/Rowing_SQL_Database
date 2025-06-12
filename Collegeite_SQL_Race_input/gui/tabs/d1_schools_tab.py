"""
D1 School Management tab for viewing and updating school participation by season.
Located at: Collegeite_SQL_Race_input/gui/tabs/d1_schools_tab.py

COMPLETE VERSION - All functionality including season management
"""

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass

from Collegeite_SQL_Race_input.config.constants import FONT_LABEL, FONT_ENTRY, FONT_BUTTON, FONT_TITLE
from Collegeite_SQL_Race_input.utils.helpers import (
    debug_print, validate_school_field, CRRNameValidator
)


@dataclass
class Season:
    """Represents an academic season."""
    start_year: int
    end_year: Optional[int]  # None means current/ongoing
    
    @property
    def display_name(self) -> str:
        if self.end_year is None:
            return f"{self.start_year} - current"
        return f"{self.start_year}-{self.end_year}"
    
    @property
    def start_date(self) -> str:
        return f"{self.start_year}-09-01"
    
    @property
    def end_date(self) -> Optional[str]:
        if self.end_year is None:
            return None
        return f"{self.end_year}-08-31"
    
    @property
    def is_current(self) -> bool:
        return self.end_year is None


@dataclass
class SchoolParticipation:
    """Represents a school's participation data."""
    school_name: str
    short_name: str
    acronym: str
    crr_name: str
    color: str
    openweight_women: bool
    heavyweight_men: bool
    lightweight_men: bool
    lightweight_women: bool


class OverlapAnalyzer:
    """Handles season overlap detection and resolution."""
    
    @staticmethod
    def analyze_overlap(new_season: Season, existing_season: Season) -> str:
        """Determine the type of overlap between two seasons.
        
        Academic years are NEVER overlapping by design!
        A season ending in year X (Aug 31, X) and another starting in year X (Sept 1, X) 
        are ADJACENT, not overlapping!
        """
        # Exact match
        if new_season.start_year == existing_season.start_year and new_season.end_year == existing_season.end_year:
            return "EXACT_MATCH"
        
        # Academic year adjacency rules
        # Case 1: Seasons ending and starting in the same year are ADJACENT
        if (existing_season.end_year is not None and 
            new_season.start_year == existing_season.end_year):
            return "NO_OVERLAP"
        
        # Case 2: New season ends, existing starts in same year - also adjacent
        if (new_season.end_year is not None and 
            existing_season.start_year == new_season.end_year):
            return "NO_OVERLAP"
        
        # Case 3: Standard year gaps (more than 1 year apart)
        if (existing_season.end_year is not None and 
            new_season.start_year > existing_season.end_year):
            return "NO_OVERLAP"
        
        if (new_season.end_year is not None and 
            existing_season.start_year > new_season.end_year):
            return "NO_OVERLAP"
        
        # Case 4: Special handling for current seasons
        if (existing_season.is_current and 
            new_season.is_current and 
            new_season.start_year == existing_season.start_year + 1):
            return "ADJACENT_CURRENT_SEASONS"
        
        # Case 5: Current season + new finite season starting next year = adjacent
        if (existing_season.is_current and 
            not new_season.is_current and 
            new_season.start_year == existing_season.start_year + 1):
            return "ADJACENT_CURRENT_TO_FINITE"
        
        # Now check for ACTUAL overlaps
        new_end = new_season.end_year if new_season.end_year is not None else 9999
        existing_end = existing_season.end_year if existing_season.end_year is not None else 9999
        
        # New completely contains existing
        if new_season.start_year <= existing_season.start_year and new_end >= existing_end:
            return "NEW_CONTAINS_EXISTING"
        
        # Existing completely contains new
        if existing_season.start_year <= new_season.start_year and existing_end >= new_end:
            return "EXISTING_CONTAINS_NEW"
        
        # Partial overlaps (these indicate actual date conflicts)
        if new_season.start_year < existing_season.start_year and new_end >= existing_season.start_year:
            return "OVERLAP_START"
        
        if new_season.start_year <= existing_end and new_season.start_year > existing_season.start_year:
            return "OVERLAP_END"
        
        # Fallback
        return "NO_OVERLAP"
    
    @staticmethod
    def plan_overlap_resolution(new_season: Season, existing_seasons: List[Season]) -> Dict:
        """Plan how to resolve all overlaps when creating a new season."""
        overlaps = []
        actions = []
        
        for existing in existing_seasons:
            overlap_type = OverlapAnalyzer.analyze_overlap(new_season, existing)
            
            if overlap_type != "NO_OVERLAP":
                overlap_info = {
                    'existing_season': existing,
                    'overlap_type': overlap_type,
                    'action': OverlapAnalyzer._plan_action(new_season, existing, overlap_type)
                }
                overlaps.append(overlap_info)
                actions.append(overlap_info['action'])
        
        return {
            'overlaps': overlaps,
            'actions': actions,
            'summary': OverlapAnalyzer._create_summary(overlaps)
        }
    
    @staticmethod
    def _plan_action(new_season: Season, existing_season: Season, overlap_type: str) -> str:
        """Plan the specific action for resolving an overlap."""
        if overlap_type == "EXACT_MATCH":
            return f"Replace '{existing_season.display_name}' with new season data"
        elif overlap_type == "NEW_CONTAINS_EXISTING":
            return f"Delete '{existing_season.display_name}' (completely replaced)"
        elif overlap_type == "ADJACENT_CURRENT_SEASONS":
            # This is the key case: 2025-current + 2026-current → trim 2025-current to 2025-2026
            return f"Trim '{existing_season.display_name}' → becomes '{existing_season.start_year}-{new_season.start_year}'"
        elif overlap_type == "ADJACENT_CURRENT_TO_FINITE":
            # e.g., 2025-current + 2026-2027 → trim 2025-current to 2025-2026
            return f"Trim '{existing_season.display_name}' → becomes '{existing_season.start_year}-{new_season.start_year}'"
        elif overlap_type == "EXISTING_CONTAINS_NEW":
            if existing_season.is_current:
                # Split: 2025-current becomes 2025-2025 when inserting 2026-current
                return f"Split '{existing_season.display_name}' → trim to '{existing_season.start_year}-{new_season.start_year-1}'"
            else:
                # Split finite season
                return f"Split '{existing_season.display_name}' → keep parts before and after new season"
        elif overlap_type == "OVERLAP_START":
            # New overlaps start of existing
            if new_season.end_year is not None:
                return f"Trim '{existing_season.display_name}' → starts from '{new_season.end_year+1}'"
            else:
                return f"Delete '{existing_season.display_name}' (new current season takes over)"
        elif overlap_type == "OVERLAP_END":
            # New overlaps end of existing
            return f"Trim '{existing_season.display_name}' → ends at '{new_season.start_year-1}'"
        
        return f"Unknown action for {overlap_type}"
    
    @staticmethod
    def _create_summary(overlaps: List[Dict]) -> Dict:
        """Create summary statistics for overlap resolution."""
        deletes = sum(1 for o in overlaps if 'Delete' in o['action'] or 'Replace' in o['action'])
        trims = sum(1 for o in overlaps if 'Trim' in o['action'])
        splits = sum(1 for o in overlaps if 'Split' in o['action'])
        
        return {
            'total_affected': len(overlaps),
            'deletes': deletes,
            'trims': trims,
            'splits': splits
        }


class SeasonManager:
    """Manages season-related database operations."""
    
    def __init__(self, db):
        self.db = db
    
    def get_all_seasons(self) -> List[Season]:
        """Get all seasons from database."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT 
                SUBSTR(start_date, 1, 4) as start_year,
                CASE 
                    WHEN end_date IS NULL THEN NULL 
                    ELSE SUBSTR(end_date, 1, 4) 
                END as end_year
            FROM school_participations
            ORDER BY start_year DESC
        """)
        
        seasons = []
        for start_year, end_year in cursor.fetchall():
            season = Season(
                start_year=int(start_year),
                end_year=int(end_year) if end_year else None
            )
            seasons.append(season)
        
        return seasons
    
    def get_season_participation_data(self, season: Season):
        """Get all school participation data for a season."""
        return self.db.get_school_participations_for_season(str(season.start_year))
    
    def create_season_with_overlap_resolution(self, new_season: Season, copy_from_season: Optional[Season] = None) -> bool:
        """Create a new season, resolving any overlaps."""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            # CRITICAL FIX: Get copy data BEFORE any deletions occur
            copy_data = None
            if copy_from_season:
                copy_data = self.get_season_participation_data(copy_from_season)
            
            # Get existing seasons and plan resolution
            existing_seasons = self.get_all_seasons()
            resolution_plan = OverlapAnalyzer.plan_overlap_resolution(new_season, existing_seasons)
            
            # Execute overlap resolution
            for overlap in resolution_plan['overlaps']:
                self._execute_overlap_resolution(cursor, new_season, overlap)
            
            # Create the new season
            self._create_new_season_records(cursor, new_season, copy_data)
            
            self.db.conn.commit()
            return True
            
        except Exception as e:
            self.db.conn.rollback()
            raise e
    
    def _execute_overlap_resolution(self, cursor, new_season: Season, overlap: Dict):
        """Execute the resolution for a specific overlap."""
        existing = overlap['existing_season']
        overlap_type = overlap['overlap_type']
        
        # Get existing data before deletion
        existing_data = self.get_season_participation_data(existing)
        
        # Delete the existing season
        cursor.execute("DELETE FROM school_participations WHERE SUBSTR(start_date, 1, 4) = ?", 
                      (str(existing.start_year),))
        
        # Handle specific overlap types
        if overlap_type == "EXACT_MATCH":
            # Just delete - new season will replace
            pass
        elif overlap_type == "NEW_CONTAINS_EXISTING":
            # Just delete - completely replaced
            pass
        elif overlap_type == "ADJACENT_CURRENT_SEASONS":
            # 2025-current + 2026-current → trim existing to 2025-2026
            trimmed_season = Season(existing.start_year, new_season.start_year)
            self._insert_season_data(cursor, trimmed_season, existing_data)
        elif overlap_type == "ADJACENT_CURRENT_TO_FINITE":
            # 2025-current + 2026-2027 → trim existing to 2025-2026
            trimmed_season = Season(existing.start_year, new_season.start_year)
            self._insert_season_data(cursor, trimmed_season, existing_data)
        elif overlap_type == "EXISTING_CONTAINS_NEW":
            # Split the existing season
            self._split_existing_season(cursor, existing, new_season, existing_data)
        elif overlap_type == "OVERLAP_START":
            # Trim existing season start
            self._trim_season_start(cursor, existing, new_season, existing_data)
        elif overlap_type == "OVERLAP_END":
            # Trim existing season end
            self._trim_season_end(cursor, existing, new_season, existing_data)
    
    def _split_existing_season(self, cursor, existing: Season, new_season: Season, existing_data: List):
        """Split an existing season around the new season."""
        # Create part before new season (if needed)
        if existing.start_year < new_season.start_year:
            before_season = Season(existing.start_year, new_season.start_year - 1)
            self._insert_season_data(cursor, before_season, existing_data)
        
        # Create part after new season (if needed and if original season was finite)
        if (existing.end_year is not None and 
            new_season.end_year is not None and 
            existing.end_year > new_season.end_year):
            after_season = Season(new_season.end_year + 1, existing.end_year)
            self._insert_season_data(cursor, after_season, existing_data)
    
    def _trim_season_start(self, cursor, existing: Season, new_season: Season, existing_data: List):
        """Trim the start of an existing season."""
        if new_season.end_year is not None:
            trimmed_season = Season(new_season.end_year + 1, existing.end_year)
            self._insert_season_data(cursor, trimmed_season, existing_data)
    
    def _trim_season_end(self, cursor, existing: Season, new_season: Season, existing_data: List):
        """Trim the end of an existing season."""
        trimmed_season = Season(existing.start_year, new_season.start_year - 1)
        self._insert_season_data(cursor, trimmed_season, existing_data)
    
    def _insert_season_data(self, cursor, season: Season, participation_data: List):
        """Insert participation data for a season."""
        for school_data in participation_data:
            crr_name = school_data[3]  # CRR name is at index 3
            
            # Get school_id
            cursor.execute("SELECT school_id FROM schools WHERE crr_name = ?", (crr_name,))
            result = cursor.fetchone()
            if result:
                school_id = result[0]
                ow, hm, lm, lw = school_data[5:]  # Participation flags
                
                cursor.execute("""
                    INSERT INTO school_participations 
                    (school_id, start_date, end_date, openweight_women, heavyweight_men, lightweight_men, lightweight_women)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (school_id, season.start_date, season.end_date, ow, hm, lm, lw))
    
    def _create_new_season_records(self, cursor, new_season: Season, copy_data: Optional[List]):
        """Create participation records for the new season."""
        if copy_data:
            # Copy from existing season data
            self._insert_season_data(cursor, new_season, copy_data)
        else:
            # Create with all schools having no participation
            cursor.execute("SELECT school_id FROM schools")
            school_ids = [row[0] for row in cursor.fetchall()]
            
            for school_id in school_ids:
                cursor.execute("""
                    INSERT INTO school_participations 
                    (school_id, start_date, end_date, openweight_women, heavyweight_men, lightweight_men, lightweight_women)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (school_id, new_season.start_date, new_season.end_date, False, False, False, False))


class SchoolTableManager:
    """Manages the school participation table display and interactions."""
    
    def __init__(self, parent_container, season_manager: SeasonManager):
        self.parent = parent_container
        self.season_manager = season_manager
        self.selected_rows: Set[int] = set()
        self.school_cells: Dict = {}
        self.editing_cell = None
        self.edit_entry = None
        self._currently_editing = False  # CRITICAL FIX: Prevent race conditions
        
        self.columns = [
            ("row_selector", "№", 30, False),
            ("school_name", "School Official Name", 200, True),
            ("short_name", "Short Name", 120, True),
            ("acronym", "Acronym", 100, True),
            ("crr_name", "Name in CRR", 180, True),
            ("color", "Color", 80, True),
            ("openweight_women", "Openweight Women", 130, False),
            ("heavyweight_men", "Heavyweight Men", 130, False),
            ("lightweight_men", "Lightweight Men", 130, False),
            ("lightweight_women", "Lightweight Women", 130, False)
        ]
    
    def display_season_data(self, season: Season):
        """Display school participation data for a season."""
        debug_print(f"Displaying season data for: {season.display_name}")
        self._clear_table()
        
        participation_data = self.season_manager.get_season_participation_data(season)
        debug_print(f"Loaded {len(participation_data)} school records")
        self._create_table(participation_data, season)
    
    def _clear_table(self):
        """Clear the current table."""
        for widget in self.parent.winfo_children():
            widget.destroy()
        self.school_cells.clear()
        self.selected_rows.clear()
        self._finish_editing()
    
    def _create_table(self, participation_data: List, season: Season):
        """Create the scrollable table with participation data."""
        # Create scrollable canvas setup
        canvas = tk.Canvas(self.parent)
        v_scroll = ttk.Scrollbar(self.parent, orient="vertical", command=canvas.yview)
        h_scroll = ttk.Scrollbar(self.parent, orient="horizontal", command=canvas.xview)
        table_frame = tk.Frame(canvas)
        
        # Configure scrolling
        table_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=table_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def on_shift_mousewheel(event):
            canvas.xview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", on_mousewheel)
        canvas.bind("<Shift-MouseWheel>", on_shift_mousewheel)
        table_frame.bind("<MouseWheel>", on_mousewheel)
        table_frame.bind("<Shift-MouseWheel>", on_shift_mousewheel)
        
        self._scroll_functions = (on_mousewheel, on_shift_mousewheel)
        
        # Create table content
        self._create_table_content(table_frame, participation_data, season)
        
        # Pack scrollbars
        canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)
    
    def _create_table_content(self, parent, participation_data: List, season: Season):
        """Create headers and data rows."""
        row_height = 25
        total_width = sum(width for _, _, width, _ in self.columns)
        
        # Create headers
        x_pos = 0
        for col_key, col_name, width, _ in self.columns:
            bg_color = '#d0d0d0' if col_key == 'row_selector' else '#e8e8e8'
            header = tk.Label(parent, text=col_name, font=FONT_LABEL, bg=bg_color, relief='ridge', bd=1)
            header.place(x=x_pos, y=0, width=width, height=row_height)
            
            # Bind scroll events
            if hasattr(self, '_scroll_functions'):
                on_mousewheel, on_shift_mousewheel = self._scroll_functions
                header.bind("<MouseWheel>", on_mousewheel)
                header.bind("<Shift-MouseWheel>", on_shift_mousewheel)
            
            x_pos += width
        
        # Create data rows
        for row_idx, school_record in enumerate(participation_data, 1):
            self._create_data_row(parent, row_idx, school_record, row_height, season)
        
        # Set container size
        container_height = (len(participation_data) + 1) * row_height
        parent.configure(width=total_width, height=container_height)
    
    def _create_data_row(self, parent, row_idx: int, school_record, row_height: int, season: Season):
        """Create a single data row."""
        school_name, short_name, acronym, crr_name, color = school_record[:5]
        ow, hm, lm, lw = school_record[5:]
        
        data_map = {
            'row_selector': str(row_idx),
            'school_name': school_name or '',
            'short_name': short_name or '',
            'acronym': acronym or '',
            'crr_name': crr_name or '',
            'color': color or '',
            'openweight_women': 'Yes' if ow else 'No',
            'heavyweight_men': 'Yes' if hm else 'No',
            'lightweight_men': 'Yes' if lm else 'No',
            'lightweight_women': 'Yes' if lw else 'No'
        }
        
        x_pos = 0
        for col_idx, (col_key, _, width, editable) in enumerate(self.columns):
            value = data_map[col_key]
            cell = self._create_cell(parent, row_idx-1, col_idx, col_key, value, editable, crr_name, season)
            cell.place(x=x_pos, y=row_idx * row_height, width=width, height=row_height)
            
            # Store cell data
            self.school_cells[(row_idx-1, col_idx)] = {
                'widget': cell,
                'column_key': col_key,
                'value': value,
                'crr_name': crr_name,
                'editable': editable
            }
            
            x_pos += width
    
    def _create_cell(self, parent, row: int, col: int, col_key: str, value: str, 
                    editable: bool, crr_name: str, season: Season):
        """Create a single table cell."""
        # Determine background color
        if row in self.selected_rows:
            bg_color = '#ffcccc'
        elif col_key == 'row_selector':
            bg_color = '#f0f0f0'
        elif col_key in ['openweight_women', 'heavyweight_men', 'lightweight_men', 'lightweight_women']:
            bg_color = '#d4edda' if value == 'Yes' else '#f8d7da'
        elif editable:
            bg_color = '#fff3cd'
        else:
            bg_color = 'white'
        
        cell = tk.Label(parent, text=value, bg=bg_color, relief='solid', bd=1,
                       font=FONT_ENTRY, anchor='w', cursor='hand2')
        
        # Bind events
        if col_key == 'row_selector':
            cell.bind('<Button-1>', lambda e, r=row: self._toggle_row_selection(r))
        elif col_key in ['openweight_women', 'heavyweight_men', 'lightweight_men', 'lightweight_women']:
            cell.bind('<Button-1>', lambda e, r=row, c=col, s=crr_name, se=season: 
                     self._toggle_participation(r, c, s, se))
        elif editable:
            cell.bind('<Double-Button-1>', lambda e, r=row, c=col, s=crr_name, k=col_key, v=value: 
                     self._start_editing(r, c, s, k, v))
        
        # Bind scroll events
        if hasattr(self, '_scroll_functions'):
            on_mousewheel, on_shift_mousewheel = self._scroll_functions
            cell.bind("<MouseWheel>", on_mousewheel)
            cell.bind("<Shift-MouseWheel>", on_shift_mousewheel)
        
        return cell
    
    def _toggle_row_selection(self, row: int):
        """Toggle row selection."""
        if row in self.selected_rows:
            self.selected_rows.remove(row)
        else:
            self.selected_rows.add(row)
        
        # Update visual appearance of all cells in row
        for col in range(len(self.columns)):
            cell_data = self.school_cells.get((row, col))
            if cell_data:
                self._update_cell_appearance(row, col, cell_data)
    
    def _update_cell_appearance(self, row: int, col: int, cell_data: Dict):
        """Update the visual appearance of a cell."""
        widget = cell_data['widget']
        col_key = cell_data['column_key']
        value = cell_data['value']
        
        # Determine background color
        if row in self.selected_rows:
            bg_color = '#ffcccc'
        elif col_key == 'row_selector':
            bg_color = '#f0f0f0'
        elif col_key in ['openweight_women', 'heavyweight_men', 'lightweight_men', 'lightweight_women']:
            bg_color = '#d4edda' if value == 'Yes' else '#f8d7da'
        elif cell_data['editable']:
            bg_color = '#fff3cd'
        else:
            bg_color = 'white'
        
        widget.configure(bg=bg_color)
    
    def _toggle_participation(self, row: int, col: int, crr_name: str, season: Season):
        """Toggle team participation for a school."""
        self._finish_editing()
        
        cell_data = self.school_cells.get((row, col))
        if cell_data:
            column_key = cell_data['column_key']
            current_value = cell_data['value']
            new_value = "No" if current_value == "Yes" else "Yes"
            
            # Update database
            success = self.season_manager.db.update_school_participation(
                crr_name, column_key, new_value == "Yes", season.display_name)
            
            if success:
                # Update cell data and appearance
                cell_data['value'] = new_value
                cell_data['widget'].configure(text=new_value)
                self._update_cell_appearance(row, col, cell_data)
    
    def _start_editing(self, row: int, col: int, crr_name: str, column_key: str, current_value: str):
        """Start editing a cell."""
        debug_print(f"Starting edit: row={row}, col={col}, crr_name='{crr_name}', field='{column_key}', value='{current_value}'")
        
        self._finish_editing()
        
        cell_data = self.school_cells.get((row, col))
        if not cell_data or not cell_data['editable']:
            return
        
        widget = cell_data['widget']
        
        try:
            x, y, width, height = widget.winfo_x(), widget.winfo_y(), widget.winfo_width(), widget.winfo_height()
            parent = widget.master
        except tk.TclError:
            return
        
        # CRITICAL FIX: Get current values from cell data, not from lambda closure parameters
        current_crr_name = cell_data['crr_name']  # Always up-to-date
        actual_current_value = cell_data['value']  # Always up-to-date
        
        debug_print(f"Lambda closure value: '{current_value}' vs Cell data value: '{actual_current_value}'", "DEBUG")
        debug_print(f"Lambda closure CRR: '{crr_name}' vs Cell data CRR: '{current_crr_name}'", "DEBUG")
        
        # Create entry widget with the ACTUAL current value
        self.edit_entry = tk.Entry(parent, font=FONT_ENTRY, bd=1, highlightthickness=1)
        self.edit_entry.place(x=x, y=y, width=width, height=height)
        self.edit_entry.insert(0, actual_current_value)  # Use actual current value
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.focus_set()
        
        # Store editing context with current values
        self.editing_cell = {
            'row': row, 'col': col, 'crr_name': current_crr_name,  # Current CRR name
            'column_key': column_key, 'original_value': actual_current_value  # Current value as "original"
        }
        
        # Bind events
        self.edit_entry.bind('<Return>', self._finish_editing)
        self.edit_entry.bind('<Tab>', self._finish_editing)
        self.edit_entry.bind('<Escape>', self._cancel_editing)
        self.edit_entry.bind('<FocusOut>', self._finish_editing)

    def _finish_editing(self, event=None):
        """Finish editing and save changes - WITH COMPREHENSIVE DEBUG OUTPUT."""
        debug_print("=== FINISH EDITING START ===", "DEBUG")
        
        if not self.editing_cell or not self.edit_entry:
            debug_print("No editing context, returning", "INFO")
            return
        
        # CRITICAL FIX: Check if we're already processing an edit to prevent race conditions
        if hasattr(self, '_currently_editing') and self._currently_editing:
            debug_print("Already processing an edit, skipping", "WARNING")
            return
        
        self._currently_editing = True
        
        try:
            new_value = self.edit_entry.get().strip()
            column_key = self.editing_cell['column_key']
            crr_name = self.editing_cell['crr_name']
            original_value = self.editing_cell['original_value']
            
            debug_print(f"Edit details:", "DEBUG")
            debug_print(f"  new_value: '{new_value}'", "DEBUG")
            debug_print(f"  column_key: '{column_key}'", "DEBUG")
            debug_print(f"  crr_name: '{crr_name}'", "DEBUG")
            debug_print(f"  original_value: '{original_value}'", "DEBUG")
            
            # Validate using helper function
            is_valid, validation_msg = validate_school_field(column_key, new_value, original_value)
            if not is_valid:
                debug_print(f"Validation failed: {validation_msg}", "ERROR")
                messagebox.showerror("Invalid Value", validation_msg)
                self.edit_entry.focus_set()
                return
            
            # Check for changes and save
            if new_value != original_value:
                debug_print(f"Value changed, processing update...", "INFO")
                
                if column_key == 'crr_name':
                    debug_print(f"CRR name validation...", "DEBUG")
                    
                    # CRITICAL FIX: Use the current CRR name from the database, not the stored one
                    row, col = self.editing_cell['row'], self.editing_cell['col']
                    cell_data = self.school_cells.get((row, col))
                    if cell_data:
                        # Get the most up-to-date CRR name from the cell data
                        current_crr_name = cell_data['crr_name']
                        debug_print(f"Using current CRR name from cell data: '{current_crr_name}'", "DEBUG")
                    else:
                        current_crr_name = crr_name
                        debug_print(f"Using original CRR name: '{current_crr_name}'", "DEBUG")
                    
                    # Use the helper validation function with debug output
                    is_unique, debug_message = CRRNameValidator.validate_uniqueness(
                        self.season_manager.db, new_value, current_crr_name)
                    
                    # Print the debug message
                    print(debug_message)
                    
                    if not is_unique:
                        debug_print(f"CRR name conflict detected", "ERROR")
                        messagebox.showerror("Duplicate Name", f"CRR name '{new_value}' already exists.")
                        self.edit_entry.focus_set()
                        return
                    else:
                        debug_print(f"CRR name is unique, proceeding", "SUCCESS")
                
                debug_print(f"Calling database update...", "INFO")
                # Use the current CRR name for the database update
                update_crr_name = current_crr_name if column_key == 'crr_name' else crr_name
                success = self._update_school_field(update_crr_name, column_key, new_value, original_value)
                debug_print(f"Database update result: {success}", "INFO")
                
                if success:
                    debug_print(f"Update successful, updating UI...", "SUCCESS")
                    # Update cell data
                    row, col = self.editing_cell['row'], self.editing_cell['col']
                    cell_data = self.school_cells.get((row, col))
                    if cell_data:
                        cell_data['value'] = new_value
                        cell_data['widget'].configure(text=new_value)
                        
                        # Update the stored crr_name in ALL cells for this row if CRR name changed
                        if column_key == 'crr_name':
                            debug_print(f"Updating crr_name in all row cells from '{crr_name}' to '{new_value}'", "INFO")
                            for c in range(len(self.columns)):
                                row_cell_data = self.school_cells.get((row, c))
                                if row_cell_data:
                                    debug_print(f"  Cell ({row},{c}): '{row_cell_data['crr_name']}' → '{new_value}'", "DEBUG")
                                    row_cell_data['crr_name'] = new_value
                else:
                    debug_print(f"Update failed", "ERROR")
            else:
                debug_print(f"No changes detected", "INFO")
            
        finally:
            debug_print(f"Cleaning up editing state...", "DEBUG")
            self._cleanup_editing()
            self._currently_editing = False
            debug_print("=== FINISH EDITING END ===", "DEBUG")
    
    def _cancel_editing(self, event=None):
        """Cancel editing without saving."""
        debug_print("Canceling edit", "INFO")
        self._cleanup_editing()
    
    def _cleanup_editing(self):
        """Clean up editing state."""
        if self.edit_entry:
            try:
                self.edit_entry.destroy()
            except tk.TclError:
                pass
            self.edit_entry = None
        self.editing_cell = None
        self._currently_editing = False  # CRITICAL FIX: Reset race condition flag
    
    def _update_school_field(self, crr_name: str, column_key: str, new_value: str, original_value: str) -> bool:
        """Update school field in database - WITH DEBUG OUTPUT."""
        debug_print(f"=== DATABASE UPDATE START ===", "DEBUG")
        debug_print(f"  crr_name: '{crr_name}'", "DEBUG")
        debug_print(f"  column_key: '{column_key}'", "DEBUG")
        debug_print(f"  new_value: '{new_value}'", "DEBUG")
        debug_print(f"  original_value: '{original_value}'", "DEBUG")
        
        try:
            # Get school_id using the current CRR name
            school_id = self.season_manager.db.get_school_id_by_crr_name(crr_name)
            debug_print(f"  school_id for '{crr_name}': {school_id}", "DEBUG")
            
            if not school_id:
                debug_print(f"School with CRR name '{crr_name}' not found", "ERROR")
                messagebox.showerror("Error", f"School with CRR name '{crr_name}' not found.")
                return False
            
            debug_print(f"Cache state before update:", "DEBUG")
            debug_print(f"  Cache size: {len(self.season_manager.db.crr_name_to_id_cache)}", "DEBUG")
            debug_print(f"  '{crr_name}' → {self.season_manager.db.crr_name_to_id_cache.get(crr_name)}", "DEBUG")
            if column_key == 'crr_name':
                debug_print(f"  '{new_value}' → {self.season_manager.db.crr_name_to_id_cache.get(new_value)}", "DEBUG")
            
            # Use the DatabaseManager's enhanced update method
            debug_print(f"Calling DatabaseManager.update_school_field({school_id}, '{column_key}', '{new_value}')", "INFO")
            success = self.season_manager.db.update_school_field(school_id, column_key, new_value)
            debug_print(f"DatabaseManager.update_school_field result: {success}", "INFO")
            
            if success and column_key == 'crr_name':
                debug_print(f"Cache state after update:", "DEBUG")
                debug_print(f"  Cache size: {len(self.season_manager.db.crr_name_to_id_cache)}", "DEBUG")
                debug_print(f"  '{crr_name}' → {self.season_manager.db.crr_name_to_id_cache.get(crr_name)}", "DEBUG")
                debug_print(f"  '{new_value}' → {self.season_manager.db.crr_name_to_id_cache.get(new_value)}", "DEBUG")
                
                # Force refresh of database caches
                debug_print(f"Forcing cache refresh...", "INFO")
                self.season_manager.db.refresh_school_caches()
                
                debug_print(f"Cache state after refresh:", "DEBUG")
                debug_print(f"  Cache size: {len(self.season_manager.db.crr_name_to_id_cache)}", "DEBUG")
                debug_print(f"  '{crr_name}' → {self.season_manager.db.crr_name_to_id_cache.get(crr_name)}", "DEBUG")
                debug_print(f"  '{new_value}' → {self.season_manager.db.crr_name_to_id_cache.get(new_value)}", "DEBUG")
                
                messagebox.showinfo("Updated", 
                    f"CRR name updated from '{original_value}' to '{new_value}'.\n"
                    f"All system references have been updated.")
            
            debug_print(f"=== DATABASE UPDATE END: {success} ===", "DEBUG")
            return success
                
        except Exception as e:
            debug_print(f"Exception in _update_school_field: {str(e)}", "CRITICAL")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to update: {str(e)}")
            return False
    
    def get_selected_schools(self) -> List[str]:
        """Get list of CRR names for selected schools."""
        selected_schools = []
        for row in self.selected_rows:
            cell_data = self.school_cells.get((row, 4))  # CRR name column
            if cell_data:
                selected_schools.append(cell_data['crr_name'])
        return selected_schools


class AddSeasonDialog:
    """Dialog for adding a new season with overlap resolution."""
    
    def __init__(self, parent, season_manager: SeasonManager, callback):
        self.parent = parent
        self.season_manager = season_manager
        self.callback = callback
        self.dialog = None
    
    def show(self):
        """Show the add season dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Add New Season")
        self.dialog.geometry("700x800")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent.winfo_toplevel())
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        self._create_dialog_content()
    
    def _create_dialog_content(self):
        """Create the dialog content."""
        main_frame = tk.Frame(self.dialog)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        tk.Label(main_frame, text="Create New Season", font=FONT_TITLE).grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Start year
        tk.Label(main_frame, text="Start Year:", font=FONT_LABEL).grid(row=1, column=0, sticky='e', padx=5, pady=10)
        
        self.start_var = tk.StringVar()
        start_combo = ttk.Combobox(main_frame, textvariable=self.start_var, 
                                  state='readonly', font=FONT_ENTRY, width=15)
        start_combo['values'] = [str(year) for year in range(2000, 2051)]
        start_combo.grid(row=1, column=1, padx=5, pady=10, sticky='w')
        start_combo.set(str(datetime.now().year))
        
        # End year
        tk.Label(main_frame, text="End Year:", font=FONT_LABEL).grid(row=2, column=0, sticky='e', padx=5, pady=10)
        
        self.end_var = tk.StringVar()
        self.end_combo = ttk.Combobox(main_frame, textvariable=self.end_var, 
                                     state='readonly', font=FONT_ENTRY, width=15)
        self.end_combo.grid(row=2, column=1, padx=5, pady=10, sticky='w')
        
        def update_end_options(*args):
            start_year = self.start_var.get()
            if start_year:
                end_options = ["current"] + [str(y) for y in range(int(start_year) + 1, 2051)]
                self.end_combo['values'] = end_options
                self.end_combo.set("current")
        
        self.start_var.trace('w', update_end_options)
        update_end_options()
        
        # Copy from season
        tk.Label(main_frame, text="Copy from season:", font=FONT_LABEL).grid(row=3, column=0, sticky='e', padx=5, pady=10)
        
        self.copy_var = tk.StringVar()
        copy_combo = ttk.Combobox(main_frame, textvariable=self.copy_var, 
                                 state='readonly', font=FONT_ENTRY, width=15)
        existing_seasons = self.season_manager.get_all_seasons()
        copy_options = ["None"] + [s.display_name for s in existing_seasons]
        copy_combo['values'] = copy_options
        copy_combo.set("None")
        copy_combo.grid(row=3, column=1, padx=5, pady=10, sticky='w')
        
        # Explanation
        explanation_frame = tk.Frame(main_frame)
        explanation_frame.grid(row=4, column=0, columnspan=2, pady=15, sticky='ew')
        
        tk.Label(explanation_frame, text="📅 Academic Year Info:", font=("Helvetica", 9, "bold"), fg='#0066cc').pack(anchor='w')
        tk.Label(explanation_frame, text="• Academic years run Sept 1 - Aug 31", 
                font=("Helvetica", 8), fg='#666').pack(anchor='w', padx=15)
        tk.Label(explanation_frame, text="• 'current' means ongoing season", 
                font=("Helvetica", 8), fg='#666').pack(anchor='w', padx=15)
        
        # Preview area
        preview_frame = tk.LabelFrame(main_frame, text="Season Overlap Analysis", font=FONT_LABEL)
        preview_frame.grid(row=5, column=0, columnspan=2, sticky='ew', pady=15, padx=5)
        
        self.preview_text = tk.Text(preview_frame, height=15, width=80, font=("Courier", 9), 
                              bg='#f8f9fa', relief='sunken', bd=1)
        preview_scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scroll.set)
        
        self.preview_text.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        preview_scroll.pack(side='right', fill='y', pady=5)
        
        def update_preview(*args):
            self._update_preview()
        
        self.start_var.trace('w', update_preview)
        self.end_var.trace('w', update_preview)
        update_preview()
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        tk.Button(button_frame, text="Create Season", font=FONT_BUTTON, 
                 command=self._create_season, default='active', bg='#28a745', fg='white').pack(side='left', padx=5)
        tk.Button(button_frame, text="Cancel", font=FONT_BUTTON, 
                 command=self.dialog.destroy).pack(side='left', padx=5)
        
        self.dialog.bind('<Return>', lambda e: self._create_season())
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
    
    def _update_preview(self):
        """Update the overlap analysis preview."""
        start_year = self.start_var.get()
        end_year = self.end_var.get()
        
        self.preview_text.delete(1.0, tk.END)
        
        if not start_year or not end_year:
            self.preview_text.insert(tk.END, "Select start and end years to see overlap analysis...")
            return
        
        try:
            start_int = int(start_year)
            end_int = None if end_year == "current" else int(end_year)
            
            # Validate input
            if end_int is not None and start_int >= end_int:
                self.preview_text.insert(tk.END, "⚠️ End year must be after start year!")
                return
            
            new_season = Season(start_int, end_int)
            existing_seasons = self.season_manager.get_all_seasons()
            
            resolution_plan = OverlapAnalyzer.plan_overlap_resolution(new_season, existing_seasons)
            
            # Display new season info
            self.preview_text.insert(tk.END, f"🆕 New Season: {new_season.display_name}\n")
            self.preview_text.insert(tk.END, f"   Range: {new_season.start_date} → {new_season.end_date or 'present'}\n\n")
            
            if not resolution_plan['overlaps']:
                self.preview_text.insert(tk.END, "✅ No overlaps detected - new season will be created cleanly.\n")
            else:
                self.preview_text.insert(tk.END, f"⚠️ {len(resolution_plan['overlaps'])} overlap(s) detected:\n\n")
                
                for action in resolution_plan['actions']:
                    self.preview_text.insert(tk.END, f"• {action}\n")
                
                summary = resolution_plan['summary']
                self.preview_text.insert(tk.END, f"\n📊 Summary:\n")
                self.preview_text.insert(tk.END, f"   • Seasons affected: {summary['total_affected']}\n")
                self.preview_text.insert(tk.END, f"   • Will be deleted/replaced: {summary['deletes']}\n")
                self.preview_text.insert(tk.END, f"   • Will be trimmed: {summary['trims']}\n")
                self.preview_text.insert(tk.END, f"   • Will be split: {summary['splits']}\n")
            
        except ValueError:
            self.preview_text.insert(tk.END, "Invalid year values...")
    
    def _create_season(self):
        """Create the new season."""
        start_year = self.start_var.get().strip()
        end_year = self.end_var.get().strip()
        copy_from = self.copy_var.get().strip()
        
        if not start_year or not end_year:
            messagebox.showerror("Invalid Input", "Please select both start and end years.")
            return
        
        try:
            start_int = int(start_year)
            end_int = None if end_year == "current" else int(end_year)
            
            if end_int is not None and start_int >= end_int:
                messagebox.showerror("Invalid Range", "End year must be after start year.")
                return
            
            new_season = Season(start_int, end_int)
            
            # Get copy source if specified
            copy_from_season = None
            if copy_from != "None":
                existing_seasons = self.season_manager.get_all_seasons()
                for season in existing_seasons:
                    if season.display_name == copy_from:
                        copy_from_season = season
                        break
            
            # Check for overlaps and confirm if needed
            existing_seasons = self.season_manager.get_all_seasons()
            resolution_plan = OverlapAnalyzer.plan_overlap_resolution(new_season, existing_seasons)
            
            if resolution_plan['overlaps']:
                summary = resolution_plan['summary']
                confirm_msg = (f"Creating season {new_season.display_name} will affect "
                              f"{summary['total_affected']} existing season(s).\n\n"
                              f"This will:\n"
                              f"• Delete/replace: {summary['deletes']} season(s)\n"
                              f"• Trim: {summary['trims']} season(s)\n"
                              f"• Split: {summary['splits']} season(s)\n\n"
                              f"Continue?")
                
                if not messagebox.askyesno("Confirm Season Creation", confirm_msg, icon='warning'):
                    return
            
            # Create the season
            success = self.season_manager.create_season_with_overlap_resolution(new_season, copy_from_season)
            
            if success:
                self.dialog.destroy()
                if resolution_plan['overlaps']:
                    messagebox.showinfo("Season Created", 
                                       f"Season '{new_season.display_name}' created successfully.\n\n"
                                       f"Processed {len(resolution_plan['overlaps'])} overlapping season(s).")
                else:
                    messagebox.showinfo("Season Created", f"Season '{new_season.display_name}' created successfully.")
                
                self.callback(new_season)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create season: {str(e)}")


class D1SchoolsTab:
    """Main tab class that coordinates all components."""
    
    def __init__(self, parent_notebook, app):
        self.notebook = parent_notebook
        self.app = app
        self.db = app.get_database()
        
        # Initialize managers
        self.season_manager = SeasonManager(self.db)
        
        # State
        self.current_season: Optional[Season] = None
        self.selected_season_for_deletion: Optional[Season] = None
        
        # Create UI
        self._create_interface()
        self._load_seasons()
    
    def _create_interface(self):
        """Create the main interface."""
        # Create the tab
        self.frame = ttk.Frame(self.notebook)
        self.notebook.add(self.frame, text="5. D1 Schools")
        
        # Title
        tk.Label(self.frame, text="D1 School Management", font=FONT_TITLE).pack(pady=10)
        
        # Main container
        main_container = tk.LabelFrame(self.frame, text="School Participation by Season", font=FONT_LABEL)
        main_container.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Season controls
        self._create_season_controls(main_container)
        
        # Table container
        self.table_container = tk.Frame(main_container)
        self.table_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Initialize table manager
        self.table_manager = SchoolTableManager(self.table_container, self.season_manager)
        
        # Bottom controls
        self._create_bottom_controls(main_container)
    
    def _create_season_controls(self, parent):
        """Create season tab controls."""
        tabs_frame = tk.Frame(parent)
        tabs_frame.pack(fill='x', padx=10, pady=(5, 10))
        
        self.season_notebook = ttk.Notebook(tabs_frame)
        self.season_notebook.pack(side='left', fill='x', expand=True)
        self.season_notebook.bind('<<NotebookTabChanged>>', self._on_season_change)
        self.season_notebook.bind('<Button-3>', self._on_season_right_click)
        
        tk.Button(tabs_frame, text="Add New Season", font=FONT_BUTTON,
                 command=self._show_add_season_dialog).pack(side='right', padx=(5, 0))
    
    def _create_bottom_controls(self, parent):
        """Create bottom control buttons."""
        controls = tk.Frame(parent)
        controls.pack(fill='x', padx=10, pady=(10, 5))
        
        # Left buttons
        left_frame = tk.Frame(controls)
        left_frame.pack(side='left')
        
        tk.Button(left_frame, text="Add School", font=FONT_BUTTON, bg='#28a745', fg='white',
                 command=self._show_add_school_dialog).pack(side='left', padx=(0, 5))
        
        tk.Button(left_frame, text="Delete Selected", font=FONT_BUTTON, fg='red',
                 command=self._delete_selected).pack(side='left')
        
        # Help text
        tk.Label(controls, text="💡 Click row numbers to select | Double-click to edit | Click team cells to toggle",
                font=("Helvetica", 9), fg='blue').pack(side='right')
    
    def _load_seasons(self):
        """Load and display all seasons."""
        debug_print("Loading seasons...")
        seasons = self.season_manager.get_all_seasons()
        
        if not seasons:
            # Create a default current season
            current_year = datetime.now().year
            default_season = Season(current_year, None)
            seasons = [default_season]
        
        debug_print(f"Found {len(seasons)} seasons")
        
        # Clear existing tabs
        for widget in self.season_notebook.winfo_children():
            widget.destroy()
        
        # Create season tabs
        for season in seasons:
            frame = ttk.Frame(self.season_notebook)
            self.season_notebook.add(frame, text=season.display_name)
        
        # Select first season
        if seasons:
            self.season_notebook.select(0)
            self.current_season = seasons[0]
            self._display_current_season()
    
    def _on_season_change(self, event):
        """Handle season tab change."""
        self.table_manager._finish_editing()
        selected_tab = self.season_notebook.select()
        if selected_tab:
            index = self.season_notebook.index(selected_tab)
            seasons = self.season_manager.get_all_seasons()
            if 0 <= index < len(seasons):
                self.current_season = seasons[index]
                self.table_manager.selected_rows.clear()
                self._display_current_season()
    
    def _on_season_right_click(self, event):
        """Handle right-click on season tab for deletion."""
        clicked_tab = self.season_notebook.tk.call(self.season_notebook._w, "identify", "tab", event.x, event.y)
        if clicked_tab != '':
            index = int(clicked_tab)
            seasons = self.season_manager.get_all_seasons()
            if 0 <= index < len(seasons):
                self.selected_season_for_deletion = seasons[index]
    
    def _display_current_season(self):
        """Display data for the current season."""
        if self.current_season:
            debug_print(f"Displaying current season: {self.current_season.display_name}")
            self.table_manager.display_season_data(self.current_season)
    
    def _show_add_season_dialog(self):
        """Show dialog to add a new season."""
        self.table_manager._finish_editing()
        
        dialog = AddSeasonDialog(self.frame, self.season_manager, self._on_season_created)
        dialog.show()
    
    def _show_add_school_dialog(self):
        """Show dialog to add a new school."""
        if not self.current_season:
            messagebox.showwarning("No Season", "Please create a season first.")
            return
        
        # Simple add school dialog
        dialog = tk.Toplevel(self.frame)
        dialog.title("Add New School")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        main_frame = tk.Frame(dialog)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(main_frame, text="Name in CRR:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=10)
        
        crr_name_var = tk.StringVar()
        entry = tk.Entry(main_frame, textvariable=crr_name_var, font=FONT_ENTRY, width=25)
        entry.grid(row=0, column=1, padx=5, pady=10, sticky='w')
        entry.focus_set()
        
        tk.Label(main_frame, text="(Primary identifier used throughout the system)",
                font=("Helvetica", 9), fg='gray').grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        def add_school():
            crr_name = crr_name_var.get().strip()
            if not crr_name:
                messagebox.showerror("Invalid Input", "Name in CRR cannot be empty.")
                return
            
            # Check if exists
            if self.season_manager.db.get_school_id_by_crr_name(crr_name) is not None:
                messagebox.showerror("School Exists", f"School '{crr_name}' already exists.")
                return
            
            try:
                cursor = self.season_manager.db.conn.cursor()
                cursor.execute("BEGIN TRANSACTION")
                
                # Insert school
                cursor.execute("INSERT INTO schools (name, short_name, acronym, crr_name, color) VALUES (?, ?, ?, ?, ?)",
                             ("", "", "", crr_name, ""))
                school_id = cursor.lastrowid
                
                # Add to current season
                cursor.execute("""
                    INSERT INTO school_participations 
                    (school_id, start_date, end_date, openweight_women, heavyweight_men, lightweight_men, lightweight_women)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (school_id, self.current_season.start_date, self.current_season.end_date, 
                     False, False, False, False))
                
                self.season_manager.db.conn.commit()
                # Refresh caches after adding new school
                self.season_manager.db.refresh_school_caches()
                
                dialog.destroy()
                self._display_current_season()
                messagebox.showinfo("Success", f"School '{crr_name}' added successfully.")
                
            except Exception as e:
                self.season_manager.db.conn.rollback()
                messagebox.showerror("Error", f"Failed to add school: {str(e)}")
        
        tk.Button(button_frame, text="Add School", font=FONT_BUTTON, command=add_school, 
                 default='active', bg='#28a745', fg='white').pack(side='left', padx=5)
        tk.Button(button_frame, text="Cancel", font=FONT_BUTTON, 
                 command=dialog.destroy).pack(side='left', padx=5)
        
        dialog.bind('<Return>', lambda e: add_school())
        dialog.bind('<Escape>', lambda e: dialog.destroy())
    
    def _delete_selected(self):
        """Delete selected schools or season."""
        self.table_manager._finish_editing()
        
        selected_schools = self.table_manager.get_selected_schools()
        if selected_schools:
            self._delete_selected_schools(selected_schools)
        elif self.selected_season_for_deletion:
            self._delete_season(self.selected_season_for_deletion)
        else:
            messagebox.showwarning("No Selection", "Select schools (row numbers) or right-click a season tab.")
    
    def _delete_selected_schools(self, school_names: List[str]):
        """Delete selected schools."""
        school_list = '\n'.join(f"• {school}" for school in school_names)
        if not messagebox.askyesno("Confirm Deletion", 
                                   f"Delete {len(school_names)} school(s)?\n\n{school_list}\n\nThis cannot be undone!"):
            return
        
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            for crr_name in school_names:
                cursor.execute("SELECT school_id FROM schools WHERE crr_name = ?", (crr_name,))
                result = cursor.fetchone()
                if result:
                    school_id = result[0]
                    cursor.execute("DELETE FROM school_participations WHERE school_id = ?", (school_id,))
                    cursor.execute("DELETE FROM schools WHERE school_id = ?", (school_id,))
            
            self.db.conn.commit()
            # Refresh caches after deletion
            self.db.refresh_school_caches()
            self.table_manager.selected_rows.clear()
            self._display_current_season()
            messagebox.showinfo("Success", f"Deleted {len(school_names)} school(s).")
            
        except Exception as e:
            self.db.conn.rollback()
            messagebox.showerror("Error", f"Failed to delete schools: {str(e)}")
    
    def _delete_season(self, season: Season):
        """Delete a season."""
        count = self.db.get_school_participation_count_for_season(str(season.start_year))
        
        if count == 0:
            messagebox.showwarning("Empty Season", "Season has no data to delete.")
            return
        
        if messagebox.askyesno("Confirm Deletion", 
                              f"Delete season '{season.display_name}' and {count} participation records?"):
            success, deleted = self.db.delete_school_participation_season(str(season.start_year))
            if success:
                messagebox.showinfo("Success", f"Deleted {deleted} records.")
                self._load_seasons()
    
    def _on_season_created(self, new_season: Season):
        """Callback when a new season is created."""
        self._load_seasons()
        
        # Select the new season
        seasons = self.season_manager.get_all_seasons()
        try:
            new_index = seasons.index(new_season)
            self.season_notebook.select(new_index)
            self.current_season = new_season
            self._display_current_season()
        except ValueError:
            pass
    
    def refresh(self):
        """Refresh tab data."""
        self.table_manager._finish_editing()
        # Refresh caches before displaying
        self.db.refresh_school_caches()
        if self.current_season:
            self._display_current_season()