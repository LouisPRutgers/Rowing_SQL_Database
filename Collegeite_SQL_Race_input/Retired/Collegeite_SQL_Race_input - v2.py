#!/usr/bin/env python3
"""
Rowing Database Entry App
========================

GUI for populating the rowing SQL database with schools, teams, regattas, events, entries, and results.
Based on the improved schema with proper foreign key relationships.

Prerequisites:
- Run database_initializer.py first to set up schools and teams data
- pip install tkcalendar

Features:
- Multi-stage data entry workflow (Regattas → Events → Entries → Results)
- Smart time parsing for both schedule and race times
- Independent event selection in each tab
- Results entry with automatic position calculation
- SQLite backend with proper schema
"""

import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import List, Dict, Optional, Tuple
import os

try:
    from tkcalendar import DateEntry
except ModuleNotFoundError:
    messagebox.showerror("Missing dependency", "pip install tkcalendar")
    exit(1)

# ── Constants ──────────────────────────────────────────────────────────
BOAT_TYPES = ["8+", "4+", "4x", "2x", "1x", "2-"]
EVENT_BOAT_CLASSES = ["1V", "2V", "3V", "4V", "A", "B", "C"]
GENDERS = [("M", "Men"), ("W", "Women")]
WEIGHTS = [("LW", "Lightweight"), ("HW", "Heavyweight"), ("OW", "Openweight")]
ROUNDS = ["Heat 1", "Heat 2", "Heat 3", "Semi 1", "Semi 2", "Final", "Time Trial"]

FONT_LABEL = ("Helvetica", 12)
FONT_ENTRY = ("Helvetica", 11)
FONT_BUTTON = ("Helvetica", 11, "bold")
FONT_TITLE = ("Helvetica", 16, "bold")

class DatabaseManager:
    """Handles all SQLite database operations."""
    
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
        
        # Verify database has been initialized
        self._verify_database_initialized()
    
    def _verify_database_initialized(self):
        """Verify that the database has been properly initialized with schools and teams."""
        cursor = self.conn.cursor()
        
        # Check if schools table exists and has data
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
    
    def get_teams_for_category(self, gender: str, weight: str) -> List[Tuple[int, str, str]]:
        """Return teams (team_id, school_name, conference) for given gender/weight."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT t.team_id, s.name, t.conference
            FROM teams t
            JOIN schools s ON t.school_id = s.school_id
            WHERE t.gender = ? AND t.weight = ?
            ORDER BY s.name
        """, (gender, weight))
        return cursor.fetchall()
    
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
    
    def add_entry(self, event_id: int, team_id: int, entry_boat_class: str = None) -> int:
        """Add a new entry and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO entries (event_id, team_id, entry_boat_class) VALUES (?, ?, ?)",
            (event_id, team_id, entry_boat_class)
        )
        self.conn.commit()
        return cursor.lastrowid
    
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

class ScheduleTimeEntry(tk.Entry):
    """Entry widget for schedule time input with smart parsing."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, font=FONT_ENTRY, **kwargs)
        self.bind("<FocusOut>", self._normalize)
        self.bind("<Return>", self._normalize)
        
        # Add placeholder text
        self._add_placeholder()
    
    def _add_placeholder(self):
        """Add placeholder text to guide user input."""
        self.insert(0, "e.g. 9:30, 1400")
        self.config(fg='gray')
        self.bind('<FocusIn>', self._clear_placeholder)
    
    def _clear_placeholder(self, event):
        """Clear placeholder text when user starts typing."""
        if self.get() == "e.g. 9:30, 1400":
            self.delete(0, tk.END)
            self.config(fg='black')
        self.unbind('<FocusIn>')
    
    def _normalize(self, *_):
        """Normalize time input to HH:MM format."""
        text = self.get().strip()
        
        # Handle empty or placeholder text
        if not text or text == "e.g. 9:30, 1400":
            return  # Leave empty - this means optional
        
        try:
            normalized = self._parse_schedule_time(text)
            self.delete(0, tk.END)
            self.insert(0, normalized)
            self.config(fg='black')
        except ValueError as e:
            messagebox.showerror("Invalid Time", str(e))
            self.focus_set()
    
    @staticmethod
    def _parse_schedule_time(text: str) -> str:
        """Parse various time formats and return HH:MM format."""
        text = text.strip().upper()
        
        # Handle common formats
        if not text:
            return ""
        
        # Handle AM/PM format
        am_pm = None
        if text.endswith('AM') or text.endswith('PM'):
            am_pm = text[-2:]
            text = text[:-2].strip()
        
        # Handle colon format (e.g., "9:30", "14:00")
        if ':' in text:
            try:
                parts = text.split(':')
                hours = int(parts[0])
                minutes = int(parts[1]) if len(parts) > 1 else 0
                
                # Handle AM/PM
                if am_pm:
                    if am_pm == 'PM' and hours != 12:
                        hours += 12
                    elif am_pm == 'AM' and hours == 12:
                        hours = 0
                
                if hours > 23 or minutes > 59:
                    raise ValueError("Hours must be 0-23, minutes 0-59")
                
                return f"{hours:02d}:{minutes:02d}"
            except (ValueError, IndexError):
                raise ValueError("Invalid time format. Use HH:MM or H:MM")
        
        # Handle 24-hour format without colon (e.g., "1430", "900")
        if text.isdigit():
            if len(text) <= 2:
                # Just hours (e.g., "9" -> "09:00")
                hours = int(text)
                minutes = 0
            elif len(text) == 3:
                # HMM format (e.g., "930" -> "09:30")
                hours = int(text[0])
                minutes = int(text[1:3])
            elif len(text) == 4:
                # HHMM format (e.g., "1430" -> "14:30")
                hours = int(text[0:2])
                minutes = int(text[2:4])
            else:
                raise ValueError("Invalid time format")
            
            # Handle AM/PM for digit-only input
            if am_pm:
                if am_pm == 'PM' and hours != 12:
                    hours += 12
                elif am_pm == 'AM' and hours == 12:
                    hours = 0
            
            if hours > 23 or minutes > 59:
                raise ValueError("Hours must be 0-23, minutes 0-59")
            
            return f"{hours:02d}:{minutes:02d}"
        
        # Handle text formats
        text_lower = text.lower()
        if 'noon' in text_lower or text_lower == '12pm':
            return "12:00"
        elif 'midnight' in text_lower or text_lower == '12am':
            return "00:00"
        
        raise ValueError("Invalid time format. Examples: 9:30, 1430, 9:30AM, noon")
    
    def get_time_or_none(self) -> str:
        """Get the time in HH:MM format, or None if empty/placeholder."""
        text = self.get().strip()
        if not text or text == "e.g. 9:30, 1400":
            return None
        return text

