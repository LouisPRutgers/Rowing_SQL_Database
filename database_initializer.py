#!/usr/bin/env python3
"""
Rowing Database Initializer - Enhanced Version
==============================================

Key Changes:
- CRR name is now the primary key for all school operations
- Schools are keyed by crr_name instead of name for easier editing
- Enhanced support for CRR name changes that propagate everywhere

Usage:
    python database_initializer.py [database_path]
"""

import sys
import os
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Collegeite_SQL_Race_input.database.manager import DatabaseManager
import sqlite3
from typing import Dict, List, Tuple

# ── School Data Keyed by CRR Name ──────────────────────────────────────────
# Format: crr_name: (name, short_name, acronym, color, openweight_women, heavyweight_men, lightweight_men, lightweight_women)
# CRR name is now the PRIMARY KEY that will be used throughout the system
SCHOOL_EXTENDED_INFO = {
    "Alabama": ("University of Alabama", "Alabama", "", "#9E1B32", True, False, False, False),
    "Boston College": ("Boston College", "", "", "#98002E", True, False, False, False),
    "Boston University - BU": ("Boston University", "BU", "BU", "#CC0000", True, True, False, True),
    "Brown": ("Brown University", "Brown", "", "#8B0000", True, True, False, False),
    "Bryant": ("Bryant University", "Bryant", "", "#002878", True, False, False, False),
    "Bucknell": ("Bucknell University", "Bucknell", "", "#FF7900", True, False, False, False),
    "California": ("University of California - Berkeley", "UC Berkeley", "", "#8B0000", True, True, False, False),
    "Canisius": ("Canisius University", "Canisius", "", "#003DA5", True, False, False, False),
    "Clemson": ("Clemson University", "Clemson", "", "#F66733", True, False, False, False),
    "Colgate": ("Colgate University", "Colgate", "", "#862633", True, True, False, False),
    "Columbia": ("Columbia University", "Columbia", "", "#0073E6", True, True, True, False),
    "Cornell": ("Cornell University", "Cornell", "", "#A31621", True, True, True, False),
    "Creighton": ("Creighton University", "Creighton", "", "#00693E", True, False, False, False),
    "Dartmouth": ("Dartmouth College", "Dartmouth", "", "#1E3A8A", True, True, True, False),
    "Dayton": ("University of Dayton", "Dayton", "", "#C41E3A", True, False, False, False),
    "Delaware": ("University of Delaware", "Delaware", "", "#003DA5", True, False, False, False),
    "Drake": ("Drake University", "Drake", "", "#004B87", True, False, False, False),
    "Drexel": ("Drexel University", "Drexel", "", "#003087", True, True, False, False),
    "Duke": ("Duke University", "Duke", "", "#8A0538", True, False, False, False),
    "Duquesne": ("Duquesne University", "Duquesne", "", "#0047AB", True, False, False, False),
    "Eastern Michigan": ("Eastern Michigan University", "Eastern Michigan", "", "#FF6600", True, False, False, False),
    "Embry-Riddle": ("Embry-Riddle Aeronautical University", "Embry-Riddle", "", "#8B0000", False, True, False, False),
    "Fairfield": ("Fairfield University", "Fairfield", "", "#862633", True, True, False, False),
    "Florida Tech - FIT": ("Florida Intitute of Technology", "Florida Tech", "FIT", "#006633", False, True, False, False),
    "Fordham": ("Fordham University", "Fordham", "", "#003DA5", True, False, False, False),
    "George Mason": ("George Mason University", "George Mason", "", "#1E3A8A", True, False, False, False),
    "George Washington": ("George Washington University", "George Washington", "", "#003087", True, False, False, False),
    "Georgetown": ("Georgetown University", "Georgetown", "", "#006747", True, True, True, True),
    "Gonzaga": ("Gonzaga University", "Gonzaga", "", "#002147", True, True, False, False),
    "Gordon College": ("Gordon College", "", "", "#A41034", False, False, True, True),
    "Harvard": ("Harvard University", "Harvard", "", "#A41034", False, True, True, True),
    "Hobart": ("Hobart College", "Hobart", "", "#7B2142", False, True, False, False),
    "Holy Cross": ("College of the Holy Cross", "Holy Cross", "", "#5C0F2E", True, True, False, False),
    "Indiana": ("Indiana University Bloomington", "Indiana", "", "#FF6600", True, False, False, False),
    "Iona": ("Iona University", "Iona", "", "#FF6600", True, True, False, False),
    "Iowa": ("University of Iowa", "Iowa", "", "#002147", True, False, False, False),
    "Jacksonville": ("Jacksonville University", "Jacksonville", "", "#8E44AD", True, True, False, False),
    "Kansas": ("University of Kansas", "Kansas", "", "#FF6600", True, False, False, False),
    "Kansas State - KSU": ("Kansas State University", "Kansas State", "KSU", "#0053A0", True, False, False, False),
    "La Salle": ("La Salle University", "La Salle", "", "#0047AB", True, True, False, False),
    "Lehigh": ("Lehigh University", "Lehigh", "", "#003153", True, False, False, False),
    "Lewis & Clark": ("Lewis & Clark College", "Lewis & Clark", "", "#FF6600", False, True, False, False),
    "Louisville": ("University of Louisville", "Louisville", "", "#002F87", True, False, False, False),
    "Loyola Maryland": ("Loyola University Maryland", "Loyola Maryland", "", "#003DA5", True, True, False, False),
    "Loyola Marymount": ("Loyola Marymount University", "Loyola Marymount", "", "#8B0000", True, False, False, False),
    "Manhattan": ("Manhattan University", "Manhattan", "", "#FF0000", True, False, False, False),
    "Marist": ("Marist College", "Marist", "", "#003DA5", True, True, False, False),
    "Mercyhurst": ("Mercyhurst University", "Mercyhurst", "", "#AD0000", False, True, True, False),
    "Miami": ("University of Miami", "Miami", "", "#8C1D40", True, False, False, False),
    "Michigan": ("University of Michigan", "Michigan", "", "#C41E3A", True, False, False, False),
    "Michigan State": ("Michigan State University", "Michigan State", "MSU", "#0053A0", True, False, False, False),
    "Minnesota": ("University of Minnesota", "Minnesota", "", "#8B0000", True, False, False, False),
    "MIT": ("Massachusetts Institute of Technology", "MIT", "MIT", "#18453B", True, True, True, True),
    "Monmouth": ("Monmouth University", "Monmouth", "", "#CC0000", True, False, False, False),
    "Navy": ("United States Naval Academy", "Navy", "", "#003F87", True, True, True, False),
    "Northeastern": ("Northeastern University", "Northeastern", "", "#BB0000", True, True, False, False),
    "Notre Dame": ("University of Notre Dame", "Notre Dame", "", "#003087", True, False, False, False),
    "Ohio State": ("Ohio State University", "Ohio State", "OSU", "#D21034", True, False, False, False),
    "Oklahoma": ("University of Oklahoma", "Oklahoma", "", "#C41E3A", True, False, False, False),
    "Oklahoma City": ("Oklahoma City University", "Oklahoma City", "OCU", "#FF6600", False, True, False, False),
    "Old Dominion": ("Old Dominion University", "Old Dominion", "", "#002147", True, False, False, False),
    "Oregon State - OSU": ("Oregon State  University", "Oregon State", "OSU", "#C8102E", True, True, False, False),
    "Penn": ("University of Pennsylvania", "Penn", "", "#FF6600", True, True, True, False),
    "Portland": ("University of Portland", "Portland", "", "#4B2E83", True, False, False, False),
    "Princeton": ("Princeton University", "Princeton", "", "#FF6600", True, True, True, True),
    "Radcliff": ("Harvard/Radcliff", "Radcliff", "", "#FF6600", True, False, False, False),
    "Robert Morris": ("Robert Morris University", "Robert Morris", "", "#003087", True, False, False, False),
    "Rollins": ("Rollins College", "Rollins", "", "#8B0000", False, True, False, False),
    "Rutgers": ("Rutgers University", "Rutgers", "", "#FF6600", True, False, False, False),
    "Sacramento State": ("California State University - Sacramento", "Sacramento State", "", "#046A38", True, False, False, False),
    "Sacred Heart": ("Sacred Heart University", "Sacred Heart", "", "#CC0000", True, False, False, False),
    "Saint Joseph's": ("Saint Joseph's University", "Saint Joseph's", "", "#003DA5", True, True, False, False),
    "Saint Mary's": ("Saint Mary's College of California", "Saint Mary's", "", "#002147", True, False, False, False),
    "Santa Clara": ("Santa Clara University", "Santa Clara", "", "#001A57", True, True, False, False),
    "Seattle": ("Seattle University", "Seattle", "", "#8B0000", True, False, False, False),
    "SMU": ("Southern Methodist University", "SMU", "SMU", "#003087", True, False, False, False),
    "Stanford": ("Stanford University", "Stanford", "", "#001E3C", True, True, False, True),
    "Stetson": ("Stetson University", "Stetson", "", "#003DA5", True, True, False, False),
    "Syracuse": ("Syracuse University", "Syracuse", "", "#8C1D40", True, True, False, False),
    "Temple": ("Temple University", "Temple", "", "#FF6600", True, True, False, False),
    "Tennessee": ("University of Tennessee", "Tennessee", "", "#C41E3A", True, False, False, False),
    "Texas": ("University of Texas at Austin", "Texas", "", "#8B0000", True, False, False, False),
    "Tulsa": ("University of Tulsa", "Tulsa", "", "#FF6600", True, False, False, False),
    "UC San Diego": ("University of California - San Diego", "UC San Diego", "UCSD", "#003DA5", True, True, False, False),
    "UCF": ("University of Central Florida", "UCF", "UCF", "#002147", True, False, False, False),
    "UCLA": ("University of California - Los Angeles", "UCLA", "UCLA", "#FFCC00", True, False, False, False),
    "Uconn": ("University of Connecticut", "UConn", "UConn", "#001B3A", True, False, False, False),
    "UMass": ("University of Massachusetts - Amherst", "UMass", "", "#FFA500", True, False, False, False),
    "University of North Carolina - UNC": ("University of North Carolina - Chapel Hill", "", "UNC", "#003DA5", True, False, False, False),
    "University of Rhode Island - URI": ("University of Rhode Island", "", "URI", "#003DA5", True, False, False, False),
    "University of San Diego - USD": ("University of San Diego", "San Diego", "USD", "#8B0000", True, True, False, False),
    "University of Southern California - USC": ("University of Southern California", "USC", "USC", "#FF6600", True, False, False, False),
    "Villanova ": ("Villanova University", "Villanova", "", "#002F87", True, False, False, False),
    "Washington - UW": ("University of Washington", "Washington", "UW", "#FF6600", True, True, False, False),
    "Washington State University - WSU": ("Washington State University", "Washington State", "WSU", "#C41E3A", True, False, False, False),
    "West Virginia University  - WVU": ("West Virginia University", "West Virginia", "WVU", "#981E32", True, False, False, False),
    "Wisconsin": ("University of Wisconsin - Madison", "Wisconsin", "", "#CC0000", True, True, False, True),
    "Yale": ("Yale University", "Yale", "", "#00274C", True, True, True, False)
}

