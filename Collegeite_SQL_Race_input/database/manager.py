"""
Enhanced Database manager for handling all SQLite database operations.
Replaces: Collegeite_SQL_Race_input/database/manager.py

Key Features:
- CRR name is the single source of truth for all school identification
- CRR name changes propagate throughout the entire system
- School ID-based architecture with CRR name change notifications
- All historical data (conferences, participations) updated when CRR names change
- Backward compatibility maintained for existing code
"""

import sqlite3
import os
from tkinter import messagebox
from typing import List, Tuple, Optional, Dict, Callable
from dataclasses import dataclass

@dataclass
class School:
    """Represents a school with all its properties."""
    school_id: int
    name: str
    short_name: str
    acronym: str
    crr_name: str  # Single source of truth for school identification
    color: str
    
    def __post_init__(self):
        """Ensure CRR name is valid."""
        if not self.crr_name or not self.crr_name.strip():
            raise ValueError("CRR name cannot be empty")

class SchoolChangeNotifier:
    """Notifies all registered components when school data changes."""
    
    def __init__(self):
        self._listeners: List[Callable[[str, School, School], None]] = []
    
    def register_listener(self, callback: Callable[[str, School, School], None]):
        """Register a callback for school changes.
        
        Callback signature: (change_type, old_school, new_school)
        change_type: 'crr_name_changed', 'school_updated', 'school_deleted', 'school_created'
        """
        self._listeners.append(callback)
    
    def notify_school_change(self, change_type: str, old_school: School, new_school: School = None):
        """Notify all listeners of a school change."""
        for listener in self._listeners:
            try:
                listener(change_type, old_school, new_school)
            except Exception as e:
                print(f"Error in school change listener: {e}")

