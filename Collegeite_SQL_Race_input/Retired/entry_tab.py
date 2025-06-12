"""
Entry management tab for adding team entries to events.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from Collegeite_SQL_Race_input.config.constants import FONT_LABEL, FONT_ENTRY, FONT_BUTTON, FONT_TITLE
from Collegeite_SQL_Race_input.utils import format_event_display_name, format_regatta_display_name, auto_size_treeview_columns, make_treeview_sortable
from Collegeite_SQL_Race_input.widgets import AutoCompleteEntry


class EntryTab:
    """Handles team entries for events."""
    
    def __init__(self, parent_notebook, app):
        self.notebook = parent_notebook
        self.app = app
        self.db = app.get_database()
        
        # Create the tab
        self.frame = ttk.Frame(self.notebook)
        self.notebook.add(self.frame, text="3. Entries")
        
        # UI components
        self.regatta_var = None
        self.regatta_combo = None
        self.regatta_id_map = {}
        self.entry_event_var = None
        self.entry_event_combo = None
        self.entry_event_id_map = {}
        self.selected_event_label = None
        self.team_school_entry = None
        self.entry_boat_class_entry = None
        self.entries_tree = None
        self.current_school_choices = []
        
        self._create_tab()
        self._populate_regatta_combo()
    
    def _create_tab(self):
        """Create the entry management interface."""
        # Title
        tk.Label(self.frame, text="Team Entries", font=FONT_TITLE).pack(pady=10)
        
        # Event selection section for entries
        entry_event_frame = tk.LabelFrame(self.frame, text="Select Event for Entries", font=FONT_LABEL)
        entry_event_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Regatta dropdown
        tk.Label(entry_event_frame, text="Regatta:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.regatta_var = tk.StringVar()
        self.regatta_combo = ttk.Combobox(entry_event_frame, textvariable=self.regatta_var, 
                                         state='readonly', font=FONT_ENTRY)
        self.regatta_combo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.regatta_combo.bind('<<ComboboxSelected>>', self._on_regatta_combo_select)
        
        # Event dropdown for entries
        tk.Label(entry_event_frame, text="Event:", font=FONT_LABEL).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.entry_event_var = tk.StringVar()
        self.entry_event_combo = ttk.Combobox(entry_event_frame, textvariable=self.entry_event_var, 
                                             state='readonly', font=FONT_ENTRY)
        self.entry_event_combo.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        self.entry_event_combo.bind('<<ComboboxSelected>>', self._on_entry_event_combo_select)
        
        # Configure column to expand
        entry_event_frame.columnconfigure(1, weight=1)
        
        # Selected event display
        self.selected_event_label = tk.Label(self.frame, text="No event selected", font=FONT_LABEL, fg='red')
        self.selected_event_label.pack(pady=5)
        
        # Entry form
        form_frame = tk.LabelFrame(self.frame, text="Add Team Entry", font=FONT_LABEL)
        form_frame.pack(fill='x', padx=20, pady=20)
        
        # Team selection with autocomplete
        tk.Label(form_frame, text="School:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.team_school_entry = AutoCompleteEntry(form_frame, [], width=25)
        self.team_school_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Entry boat class (auto-filled from event)
        tk.Label(form_frame, text="Team's Boat Class:", font=FONT_LABEL).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.entry_boat_class_entry = tk.Entry(form_frame, font=FONT_ENTRY, width=15)
        self.entry_boat_class_entry.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        tk.Label(form_frame, text="(auto-filled from event, can edit)", font=("Helvetica", 9)).grid(row=1, column=2, padx=5)
        
        # Add entry button
        tk.Button(form_frame, text="Add Entry", font=FONT_BUTTON, 
                 command=self._add_entry).grid(row=2, column=1, pady=10)
        
        # Current entries display
        entries_frame = tk.LabelFrame(self.frame, text="Current Entries", font=FONT_LABEL)
        entries_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create treeview for entries
        entry_columns = ('Regatta Name', 'Event', 'School', 'Boat Class', 'Conference')
        self.entries_tree = ttk.Treeview(entries_frame, columns=entry_columns, show='headings', height=8)
        
        # Define column headings and widths (initial widths, will be auto-sized)
        self.entries_tree.heading('Regatta Name', text='Regatta Name')
        self.entries_tree.heading('Event', text='Event')
        self.entries_tree.heading('School', text='School')
        self.entries_tree.heading('Boat Class', text='Boat Class')
        self.entries_tree.heading('Conference', text='Conference')
        
        # Set minimum column widths (will be expanded as needed)
        self.entries_tree.column('Regatta Name', width=120, anchor='center')
        self.entries_tree.column('Event', width=200, anchor='center')
        self.entries_tree.column('School', width=150, anchor='center')
        self.entries_tree.column('Boat Class', width=80, anchor='center')
        self.entries_tree.column('Conference', width=120, anchor='center')
        
        # Add scrollbar
        entries_scrollbar = ttk.Scrollbar(entries_frame, orient='vertical', command=self.entries_tree.yview)
        self.entries_tree.configure(yscrollcommand=entries_scrollbar.set)
        
        self.entries_tree.pack(side='left', fill='both', expand=True, padx=10, pady=5)
        entries_scrollbar.pack(side='right', fill='y', pady=5)
        
        # Make the entries table sortable
        sortable_columns = ['Regatta Name', 'Event', 'School', 'Boat Class', 'Conference']
        make_treeview_sortable(self.entries_tree, sortable_columns)
    
    def _populate_regatta_combo(self):
        """Populate the regatta dropdown."""
        regattas = self.db.get_regattas()
        regatta_options = []
        self.regatta_id_map = {}
        
        for regatta_id, name, location, start_date, end_date in regattas:
            display_text = format_regatta_display_name(name, location, start_date)
            regatta_options.append(display_text)
            self.regatta_id_map[display_text] = regatta_id
        
        self.regatta_combo['values'] = regatta_options
        if regatta_options:
            self.regatta_combo.set(regatta_options[0])
            self._on_regatta_combo_select(None)
    
    def _on_regatta_combo_select(self, event):
        """Handle regatta selection and populate events for that regatta."""
        selected_text = self.regatta_var.get()
        if selected_text in self.regatta_id_map:
            regatta_id = self.regatta_id_map[selected_text]
            self._populate_entry_event_combo(regatta_id)
    
    def _populate_entry_event_combo(self, regatta_id=None):
        """Populate the event dropdown for the selected regatta."""
        if regatta_id is None:
            self.entry_event_combo['values'] = []
            return
            
        events = self.db.get_events_for_regatta(regatta_id)
        event_options = []
        self.entry_event_id_map = {}
        
        for event_id, boat_type, event_boat_class, gender, weight, round_name, scheduled_at in events:
            display_text = format_event_display_name(gender, weight, event_boat_class, boat_type, round_name, scheduled_at)
            event_options.append(display_text)
            self.entry_event_id_map[display_text] = event_id
        
        self.entry_event_combo['values'] = event_options
        # Clear selection when regatta changes
        self.entry_event_var.set("")
        self.selected_event_label.config(text="No event selected", fg='red')
        self._clear_entries_display()
        
        # Clear school autocomplete and form
        self.team_school_entry.update_choices([])
        self.team_school_entry.delete(0, tk.END)
        self.entry_boat_class_entry.delete(0, tk.END)
        self.current_school_choices = []
    
    def _on_entry_event_combo_select(self, event):
        """Handle event selection in Entries tab."""
        selected_text = self.entry_event_var.get()
        if selected_text in self.entry_event_id_map:
            event_id = self.entry_event_id_map[selected_text]
            
            # Get event details for team filtering
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT gender, weight, event_boat_class FROM events WHERE event_id = ?", (event_id,))
            event_info = cursor.fetchone()
            
            if event_info:
                gender, weight, event_boat_class = event_info
                
                # Set current event in app
                self.app.set_current_event(event_id, event_boat_class)
                
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
                
                # Focus on school entry for immediate input
                self.team_school_entry.focus_set()
    
    def _populate_team_choices(self, gender: str, weight: str):
        """Populate team choices based on event gender/weight."""
        teams = self.db.get_teams_for_category(gender, weight)
        school_names = [school_name for team_id, school_name, conference in teams]
        
        self.current_school_choices = school_names
        self.team_school_entry.update_choices(school_names)
    
    def _add_entry(self):
        """Add a team entry to the current event."""
        if not self.app.current_event_id:
            messagebox.showerror("Error", "Please select an event first")
            return
        
        school_name = self.team_school_entry.get().strip()
        entry_boat_class = self.entry_boat_class_entry.get().strip()
        
        if not school_name:
            messagebox.showerror("Error", "Please enter a school name")
            return
        
        # Validate that the school is in the allowed list
        if school_name not in self.current_school_choices:
            messagebox.showerror("Error", f"'{school_name}' is not valid for this event. Please select from the autocomplete suggestions.")
            return
        
        # Check for duplicate entries
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM entries e
            JOIN teams t ON e.team_id = t.team_id
            JOIN schools s ON t.school_id = s.school_id
            WHERE e.event_id = ? AND s.name = ?
        """, (self.app.current_event_id, school_name))
        
        if cursor.fetchone()[0] > 0:
            messagebox.showerror("Error", f"'{school_name}' is already entered in this event")
            return
        
        # Get team_id for this school
        cursor.execute("SELECT gender, weight FROM events WHERE event_id = ?", (self.app.current_event_id,))
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
            entry_id = self.db.add_entry(self.app.current_event_id, team_id, entry_boat_class)
            messagebox.showinfo("Success", f"Added entry for {school_name}")
            
            # Clear the school entry for next input
            self.team_school_entry.delete(0, tk.END)
            
            # Focus back on school entry for quick successive entries
            self.team_school_entry.focus_set()
            
            # Refresh entries display
            self._refresh_entries_display()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add entry: {str(e)}")
    
    def _refresh_entries_display(self):
        """Refresh the entries display."""
        # Clear entries tree
        for item in self.entries_tree.get_children():
            self.entries_tree.delete(item)
        
        if not self.app.current_event_id:
            return
        
        # Get entries for current event with regatta and event details
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT e.entry_id, s.name, e.entry_boat_class, t.conference,
                   r.name as regatta_name, 
                   ev.gender, ev.weight, ev.event_boat_class, ev.boat_type, ev.round, ev.scheduled_at
            FROM entries e
            JOIN teams t ON e.team_id = t.team_id
            JOIN schools s ON t.school_id = s.school_id
            JOIN events ev ON e.event_id = ev.event_id
            JOIN regattas r ON ev.regatta_id = r.regatta_id
            WHERE e.event_id = ?
            ORDER BY s.name
        """, (self.app.current_event_id,))
        
        entries = cursor.fetchall()
        
        # Prepare data for display and auto-sizing
        display_data = []
        
        # Populate entries tree
        for (entry_id, school_name, boat_class, conference, 
             regatta_name, gender, weight, event_boat_class, boat_type, round_name, scheduled_at) in entries:
            
            boat_class_display = boat_class if boat_class else ""
            
            # Format event display using the helper function
            event_display = format_event_display_name(gender, weight, event_boat_class, boat_type, round_name, scheduled_at)
            
            row_data = (regatta_name, event_display, school_name, boat_class_display, conference)
            display_data.append(row_data)
            
            self.entries_tree.insert('', 'end', values=row_data)
        
        # Auto-size columns using the utility function
        column_headers = {
            'Regatta Name': 'Regatta Name',
            'Event': 'Event',
            'School': 'School',
            'Boat Class': 'Boat Class',
            'Conference': 'Conference'
        }
        
        min_widths = {
            'Regatta Name': 120,
            'Event': 200,
            'School': 150,
            'Boat Class': 80,
            'Conference': 120
        }
        
        auto_size_treeview_columns(self.entries_tree, display_data, column_headers, min_widths)
    
    def _clear_entries_display(self):
        """Clear the entries display when regatta/event changes."""
        for item in self.entries_tree.get_children():
            self.entries_tree.delete(item)
    
    def refresh(self):
        """Refresh this tab's data (called by main app)."""
        self._populate_regatta_combo()