# Conference mappings ONLY for Openweight Women teams - KEYED BY CRR NAME
OPENWEIGHT_WOMEN_CONFERENCES = {
    # Atlantic Coast Conference (ACC)
    "Boston College": "ACC",
    "California": "ACC",
    "Clemson": "ACC", 
    "Duke": "ACC",
    "Louisville": "ACC",
    "Miami": "ACC",
    "University of North Carolina - UNC": "ACC",
    "Notre Dame": "ACC",
    "SMU": "ACC",
    "Stanford": "ACC",
    "Syracuse": "ACC",
    
    # Big Ten Conference
    "Indiana": "Big Ten",
    "Iowa": "Big Ten", 
    "Michigan": "Big Ten",
    "Michigan State": "Big Ten",
    "Minnesota": "Big Ten",
    "Ohio State": "Big Ten",
    "Rutgers": "Big Ten",
    "UCLA": "Big Ten",
    "University of Southern California - USC": "Big Ten",
    "Washington - UW": "Big Ten",
    "Wisconsin": "Big Ten",
    
    # Southeastern Conference (SEC)
    "Alabama": "SEC",
    "Oklahoma": "SEC",
    "Tennessee": "SEC",
    "Texas": "SEC",
    
    # Ivy League
    "Brown": "Ivy League",
    "Columbia": "Ivy League",
    "Cornell": "Ivy League",
    "Dartmouth": "Ivy League",
    "Penn": "Ivy League",
    "Princeton": "Ivy League",
    "Radcliff": "Ivy League",
    "Yale": "Ivy League",
    
    # West Coast Conference (WCC)
    "Creighton": "WCC", 
    "Gonzaga": "WCC",
    "Loyola Marymount": "WCC",
    "Oregon State - OSU": "WCC",
    "Portland": "WCC",
    "Saint Mary's": "WCC",
    "University of San Diego - USD": "WCC",
    "Santa Clara": "WCC",
    "Washington State University - WSU": "WCC",
    
    # Atlantic 10 Conference (A-10)
    "Dayton": "A-10",
    "Duquesne": "A-10",
    "Fordham": "A-10",
    "George Mason": "A-10",
    "George Washington": "A-10",
    "La Salle": "A-10",
    "University of Rhode Island - URI": "A-10",
    "Saint Joseph's": "A-10",
    "UMass": "A-10",
    
    # Patriot League
    "Boston University - BU": "Patriot League",
    "Bucknell": "Patriot League",
    "Colgate": "Patriot League",
    "Holy Cross": "Patriot League",
    "Lehigh": "Patriot League",
    "Loyola Maryland": "Patriot League",
    "MIT": "Patriot League",
    "Navy": "Patriot League",
    
    # Coastal Athletic Association (CAA)
    "Delaware": "CAA",
    "Drexel": "CAA",
    "Eastern Michigan": "CAA",
    "Monmouth": "CAA",
    "Northeastern": "CAA",
    "UC San Diego": "CAA",
    "Uconn": "CAA",
    "Villanova ": "CAA",
    
    # Metro Atlantic Athletic Conference (MAAC)
    "Canisius": "MAAC",
    "Drake": "MAAC",
    "Fairfield": "MAAC",
    "Iona": "MAAC",
    "Jacksonville": "MAAC",
    "Manhattan": "MAAC",
    "Marist": "MAAC",
    "Robert Morris": "MAAC",
    "Sacred Heart": "MAAC",
    "Stetson": "MAAC",
    
    # Big 12 Conference
    "Kansas": "Big 12",
    "Kansas State - KSU": "Big 12",
    "Old Dominion": "Big 12",
    "Tulsa": "Big 12",
    "UCF": "Big 12",
    "West Virginia University  - WVU": "Big 12",
    
    # Independents & Other Programs
    "Bryant": "Independent",
    "Georgetown": "Independent",
    "Sacramento State": "Independent",
    "Seattle": "Independent",
    "Temple": "Independent",
}

