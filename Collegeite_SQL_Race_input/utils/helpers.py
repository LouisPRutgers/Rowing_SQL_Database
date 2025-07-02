"""
Helper utility functions for the rowing database application.
Enhanced with D1 Schools tab components for better code organization.
"""

from tkinter import ttk, messagebox
from typing import Dict, List, Tuple, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime


# ── Original Helper Functions ──────────────────────────────────────────

def format_event_display_name(gender, weight, event_boat_class, boat_type, round_name, event_distance=None, scheduled_at=None):
    """
    Format an event name for display in dropdowns and other UI elements.
    
    Args:
        gender: 'M' or 'W'
        weight: 'LW', 'HW', or 'OW'  
        event_boat_class: '1V', '2V', etc.
        boat_type: '8+', '4+', etc.
        round_name: 'Final', 'Heat 1', etc.
        event_distance: '2k', '5k', etc. (optional)
        scheduled_at: Optional datetime string
        
    Returns:
        Formatted string like "Openweight Women's 1V 8+ - Final (2k)"
    """
    # Gender mapping
    gender_map = {
        'M': "Men's",
        'W': "Women's"
    }
    
    # Weight mapping
    weight_map = {
        'LW': "Lightweight",
        'HW': "Heavyweight", 
        'OW': "Openweight"
    }
    
    # Build the display name
    gender_str = gender_map.get(gender, gender)
    weight_str = weight_map.get(weight, weight)
    
    display_name = f"{weight_str} {gender_str} {event_boat_class} {boat_type} - {round_name}"
      
    # Add scheduled time if provided
    if scheduled_at:
        display_name += f" at {scheduled_at}"
    
    return display_name


def format_regatta_display_name(name, location, start_date):
    """
    Format a regatta name for display in dropdowns.
    
    Args:
        name: Regatta name
        location: Regatta location
        start_date: Start date string
        
    Returns:
        Formatted string like "Head of the Charles - Boston (2024-10-19)"
    """
    if start_date:
        return f"{name} - ({start_date})"
    else:
        return f"{name}"



def auto_size_treeview_columns(treeview: ttk.Treeview, data_rows: List[Tuple], 
                              column_headers: Dict[str, str], 
                              min_widths: Dict[str, int] = None,
                              font_width_multiplier: int = 8, 
                              padding: int = 20):
    """
    Auto-size treeview columns based on content width.
    
    Args:
        treeview: The ttk.Treeview widget to resize
        data_rows: List of tuples containing the data for each row
        column_headers: Dict mapping column identifiers to header text
        min_widths: Dict of minimum widths for each column (optional)
        font_width_multiplier: Pixels per character estimate
        padding: Extra padding in pixels
    """
    if not data_rows:
        return
    
    # Initialize with header text lengths
    column_widths = {col: len(header) for col, header in column_headers.items()}
    
    # Get column identifiers in order
    columns = list(column_headers.keys())
    
    # Calculate maximum content width for each column
    for row_data in data_rows:
        for i, value in enumerate(row_data):
            if i < len(columns):
                column_id = columns[i]
                str_value = str(value) if value is not None else ""
                column_widths[column_id] = max(column_widths[column_id], len(str_value))
    
    # Set default minimum widths if not provided
    if min_widths is None:
        min_widths = {}
    
    # Apply calculated widths to treeview columns
    for column_id, char_width in column_widths.items():
        pixel_width = char_width * font_width_multiplier + padding
        min_width = min_widths.get(column_id, 80)  # Default minimum 80px
        final_width = max(pixel_width, min_width)
        treeview.column(column_id, width=final_width)


def make_treeview_sortable(treeview: ttk.Treeview, columns: List[str]):
    """
    Make a treeview sortable by clicking column headers.
    
    Args:
        treeview: The ttk.Treeview widget to make sortable
        columns: List of column identifiers that should be sortable
    """
    # Dictionary to track sort direction for each column
    sort_directions = {col: False for col in columns}  # False = ascending, True = descending
    
    def sort_treeview(col):
        """Sort treeview by the specified column."""
        # Get all items with their values
        items = [(treeview.set(item, col), item) for item in treeview.get_children('')]
        
        # Determine sort direction
        reverse = sort_directions[col]
        sort_directions[col] = not sort_directions[col]  # Toggle for next click
        
        # Smart sorting: try numeric first, fall back to string
        try:
            # Try to sort numerically (handles times, positions, etc.)
            items.sort(key=lambda x: float(x[0].replace('+', '').replace(':', '').replace('.', '')) if x[0] else 0, reverse=reverse)
        except (ValueError, AttributeError):
            # Fall back to string sorting
            items.sort(key=lambda x: str(x[0]).lower(), reverse=reverse)
        
        # Rearrange items in treeview
        for index, (val, item) in enumerate(items):
            treeview.move(item, '', index)
        
        # Update column header to show sort direction
        current_text = treeview.heading(col)['text']
        base_text = current_text.replace(' ↑', '').replace(' ↓', '')
        arrow = ' ↑' if reverse else ' ↓'
        treeview.heading(col, text=base_text + arrow)
        
        # Clear arrows from other columns
        for other_col in columns:
            if other_col != col:
                other_text = treeview.heading(other_col)['text']
                clean_text = other_text.replace(' ↑', '').replace(' ↓', '')
                treeview.heading(other_col, text=clean_text)
    
    # Bind click events to column headers
    for col in columns:
        treeview.heading(col, command=lambda c=col: sort_treeview(c))
        # Add cursor change to indicate clickability
        treeview.heading(col, text=treeview.heading(col)['text'])