class DatabaseManager:
    """Enhanced database manager with CRR name-based school management and full propagation."""
    
    def __init__(self, db_path: str = "rowing_database.db"):
        self.db_path = db_path
        if not os.path.exists(db_path):
            messagebox.showerror(
                "Database Not Found", 
                f"Database file '{db_path}' not found.\n\n"
                "Please run 'python database_initializer.py' first to create the database with schools and teams."
            )
            exit(1)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # Initialize enhanced school management
        self.school_cache: Dict[int, School] = {}
        self.crr_name_to_id_cache: Dict[str, int] = {}
        self.change_notifier = SchoolChangeNotifier()
        
        # Verify database and initialize caches
        self._verify_database_initialized()
        self._initialize_school_caches()
    
    def _verify_database_initialized(self):
        """Verify that the database has been properly initialized."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM schools")
            school_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM teams")
            team_count = cursor.fetchone()[0]
            
            if school_count == 0 or team_count == 0:
                messagebox.showerror(
                    "Database Not Initialized", 
                    "The database exists but appears to be empty.\n\n"
                    "Please run 'python database_initializer.py' to populate it with schools and teams."
                )
                exit(1)
            
            print(f"Database ready: {school_count} schools, {team_count} teams")
            
        except sqlite3.OperationalError:
            messagebox.showerror(
                "Invalid Database", 
                "The database file exists but doesn't have the correct schema.\n\n"
                "Please run 'python database_initializer.py' to create a properly structured database."
            )
            exit(1)
    
    def _initialize_school_caches(self):
        """Initialize in-memory caches for fast school lookups."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT school_id, name, COALESCE(short_name, '') as short_name, 
                   COALESCE(acronym, '') as acronym, crr_name, 
                   COALESCE(color, '') as color
            FROM schools 
            WHERE crr_name IS NOT NULL AND crr_name != ''
            ORDER BY crr_name
        """)
        
        self.school_cache.clear()
        self.crr_name_to_id_cache.clear()
        
        for row in cursor.fetchall():
            school = School(*row)
            self.school_cache[school.school_id] = school
            self.crr_name_to_id_cache[school.crr_name] = school.school_id
    
    # ── Enhanced School Management Methods ──────────────────────────────────
    
    def register_school_change_listener(self, callback: Callable[[str, School, School], None]):
        """Register a callback for school changes. Used by UI components for updates."""
        self.change_notifier.register_listener(callback)
    
    def get_school_by_id(self, school_id: int) -> Optional[School]:
        """Get school by ID."""
        return self.school_cache.get(school_id)
    
    def get_school_by_crr_name(self, crr_name: str) -> Optional[School]:
        """Get school by CRR name (primary lookup method)."""
        school_id = self.crr_name_to_id_cache.get(crr_name)
        if school_id:
            return self.school_cache.get(school_id)
        return None
    
    def get_school_id_by_crr_name(self, crr_name: str) -> Optional[int]:
        """Get school ID by CRR name."""
        return self.crr_name_to_id_cache.get(crr_name)
    
    def get_all_schools(self) -> List[School]:
        """Get all schools sorted by CRR name."""
        return sorted(self.school_cache.values(), key=lambda s: s.crr_name.lower())
    
    def get_crr_names_for_autocomplete(self) -> List[str]:
        """Get all CRR names for autocomplete functionality."""
        return sorted(self.crr_name_to_id_cache.keys())
    
    def update_school_field(self, school_id: int, field_name: str, new_value: str) -> bool:
        """Update a school field with FULL SYSTEM PROPAGATION.
        
        When CRR name changes, ALL references throughout the system are updated:
        - Conference affiliations remain linked to the same school
        - School participations remain linked to the same school  
        - Teams remain linked to the same school
        - Entries and results remain linked to the same teams
        - UI components are notified to refresh autocomplete, dropdowns, etc.
        
        Args:
            school_id: ID of school to update
            field_name: 'name', 'short_name', 'acronym', 'crr_name', or 'color'
            new_value: New value for the field
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If field_name invalid, school not found, or CRR name conflicts
        """
        if field_name not in ['name', 'short_name', 'acronym', 'crr_name', 'color']:
            raise ValueError(f"Invalid field name: {field_name}")
        
        old_school = self.school_cache.get(school_id)
        if not old_school:
            raise ValueError(f"School with ID {school_id} not found")
        
        # Validate CRR name uniqueness and requirements
        if field_name == 'crr_name':
            if not new_value or not new_value.strip():
                raise ValueError("CRR name cannot be empty")
            
            new_value = new_value.strip()
            
            # Check if another school already uses this CRR name
            existing_id = self.crr_name_to_id_cache.get(new_value)
            if existing_id and existing_id != school_id:
                raise ValueError(f"CRR name '{new_value}' is already used by another school")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # Update the school record
            cursor.execute(f"UPDATE schools SET {field_name} = ?, updated_at = CURRENT_TIMESTAMP WHERE school_id = ?", 
                          (new_value, school_id))
            
            # Update cache
            if field_name == 'crr_name':
                # Remove old CRR name from cache
                if old_school.crr_name in self.crr_name_to_id_cache:
                    del self.crr_name_to_id_cache[old_school.crr_name]
                # Add new CRR name to cache
                self.crr_name_to_id_cache[new_value] = school_id
                
                print(f"CRR name propagation: '{old_school.crr_name}' → '{new_value}'")
                print("  ✓ School record updated")
                print("  ✓ All teams remain linked (via school_id)")
                print("  ✓ All conference affiliations remain linked (via team_id)")
                print("  ✓ All participations remain linked (via school_id)")
                print("  ✓ All entries/results remain linked (via team_id)")
                print("  ✓ System-wide consistency maintained")
            
            # Create updated school object
            updated_values = {
                'school_id': old_school.school_id,
                'name': old_school.name,
                'short_name': old_school.short_name,
                'acronym': old_school.acronym,
                'crr_name': old_school.crr_name,
                'color': old_school.color
            }
            updated_values[field_name] = new_value
            
            new_school = School(**updated_values)
            self.school_cache[school_id] = new_school
            
            self.conn.commit()
            
            # Notify listeners of the change (UI updates, autocomplete refresh, etc.)
            change_type = 'crr_name_changed' if field_name == 'crr_name' else 'school_updated'
            self.change_notifier.notify_school_change(change_type, old_school, new_school)
            
            return True
            
        except Exception as e:
            self.conn.rollback()
            # Restore cache state on error
            if field_name == 'crr_name' and old_school.crr_name not in self.crr_name_to_id_cache:
                self.crr_name_to_id_cache[old_school.crr_name] = school_id
            raise e
    
    def add_school(self, name: str, short_name: str = "", acronym: str = "", 
                   crr_name: str = "", color: str = "") -> int:
        """Add a new school and return its ID."""
        if not crr_name:
            crr_name = name  # Default CRR name to school name
        
        crr_name = crr_name.strip()
        
        # Check uniqueness
        if crr_name in self.crr_name_to_id_cache:
            raise ValueError(f"CRR name '{crr_name}' already exists")
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO schools (name, short_name, acronym, crr_name, color) 
                VALUES (?, ?, ?, ?, ?)
            """, (name, short_name, acronym, crr_name, color))
            
            school_id = cursor.lastrowid
            
            # Add to cache
            new_school = School(school_id, name, short_name, acronym, crr_name, color)
            self.school_cache[school_id] = new_school
            self.crr_name_to_id_cache[crr_name] = school_id
            
            self.conn.commit()
            
            # Notify listeners
            self.change_notifier.notify_school_change('school_created', None, new_school)
            
            return school_id
            
        except Exception as e:
            self.conn.rollback()
            raise e
    
    # ── Enhanced Backward Compatibility Methods ──────────────────────────────────
    
    def get_teams_for_category(self, gender: str, weight: str) -> List[Tuple[int, str, str]]:
        """Return teams (team_id, crr_name, current_conference) for given gender/weight."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT t.team_id, s.crr_name,
                   COALESCE(ca.conference, 'Unknown') as current_conference
            FROM teams t
            JOIN schools s ON t.school_id = s.school_id
            LEFT JOIN conference_affiliations ca ON t.team_id = ca.team_id 
                AND ca.end_date IS NULL
            WHERE t.gender = ? AND t.weight = ?
            ORDER BY s.crr_name
        """, (gender, weight))
        return cursor.fetchall()
    
    # ── Original Methods Enhanced for CRR Name Support ──────────────────────────────
    
    def get_regattas(self) -> List[Tuple[int, str, str, str, str]]:
        """Return all regattas with (id, name, location, start_date, end_date)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT regatta_id, name, location, start_date, end_date FROM regattas ORDER BY start_date DESC")
        return cursor.fetchall()
    
    def get_events_for_regatta(self, regatta_id: int) -> List[Tuple[int, str, str, str, str, str, str]]:
        """Return events for a specific regatta."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT event_id, boat_type, event_boat_class, gender, weight, round, scheduled_at
            FROM events
            WHERE regatta_id = ?
            ORDER BY scheduled_at, gender, weight, event_boat_class
        """, (regatta_id,))
        return cursor.fetchall()
    
    def get_all_events(self) -> List[Tuple[int, str, str, str, str, str, str, str, str]]:
        """Return all events with regatta info."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT e.event_id, r.name, e.gender, e.weight, e.event_boat_class, e.boat_type, e.round, e.scheduled_at, r.regatta_id
            FROM events e
            JOIN regattas r ON e.regatta_id = r.regatta_id
            ORDER BY r.start_date DESC, e.scheduled_at
        """)
        return cursor.fetchall()
    
    def add_regatta(self, name: str, location: str, start_date: str, end_date: str) -> int:
        """Add a new regatta and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO regattas (name, location, start_date, end_date) VALUES (?, ?, ?, ?)",
            (name, location, start_date, end_date)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def add_event(self, regatta_id: int, boat_type: str, event_boat_class: str, 
                  gender: str, weight: str, round_name: str, scheduled_at: str = None) -> int:
        """Add a new event and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO events (regatta_id, boat_type, event_boat_class, gender, weight, round, scheduled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (regatta_id, boat_type, event_boat_class, gender, weight, round_name, scheduled_at))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_event_date(self, event_id: int) -> str:
        """Get the scheduled date for an event."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COALESCE(e.scheduled_at, r.start_date, '2024-01-01') as event_date
            FROM events e
            JOIN regattas r ON e.regatta_id = r.regatta_id
            WHERE e.event_id = ?
        """, (event_id,))
        
        result = cursor.fetchone()
        return result[0] if result else "2024-01-01"
    
    def get_team_conference_at_date(self, team_id: int, event_date: str) -> str:
        """Get the conference a team was in on a specific date."""
        cursor = self.conn.cursor()
        
        # Extract just the date part if datetime is provided
        date_only = event_date.split(' ')[0] if ' ' in event_date else event_date
        
        cursor.execute("""
            SELECT conference FROM conference_affiliations 
            WHERE team_id = ? 
            AND start_date <= ? 
            AND (end_date IS NULL OR end_date > ?)
            ORDER BY start_date DESC LIMIT 1
        """, (team_id, date_only, date_only))
        
        result = cursor.fetchone()
        return result[0] if result else "Unknown"
    
    def add_entry(self, event_id: int, team_id: int, entry_boat_class: str = None, notes: str = "") -> int:
        """Add a new entry and return its ID, capturing conference at time of event."""
        cursor = self.conn.cursor()
        
        # Get the event date to determine conference at that time
        event_date = self.get_event_date(event_id)
        
        # Get the team's conference at the time of the event
        conference_at_time = self.get_team_conference_at_date(team_id, event_date)
        
        cursor.execute("""
            INSERT INTO entries (event_id, team_id, entry_boat_class, conference_at_time, notes) 
            VALUES (?, ?, ?, ?, ?)
        """, (event_id, team_id, entry_boat_class, conference_at_time, notes))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def update_entry_notes(self, entry_id: int, notes: str) -> bool:
        """Update the notes for an existing entry."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE entries 
                SET notes = ?
                WHERE entry_id = ?
            """, (notes, entry_id))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error updating entry notes: {str(e)}")
            return False

    def get_entry_with_notes(self, entry_id: int) -> Optional[Tuple]:
        """Get entry details including notes."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT e.entry_id, e.event_id, e.team_id, e.entry_boat_class, 
                e.conference_at_time, e.seed, e.notes,
                s.crr_name as school_name
            FROM entries e
            JOIN teams t ON e.team_id = t.team_id
            JOIN schools s ON t.school_id = s.school_id
            WHERE e.entry_id = ?
        """, (entry_id,))
        
        return cursor.fetchone()

    def get_entries_for_event_with_notes(self, event_id: int) -> List[Tuple]:
        """Get all entries for an event including notes."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT e.entry_id, s.crr_name, e.entry_boat_class, r.lane, r.position, r.elapsed_sec, e.notes
            FROM entries e
            JOIN teams t ON e.team_id = t.team_id
            JOIN schools s ON t.school_id = s.school_id
            LEFT JOIN results r ON e.entry_id = r.entry_id
            WHERE e.event_id = ?
            ORDER BY COALESCE(r.position, 999), s.crr_name
        """, (event_id,))
        
        return cursor.fetchall()

    def bulk_update_entry_notes(self, entry_notes_list: List[Tuple[int, str]]) -> bool:
        """Bulk update notes for multiple entries."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            for entry_id, notes in entry_notes_list:
                cursor.execute("""
                    UPDATE entries 
                    SET notes = ?
                    WHERE entry_id = ?
                """, (notes, entry_id))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error bulk updating entry notes: {str(e)}")
            return False

    def add_result(self, entry_id: int, lane: int = None, position: int = None, 
                   elapsed_sec: float = None, margin_sec: float = None) -> int:
        """Add a result and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO results (entry_id, lane, position, elapsed_sec, margin_sec) VALUES (?, ?, ?, ?, ?)",
            (entry_id, lane, position, elapsed_sec, margin_sec)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def add_conference_affiliation(self, team_id: int, conference: str, start_date: str, end_date: str = None) -> int:
        """Add a new conference affiliation for a team."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO conference_affiliations (team_id, conference, start_date, end_date)
            VALUES (?, ?, ?, ?)
        """, (team_id, conference, start_date, end_date))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_conference_history(self, team_id: int) -> List[Tuple[int, str, str, str]]:
        """Get the conference history for a team."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT affiliation_id, conference, start_date, end_date
            FROM conference_affiliations
            WHERE team_id = ?
            ORDER BY start_date DESC
        """, (team_id,))
        
        return cursor.fetchall()
    
    def get_current_conference(self, team_id: int) -> str:
        """Get the current conference for a team."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT conference FROM conference_affiliations
            WHERE team_id = ? AND end_date IS NULL
            ORDER BY start_date DESC LIMIT 1
        """, (team_id,))
        
        result = cursor.fetchone()
        return result[0] if result else "Unknown"
    
    def update_conference_affiliation(self, team_id: int, new_conference: str, change_date: str):
        """Update a team's conference affiliation by ending the current one and starting a new one."""
        cursor = self.conn.cursor()
        
        try:
            # End the current affiliation
            cursor.execute("""
                UPDATE conference_affiliations 
                SET end_date = ?
                WHERE team_id = ? AND end_date IS NULL
            """, (change_date, team_id))
            
            # Add new affiliation
            cursor.execute("""
                INSERT INTO conference_affiliations (team_id, conference, start_date, end_date)
                VALUES (?, ?, ?, NULL)
            """, (team_id, new_conference, change_date))
            
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            raise e
    
    def delete_event(self, event_id: int) -> Tuple[int, int, int]:
        """Delete an event and all associated entries and results."""
        cursor = self.conn.cursor()
        
        try:
            # Step 1: Delete results first (they reference entries)
            cursor.execute("""
                DELETE FROM results 
                WHERE entry_id IN (
                    SELECT entry_id FROM entries WHERE event_id = ?
                )
            """, (event_id,))
            results_deleted = cursor.rowcount
            
            # Step 2: Delete entries (they reference events)
            cursor.execute("DELETE FROM entries WHERE event_id = ?", (event_id,))
            entries_deleted = cursor.rowcount
            
            # Step 3: Delete the event itself
            cursor.execute("DELETE FROM events WHERE event_id = ?", (event_id,))
            events_deleted = cursor.rowcount
            
            # Commit the transaction
            self.conn.commit()
            
            return (results_deleted, entries_deleted, events_deleted)
            
        except Exception as e:
            # Rollback on any error
            self.conn.rollback()
            raise e
    
    def get_event_entry_count(self, event_id: int) -> int:
        """Get the number of entries for a specific event."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entries WHERE event_id = ?", (event_id,))
        return cursor.fetchone()[0]
    
    def get_event_details(self, event_id: int) -> Optional[Tuple[int, str, str, str, str, str, str]]:
        """Get detailed information about a specific event."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT event_id, boat_type, event_boat_class, gender, weight, round, scheduled_at
            FROM events
            WHERE event_id = ?
        """, (event_id,))
        return cursor.fetchone()
    
    def delete_regatta(self, regatta_id: int) -> Tuple[int, int, int, int]:
        """Delete a regatta and all associated events, entries, and results."""
        cursor = self.conn.cursor()
        
        try:
            # Step 1: Delete results first (they reference entries)
            cursor.execute("""
                DELETE FROM results 
                WHERE entry_id IN (
                    SELECT e.entry_id FROM entries e
                    JOIN events ev ON e.event_id = ev.event_id
                    WHERE ev.regatta_id = ?
                )
            """, (regatta_id,))
            results_deleted = cursor.rowcount
            
            # Step 2: Delete entries (they reference events)
            cursor.execute("""
                DELETE FROM entries 
                WHERE event_id IN (
                    SELECT event_id FROM events WHERE regatta_id = ?
                )
            """, (regatta_id,))
            entries_deleted = cursor.rowcount
            
            # Step 3: Delete events (they reference regattas)
            cursor.execute("DELETE FROM events WHERE regatta_id = ?", (regatta_id,))
            events_deleted = cursor.rowcount
            
            # Step 4: Delete the regatta itself
            cursor.execute("DELETE FROM regattas WHERE regatta_id = ?", (regatta_id,))
            regattas_deleted = cursor.rowcount
            
            # Commit the transaction
            self.conn.commit()
            
            return (results_deleted, entries_deleted, events_deleted, regattas_deleted)
            
        except Exception as e:
            # Rollback on any error
            self.conn.rollback()
            raise e
    
    def get_regatta_event_count(self, regatta_id: int) -> int:
        """Get the number of events for a specific regatta."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events WHERE regatta_id = ?", (regatta_id,))
        return cursor.fetchone()[0]
    
    def get_regatta_entry_count(self, regatta_id: int) -> int:
        """Get the number of entries across all events for a specific regatta."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM entries e
            JOIN events ev ON e.event_id = ev.event_id
            WHERE ev.regatta_id = ?
        """, (regatta_id,))
        return cursor.fetchone()[0]
    
    def get_regatta_details(self, regatta_id: int) -> Optional[Tuple[int, str, str, str, str]]:
        """Get detailed information about a specific regatta."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT regatta_id, name, location, start_date, end_date
            FROM regattas
            WHERE regatta_id = ?
        """, (regatta_id,))
        return cursor.fetchone()
    
    # ── D1 School Management Methods Enhanced for CRR Name Propagation ──────────────────────────────────────
    
    def get_school_participations_for_season(self, season_year: str):
        """Get all school participation data for a specific season using CRR names.
        
        Returns data in format expected by D1 Schools tab:
        (name, short_name, acronym, crr_name, color, openweight_women, heavyweight_men, lightweight_men, lightweight_women)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT s.name, COALESCE(s.short_name, '') as short_name, 
                   COALESCE(s.acronym, '') as acronym, s.crr_name, 
                   COALESCE(s.color, '') as color,
                   COALESCE(sp.openweight_women, 0) as openweight_women,
                   COALESCE(sp.heavyweight_men, 0) as heavyweight_men,
                   COALESCE(sp.lightweight_men, 0) as lightweight_men,
                   COALESCE(sp.lightweight_women, 0) as lightweight_women
            FROM schools s
            LEFT JOIN school_participations sp ON s.school_id = sp.school_id
                AND SUBSTR(sp.start_date, 1, 4) = ?
                AND (sp.end_date IS NULL OR SUBSTR(sp.end_date, 1, 4) > ?)
            WHERE s.crr_name IS NOT NULL AND s.crr_name != ''
            ORDER BY s.crr_name
        """, (season_year, season_year))
        
        return cursor.fetchall()

    def update_school_participation(self, crr_name: str, team_type: str, participating: bool, season_display: str) -> bool:
        """Update school participation using CRR name lookup."""
        school_id = self.get_school_id_by_crr_name(crr_name)
        if not school_id:
            print(f"School with CRR name '{crr_name}' not found")
            return False
        
        return self.update_school_participation_by_id(school_id, team_type, participating, season_display)
    
    def update_school_participation_by_id(self, school_id: int, team_type: str, participating: bool, season_display: str) -> bool:
        """Update school participation using school ID."""
        # Extract season year and determine if current
        if " - current" in season_display:
            season_year = season_display.split(' - current')[0]
            is_current = True
        else:
            season_year = season_display.split('-')[0]
            is_current = False
        
        start_date = f"{season_year}-09-01"
        end_date = None if is_current else f"{int(season_year) + 1}-08-31"
        
        cursor = self.conn.cursor()
        
        try:
            # Check if participation record exists for this season
            cursor.execute("""
                SELECT participation_id FROM school_participations
                WHERE school_id = ? AND SUBSTR(start_date, 1, 4) = ?
            """, (school_id, season_year))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute(f"""
                    UPDATE school_participations
                    SET {team_type} = ?
                    WHERE participation_id = ?
                """, (participating, existing[0]))
            else:
                # Create new participation record
                cursor.execute("""
                    INSERT INTO school_participations 
                    (school_id, start_date, end_date, openweight_women, heavyweight_men, lightweight_men, lightweight_women)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (school_id, start_date, end_date, 
                     participating if team_type == 'openweight_women' else False,
                     participating if team_type == 'heavyweight_men' else False,
                     participating if team_type == 'lightweight_men' else False,
                     participating if team_type == 'lightweight_women' else False))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error updating school participation: {str(e)}")
            return False

    def create_school_participation_season(self, start_year: str, end_date: str = None, copy_from_season: str = None) -> bool:
        """Create a new school participation season, optionally copying from another season."""
        start_date = f"{start_year}-09-01"
        
        cursor = self.conn.cursor()
        
        try:
            # If copying from another season, get the source data
            if copy_from_season:
                if " - current" in copy_from_season:
                    source_year = copy_from_season.split(' - current')[0]
                else:
                    source_year = copy_from_season.split('-')[0]
                
                # Get source participation data
                cursor.execute("""
                    SELECT school_id, openweight_women, heavyweight_men, lightweight_men, lightweight_women
                    FROM school_participations
                    WHERE SUBSTR(start_date, 1, 4) = ?
                """, (source_year,))
                
                source_data = cursor.fetchall()
                
                copied_count = 0
                for school_id, ow, hm, lm, lw in source_data:
                    # Check if target season participation already exists
                    cursor.execute("""
                        SELECT COUNT(*) FROM school_participations
                        WHERE school_id = ? AND SUBSTR(start_date, 1, 4) = ?
                    """, (school_id, start_year))
                    
                    if cursor.fetchone()[0] == 0:
                        cursor.execute("""
                            INSERT INTO school_participations 
                            (school_id, start_date, end_date, openweight_women, heavyweight_men, lightweight_men, lightweight_women)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (school_id, start_date, end_date, ow, hm, lm, lw))
                        copied_count += 1
                
                print(f"✓ Copied {copied_count} school participations from {copy_from_season}")
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error creating school participation season: {str(e)}")
            return False

    def get_school_participation_count_for_season(self, season_year: str) -> int:
        """Get the count of school participation records for a specific season."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM school_participations
            WHERE SUBSTR(start_date, 1, 4) = ?
        """, (season_year,))
        
        return cursor.fetchone()[0]

    def delete_school_participation_season(self, season_year: str) -> Tuple[bool, int]:
        """Delete all school participation data for a specific season."""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM school_participations
                WHERE SUBSTR(start_date, 1, 4) = ?
            """, (season_year,))
            
            deleted_count = cursor.rowcount
            self.conn.commit()
            
            print(f"✓ Deleted {deleted_count} school participation records for season {season_year}")
            return True, deleted_count
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error deleting school participation season: {str(e)}")
            return False, 0

    def get_all_schools_with_details(self):
        """Get all schools with their extended information."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT school_id, name, COALESCE(short_name, '') as short_name, 
                   COALESCE(acronym, '') as acronym, crr_name, COALESCE(color, '') as color
            FROM schools
            WHERE crr_name IS NOT NULL AND crr_name != ''
            ORDER BY crr_name
        """)
        
        return cursor.fetchall()

    def update_school_details(self, school_id: int, short_name: str = None, acronym: str = None, 
                             crr_name: str = None, color: str = None) -> bool:
        """Update extended details for a school (legacy method - use update_school_field instead)."""
        try:
            if short_name is not None:
                self.update_school_field(school_id, 'short_name', short_name)
            if acronym is not None:
                self.update_school_field(school_id, 'acronym', acronym)
            if crr_name is not None:
                self.update_school_field(school_id, 'crr_name', crr_name)
            if color is not None:
                self.update_school_field(school_id, 'color', color)
            return True
        except Exception as e:
            print(f"❌ Error updating school details: {str(e)}")
            return False

    def ensure_school_participations_table_exists(self) -> bool:
        """Ensure the school_participations table exists with the correct schema."""
        cursor = self.conn.cursor()
        
        try:
            # Check if table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='school_participations'
            """)
            
            if not cursor.fetchone():
                # Create the table
                cursor.execute("""
                    CREATE TABLE school_participations (
                        participation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        school_id INTEGER NOT NULL,
                        start_date DATE NOT NULL,
                        end_date DATE,
                        openweight_women BOOLEAN DEFAULT FALSE,
                        heavyweight_men BOOLEAN DEFAULT FALSE,
                        lightweight_men BOOLEAN DEFAULT FALSE,
                        lightweight_women BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (school_id) REFERENCES schools (school_id) ON UPDATE CASCADE ON DELETE CASCADE
                    )
                """)
                print("✓ Created school_participations table")
            
            # Check if schools table has extended columns
            cursor.execute("PRAGMA table_info(schools)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns if they don't exist
            columns_to_add = [
                ("short_name", "TEXT"),
                ("acronym", "TEXT"), 
                ("crr_name", "TEXT"),
                ("color", "TEXT"),
                ("created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
                ("updated_at", "DATETIME DEFAULT CURRENT_TIMESTAMP")
            ]
            
            for column_name, column_type in columns_to_add:
                if column_name not in existing_columns:
                    cursor.execute(f"ALTER TABLE schools ADD COLUMN {column_name} {column_type}")
                    print(f"✓ Added {column_name} column to schools table")
            
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error ensuring school_participations table: {str(e)}")
            return False

    def populate_initial_school_participations(self) -> int:
        """Create initial school participation records based on existing teams."""
        cursor = self.conn.cursor()
        
        try:
            from datetime import datetime
            current_year = datetime.now().year
            start_date = f"{current_year}-09-01"
            
            # Create participation records based on existing teams
            cursor.execute("""
                SELECT s.school_id,
                       MAX(CASE WHEN t.gender = 'W' AND t.weight = 'OW' THEN 1 ELSE 0 END) as openweight_women,
                       MAX(CASE WHEN t.gender = 'M' AND t.weight = 'HW' THEN 1 ELSE 0 END) as heavyweight_men,
                       MAX(CASE WHEN t.gender = 'M' AND t.weight = 'LW' THEN 1 ELSE 0 END) as lightweight_men,
                       MAX(CASE WHEN t.gender = 'W' AND t.weight = 'LW' THEN 1 ELSE 0 END) as lightweight_women
                FROM schools s
                LEFT JOIN teams t ON s.school_id = t.school_id
                WHERE s.crr_name IS NOT NULL AND s.crr_name != ''
                GROUP BY s.school_id
            """)
            
            team_data = cursor.fetchall()
            participation_count = 0
            
            for school_id, ow, hm, lm, lw in team_data:
                # Only create participation record if school has at least one team
                if ow or hm or lm or lw:
                    # Check if participation already exists
                    cursor.execute("""
                        SELECT COUNT(*) FROM school_participations
                        WHERE school_id = ? AND SUBSTR(start_date, 1, 4) = ?
                    """, (school_id, str(current_year)))
                    
                    if cursor.fetchone()[0] == 0:
                        cursor.execute("""
                            INSERT INTO school_participations 
                            (school_id, start_date, end_date, openweight_women, heavyweight_men, lightweight_men, lightweight_women)
                            VALUES (?, ?, NULL, ?, ?, ?, ?)
                        """, (school_id, start_date, bool(ow), bool(hm), bool(lm), bool(lw)))
                        participation_count += 1
            
            self.conn.commit()
            print(f"✓ Created {participation_count} initial participation records")
            return participation_count
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Error populating initial school participations: {str(e)}")
            return 0
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
    
    # ── Helper Methods for CRR Name Management ──────────────────────────────────
    
    def refresh_school_caches(self):
        """Refresh school caches after external database changes."""
        self._initialize_school_caches()
    
    def validate_crr_name_uniqueness(self, crr_name: str, exclude_school_id: int = None) -> bool:
        """Validate that a CRR name is unique across all schools."""
        existing_id = self.crr_name_to_id_cache.get(crr_name)
        return existing_id is None or existing_id == exclude_school_id
    
    def get_system_wide_crr_name_usage(self, crr_name: str) -> Dict[str, int]:
        """Get system-wide usage count of a CRR name across all tables.
        
        Returns dict with counts for each table that references the school.
        Useful for understanding impact before making changes.
        """
        school_id = self.get_school_id_by_crr_name(crr_name)
        if not school_id:
            return {}
        
        cursor = self.conn.cursor()
        usage = {}
        
        # Count teams
        cursor.execute("SELECT COUNT(*) FROM teams WHERE school_id = ?", (school_id,))
        usage['teams'] = cursor.fetchone()[0]
        
        # Count conference affiliations (via teams)
        cursor.execute("""
            SELECT COUNT(*) FROM conference_affiliations ca
            JOIN teams t ON ca.team_id = t.team_id
            WHERE t.school_id = ?
        """, (school_id,))
        usage['conference_affiliations'] = cursor.fetchone()[0]
        
        # Count school participations
        cursor.execute("SELECT COUNT(*) FROM school_participations WHERE school_id = ?", (school_id,))
        usage['school_participations'] = cursor.fetchone()[0]
        
        # Count entries (via teams)
        cursor.execute("""
            SELECT COUNT(*) FROM entries e
            JOIN teams t ON e.team_id = t.team_id
            WHERE t.school_id = ?
        """, (school_id,))
        usage['entries'] = cursor.fetchone()[0]
        
        # Count results (via entries and teams)
        cursor.execute("""
            SELECT COUNT(*) FROM results r
            JOIN entries e ON r.entry_id = e.entry_id
            JOIN teams t ON e.team_id = t.team_id
            WHERE t.school_id = ?
        """, (school_id,))
        usage['results'] = cursor.fetchone()[0]
        
        return usage