class RowingDatabaseInitializer:
    """Initializes the rowing database with CRR name as the primary school identifier."""
    
    def __init__(self, db_path: str = "rowing_database.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        print(f"Connected to database: {db_path}")
    
    def create_tables(self):
        """Create all tables with enhanced schema for CRR name management."""
        print("Creating database tables...")
        cursor = self.conn.cursor()
        
        # Schools table - CRR name is the primary display identifier
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                school_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                short_name TEXT,
                acronym TEXT,
                crr_name TEXT NOT NULL UNIQUE,
                color TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add index on CRR name for fast lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schools_crr_name ON schools(crr_name)")
        
        # Teams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                team_id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id INTEGER NOT NULL,
                gender TEXT NOT NULL CHECK (gender IN ('M', 'W')),
                weight TEXT NOT NULL CHECK (weight IN ('LW', 'HW', 'OW')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (school_id) REFERENCES schools (school_id) ON UPDATE CASCADE ON DELETE CASCADE,
                UNIQUE(school_id, gender, weight)
            )
        """)
        
        # Conference affiliations table for historical tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conference_affiliations (
                affiliation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                conference TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams (team_id) ON UPDATE CASCADE ON DELETE CASCADE
            )
        """)
        
        # School participations table for D1 Schools tab
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS school_participations (
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
        
        # Regattas table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regattas (
                regatta_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                start_date DATE,
                end_date DATE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
                event_distance TEXT DEFAULT '2k',
                scheduled_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (regatta_id) REFERENCES regattas (regatta_id) ON UPDATE CASCADE ON DELETE CASCADE
            )
        """)
        
        # Entries table with conference_at_time for historical accuracy
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                entry_boat_class TEXT,
                conference_at_time TEXT,
                seed INTEGER,
                notes TEXT DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events (event_id) ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY (team_id) REFERENCES teams (team_id) ON UPDATE CASCADE ON DELETE CASCADE
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
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES entries (entry_id) ON UPDATE CASCADE ON DELETE CASCADE
            )
        """)
        
        # Add trigger to update timestamps
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_schools_timestamp 
            AFTER UPDATE ON schools 
            BEGIN
                UPDATE schools SET updated_at = CURRENT_TIMESTAMP WHERE school_id = NEW.school_id;
            END
        """)
        
        self.conn.commit()
        print("✓ Database tables created successfully with CRR name support")
    
    def migrate_existing_data(self):
        """Migrate existing data to new schema if needed."""
        print("Checking for existing data to migrate...")
        cursor = self.conn.cursor()
        
        # Check if schools table needs extended columns
        cursor.execute("PRAGMA table_info(schools)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
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
                print(f"  ✓ Added {column_name} column to schools table")
        
        # Ensure CRR name is populated and unique
        cursor.execute("SELECT school_id, name, crr_name FROM schools WHERE crr_name IS NULL OR crr_name = ''")
        schools_to_update = cursor.fetchall()
        
        for school_id, name, crr_name in schools_to_update:
            # Use name as CRR name if not set
            new_crr_name = crr_name if crr_name else name
            cursor.execute("UPDATE schools SET crr_name = ? WHERE school_id = ?", (new_crr_name, school_id))
            print(f"  ✓ Set CRR name for {name}: '{new_crr_name}'")
        
        # Add unique constraint to CRR name if it doesn't exist
        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_schools_crr_name_unique ON schools(crr_name)")
        except sqlite3.IntegrityError:
            print("  ⚠️  Warning: Duplicate CRR names found - manual cleanup required")
        
        # Add migration for entries table notes column
        self.migrate_entries_table_for_notes()
        self.migrate_events_table_for_event_distance()
        self.conn.commit()
        print("✓ Migration completed")

    def migrate_entries_table_for_notes(self):
        """Add notes column to existing entries table if it doesn't exist."""
        print("Checking entries table for notes column...")
        cursor = self.conn.cursor()
        
        try:
            # Check if notes column exists
            cursor.execute("PRAGMA table_info(entries)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            
            if 'notes' not in existing_columns:
                cursor.execute("ALTER TABLE entries ADD COLUMN notes TEXT DEFAULT ''")
                print("  ✓ Added notes column to entries table")
                self.conn.commit()
            else:
                print("  ✓ Notes column already exists in entries table")
                
        except Exception as e:
            print(f"  ⚠️  Error adding notes column: {e}")
            self.conn.rollback()

    def migrate_events_table_for_event_distance(self):
        """Add event_distance column to existing events table if it doesn't exist."""
        print("Checking events table for event_distance column...")
        cursor = self.conn.cursor()
        
        try:
            # Check if event_distance column exists
            cursor.execute("PRAGMA table_info(events)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            
            if 'event_distance' not in existing_columns:
                cursor.execute("ALTER TABLE events ADD COLUMN event_distance TEXT DEFAULT '2k'")
                print("  ✓ Added event_distance column to events table")
                self.conn.commit()
            else:
                print("  ✓ event_distance column already exists in events table")
                
        except Exception as e:
            print(f"  ⚠️  Error adding event_distance column: {e}")
            self.conn.rollback()

    def clear_existing_data(self):
        """Clear existing schools and teams data."""
        print("Clearing existing schools and teams data...")
        cursor = self.conn.cursor()
        
        # Delete in order due to foreign key constraints
        cursor.execute("DELETE FROM results")
        cursor.execute("DELETE FROM entries") 
        cursor.execute("DELETE FROM school_participations")
        cursor.execute("DELETE FROM conference_affiliations")
        cursor.execute("DELETE FROM teams")
        cursor.execute("DELETE FROM schools")
        
        self.conn.commit()
        print("✓ Existing data cleared")
    
    def populate_schools(self):
        """Add all schools from SCHOOL_EXTENDED_INFO with CRR name as key."""
        print("Populating schools with CRR name as primary identifier...")
        cursor = self.conn.cursor()
        
        schools_added = 0
        for crr_name, school_info in SCHOOL_EXTENDED_INFO.items():
            # Unpack the school info tuple
            name, short_name, acronym, color, ow, hm, lm, lw = school_info
            
            try:
                cursor.execute("""
                    INSERT INTO schools (name, short_name, acronym, crr_name, color) 
                    VALUES (?, ?, ?, ?, ?)
                """, (name, short_name, acronym, crr_name, color))
                schools_added += 1
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    # School already exists, update extended info
                    cursor.execute("""
                        UPDATE schools 
                        SET name = ?, short_name = ?, acronym = ?, color = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE crr_name = ?
                    """, (name, short_name, acronym, color, crr_name))
                    print(f"  ✓ Updated existing school: {crr_name}")
                else:
                    raise e
        
        self.conn.commit()
        print(f"✓ Added/updated {schools_added} schools using CRR name as key")
    
    def populate_teams(self):
        """Add teams for each school based on their participation."""
        print("Populating teams...")
        cursor = self.conn.cursor()
        
        teams_added = 0
        for crr_name, school_info in SCHOOL_EXTENDED_INFO.items():
            name, short_name, acronym, color, ow, hm, lm, lw = school_info
            
            # Get school_id by CRR name
            cursor.execute("SELECT school_id FROM schools WHERE crr_name = ?", (crr_name,))
            result = cursor.fetchone()
            if not result:
                print(f"Warning: School with CRR name '{crr_name}' not found")
                continue
            
            school_id = result[0]
            
            # Create teams based on participation flags
            team_types = []
            if ow:
                team_types.append(("W", "OW"))
            if hm:
                team_types.append(("M", "HW"))
            if lm:
                team_types.append(("M", "LW"))
            if lw:
                team_types.append(("W", "LW"))
            
            for gender, weight in team_types:
                try:
                    cursor.execute(
                        "INSERT INTO teams (school_id, gender, weight) VALUES (?, ?, ?)",
                        (school_id, gender, weight)
                    )
                    teams_added += 1
                except sqlite3.IntegrityError:
                    # Team already exists
                    pass
        
        self.conn.commit()
        print(f"✓ Added {teams_added} teams")
    
    def populate_conference_affiliations(self):
        """Add conference affiliations using CRR names."""
        print("Populating conference affiliations for 2024-2025 academic year...")
        cursor = self.conn.cursor()
        
        affiliations_added = 0
        start_date = "2024-09-01"
        end_date = "2025-08-31"
        
        for crr_name, conference in OPENWEIGHT_WOMEN_CONFERENCES.items():
            # Find the team_id using CRR name
            cursor.execute("""
                SELECT t.team_id FROM teams t
                JOIN schools s ON t.school_id = s.school_id
                WHERE s.crr_name = ? AND t.gender = 'W' AND t.weight = 'OW'
            """, (crr_name,))
            
            result = cursor.fetchone()
            if not result:
                print(f"Warning: Openweight Women team not found for CRR name '{crr_name}'")
                continue
            
            team_id = result[0]
            
            try:
                cursor.execute("""
                    INSERT INTO conference_affiliations (team_id, conference, start_date, end_date)
                    VALUES (?, ?, ?, ?)
                """, (team_id, conference, start_date, end_date))
                affiliations_added += 1
            except sqlite3.IntegrityError:
                # Affiliation already exists
                pass
        
        self.conn.commit()
        print(f"✓ Added {affiliations_added} conference affiliations using CRR names")
    
    def populate_school_participations(self):
        """Create initial school participation records using CRR names."""
        print("Creating initial school participation records...")
        cursor = self.conn.cursor()
        
        current_year = datetime.now().year
        start_date = f"{current_year}-09-01"
        
        participation_count = 0
        for crr_name, school_info in SCHOOL_EXTENDED_INFO.items():
            name, short_name, acronym, color, ow, hm, lm, lw = school_info
            
            # Get school_id by CRR name
            cursor.execute("SELECT school_id FROM schools WHERE crr_name = ?", (crr_name,))
            result = cursor.fetchone()
            if not result:
                continue
            
            school_id = result[0]
            
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
                    """, (school_id, start_date, ow, hm, lm, lw))
                    participation_count += 1
        
        self.conn.commit()
        print(f"✓ Created {participation_count} initial participation records for {current_year} season")
    
    def print_summary(self):
        """Print a summary of what was added to the database."""
        print("\n" + "="*60)
        print("DATABASE INITIALIZATION SUMMARY")
        print("="*60)
        
        cursor = self.conn.cursor()
        
        # Count schools
        cursor.execute("SELECT COUNT(*) FROM schools")
        school_count = cursor.fetchone()[0]
        print(f"Schools: {school_count}")
        
        # Show sample CRR names
        cursor.execute("SELECT crr_name FROM schools ORDER BY crr_name LIMIT 5")
        sample_crr_names = [row[0] for row in cursor.fetchall()]
        print(f"Sample CRR names: {', '.join(sample_crr_names)}...")
        
        # Count teams by category
        cursor.execute("SELECT gender, weight, COUNT(*) FROM teams GROUP BY gender, weight ORDER BY gender, weight")
        team_counts = cursor.fetchall()
        print("Teams by category:")
        for gender, weight, count in team_counts:
            category_name = f"{gender} {weight}"
            print(f"  {category_name}: {count}")
        
        # Count total teams
        cursor.execute("SELECT COUNT(*) FROM teams")
        total_teams = cursor.fetchone()[0]
        print(f"Total teams: {total_teams}")
        
        # Count conference affiliations by conference for 2024-2025
        cursor.execute("""
            SELECT ca.conference, COUNT(*) 
            FROM conference_affiliations ca
            JOIN teams t ON ca.team_id = t.team_id
            WHERE t.gender = 'W' AND t.weight = 'OW' 
            AND ca.start_date = '2024-09-01' AND ca.end_date = '2025-08-31'
            GROUP BY ca.conference 
            ORDER BY ca.conference
        """)
        conference_counts = cursor.fetchall()
        print("2024-2025 Openweight Women conference affiliations:")
        for conference, count in conference_counts:
            print(f"  {conference}: {count}")
        
        # Count total conference affiliations
        cursor.execute("SELECT COUNT(*) FROM conference_affiliations")
        total_affiliations = cursor.fetchone()[0]
        print(f"Total conference affiliations: {total_affiliations}")
        
        # Count school participations
        cursor.execute("SELECT COUNT(*) FROM school_participations")
        total_participations = cursor.fetchone()[0]
        print(f"School participation records: {total_participations}")
        
        # Show current participation season
        current_year = datetime.now().year
        cursor.execute("""
            SELECT COUNT(*) FROM school_participations
            WHERE SUBSTR(start_date, 1, 4) = ? AND end_date IS NULL
        """, (str(current_year),))
        current_participations = cursor.fetchone()[0]
        print(f"Current season ({current_year} - current) participations: {current_participations}")
        
        print("="*60)
        print(f"Database ready at: {os.path.abspath(self.db_path)}")
        print("✓ CRR name is now the primary school identifier")
        print("✓ All school references use CRR names for consistency")
        print("✓ D1 School Management tab ready with editable CRR names")
        print("✓ CRR name changes will propagate throughout the system")
    
    def initialize(self, force_recreate: bool = False):
        """Run the complete initialization process."""
        print("Starting rowing database initialization with CRR name support...")
        
        if force_recreate:
            self.clear_existing_data()
        
        self.create_tables()
        self.migrate_existing_data()
        
        # Check if we already have data
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM schools")
        if cursor.fetchone()[0] > 0 and not force_recreate:
            print("Database already contains data. Use --force to recreate.")
            return
        
        self.populate_schools()
        self.populate_teams()
        self.populate_conference_affiliations()
        self.populate_school_participations()
        self.print_summary()
    
    def close(self):
        """Close the database connection."""
        self.conn.close()

def main():
    """Main function to run the initializer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize the rowing database with CRR name-based school management")
    parser.add_argument("database", nargs="?", default="rowing_database.db", 
                       help="Path to the database file (default: rowing_database.db)")
    parser.add_argument("--force", action="store_true", 
                       help="Force recreation of data (will clear existing schools/teams)")
    
    args = parser.parse_args()
    
    try:
        initializer = RowingDatabaseInitializer(args.database)
        initializer.initialize(force_recreate=args.force)
        initializer.close()
        print("\n✓ Database initialization completed successfully!")
        print("✓ CRR names are now the primary school identifiers")
        print("✓ Ready for D1 Schools tab with editable CRR name propagation")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()