def _smart_sort_key(value: Any) -> Tuple[int, Any]:
    """
    Create a smart sort key that handles different data types intelligently.
    
    Returns a tuple where the first element indicates the type priority:
    0 = numbers, 1 = strings, 2 = empty/None
    """
    if value is None or value == '':
        return (2, '')
    
    str_value = str(value).strip()
    
    # Try to parse as number (including times like "18:47.000")
    try:
        # Handle time formats (mm:ss.fff)
        if ':' in str_value:
            parts = str_value.replace('.', ':').split(':')
            if len(parts) >= 2:
                minutes = float(parts[0])
                seconds = float(parts[1])
                milliseconds = float(parts[2]) if len(parts) > 2 else 0
                total_seconds = minutes * 60 + seconds + milliseconds / 1000
                return (0, total_seconds)
        
        # Handle margin formats ("+3.000")
        clean_value = str_value.replace('+', '').replace('-', '')
        if clean_value.replace('.', '').isdigit():
            return (0, float(clean_value))
        
        # Try direct numeric conversion
        return (0, float(str_value))
    except (ValueError, IndexError):
        pass
    
    # Fall back to string sorting
    return (1, str_value.lower())

def parse_time_input(text: str) -> Tuple[int, int, int]:
    """
    Parse time input with smart digit interpretation.
    Returns (minutes, seconds, milliseconds).
    
    Smart digit logic (based on Race Ranker):
    - Extract all digits from input
    - First digit: single minutes
    - Second digit: 10s of seconds  
    - Third digit: 1s of seconds
    - Fourth digit: tenths of seconds
    - Fifth digit: hundredths of seconds
    - Sixth digit: thousandths of seconds
    - Additional digits: add to 10s of minutes
    
    Examples:
    - "704" -> (7, 4, 0) = 7:04.000
    - "7" -> (7, 0, 0) = 7:00.000  
    - "1150123" -> (11, 50, 123) = 11:50.123
    - "11150123" -> (111, 50, 123) = 111:50.123
    - "7:04.123" -> (7, 4, 123) = 7:04.123
    """
    text = text.strip()
    
    # If it contains colon or period, try to parse as formatted time first
    if ":" in text or "." in text:
        try:
            # Handle formats like "7:04.123" or "7:04"
            if ":" in text:
                time_part, *rest = text.split(":")
                minutes = int(time_part) if time_part else 0
                
                if rest:
                    sec_part = rest[0]
                    if "." in sec_part:
                        sec_str, ms_str = sec_part.split(".", 1)
                        seconds = int(sec_str) if sec_str else 0
                        # Pad or truncate milliseconds to 3 digits
                        ms_str = ms_str.ljust(3, '0')[:3]
                        milliseconds = int(ms_str)
                    else:
                        seconds = int(sec_part) if sec_part else 0
                        milliseconds = 0
                else:
                    seconds = 0
                    milliseconds = 0
            elif "." in text:
                # Handle format like "404.123" (assume seconds.fff)
                sec_str, ms_str = text.split(".", 1)
                minutes = 0
                seconds = int(sec_str) if sec_str else 0
                ms_str = ms_str.ljust(3, '0')[:3]
                milliseconds = int(ms_str)
                
            if seconds >= 60:
                raise ValueError("Seconds must be less than 60")
                
            return minutes, seconds, milliseconds
        except (ValueError, IndexError):
            # Fall through to digit parsing if formatted parsing fails
            pass
    
    # Extract only digits for smart parsing
    digits = "".join(filter(str.isdigit, text))
    if not digits:
        raise ValueError("No digits found")
        
    # Smart digit parsing based on position
    if len(digits) <= 6:
        # For 6 or fewer digits, parse as: M SS T H T
        # where M=minutes, S=seconds, T=tenths, H=hundredths, T=thousandths
        digits = digits.ljust(6, '0')  # Pad right with zeros
        
        minutes = int(digits[0])
        seconds = int(digits[1:3])
        milliseconds = int(digits[3:6])
    else:
        # For more than 6 digits, extra digits become 10s of minutes
        # Format: [extra digits for 10s of minutes][M][SS][THT]
        extra_digits = digits[:-6]  # All but last 6 digits
        core_digits = digits[-6:]   # Last 6 digits
        
        tens_of_minutes = int(extra_digits)
        single_minutes = int(core_digits[0])
        minutes = tens_of_minutes * 10 + single_minutes
        seconds = int(core_digits[1:3])
        milliseconds = int(core_digits[3:6])
    
    if seconds >= 60:
        raise ValueError("Seconds must be less than 60")
        
    return minutes, seconds, milliseconds


