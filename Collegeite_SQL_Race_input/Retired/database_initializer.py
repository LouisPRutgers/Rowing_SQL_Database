#!/usr/bin/env python3
"""
Rowing Database Initializer
===========================

Standalone script to initialize the rowing database with all schools, teams, and conference data.
Run this once to set up the database, then use the main application.

Usage:
    python rowing_db_initializer.py [database_path]
    
If no database path is provided, it will create "rowing_database.db" in the current directory.
"""

import sqlite3
import sys
import os
from typing import Dict, List, Tuple

# ── School and Team Data ──────────────────────────────────────────────
TEAM_SCHOOLS = {
    "Openweight Women": [
        "Alabama", "Boston College", "Boston University - BU", "Brown", "Bryant",
        "Bucknell", "California", "Canisius", "Clemson", "Colgate", "Columbia",
        "Cornell", "Creighton", "Dartmouth", "Dayton", "Delaware", "Drake",
        "Drexel", "Duke", "Duquesne", "Eastern Michigan", "Fairfield", "Fordham",
        "George Mason", "George Washington", "Georgetown", "Gonzaga", "Holy Cross",
        "Indiana", "Iona", "Iowa", "Jacksonville", "Kansas", "Kansas State - KSU",
        "La Salle", "Lehigh", "Louisville", "Loyola Maryland", "Loyola Marymount",
        "MIT", "Manhattan", "Marist", "Miami", "Michigan", "Michigan State",
        "Minnesota", "Monmouth", "Navy", "Northeastern", "Notre Dame", "Ohio State",
        "Oklahoma", "Old Dominion", "Oregon State - OSU", "Penn", "Portland",
        "Princeton", "Radcliff", "Robert Morris", "Rutgers", "SMU", "Sacramento State",
        "Sacred Heart", "Saint Joseph's", "Saint Mary's", "Santa Clara", "Seattle",
        "Stanford", "Stetson", "Syracuse", "Temple", "Tennessee", "Texas", "Tulsa",
        "UC San Diego", "UCF", "UCLA", "UMass", "Uconn", "University of North Carolina - UNC",
        "University of Rhode Island - URI", "University of San Diego - USD",
        "University of Southern California - USC", "Villanova ", "Washington - UW",
        "Washington State University - WSU", "West Virginia University  - WVU",
        "Wisconsin", "Yale"
    ],
    "Heavyweight Men": [
        "Boston University - BU", "Brown", "California", "Colgate", "Columbia",
        "Cornell", "Dartmouth", "Drexel", "Embry-Riddle", "Fairfield",
        "Florida Tech - FIT", "Georgetown", "Gonzaga", "Harvard", "Hobart",
        "Holy Cross", "Iona", "Jacksonville", "La Salle", "Lewis & Clark",
        "Loyola Maryland", "MIT", "Marist", "Mercyhurst", "Navy", "Northeastern",
        "Oklahoma City", "Oregon State - OSU", "Penn", "Princeton", "Rollins",
        "Saint Joseph's", "Santa Clara", "Stanford", "Stetson", "Syracuse",
        "Temple", "UC San Diego", "University of San Diego - USD", "Washington - UW",
        "Wisconsin", "Yale"
    ],
    "Lightweight Men": [
        "Columbia", "Cornell", "Dartmouth", "Georgetown", "Gordon College",
        "Harvard", "MIT", "Mercyhurst", "Navy", "Penn", "Princeton", "Yale"
    ],
    "Lightweight Women": [
        "Boston University - BU", "Georgetown", "Gordon College", "Harvard",
        "MIT", "Princeton", "Stanford", "Wisconsin"
    ],
}

# Conference mappings ONLY for Openweight Women teams
OPENWEIGHT_WOMEN_CONFERENCES = {
    # Atlantic Coast Conference (ACC)
    "Boston College": "ACC",
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
    "Gonzaga": "WCC",
    "Loyola Marymount": "WCC",
    "Oregon State - OSU": "WCC",
    "Portland": "WCC",
    "Saint Mary's": "WCC",
    "University of San Diego - USD": "WCC",
    "Santa Clara": "WCC",
    
    # Atlantic 10 Conference (A-10)
    "Dayton": "A-10",
    "Duquesne": "A-10",
    "Fordham": "A-10",
    "George Mason": "A-10",
    "La Salle": "A-10",
    "George Washington": "A-10",
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
    "Villanova ": "CAA",
    
    # Metro Atlantic Athletic Conference (MAAC)
    "Canisius": "MAAC",
    "Fairfield": "MAAC",
    "Iona": "MAAC",
    "Manhattan": "MAAC",
    "Marist": "MAAC",
    
    # Big 12 Conference
    "Kansas": "Big 12",
    "Kansas State - KSU": "Big 12",
    "UCF": "Big 12",
    "West Virginia University  - WVU": "Big 12",
    
    # Independents & Other Programs
    "Bryant": "Independent",
    "California": "Pac-12",
    "Creighton": "Big East",
    "Drake": "MVC",
    "Georgetown": "Big East",
    "Jacksonville": "ASUN",
    "Old Dominion": "Sun Belt",
    "Robert Morris": "Horizon League",
    "Sacramento State": "Big Sky",
    "Sacred Heart": "NEC",
    "Seattle": "WAC",
    "Stetson": "ASUN",
    "Temple": "AAC",
    "Tulsa": "AAC",
    "UC San Diego": "Big West",
    "UCLA": "Pac-12",
    "Uconn": "Big East",
    "University of Southern California - USC": "Pac-12",
    "Washington - UW": "Pac-12",
    "Washington State University - WSU": "Pac-12"
}