class TimeEntry(tk.Entry):
    """Entry widget for race time input with smart parsing."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, font=FONT_ENTRY, **kwargs)
        self.bind("<FocusOut>", self._normalize)
        self.bind("<Return>", self._normalize)
    
    def _normalize(self, *_):
        """Normalize time input to mm:ss.fff format."""
        text = self.get().strip()
        if not text:
            return
        
        try:
            minutes, seconds, milliseconds = self._parse_time(text)
            normalized = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            self.delete(0, tk.END)
            self.insert(0, normalized)
        except ValueError as e:
            messagebox.showerror("Invalid Time", str(e))
            self.focus_set()
    
    @staticmethod
    def _parse_time(text: str) -> Tuple[int, int, int]:
        """Parse time input and return (minutes, seconds, milliseconds)."""
        text = text.strip()
        
        # Handle formatted time first
        if ":" in text or "." in text:
            if ":" in text:
                parts = text.split(":")
                minutes = int(parts[0]) if parts[0] else 0
                if len(parts) > 1:
                    sec_part = parts[1]
                    if "." in sec_part:
                        sec_str, ms_str = sec_part.split(".", 1)
                        seconds = int(sec_str) if sec_str else 0
                        ms_str = ms_str.ljust(3, '0')[:3]
                        milliseconds = int(ms_str)
                    else:
                        seconds = int(sec_part) if sec_part else 0
                        milliseconds = 0
                else:
                    seconds = 0
                    milliseconds = 0
            elif "." in text:
                sec_str, ms_str = text.split(".", 1)
                minutes = 0
                seconds = int(sec_str) if sec_str else 0
                ms_str = ms_str.ljust(3, '0')[:3]
                milliseconds = int(ms_str)
        else:
            # Parse digits only
            digits = "".join(filter(str.isdigit, text))
            if not digits:
                raise ValueError("No digits found")
            
            if len(digits) <= 6:
                digits = digits.ljust(6, '0')
                minutes = int(digits[0])
                seconds = int(digits[1:3])
                milliseconds = int(digits[3:6])
            else:
                extra_digits = digits[:-6]
                core_digits = digits[-6:]
                tens_of_minutes = int(extra_digits)
                single_minutes = int(core_digits[0])
                minutes = tens_of_minutes * 10 + single_minutes
                seconds = int(core_digits[1:3])
                milliseconds = int(core_digits[3:6])
        
        if seconds >= 60:
            raise ValueError("Seconds must be less than 60")
        
        return minutes, seconds, milliseconds
    
    def get_seconds(self) -> float:
        """Get the time as total seconds."""
        text = self.get().strip()
        if not text:
            return 0.0
        minutes, seconds, milliseconds = self._parse_time(text)
        return minutes * 60 + seconds + milliseconds / 1000.0

class RowingDatabaseApp:
    """Main application class."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Rowing Database Entry")
        self.root.geometry("1000x700")
        
        # Initialize database
        self.db = DatabaseManager()
        
        # Current workflow state
        self.current_regatta_id: Optional[int] = None
        self.current_event_id: Optional[int] = None
        self.current_event_boat_class: Optional[str] = None
        
        self._setup_ui()
        self._refresh_regatta_list()
        self._populate_regatta_combo()
    
    def _setup_ui(self):
        """Set up the main user interface."""
        # Create notebook for different sections
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self._create_regatta_tab()
        self._create_event_tab()
        self._create_entry_tab()
        self._create_results_tab()
    
    def _create_regatta_tab(self):
        """Create the regatta management tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="1. Regattas")
        
        # Title
        tk.Label(frame, text="Regatta Management", font=FONT_TITLE).pack(pady=10)
        
        # Existing regattas
        tk.Label(frame, text="Existing Regattas:", font=FONT_LABEL).pack(anchor='w', padx=20)
        
        # Regatta listbox
        list_frame = tk.Frame(frame)
        list_frame.pack(fill='x', padx=20, pady=5)
        
        self.regatta_listbox = tk.Listbox(list_frame, height=8, font=FONT_ENTRY)
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.regatta_listbox.yview)
        self.regatta_listbox.config(yscrollcommand=scrollbar.set)
        self.regatta_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # New regatta form
        form_frame = tk.LabelFrame(frame, text="Add New Regatta", font=FONT_LABEL)
        form_frame.pack(fill='x', padx=20, pady=20)
        
        # Regatta name
        tk.Label(form_frame, text="Name:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.regatta_name_entry = tk.Entry(form_frame, font=FONT_ENTRY, width=30)
        self.regatta_name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Location
        tk.Label(form_frame, text="Location:", font=FONT_LABEL).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.regatta_location_entry = tk.Entry(form_frame, font=FONT_ENTRY, width=30)
        self.regatta_location_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Dates
        tk.Label(form_frame, text="Start Date:", font=FONT_LABEL).grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.regatta_start_date = DateEntry(form_frame, font=FONT_ENTRY, date_pattern='yyyy-mm-dd')
        self.regatta_start_date.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        
        tk.Label(form_frame, text="End Date:", font=FONT_LABEL).grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.regatta_end_date = DateEntry(form_frame, font=FONT_ENTRY, date_pattern='yyyy-mm-dd')
        self.regatta_end_date.grid(row=3, column=1, sticky='w', padx=5, pady=5)
        
        # Add button
        tk.Button(form_frame, text="Add Regatta", font=FONT_BUTTON, command=self._add_regatta).grid(row=4, column=1, pady=10)
    
    def _create_event_tab(self):
        """Create the event creation tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="2. Events")
        
        # Title
        tk.Label(frame, text="Event Creation", font=FONT_TITLE).pack(pady=10)
        
        # Regatta selection section
        regatta_frame = tk.LabelFrame(frame, text="Select Regatta", font=FONT_LABEL)
        regatta_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Regatta dropdown
        tk.Label(regatta_frame, text="Regatta:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.regatta_var = tk.StringVar()
        self.regatta_combo = ttk.Combobox(regatta_frame, textvariable=self.regatta_var, 
                                         state='readonly', font=FONT_ENTRY, width=40)
        self.regatta_combo.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.regatta_combo.bind('<<ComboboxSelected>>', self._on_regatta_combo_select)
        
        # Event form
        form_frame = tk.LabelFrame(frame, text="Create New Event", font=FONT_LABEL)
        form_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Boat type
        tk.Label(form_frame, text="Boat Type:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.boat_type_var = tk.StringVar(value=BOAT_TYPES[0])
        boat_type_combo = ttk.Combobox(form_frame, textvariable=self.boat_type_var, values=BOAT_TYPES, state='readonly', font=FONT_ENTRY)
        boat_type_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Event boat class
        tk.Label(form_frame, text="Event Class:", font=FONT_LABEL).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.event_class_var = tk.StringVar(value=EVENT_BOAT_CLASSES[0])
        event_class_combo = ttk.Combobox(form_frame, textvariable=self.event_class_var, values=EVENT_BOAT_CLASSES, state='readonly', font=FONT_ENTRY)
        event_class_combo.grid(row=1, column=1, padx=5, pady=5)
        
        # Gender
        tk.Label(form_frame, text="Gender:", font=FONT_LABEL).grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.gender_var = tk.StringVar(value=GENDERS[0][0])
        gender_combo = ttk.Combobox(form_frame, textvariable=self.gender_var, values=[f"{code} ({desc})" for code, desc in GENDERS], state='readonly', font=FONT_ENTRY)
        gender_combo.grid(row=2, column=1, padx=5, pady=5)
        
        # Weight
        tk.Label(form_frame, text="Weight:", font=FONT_LABEL).grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.weight_var = tk.StringVar(value=WEIGHTS[0][0])
        weight_combo = ttk.Combobox(form_frame, textvariable=self.weight_var, values=[f"{code} ({desc})" for code, desc in WEIGHTS], state='readonly', font=FONT_ENTRY)
        weight_combo.grid(row=3, column=1, padx=5, pady=5)
        
        # Round
        tk.Label(form_frame, text="Round:", font=FONT_LABEL).grid(row=4, column=0, sticky='e', padx=5, pady=5)
        self.round_var = tk.StringVar(value=ROUNDS[0])
        round_combo = ttk.Combobox(form_frame, textvariable=self.round_var, values=ROUNDS, state='normal', font=FONT_ENTRY)
        round_combo.grid(row=4, column=1, padx=5, pady=5)
        
        # Scheduled date and time
        tk.Label(form_frame, text="Scheduled:", font=FONT_LABEL).grid(row=5, column=0, sticky='e', padx=5, pady=5)
        
        datetime_frame = tk.Frame(form_frame)
        datetime_frame.grid(row=5, column=1, columnspan=2, sticky='w', padx=5, pady=5)
        
        # Date picker
        self.scheduled_date = DateEntry(datetime_frame, font=FONT_ENTRY, date_pattern='yyyy-mm-dd', width=12)
        self.scheduled_date.pack(side='left', padx=(0, 15))
        
        # Time input
        tk.Label(datetime_frame, text="Time (optional):", font=FONT_LABEL).pack(side='left')
        self.scheduled_time_entry = ScheduleTimeEntry(datetime_frame, width=10)
        self.scheduled_time_entry.pack(side='left', padx=(5, 0))
        
        # Add event button
        tk.Button(form_frame, text="Create Event", font=FONT_BUTTON, command=self._add_event).grid(row=6, column=1, pady=10)
        
        # Events table for selected regatta
        events_frame = tk.LabelFrame(frame, text="Events for Selected Regatta", font=FONT_LABEL)
        events_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create treeview for events
        columns = ('Boat Type', 'Class', 'Gender', 'Weight', 'Round', 'Scheduled')
        self.events_tree = ttk.Treeview(events_frame, columns=columns, show='headings', height=8)
        
        # Define column headings and widths
        self.events_tree.heading('Boat Type', text='Boat Type')
        self.events_tree.heading('Class', text='Class')
        self.events_tree.heading('Gender', text='Gender')
        self.events_tree.heading('Weight', text='Weight')
        self.events_tree.heading('Round', text='Round')
        self.events_tree.heading('Scheduled', text='Scheduled')
        
        self.events_tree.column('Boat Type', width=80)
        self.events_tree.column('Class', width=60)
        self.events_tree.column('Gender', width=60)
        self.events_tree.column('Weight', width=80)
        self.events_tree.column('Round', width=100)
        self.events_tree.column('Scheduled', width=120)
        
        # Add scrollbar
        events_scrollbar = ttk.Scrollbar(events_frame, orient='vertical', command=self.events_tree.yview)
        self.events_tree.configure(yscrollcommand=events_scrollbar.set)
        
        self.events_tree.pack(side='left', fill='both', expand=True)
        events_scrollbar.pack(side='right', fill='y')
    
    def _create_entry_tab(self):
        """Create the entry management tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="3. Entries")
        
        # Title
        tk.Label(frame, text="Team Entries", font=FONT_TITLE).pack(pady=10)
        
        # Event selection section for entries
        entry_event_frame = tk.LabelFrame(frame, text="Select Event for Entries", font=FONT_LABEL)
        entry_event_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Event dropdown for entries
        tk.Label(entry_event_frame, text="Event:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.entry_event_var = tk.StringVar()
        self.entry_event_combo = ttk.Combobox(entry_event_frame, textvariable=self.entry_event_var, 
                                             state='readonly', font=FONT_ENTRY, width=50)
        self.entry_event_combo.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.entry_event_combo.bind('<<ComboboxSelected>>', self._on_entry_event_combo_select)
        
        # Selected event display
        self.selected_event_label = tk.Label(frame, text="No event selected", font=FONT_LABEL, fg='red')
        self.selected_event_label.pack(pady=5)
        
        # Entry form
        form_frame = tk.LabelFrame(frame, text="Add Team Entry", font=FONT_LABEL)
        form_frame.pack(fill='x', padx=20, pady=20)
        
        # Team selection
        tk.Label(form_frame, text="School:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.team_school_var = tk.StringVar()
        self.team_school_combo = ttk.Combobox(form_frame, textvariable=self.team_school_var, state='readonly', font=FONT_ENTRY, width=25)
        self.team_school_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Entry boat class (auto-filled from event)
        tk.Label(form_frame, text="Team's Boat Class:", font=FONT_LABEL).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.entry_boat_class_entry = tk.Entry(form_frame, font=FONT_ENTRY, width=15)
        self.entry_boat_class_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        tk.Label(form_frame, text="(auto-filled from event, can edit)", font=("Helvetica", 9)).grid(row=1, column=2, padx=5)
        
        # Add entry button
        tk.Button(form_frame, text="Add Entry", font=FONT_BUTTON, command=self._add_entry).grid(row=2, column=1, pady=10)
        
        # Current entries display
        entries_frame = tk.LabelFrame(frame, text="Current Entries", font=FONT_LABEL)
        entries_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create treeview for entries
        entry_columns = ('School', 'Boat Class', 'Conference')
        self.entries_tree = ttk.Treeview(entries_frame, columns=entry_columns, show='headings', height=8)
        
        # Define column headings and widths
        self.entries_tree.heading('School', text='School')
        self.entries_tree.heading('Boat Class', text='Boat Class')
        self.entries_tree.heading('Conference', text='Conference')
        
        self.entries_tree.column('School', width=200)
        self.entries_tree.column('Boat Class', width=100)
        self.entries_tree.column('Conference', width=150)
        
        # Add scrollbar
        entries_scrollbar = ttk.Scrollbar(entries_frame, orient='vertical', command=self.entries_tree.yview)
        self.entries_tree.configure(yscrollcommand=entries_scrollbar.set)
        
        self.entries_tree.pack(side='left', fill='both', expand=True)
        entries_scrollbar.pack(side='right', fill='y')
    
    def _create_results_tab(self):
        """Create the results entry tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="4. Results")
        
        # Title
        tk.Label(frame, text="Race Results", font=FONT_TITLE).pack(pady=10)
        
        # Event selection section for results
        event_selection_frame = tk.LabelFrame(frame, text="Select Event for Results", font=FONT_LABEL)
        event_selection_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Event dropdown for results
        tk.Label(event_selection_frame, text="Event:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.results_event_var = tk.StringVar()
        self.results_event_combo = ttk.Combobox(event_selection_frame, textvariable=self.results_event_var, 
                                               state='readonly', font=FONT_ENTRY, width=50)
        self.results_event_combo.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.results_event_combo.bind('<<ComboboxSelected>>', self._on_results_event_combo_select)
        
        # Selected event info display
        self.selected_event_results_label = tk.Label(frame, text="No event selected for results", font=FONT_LABEL, fg='red')
        self.selected_event_results_label.pack(pady=5)
        
        # Results entry area
        self.results_frame = tk.LabelFrame(frame, text="Enter Results", font=FONT_LABEL)
        self.results_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Headers
        headers_frame = tk.Frame(self.results_frame)
        headers_frame.pack(fill='x', pady=5)
        
        tk.Label(headers_frame, text="Pos", font=FONT_LABEL, width=5).grid(row=0, column=0, padx=2)
        tk.Label(headers_frame, text="", font=FONT_LABEL, width=3).grid(row=0, column=1, padx=2)  # For arrows
        tk.Label(headers_frame, text="School", font=FONT_LABEL, width=20).grid(row=0, column=2, padx=2)
        tk.Label(headers_frame, text="Lane", font=FONT_LABEL, width=6).grid(row=0, column=3, padx=2)
        tk.Label(headers_frame, text="Time (mm:ss.fff)", font=FONT_LABEL, width=15).grid(row=0, column=4, padx=2)
        tk.Label(headers_frame, text="Margin", font=FONT_LABEL, width=10).grid(row=0, column=5, padx=2)
        
        # Scrollable results area
        canvas = tk.Canvas(self.results_frame)
        scrollbar_results = tk.Scrollbar(self.results_frame, orient="vertical", command=canvas.yview)
        self.results_scroll_frame = tk.Frame(canvas)
        
        self.results_scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.results_scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar_results.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar_results.pack(side="right", fill="y")
        
        self.result_entries = []
        
        # Submit results button
        self.submit_results_button = tk.Button(self.results_frame, text="Submit All Results", font=FONT_BUTTON, 
                                              command=self._submit_results, state='disabled')
        self.submit_results_button.pack(pady=10)
    
    # ── Data Population Methods ──────────────────────────────────────────
    
    def _refresh_regatta_list(self):
        """Refresh the regatta listbox with current data."""
        self.regatta_listbox.delete(0, tk.END)
        regattas = self.db.get_regattas()
        for regatta_id, name, location, start_date, end_date in regattas:
            display_text = f"{name} - {location} ({start_date})"
            self.regatta_listbox.insert(tk.END, display_text)
    
    def _populate_regatta_combo(self):
        """Populate the regatta dropdown on Events tab."""
        regattas = self.db.get_regattas()
        regatta_options = []
        self.regatta_id_map = {}
        
        for regatta_id, name, location, start_date, end_date in regattas:
            display_text = f"{name} - {location} ({start_date})"
            regatta_options.append(display_text)
            self.regatta_id_map[display_text] = regatta_id
        
        self.regatta_combo['values'] = regatta_options
        if regatta_options:
            self.regatta_combo.set(regatta_options[0])
            self._on_regatta_combo_select(None)
    
    def _populate_entry_event_combo(self):
        """Populate the event dropdown on Entries tab."""
        events = self.db.get_all_events()
        event_options = []
        self.entry_event_id_map = {}
        
        for event_id, regatta_name, gender, weight, event_boat_class, boat_type, round_name, scheduled_at, regatta_id in events:
            display_text = f"{regatta_name}: {gender} {weight} {event_boat_class} {boat_type} - {round_name}"
            if scheduled_at:
                display_text += f" ({scheduled_at})"
            event_options.append(display_text)
            self.entry_event_id_map[display_text] = event_id
        
        self.entry_event_combo['values'] = event_options
    
    def _populate_results_event_combo(self):
        """Populate the event dropdown on Results tab."""
        events = self.db.get_all_events()
        event_options = []
        self.results_event_id_map = {}
        
        for event_id, regatta_name, gender, weight, event_boat_class, boat_type, round_name, scheduled_at, regatta_id in events:
            display_text = f"{regatta_name}: {gender} {weight} {event_boat_class} {boat_type} - {round_name}"
            if scheduled_at:
                display_text += f" ({scheduled_at})"
            event_options.append(display_text)
            self.results_event_id_map[display_text] = event_id
        
        self.results_event_combo['values'] = event_options
    
    def _refresh_events_list(self):
        """Refresh the events table for the selected regatta."""
        # Clear existing items
        for item in self.events_tree.get_children():
            self.events_tree.delete(item)
        
        if not self.current_regatta_id:
            return
        
        events = self.db.get_events_for_regatta(self.current_regatta_id)
        for event_id, boat_type, event_boat_class, gender, weight, round_name, scheduled_at in events:
            scheduled_display = scheduled_at if scheduled_at else ""
            self.events_tree.insert('', 'end', values=(boat_type, event_boat_class, gender, weight, round_name, scheduled_display))
    
    def _populate_team_choices(self, gender: str, weight: str):
        """Populate team choices based on event gender/weight."""
        teams = self.db.get_teams_for_category(gender, weight)
        school_names = [school_name for team_id, school_name, conference in teams]
        
        self.team_school_combo['values'] = school_names
        if school_names:
            self.team_school_combo.set(school_names[0])
    
    # ── Event Handlers ──────────────────────────────────────────────────
    
    def _on_regatta_combo_select(self, event):
        """Handle regatta selection in Events tab."""
        selected_text = self.regatta_var.get()
        if selected_text in self.regatta_id_map:
            self.current_regatta_id = self.regatta_id_map[selected_text]
            self._refresh_events_list()
    
    def _on_entry_event_combo_select(self, event):
        """Handle event selection in Entries tab."""
        selected_text = self.entry_event_var.get()
        if selected_text in self.entry_event_id_map:
            self.current_event_id = self.entry_event_id_map[selected_text]
            
            # Get event details for team filtering
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT gender, weight, event_boat_class FROM events WHERE event_id = ?", (self.current_event_id,))
            event_info = cursor.fetchone()
            
            if event_info:
                gender, weight, event_boat_class = event_info
                self.current_event_boat_class = event_boat_class
                
                # Auto-fill the boat class entry
                self.entry_boat_class_entry.delete(0, tk.END)
                self.entry_boat_class_entry.insert(0, event_boat_class)
                
                self._populate_team_choices(gender, weight)
                self._refresh_entries_display()
                
                # Update selected event display
                self.selected_event_label.config(
                    text=f"Selected Event: {selected_text}",
                    fg='green'
                )
    
    def _on_results_event_combo_select(self, event):
        """Handle event selection in Results tab."""
        selected_text = self.results_event_var.get()
        if selected_text in self.results_event_id_map:
            self.current_event_id = self.results_event_id_map[selected_text]
            
            self.selected_event_results_label.config(
                text=f"Selected Event: {selected_text}",
                fg='green'
            )
            self.submit_results_button.config(state='normal')
            self._refresh_entries_display()
    
    def _move_entry_up(self, index):
        """Move an entry up in the results order."""
        if index > 0:
            # Swap with the entry above
            self.result_entries[index], self.result_entries[index-1] = self.result_entries[index-1], self.result_entries[index]
            self._update_position_displays()
    
    def _move_entry_down(self, index):
        """Move an entry down in the results order."""
        if index < len(self.result_entries) - 1:
            # Swap with the entry below
            self.result_entries[index], self.result_entries[index+1] = self.result_entries[index+1], self.result_entries[index]
            self._update_position_displays()
    
    def _update_position_displays(self):
        """Update position numbers after reordering."""
        for i, entry_data in enumerate(self.result_entries):
            entry_data['position_var'].set(str(i + 1))
        self._update_margins()
    
    # ── Database Operations ──────────────────────────────────────────────
    
    def _add_regatta(self):
        """Add a new regatta to the database."""
        name = self.regatta_name_entry.get().strip()
        location = self.regatta_location_entry.get().strip()
        start_date = self.regatta_start_date.get()
        end_date = self.regatta_end_date.get()
        
        if not name:
            messagebox.showerror("Error", "Regatta name is required")
            return
        
        try:
            regatta_id = self.db.add_regatta(name, location, start_date, end_date)
            messagebox.showinfo("Success", f"Added regatta: {name}")
            
            # Clear form
            self.regatta_name_entry.delete(0, tk.END)
            self.regatta_location_entry.delete(0, tk.END)
            
            # Refresh all regatta-related data
            self._refresh_regatta_list()
            self._populate_regatta_combo()
            self._populate_entry_event_combo()
            self._populate_results_event_combo()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add regatta: {str(e)}")
    
    def _add_event(self):
        """Add a new event to the selected regatta."""
        if not self.current_regatta_id:
            messagebox.showerror("Error", "Please select a regatta first")
            return
        
        boat_type = self.boat_type_var.get()
        event_boat_class = self.event_class_var.get()
        gender = self.gender_var.get().split()[0]  # Extract code from "M (Men)"
        weight = self.weight_var.get().split()[0]  # Extract code from "LW (Lightweight)"
        round_name = self.round_var.get()
        
        # Get scheduled datetime if provided
        scheduled_at = None
        time_str = self.scheduled_time_entry.get_time_or_none()
        
        if time_str:
            try:
                scheduled_date = self.scheduled_date.get_date().strftime("%Y-%m-%d")
                scheduled_at = f"{scheduled_date} {time_str}:00"
            except Exception as e:
                messagebox.showerror("Error", f"Invalid date/time: {str(e)}")
                return
        
        try:
            event_id = self.db.add_event(
                self.current_regatta_id, boat_type, event_boat_class,
                gender, weight, round_name, scheduled_at
            )
            
            event_description = f"{gender} {weight} {event_boat_class} {boat_type} - {round_name}"
            if scheduled_at:
                event_description += f" at {scheduled_at}"
            
            messagebox.showinfo("Success", f"Created event: {event_description}")
            
            # Reset form for next event
            self.scheduled_time_entry.delete(0, tk.END)
            self.scheduled_time_entry._add_placeholder()
            
            # Refresh all event-related data
            self._refresh_events_list()
            self._populate_entry_event_combo()
            self._populate_results_event_combo()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create event: {str(e)}")
    
    def _add_entry(self):
        """Add a team entry to the current event."""
        if not self.current_event_id:
            messagebox.showerror("Error", "Please select an event first")
            return
        
        school_name = self.team_school_var.get()
        entry_boat_class = self.entry_boat_class_entry.get().strip()
        
        if not school_name:
            messagebox.showerror("Error", "Please select a school")
            return
        
        # Get team_id for this school
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT gender, weight FROM events WHERE event_id = ?", (self.current_event_id,))
        event_info = cursor.fetchone()
        if not event_info:
            messagebox.showerror("Error", "Event not found")
            return
        
        gender, weight = event_info
        teams = self.db.get_teams_for_category(gender, weight)
        team_id = None
        for tid, tschool, tconference in teams:
            if tschool == school_name:
                team_id = tid
                break
        
        if not team_id:
            messagebox.showerror("Error", f"Team not found for {school_name}")
            return
        
        try:
            entry_id = self.db.add_entry(self.current_event_id, team_id, entry_boat_class)
            messagebox.showinfo("Success", f"Added entry for {school_name}")
            
            # Clear entry form (but keep boat class for convenience)
            
            # Refresh entries display
            self._refresh_entries_display()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add entry: {str(e)}")
    
    def _refresh_entries_display(self):
        """Refresh the entries display and results form."""
        # Clear entries tree
        for item in self.entries_tree.get_children():
            self.entries_tree.delete(item)
        
        if not self.current_event_id:
            return
        
        # Get entries for current event
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT e.entry_id, s.name, e.entry_boat_class, t.conference
            FROM entries e
            JOIN teams t ON e.team_id = t.team_id
            JOIN schools s ON t.school_id = s.school_id
            WHERE e.event_id = ?
            ORDER BY s.name
        """, (self.current_event_id,))
        
        entries = cursor.fetchall()
        
        # Populate entries tree
        for entry_id, school_name, boat_class, conference in entries:
            boat_class_display = boat_class if boat_class else ""
            self.entries_tree.insert('', 'end', values=(school_name, boat_class_display, conference))
        
        # Update results form
        self._setup_results_form(entries)
    
    def _setup_results_form(self, entries):
        """Set up the results entry form based on current entries."""
        # Clear existing result entries
        for widget in self.results_scroll_frame.winfo_children():
            widget.destroy()
        self.result_entries.clear()
        
        if not entries:
            return
        
        # Create result entry rows
        for i, (entry_id, school_name, boat_class, conference) in enumerate(entries):
            row_frame = tk.Frame(self.results_scroll_frame)
            row_frame.pack(fill='x', pady=2)
            
            # Position
            position_var = tk.StringVar(value=str(i + 1))
            position_entry = tk.Entry(row_frame, textvariable=position_var, font=FONT_ENTRY, width=5, state='readonly')
            position_entry.grid(row=0, column=0, padx=2)
            
            # Up/Down arrows
            arrow_frame = tk.Frame(row_frame)
            arrow_frame.grid(row=0, column=1, padx=2)
            
            up_btn = tk.Button(arrow_frame, text="↑", font=("Arial", 8), width=2, height=1,
                              command=lambda idx=i: self._move_entry_up(idx))
            up_btn.pack(side='top')
            
            down_btn = tk.Button(arrow_frame, text="↓", font=("Arial", 8), width=2, height=1,
                                command=lambda idx=i: self._move_entry_down(idx))
            down_btn.pack(side='bottom')
            
            # School name (read-only)
            school_label = tk.Label(row_frame, text=school_name, font=FONT_ENTRY, width=20, anchor='w')
            school_label.grid(row=0, column=2, padx=2)
            
            # Lane
            lane_entry = tk.Entry(row_frame, font=FONT_ENTRY, width=6)
            lane_entry.grid(row=0, column=3, padx=2)
            
            # Time
            time_entry = TimeEntry(row_frame, width=15)
            time_entry.grid(row=0, column=4, padx=2)
            
            # Margin (calculated automatically)
            margin_var = tk.StringVar()
            margin_label = tk.Label(row_frame, textvariable=margin_var, font=FONT_ENTRY, width=10)
            margin_label.grid(row=0, column=5, padx=2)
            
            self.result_entries.append({
                'entry_id': entry_id,
                'school_name': school_name,
                'position_var': position_var,
                'position_entry': position_entry,
                'lane_entry': lane_entry,
                'time_entry': time_entry,
                'margin_var': margin_var,
                'up_btn': up_btn,
                'down_btn': down_btn
            })
            
            # Bind time entry to update margins and positions
            time_entry.bind('<KeyRelease>', self._update_margins_and_positions)
            time_entry.bind('<FocusOut>', self._update_margins_and_positions)
    
    def _update_margins_and_positions(self, event=None):
        """Update margins and auto-sort by time when times change."""
        if not self.result_entries:
            return
        
        # Get all times and create sortable list
        entries_with_times = []
        for i, entry_data in enumerate(self.result_entries):
            try:
                time_seconds = entry_data['time_entry'].get_seconds()
                if time_seconds > 0:
                    entries_with_times.append((time_seconds, i, entry_data))
                else:
                    entries_with_times.append((float('inf'), i, entry_data))  # Put entries without times at end
            except:
                entries_with_times.append((float('inf'), i, entry_data))
        
        # Sort by time
        entries_with_times.sort(key=lambda x: x[0])
        
        # Reorder the result_entries list
        self.result_entries = [entry_data for _, _, entry_data in entries_with_times]
        
        # Update positions and margins
        valid_times = [time_sec for time_sec, _, _ in entries_with_times if time_sec != float('inf')]
        fastest_time = min(valid_times) if valid_times else 0
        
        for i, (time_seconds, _, entry_data) in enumerate(entries_with_times):
            # Update position
            entry_data['position_var'].set(str(i + 1))
            
            # Update margin
            if time_seconds != float('inf') and fastest_time > 0:
                margin = time_seconds - fastest_time
                if margin == 0:
                    entry_data['margin_var'].set("0.000")
                else:
                    entry_data['margin_var'].set(f"+{margin:.3f}")
            else:
                entry_data['margin_var'].set("")
            
            # Update button commands with new indices
            entry_data['up_btn'].config(command=lambda idx=i: self._move_entry_up(idx))
            entry_data['down_btn'].config(command=lambda idx=i: self._move_entry_down(idx))
    
    def _update_margins(self, event=None):
        """Update margin calculations when times change."""
        if not self.result_entries:
            return
        
        # Get all times
        times = []
        for entry_data in self.result_entries:
            try:
                time_seconds = entry_data['time_entry'].get_seconds()
                if time_seconds > 0:
                    times.append(time_seconds)
                else:
                    times.append(None)
            except:
                times.append(None)
        
        # Find the fastest time (winner)
        valid_times = [t for t in times if t is not None]
        if not valid_times:
            return
        
        fastest_time = min(valid_times)
        
        # Update margins
        for i, entry_data in enumerate(self.result_entries):
            if times[i] is not None:
                margin = times[i] - fastest_time
                if margin == 0:
                    entry_data['margin_var'].set("0.000")
                else:
                    entry_data['margin_var'].set(f"+{margin:.3f}")
            else:
                entry_data['margin_var'].set("")
    
    def _submit_results(self):
        """Submit all results to the database."""
        if not self.result_entries:
            messagebox.showerror("Error", "No entries to submit results for")
            return
        
        # Validate all entries have times
        for entry_data in self.result_entries:
            time_text = entry_data['time_entry'].get().strip()
            if not time_text:
                messagebox.showerror("Error", f"Please enter time for {entry_data['school_name']}")
                return
        
        try:
            # Results are already sorted by position
            for position, entry_data in enumerate(self.result_entries, 1):
                time_seconds = entry_data['time_entry'].get_seconds()
                lane_text = entry_data['lane_entry'].get().strip()
                lane = int(lane_text) if lane_text else None
                
                # Calculate margin from winner
                winner_time = self.result_entries[0]['time_entry'].get_seconds()
                margin = time_seconds - winner_time
                
                # Add result to database
                self.db.add_result(
                    entry_data['entry_id'],
                    lane=lane,
                    position=position,
                    elapsed_sec=time_seconds,
                    margin_sec=margin
                )
            
            messagebox.showinfo("Success", "All results submitted successfully!")
            
            # Clear the results form
            for widget in self.results_scroll_frame.winfo_children():
                widget.destroy()
            self.result_entries.clear()
            
            # Reset the results tab
            self.results_event_var.set("")
            self.selected_event_results_label.config(text="No event selected for results", fg='red')
            self.submit_results_button.config(state='disabled')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit results: {str(e)}")

def main():
    """Launch the application."""
    root = tk.Tk()
    app = RowingDatabaseApp(root)
    
    # Initialize the event combos after app is created
    app._populate_entry_event_combo()
    app._populate_results_event_combo()
    
    root.mainloop()

if __name__ == "__main__":
    main()