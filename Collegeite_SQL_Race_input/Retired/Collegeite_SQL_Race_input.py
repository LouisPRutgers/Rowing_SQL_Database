#!/usr/bin/env python3
"""
Rowing Database Entry App
========================

GUI for populating the rowing SQL database with schools, teams, regattas, events, entries, and results.
Based on the improved schema with proper foreign key relationships.

Features:
- Multi-stage data entry workflow (Schools → Regattas → Events → Entries → Results)
- Smart autocomplete for all relevant fields
- Team-specific school filtering
- Event creation with boat type + class combinations
- Results entry with time parsing and validation
- SQLite backend with proper schema
"""

import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import List, Dict, Optional, Tuple, Set
import os

try:
    from tkcalendar import DateEntry
except ModuleNotFoundError:
    messagebox.showerror("Missing dependency", "pip install tkcalendar")
    exit(1)

# ── Constants ──────────────────────────────────────────────────────────
SCHOOLS_DATA = [
    ("Alabama", "SEC"),
    ("Boston College", "ACC"),
    ("Boston University", "Patriot League"),
    ("Brown", "Ivy League"),
    ("Bryant", "NEC"),
    ("Bucknell", "Patriot League"),
    ("California", "Pac-12"),
    ("Canisius", "MAAC"),
    ("Clemson", "ACC"),
    ("Colgate", "Patriot League"),
    ("Columbia", "Ivy League"),
    ("Cornell", "Ivy League"),
    ("Creighton", "Big East"),
    ("Dartmouth", "Ivy League"),
    ("Delaware", "CAA"),
    ("Drake", "MVC"),
    ("Drexel", "CAA"),
    ("Duke", "ACC"),
    ("Georgetown", "Big East"),
    ("Harvard", "Ivy League"),
    ("MIT", "NESCAC"),
    ("Navy", "Patriot League"),
    ("Princeton", "Ivy League"),
    ("Stanford", "Pac-12"),
    ("Syracuse", "ACC"),
    ("Yale", "Ivy League"),
]