# Create team participation mapping (gender/weight -> schools)
TEAM_PARTICIPATION = {
    ("W", "OW"): TEAM_SCHOOLS["Openweight Women"],
    ("W", "LW"): TEAM_SCHOOLS["Lightweight Women"],
    ("M", "HW"): TEAM_SCHOOLS["Heavyweight Men"],
    ("M", "LW"): TEAM_SCHOOLS["Lightweight Men"],
}

class RowingDatabaseInitializer:
    """Initializes the rowing database with all required data."""
    
    def __init__(self, db_path: str = "rowing_database.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        print(f"Connected to database: {db_path}")
    
    def create_tables(self):
        """Create all tables according to the schema."""
        print("Creating database tables...")
        cursor = self.conn.cursor()
        
        # Schools table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                school_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        # Teams table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                team_id INTEGER PRIMARY KEY AUTOINCREMENT,
                school_id INTEGER NOT NULL,
                gender TEXT NOT NULL CHECK (gender IN ('M', 'W')),
                weight TEXT NOT NULL CHECK (weight IN ('LW', 'HW', 'OW')),
                conference TEXT,
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
        print("✓ Database tables created successfully")
    
    def clear_existing_data(self):
        """Clear existing schools and teams data (but preserve regattas, events, etc.)."""
        print("Clearing existing schools and teams data...")
        cursor = self.conn.cursor()
        
        # Delete in order due to foreign key constraints
        cursor.execute("DELETE FROM results")
        cursor.execute("DELETE FROM entries") 
        cursor.execute("DELETE FROM teams")
        cursor.execute("DELETE FROM schools")
        
        self.conn.commit()
        print("✓ Existing data cleared")
    
    def populate_schools(self):
        """Add all schools from the comprehensive list."""
        print("Populating schools...")
        cursor = self.conn.cursor()
        
        # Get all unique schools from all teams
        all_schools = set()
        for team_schools in TEAM_SCHOOLS.values():
            all_schools.update(team_schools)
        
        schools_added = 0
        for school_name in sorted(all_schools):
            try:
                cursor.execute("INSERT INTO schools (name) VALUES (?)", (school_name,))
                schools_added += 1
            except sqlite3.IntegrityError:
                # School already exists
                pass
        
        self.conn.commit()
        print(f"✓ Added {schools_added} schools")
    
    def populate_teams(self):
        """Add teams for each school based on their participation."""
        print("Populating teams...")
        cursor = self.conn.cursor()
        
        teams_added = 0
        for (gender, weight), school_names in TEAM_PARTICIPATION.items():
            for school_name in school_names:
                # Get school_id
                cursor.execute("SELECT school_id FROM schools WHERE name = ?", (school_name,))
                result = cursor.fetchone()
                if not result:
                    print(f"Warning: School '{school_name}' not found")
                    continue
                
                school_id = result[0]
                
                # Determine conference (only for Openweight Women)
                conference = None
                if gender == "W" and weight == "OW":
                    conference = OPENWEIGHT_WOMEN_CONFERENCES.get(school_name, "Independent")
                
                try:
                    cursor.execute(
                        "INSERT INTO teams (school_id, gender, weight, conference) VALUES (?, ?, ?, ?)",
                        (school_id, gender, weight, conference)
                    )
                    teams_added += 1
                except sqlite3.IntegrityError:
                    # Team already exists
                    pass
        
        self.conn.commit()
        print(f"✓ Added {teams_added} teams")
    
    def print_summary(self):
        """Print a summary of what was added to the database."""
        print("\n" + "="*50)
        print("DATABASE INITIALIZATION SUMMARY")
        print("="*50)
        
        cursor = self.conn.cursor()
        
        # Count schools
        cursor.execute("SELECT COUNT(*) FROM schools")
        school_count = cursor.fetchone()[0]
        print(f"Schools: {school_count}")
        
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
        
        # Count conferences (Openweight Women only)
        cursor.execute("""
            SELECT conference, COUNT(*) 
            FROM teams 
            WHERE gender = 'W' AND weight = 'OW' AND conference IS NOT NULL
            GROUP BY conference 
            ORDER BY conference
        """)
        conference_counts = cursor.fetchall()
        print("Openweight Women conferences:")
        for conference, count in conference_counts:
            print(f"  {conference}: {count}")
        
        print("="*50)
        print(f"Database ready at: {os.path.abspath(self.db_path)}")
        print("You can now run the main rowing database application.")
    
    def initialize(self, force_recreate: bool = False):
        """Run the complete initialization process."""
        print("Starting rowing database initialization...")
        
        if force_recreate:
            self.clear_existing_data()
        
        self.create_tables()
        
        # Check if we already have data
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM schools")
        if cursor.fetchone()[0] > 0 and not force_recreate:
            print("Database already contains data. Use --force to recreate.")
            return
        
        self.populate_schools()
        self.populate_teams()
        self.print_summary()
    
    def close(self):
        """Close the database connection."""
        self.conn.close()

def main():
    """Main function to run the initializer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize the rowing database with schools and teams")
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
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()