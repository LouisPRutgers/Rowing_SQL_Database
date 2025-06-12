"""
models.py
Database models and schemas for the rowing competition database.
Located at: Collegeite_SQL_Race_input/database/models.py
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, date


@dataclass
class School:
    """Represents a school/university in the database."""
    school_id: int
    name: str
    short_name: Optional[str] = None
    acronym: Optional[str] = None
    crr_name: Optional[str] = None  # Name as it appears in CRR
    color: Optional[str] = None  # Hex color code
    
    def __str__(self) -> str:
        return self.name
    
    @property
    def display_name(self) -> str:
        """Return the preferred display name."""
        return self.short_name or self.name


@dataclass
class Team:
    """Represents a team (school + gender + weight combination)."""
    team_id: int
    school_id: int
    gender: str  # 'M' or 'W'
    weight: str  # 'LW', 'HW', or 'OW'
    
    # Related objects (populated by queries)
    school: Optional[School] = None
    
    def __str__(self) -> str:
        school_name = self.school.name if self.school else f"School({self.school_id})"
        return f"{school_name} {self.gender} {self.weight}"
    
    @property
    def category_display(self) -> str:
        """Return human-readable team category."""
        gender_map = {'M': "Men's", 'W': "Women's"}
        weight_map = {'LW': "Lightweight", 'HW': "Heavyweight", 'OW': "Openweight"}
        return f"{weight_map.get(self.weight, self.weight)} {gender_map.get(self.gender, self.gender)}"


@dataclass
class ConferenceAffiliation:
    """Represents a team's conference membership during a specific time period."""
    affiliation_id: int
    team_id: int
    conference: str
    start_date: date
    end_date: Optional[date] = None  # NULL for current affiliation
    created_at: Optional[datetime] = None
    
    # Related objects
    team: Optional[Team] = None
    
    def __str__(self) -> str:
        return f"{self.conference} ({self.start_date} - {self.end_date or 'current'})"
    
    @property
    def is_current(self) -> bool:
        """Check if this is the current/active affiliation."""
        return self.end_date is None
    
    @property
    def season_year(self) -> str:
        """Get the academic year (e.g., '2024-2025')."""
        start_year = self.start_date.year
        if self.start_date.month >= 9:  # Academic year starts in September
            return f"{start_year}-{start_year + 1}"
        else:
            return f"{start_year - 1}-{start_year}"


@dataclass
class SchoolParticipation:
    """Represents a school's team participation during a specific season."""
    participation_id: int
    school_id: int
    start_date: date
    end_date: Optional[date] = None  # NULL for current season
    openweight_women: bool = False
    heavyweight_men: bool = False
    lightweight_men: bool = False
    lightweight_women: bool = False
    created_at: Optional[datetime] = None
    
    # Related objects
    school: Optional[School] = None
    
    def __str__(self) -> str:
        school_name = self.school.name if self.school else f"School({self.school_id})"
        season = self.season_display
        return f"{school_name} ({season})"
    
    @property
    def is_current(self) -> bool:
        """Check if this is the current season participation."""
        return self.end_date is None
    
    @property
    def season_display(self) -> str:
        """Get the season display string."""
        start_year = self.start_date.year
        if self.start_date.month >= 9:  # Academic year starts in September
            if self.is_current:
                return f"{start_year} - current"
            else:
                return f"{start_year}-{start_year + 1}"
        else:
            if self.is_current:
                return f"{start_year - 1} - current"
            else:
                return f"{start_year - 1}-{start_year}"
    
    @property
    def participating_teams(self) -> List[str]:
        """Get list of team types this school participates in."""
        teams = []
        if self.openweight_women:
            teams.append("Openweight Women")
        if self.heavyweight_men:
            teams.append("Heavyweight Men")
        if self.lightweight_men:
            teams.append("Lightweight Men")
        if self.lightweight_women:
            teams.append("Lightweight Women")
        return teams


@dataclass
class Regatta:
    """Represents a rowing regatta/competition."""
    regatta_id: int
    name: str
    location: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    def __str__(self) -> str:
        return self.name
    
    @property
    def display_name(self) -> str:
        """Return regatta name with location and date."""
        parts = [self.name]
        if self.location:
            parts.append(f"- {self.location}")
        if self.start_date:
            parts.append(f"({self.start_date})")
        return " ".join(parts)


@dataclass
class Event:
    """Represents a specific event within a regatta."""
    event_id: int
    regatta_id: int
    boat_type: str  # '8+', '4+', '4x', '2x', '1x', '2-'
    event_boat_class: str  # '1V', '2V', '3V', etc.
    gender: str  # 'M' or 'W'
    weight: str  # 'LW', 'HW', or 'OW'
    round: str  # 'Final', 'Heat 1', etc.
    scheduled_at: Optional[datetime] = None
    
    # Related objects
    regatta: Optional[Regatta] = None
    
    def __str__(self) -> str:
        return self.display_name
    
    @property
    def display_name(self) -> str:
        """Return formatted event name."""
        gender_map = {'M': "Men's", 'W': "Women's"}
        weight_map = {'LW': "Lightweight", 'HW': "Heavyweight", 'OW': "Openweight"}
        
        gender_str = gender_map.get(self.gender, self.gender)
        weight_str = weight_map.get(self.weight, self.weight)
        
        name = f"{weight_str} {gender_str} {self.event_boat_class} {self.boat_type} - {self.round}"
        
        if self.scheduled_at:
            name += f" ({self.scheduled_at.strftime('%H:%M')})"
        
        return name