def format_time_seconds(total_seconds: float) -> str:
    """Convert seconds to mm:ss.fff format."""
    total_ms = int(round(total_seconds * 1000))
    minutes, remainder = divmod(total_ms, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def time_to_seconds(time_str: str) -> float:
    """Convert time string to total seconds."""
    try:
        minutes, seconds, milliseconds = parse_time_input(time_str)
        return minutes * 60 + seconds + milliseconds / 1000.0
    except ValueError:
        return 0.0


# ── D1 Schools Tab Helper Classes ──────────────────────────────────────

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


class CRRNameValidator:
    """Handles CRR name validation with comprehensive debugging."""
    
    @staticmethod
    def validate_uniqueness(db_manager, new_name: str, current_crr_name: str) -> Tuple[bool, str]:
        """
        Check if CRR name already exists, excluding the current school being edited.
        
        Returns:
            (is_valid, debug_message): Tuple of validation result and debug info
        """
        debug_lines = []
        debug_lines.append(f"🔍 CRR Name Validation:")
        debug_lines.append(f"   new_name: '{new_name}'")
        debug_lines.append(f"   current_crr_name: '{current_crr_name}'")
        
        # Get school_id for the current school
        school_id = db_manager.get_school_id_by_crr_name(current_crr_name)
        debug_lines.append(f"   school_id for '{current_crr_name}': {school_id}")
        
        if school_id is None:
            debug_lines.append(f"   ❌ Current school '{current_crr_name}' not found in cache")
            # School not found, so new name definitely conflicts if it exists
            exists = db_manager.get_school_id_by_crr_name(new_name) is not None
            debug_lines.append(f"   Checking if '{new_name}' exists: {exists}")
            debug_message = "\n".join(debug_lines)
            return not exists, debug_message
        
        # Check current cache state
        debug_lines.append(f"   📋 Current cache state:")
        cache_names = list(db_manager.crr_name_to_id_cache.keys())[:5]  # Show first 5
        debug_lines.append(f"   Cache contains {len(db_manager.crr_name_to_id_cache)} names: {cache_names}...")
        debug_lines.append(f"   '{current_crr_name}' in cache: {current_crr_name in db_manager.crr_name_to_id_cache}")
        debug_lines.append(f"   '{new_name}' in cache: {new_name in db_manager.crr_name_to_id_cache}")
        
        # Use DatabaseManager's validation method
        is_unique = db_manager.validate_crr_name_uniqueness(new_name, school_id)
        debug_lines.append(f"   DatabaseManager.validate_crr_name_uniqueness('{new_name}', {school_id}): {is_unique}")
        
        # Double-check with direct database query
        cursor = db_manager.conn.cursor()
        cursor.execute("SELECT school_id, crr_name FROM schools WHERE crr_name = ?", (new_name,))
        direct_results = cursor.fetchall()
        debug_lines.append(f"   Direct DB query for '{new_name}': {direct_results}")
        
        is_valid = is_unique
        debug_lines.append(f"   🎯 Final result: {is_valid} (True means name is valid/unique)")
        
        debug_message = "\n".join(debug_lines)
        return is_valid, debug_message


def debug_print(message: str, level: str = "INFO"):
    """Enhanced debug printing with levels."""
    prefix_map = {
        "DEBUG": "🔍",
        "INFO": "ℹ️",
        "SUCCESS": "✅", 
        "WARNING": "⚠️",
        "ERROR": "❌",
        "CRITICAL": "💥"
    }
    
    prefix = prefix_map.get(level, "📝")
    print(f"{prefix} {message}")


def validate_school_field(field_name: str, new_value: str, original_value: str) -> Tuple[bool, str]:
    """Validate school field changes."""
    if field_name == 'crr_name':
        if not new_value or not new_value.strip():
            return False, "Name in CRR cannot be empty"
        
        if new_value != original_value:
            # Additional validation can be added here
            pass
    
    return True, ""