TEAM_PARTICIPATION = {
    "Openweight Women": [school[0] for school in SCHOOLS_DATA],
    "Lightweight Women": ["Boston University", "Georgetown", "Harvard", "MIT", "Princeton", "Stanford", "Wisconsin"],
    "Heavyweight Men": [school[0] for school in SCHOOLS_DATA[:20]],
    "Lightweight Men": ["Columbia", "Cornell", "Dartmouth", "Georgetown", "Harvard", "MIT", "Navy", "Penn", "Princeton", "Yale"]
}

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
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        self._populate_initial_data()
    
    def _create_tables(self):
        """Create all tables according to the schema."""
        cursor = self.conn.cursor()
        
        # Schools table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                school_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                conference TEXT
            )
        """)
        
        # Teams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                team_id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id INTEGER NOT NULL,
                gender TEXT NOT NULL CHECK (gender IN ('M', 'W')),
                weight TEXT NOT NULL CHECK (weight IN ('LW', 'HW', 'OW')),
                FOREIGN KEY (school_id) REFERENCES schools (school_id),
                UNIQUE(school_id, gender, weight)
            )
        """)
        
        # Regattas table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regattas (
                regatta_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                start_date DATE,
                end_date DATE
            )
        """)
        
        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                regatta_id INTEGER NOT NULL,
                boat_type TEXT NOT NULL CHECK (boat_type IN ('8+', '4+', '4x', '2x', '1x', '2-')),
                event_boat_class TEXT NOT NULL,
                gender TEXT NOT NULL CHECK (gender IN ('M', 'W')),
                weight TEXT NOT NULL CHECK (weight IN ('LW', 'HW', 'OW')),
                round TEXT NOT NULL,
                scheduled_at DATETIME,
                FOREIGN KEY (regatta_id) REFERENCES regattas (regatta_id)
            )
        """)
        
        # Entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                entry_boat_class TEXT,
                seed INTEGER,
                FOREIGN KEY (event_id) REFERENCES events (event_id),
                FOREIGN KEY (team_id) REFERENCES teams (team_id)
            )
        """)
        
        # Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id INTEGER NOT NULL,
                lane INTEGER,
                position INTEGER,
                elapsed_sec REAL,
                margin_sec REAL,
                FOREIGN KEY (entry_id) REFERENCES entries (entry_id)
            )
        """)
        
        self.conn.commit()
    
    def _populate_initial_data(self):
        """Add initial schools and teams if database is empty."""
        cursor = self.conn.cursor()
        
        # Check if we already have data
        cursor.execute("SELECT COUNT(*) FROM schools")
        if cursor.fetchone()[0] > 0:
            return
        
        # Add schools
        for name, conference in SCHOOLS_DATA:
            cursor.execute("INSERT INTO schools (name, conference) VALUES (?, ?)", (name, conference))
        
        # Add teams for each school
        for team_type, school_names in TEAM_PARTICIPATION.items():
            gender = "W" if "Women" in team_type else "M"
            weight = "LW" if "Lightweight" in team_type else ("HW" if "Heavyweight" in team_type else "OW")
            
            for school_name in school_names:
                cursor.execute("SELECT school_id FROM schools WHERE name = ?", (school_name,))
                school_id = cursor.fetchone()[0]
                
                try:
                    cursor.execute(
                        "INSERT INTO teams (school_id, gender, weight) VALUES (?, ?, ?)",
                        (school_id, gender, weight)
                    )
                except sqlite3.IntegrityError:
                    pass  # Team already exists
        
        self.conn.commit()
    
    def get_schools(self) -> List[Tuple[int, str, str]]:
        """Return all schools with (id, name, conference)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT school_id, name, conference FROM schools ORDER BY name")
        return cursor.fetchall()
    
    def get_teams_for_category(self, gender: str, weight: str) -> List[Tuple[int, str]]:
        """Return teams (team_id, school_name) for given gender/weight."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT t.team_id, s.name
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
    
    def add_entry(self, event_id: int, team_id: int, entry_boat_class: str = None, seed: int = None) -> int:
        """Add a new entry and return its ID."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO entries (event_id, team_id, entry_boat_class, seed) VALUES (?, ?, ?, ?)",
            (event_id, team_id, entry_boat_class, seed)
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

class AutoCompleteEntry(tk.Entry):
    """Entry widget with autocomplete dropdown."""
    
    def __init__(self, master, choices: List[str], **kwargs):
        super().__init__(master, font=FONT_ENTRY, **kwargs)
        self.choices = sorted(choices, key=str.lower)
        self.var = tk.StringVar()
        self.config(textvariable=self.var)
        self.var.trace_add("write", self._update_matches)
        self.listbox: Optional[tk.Listbox] = None
        
        # Bind events
        self.bind("<KeyPress-Tab>", self._on_tab)
        self.bind("<Return>", self._on_enter)
        self.bind("<Down>", self._on_down)
        self.bind("<Up>", self._on_up)
        self.bind("<Escape>", self._destroy_listbox)
        self.bind("<FocusOut>", self._on_focus_out)
    
    def update_choices(self, new_choices: List[str]):
        """Update the autocomplete choices."""
        self.choices = sorted(new_choices, key=str.lower)
    
    def _update_matches(self, *_):
        """Update the dropdown with matching choices."""
        self._destroy_listbox()
        text = self.var.get().lower()
        if not text:
            return
        
        matches = [choice for choice in self.choices if text in choice.lower()]
        if not matches:
            return
        
        # Create listbox
        self.listbox = tk.Listbox(self.master, height=min(6, len(matches)), font=FONT_ENTRY)
        
        # Position listbox below entry
        x = self.winfo_x()
        y = self.winfo_y() + self.winfo_height()
        self.listbox.place(x=x, y=y, width=self.winfo_width())
        
        # Populate listbox
        for match in matches:
            self.listbox.insert(tk.END, match)
        
        if matches:
            self.listbox.selection_set(0)
        
        # Bind listbox events
        self.listbox.bind("<Double-Button-1>", lambda e: self._complete())
        self.listbox.bind("<Return>", lambda e: self._complete())
    
    def _destroy_listbox(self, *_):
        """Destroy the autocomplete listbox."""
        if self.listbox:
            self.listbox.destroy()
            self.listbox = None
    
    def _complete(self):
        """Complete the entry with selected listbox item."""
        if self.listbox and self.listbox.curselection():
            selected = self.listbox.get(self.listbox.curselection()[0])
            self.var.set(selected)
            self._destroy_listbox()
            # Move focus to next widget
            self.tk_focusNext().focus_set()
    
    def _on_tab(self, event):
        """Handle Tab key."""
        if self.listbox:
            self._complete()
            return "break"
    
    def _on_enter(self, event):
        """Handle Enter key."""
        if self.listbox:
            self._complete()
            return "break"
    
    def _on_down(self, event):
        """Handle Down arrow key."""
        if self.listbox:
            current = self.listbox.curselection()
            if current:
                next_idx = min(current[0] + 1, self.listbox.size() - 1)
            else:
                next_idx = 0
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(next_idx)
            self.listbox.see(next_idx)
            return "break"
    
    def _on_up(self, event):
        """Handle Up arrow key."""
        if self.listbox:
            current = self.listbox.curselection()
            if current:
                prev_idx = max(current[0] - 1, 0)
            else:
                prev_idx = self.listbox.size() - 1
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(prev_idx)
            self.listbox.see(prev_idx)
            return "break"
    
    def _on_focus_out(self, event):
        """Handle focus leaving the entry."""
        # Delay to allow listbox clicks
        self.after(100, self._destroy_listbox)

class TimeEntry(tk.Entry):
    """Entry widget for time input with smart parsing."""
    
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
            # Parse using the same logic as the original app
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
        self.root.geometry("900x700")
        
        # Initialize database
        self.db = DatabaseManager()
        
        # Current workflow state
        self.current_regatta_id: Optional[int] = None
        self.current_event_id: Optional[int] = None
        
        self._setup_ui()
        self._refresh_regatta_list()
    
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
        
        self.regatta_listbox.bind('<<ListboxSelect>>', self._on_regatta_select)
        
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
        
        # Selected regatta display
        self.selected_regatta_label = tk.Label(frame, text="No regatta selected", font=FONT_LABEL, fg='red')
        self.selected_regatta_label.pack(pady=5)
        
        # Event form
        form_frame = tk.LabelFrame(frame, text="Create New Event", font=FONT_LABEL)
        form_frame.pack(fill='x', padx=20, pady=20)
        
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
        
        # Scheduled time (optional)
        tk.Label(form_frame, text="Scheduled Time:", font=FONT_LABEL).grid(row=5, column=0, sticky='e', padx=5, pady=5)
        self.scheduled_time_entry = tk.Entry(form_frame, font=FONT_ENTRY, width=20)
        self.scheduled_time_entry.grid(row=5, column=1, padx=5, pady=5)
        tk.Label(form_frame, text="(Optional: YYYY-MM-DD HH:MM)", font=("Helvetica", 9)).grid(row=5, column=2, padx=5)
        
        # Add event button
        tk.Button(form_frame, text="Create Event", font=FONT_BUTTON, command=self._add_event).grid(row=6, column=1, pady=10)
    
    def _create_entry_tab(self):
        """Create the entry management tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="3. Entries")
        
        # Title
        tk.Label(frame, text="Team Entries", font=FONT_TITLE).pack(pady=10)
        
        # Selected event display
        self.selected_event_label = tk.Label(frame, text="No event selected", font=FONT_LABEL, fg='red')
        self.selected_event_label.pack(pady=5)
        
        # Entry form
        form_frame = tk.LabelFrame(frame, text="Add Team Entry", font=FONT_LABEL)
        form_frame.pack(fill='x', padx=20, pady=20)
        
        # Team selection (will be populated based on event gender/weight)
        tk.Label(form_frame, text="School:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.team_school_var = tk.StringVar()
        self.team_school_combo = ttk.Combobox(form_frame, textvariable=self.team_school_var, state='readonly', font=FONT_ENTRY, width=25)
        self.team_school_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Entry boat class (what the team calls their boat)
        tk.Label(form_frame, text="Team's Boat Class:", font=FONT_LABEL).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.entry_boat_class_entry = tk.Entry(form_frame, font=FONT_ENTRY, width=15)
        self.entry_boat_class_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        tk.Label(form_frame, text="(e.g., 1V, 2V, A, B)", font=("Helvetica", 9)).grid(row=1, column=2, padx=5)
        
        # Seed (optional)
        tk.Label(form_frame, text="Seed:", font=FONT_LABEL).grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.seed_entry = tk.Entry(form_frame, font=FONT_ENTRY, width=10)
        self.seed_entry.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        tk.Label(form_frame, text="(Optional)", font=("Helvetica", 9)).grid(row=2, column=2, padx=5)
        
        # Add entry button
        tk.Button(form_frame, text="Add Entry", font=FONT_BUTTON, command=self._add_entry).grid(row=3, column=1, pady=10)
        
        # Current entries display
        entries_frame = tk.LabelFrame(frame, text="Current Entries", font=FONT_LABEL)
        entries_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Entries listbox
        self.entries_listbox = tk.Listbox(entries_frame, font=FONT_ENTRY)
        entries_scrollbar = tk.Scrollbar(entries_frame, orient='vertical', command=self.entries_listbox.yview)
        self.entries_listbox.config(yscrollcommand=entries_scrollbar.set)
        self.entries_listbox.pack(side='left', fill='both', expand=True)
        entries_scrollbar.pack(side='right', fill='y')
    
    def _create_results_tab(self):
        """Create the results entry tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="4. Results")
        
        # Title
        tk.Label(frame, text="Race Results", font=FONT_TITLE).pack(pady=10)
        
        # Selected event display
        self.selected_event_results_label = tk.Label(frame, text="No event selected", font=FONT_LABEL, fg='red')
        self.selected_event_results_label.pack(pady=5)
        
        # Results entry area
        results_frame = tk.LabelFrame(frame, text="Enter Results", font=FONT_LABEL)
        results_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Headers
        headers_frame = tk.Frame(results_frame)
        headers_frame.pack(fill='x', pady=5)
        
        tk.Label(headers_frame, text="Pos", font=FONT_LABEL, width=5).grid(row=0, column=0, padx=2)
        tk.Label(headers_frame, text="School", font=FONT_LABEL, width=20).grid(row=0, column=1, padx=2)
        tk.Label(headers_frame, text="Lane", font=FONT_LABEL, width=6).grid(row=0, column=2, padx=2)
        tk.Label(headers_frame, text="Time (mm:ss.fff)", font=FONT_LABEL, width=15).grid(row=0, column=3, padx=2)
        tk.Label(headers_frame, text="Margin", font=FONT_LABEL, width=10).grid(row=0, column=4, padx=2)
        
        # Scrollable results area
        canvas = tk.Canvas(results_frame)
        scrollbar_results = tk.Scrollbar(results_frame, orient="vertical", command=canvas.yview)
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
        tk.Button(results_frame, text="Submit All Results", font=FONT_BUTTON, 
                 command=self._submit_results).pack(pady=10)
    
    def _refresh_regatta_list(self):
        """Refresh the regatta listbox with current data."""
        self.regatta_listbox.delete(0, tk.END)
        regattas = self.db.get_regattas()
        for regatta_id, name, location, start_date, end_date in regattas:
            display_text = f"{name} - {location} ({start_date})"
            self.regatta_listbox.insert(tk.END, display_text)
            # Store the ID for later retrieval
            self.regatta_listbox.insert(tk.END, f"ID:{regatta_id}")
            self.regatta_listbox.delete(tk.END)  # Remove the ID line from display
    
    def _on_regatta_select(self, event):
        """Handle regatta selection."""
        selection = self.regatta_listbox.curselection()
        if not selection:
            return
        
        # Get regatta info
        regattas = self.db.get_regattas()
        if selection[0] < len(regattas):
            regatta_id, name, location, start_date, end_date = regattas[selection[0]]
            self.current_regatta_id = regatta_id
            self.selected_regatta_label.config(
                text=f"Selected: {name} - {location} ({start_date})",
                fg='green'
            )
            # Enable the Events tab
            self.notebook.tab(1, state='normal')
    
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
            
            # Refresh list
            self._refresh_regatta_list()
            
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
        scheduled_at = self.scheduled_time_entry.get().strip() or None
        
        try:
            event_id = self.db.add_event(
                self.current_regatta_id, boat_type, event_boat_class,
                gender, weight, round_name, scheduled_at
            )
            
            self.current_event_id = event_id
            event_description = f"{gender} {weight} {event_boat_class} {boat_type} - {round_name}"
            
            messagebox.showinfo("Success", f"Created event: {event_description}")
            
            # Update event labels
            self.selected_event_label.config(
                text=f"Selected Event: {event_description}",
                fg='green'
            )
            self.selected_event_results_label.config(
                text=f"Selected Event: {event_description}",
                fg='green'
            )
            
            # Clear scheduled time
            self.scheduled_time_entry.delete(0, tk.END)
            
            # Enable subsequent tabs and populate team choices
            self.notebook.tab(2, state='normal')  # Entries tab
            self.notebook.tab(3, state='normal')  # Results tab
            self._populate_team_choices(gender, weight)
            self._refresh_entries_display()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create event: {str(e)}")
    
    def _populate_team_choices(self, gender: str, weight: str):
        """Populate team choices based on event gender/weight."""
        teams = self.db.get_teams_for_category(gender, weight)
        school_names = [school_name for team_id, school_name in teams]
        
        self.team_school_combo['values'] = school_names
        if school_names:
            self.team_school_combo.set(school_names[0])
    
    def _add_entry(self):
        """Add a team entry to the current event."""
        if not self.current_event_id:
            messagebox.showerror("Error", "Please select an event first")
            return
        
        school_name = self.team_school_var.get()
        entry_boat_class = self.entry_boat_class_entry.get().strip()
        seed_text = self.seed_entry.get().strip()
        
        if not school_name:
            messagebox.showerror("Error", "Please select a school")
            return
        
        # Get team_id for this school
        # First get the event to determine gender/weight
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT gender, weight FROM events WHERE event_id = ?", (self.current_event_id,))
        event_info = cursor.fetchone()
        if not event_info:
            messagebox.showerror("Error", "Event not found")
            return
        
        gender, weight = event_info
        teams = self.db.get_teams_for_category(gender, weight)
        team_id = None
        for tid, tschool in teams:
            if tschool == school_name:
                team_id = tid
                break
        
        if not team_id:
            messagebox.showerror("Error", f"Team not found for {school_name}")
            return
        
        seed = None
        if seed_text:
            try:
                seed = int(seed_text)
            except ValueError:
                messagebox.showerror("Error", "Seed must be a number")
                return
        
        try:
            entry_id = self.db.add_entry(self.current_event_id, team_id, entry_boat_class, seed)
            messagebox.showinfo("Success", f"Added entry for {school_name}")
            
            # Clear entry form
            self.entry_boat_class_entry.delete(0, tk.END)
            self.seed_entry.delete(0, tk.END)
            
            # Refresh entries display
            self._refresh_entries_display()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add entry: {str(e)}")
    
    def _refresh_entries_display(self):
        """Refresh the entries listbox and results form."""
        # Clear entries list
        self.entries_listbox.delete(0, tk.END)
        
        if not self.current_event_id:
            return
        
        # Get entries for current event
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT e.entry_id, s.name, e.entry_boat_class, e.seed
            FROM entries e
            JOIN teams t ON e.team_id = t.team_id
            JOIN schools s ON t.school_id = s.school_id
            WHERE e.event_id = ?
            ORDER BY e.seed, s.name
        """, (self.current_event_id,))
        
        entries = cursor.fetchall()
        
        # Populate entries list
        for entry_id, school_name, boat_class, seed in entries:
            display_text = f"{school_name}"
            if boat_class:
                display_text += f" ({boat_class})"
            if seed:
                display_text += f" [Seed: {seed}]"
            self.entries_listbox.insert(tk.END, display_text)
        
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
        for i, (entry_id, school_name, boat_class, seed) in enumerate(entries):
            row_frame = tk.Frame(self.results_scroll_frame)
            row_frame.pack(fill='x', pady=2)
            
            # Position
            position_var = tk.StringVar(value=str(i + 1))
            position_entry = tk.Entry(row_frame, textvariable=position_var, font=FONT_ENTRY, width=5)
            position_entry.grid(row=0, column=0, padx=2)
            
            # School name (read-only)
            school_label = tk.Label(row_frame, text=school_name, font=FONT_ENTRY, width=20, anchor='w')
            school_label.grid(row=0, column=1, padx=2)
            
            # Lane
            lane_entry = tk.Entry(row_frame, font=FONT_ENTRY, width=6)
            lane_entry.grid(row=0, column=2, padx=2)
            
            # Time
            time_entry = TimeEntry(row_frame, width=15)
            time_entry.grid(row=0, column=3, padx=2)
            
            # Margin (calculated automatically)
            margin_var = tk.StringVar()
            margin_label = tk.Label(row_frame, textvariable=margin_var, font=FONT_ENTRY, width=10)
            margin_label.grid(row=0, column=4, padx=2)
            
            self.result_entries.append({
                'entry_id': entry_id,
                'school_name': school_name,
                'position_var': position_var,
                'position_entry': position_entry,
                'lane_entry': lane_entry,
                'time_entry': time_entry,
                'margin_var': margin_var
            })
            
            # Bind time entry to update margins
            time_entry.bind('<KeyRelease>', self._update_margins)
            time_entry.bind('<FocusOut>', self._update_margins)
    
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
            # Sort entries by time to get proper finishing order
            entries_with_times = []
            for entry_data in self.result_entries:
                time_seconds = entry_data['time_entry'].get_seconds()
                lane_text = entry_data['lane_entry'].get().strip()
                lane = int(lane_text) if lane_text else None
                
                entries_with_times.append((time_seconds, entry_data, lane))
            
            # Sort by time
            entries_with_times.sort(key=lambda x: x[0])
            
            # Calculate margins and assign positions
            fastest_time = entries_with_times[0][0]
            
            for position, (time_seconds, entry_data, lane) in enumerate(entries_with_times, 1):
                margin = time_seconds - fastest_time
                
                # Add result to database
                self.db.add_result(
                    entry_data['entry_id'],
                    lane=lane,
                    position=position,
                    elapsed_sec=time_seconds,
                    margin_sec=margin
                )
            
            messagebox.showinfo("Success", "All results submitted successfully!")
            
            # Clear the current event to prevent duplicate submissions
            self.current_event_id = None
            self.selected_event_label.config(text="No event selected", fg='red')
            self.selected_event_results_label.config(text="No event selected", fg='red')
            
            # Disable entries and results tabs
            self.notebook.tab(2, state='disabled')
            self.notebook.tab(3, state='disabled')
            
            # Switch back to events tab for next race
            self.notebook.select(1)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit results: {str(e)}")

def main():
    """Launch the application."""
    root = tk.Tk()
    app = RowingDatabaseApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()