@dataclass
class Entry:
    """Represents a team's entry into a specific event."""
    entry_id: int
    event_id: int
    team_id: int
    entry_boat_class: Optional[str] = None  # Override event boat class if needed
    conference_at_time: Optional[str] = None  # Historical conference when race occurred
    seed: Optional[int] = None
    notes: Optional[str] = ""  # NEW: Notes field for additional information
    
    # Related objects
    event: Optional[Event] = None
    team: Optional[Team] = None
    
    def __str__(self) -> str:
        team_name = str(self.team) if self.team else f"Team({self.team_id})"
        event_name = str(self.event) if self.event else f"Event({self.event_id})"
        return f"{team_name} in {event_name}"
    
    @property
    def boat_class(self) -> str:
        """Get the effective boat class (entry override or event default)."""
        return self.entry_boat_class or (self.event.event_boat_class if self.event else "Unknown")
    
    @property
    def notes_preview(self) -> str:
        """Get a truncated version of notes for display purposes."""
        if not self.notes:
            return ""
        
        MAX_DISPLAY_LENGTH = 50  # Can be moved to constants.py
        if len(self.notes) <= MAX_DISPLAY_LENGTH:
            return self.notes
        else:
            return self.notes[:MAX_DISPLAY_LENGTH-3] + "..."
    
    @property
    def has_notes(self) -> bool:
        """Check if this entry has any notes."""
        return bool(self.notes and self.notes.strip())


@dataclass
class Result:
    """Represents the result of an entry in an event."""
    result_id: int
    entry_id: int
    lane: Optional[int] = None
    position: Optional[int] = None  # 1st, 2nd, 3rd, etc.
    elapsed_sec: Optional[float] = None  # Total race time in seconds
    margin_sec: Optional[float] = None  # Time behind winner in seconds
    
    # Related objects
    entry: Optional[Entry] = None
    
    def __str__(self) -> str:
        if self.position:
            return f"Position {self.position}"
        elif self.elapsed_sec:
            return f"Time: {self.formatted_time}"
        else:
            return "No result"
    
    @property
    def formatted_time(self) -> str:
        """Format elapsed time as MM:SS.fff"""
        if self.elapsed_sec is None:
            return ""
        
        total_ms = int(round(self.elapsed_sec * 1000))
        minutes, remainder = divmod(total_ms, 60000)
        seconds, milliseconds = divmod(remainder, 1000)
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
    
    @property
    def formatted_margin(self) -> str:
        """Format margin as +MM:SS.fff or winner"""
        if self.position == 1:
            return "Winner"
        elif self.margin_sec is None:
            return ""
        else:
            total_ms = int(round(self.margin_sec * 1000))
            minutes, remainder = divmod(total_ms, 60000)
            seconds, milliseconds = divmod(remainder, 1000)
            return f"+{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


# ── Utility Classes ──────────────────────────────────────────────────────

@dataclass
class TeamCategory:
    """Represents a team category (gender + weight combination)."""
    gender: str
    weight: str
    
    @property
    def display_name(self) -> str:
        """Return human-readable category name."""
        gender_map = {'M': "Men's", 'W': "Women's"}
        weight_map = {'LW': "Lightweight", 'HW': "Heavyweight", 'OW': "Openweight"}
        return f"{weight_map.get(self.weight, self.weight)} {gender_map.get(self.gender, self.gender)}"
    
    @property
    def short_name(self) -> str:
        """Return short category name."""
        return f"{self.gender} {self.weight}"


@dataclass
class ConferenceSummary:
    """Summary information about a conference in a specific season."""
    conference: str
    season: str
    team_count: int
    schools: List[str]
    
    def __str__(self) -> str:
        return f"{self.conference} ({self.season}): {self.team_count} teams"


@dataclass
class SeasonSummary:
    """Summary information about a season's participation."""
    season: str
    total_schools: int
    openweight_women: int
    heavyweight_men: int
    lightweight_men: int
    lightweight_women: int
    
    def __str__(self) -> str:
        return f"{self.season}: {self.total_schools} schools participating"
    
    @property
    def team_counts(self) -> dict:
        """Return dictionary of team type counts."""
        return {
            "Openweight Women": self.openweight_women,
            "Heavyweight Men": self.heavyweight_men,
            "Lightweight Men": self.lightweight_men,
            "Lightweight Women": self.lightweight_women
        }


# ── Constants ──────────────────────────────────────────────────────────

BOAT_TYPES = ['8+', '4+', '4x', '2x', '1x', '2-']
GENDERS = ['M', 'W']
WEIGHTS = ['LW', 'HW', 'OW']

GENDER_DISPLAY = {
    'M': "Men's",
    'W': "Women's"
}

WEIGHT_DISPLAY = {
    'LW': "Lightweight",
    'HW': "Heavyweight", 
    'OW': "Openweight"
}

# Common team categories
TEAM_CATEGORIES = [
    TeamCategory('W', 'OW'),  # Women's Openweight
    TeamCategory('W', 'LW'),  # Women's Lightweight
    TeamCategory('M', 'HW'),  # Men's Heavyweight
    TeamCategory('M', 'LW'),  # Men's Lightweight
]

MAX_NOTES_LENGTH = 500
NOTES_DISPLAY_LENGTH = 50