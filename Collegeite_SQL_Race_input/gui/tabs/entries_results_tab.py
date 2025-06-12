"""
Combined entries and results tab for adding teams and recording race results.
UPDATED VERSION - Now includes Notes field for each entry
"""
import tkinter as tk
from tkinter import messagebox, ttk

from Collegeite_SQL_Race_input.config.constants import FONT_LABEL, FONT_ENTRY, FONT_BUTTON, FONT_TITLE
from Collegeite_SQL_Race_input.widgets.time_entries import AutoCompleteEntry, TimeEntry
from Collegeite_SQL_Race_input.utils.helpers import (
    format_event_display_name, 
    format_regatta_display_name, 
    auto_size_treeview_columns, 
    make_treeview_sortable,
    format_time_seconds
)


class EntriesResultsTab:
    """Handles team entries and race results in a single workflow."""
    
    def __init__(self, parent_notebook, app):
        self.notebook = parent_notebook
        self.app = app
        self.db = app.get_database()
        
        # Create the tab
        self.frame = ttk.Frame(self.notebook)
        self.notebook.add(self.frame, text="3. Entries & Results")
        
        # UI components
        self.regatta_var = None
        self.regatta_combo = None
        self.regatta_id_map = {}
        self.event_var = None
        self.event_combo = None
        self.event_id_map = {}
        self.selected_event_label = None
        
        # Entry form components
        self.entry_rows = []  # List of (lane_entry, position_label, school_entry, boat_class_entry, time_entry, notes_entry)
        self.results_frame = None
        self.current_school_choices = []
        self.current_event_boat_class = ""
        
        # Results display
        self.results_tree = None
        
        # CRITICAL FIX: Track if this tab is currently active
        self.is_active_tab = False
        
        self._create_tab()
        self._populate_regatta_combo()
        self._setup_tab_focus_tracking()
    
    def _setup_tab_focus_tracking(self):
        """Setup tracking of when this tab becomes active/inactive."""
        # Bind to notebook tab change events
        self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
        
        # Bind Enter key to the entire application window, but filter by tab
        root = self.frame.winfo_toplevel()
        root.bind("<Return>", self._on_global_enter, "+")
    
    def _on_global_enter(self, event):
        """Handle Enter key from anywhere in the application."""
        # Only handle if this tab is currently selected
        try:
            current_tab = self.notebook.select()
            if current_tab:
                current_tab_text = self.notebook.tab(current_tab, 'text')
                if current_tab_text == "3. Entries & Results":
                    print("Global Enter key detected in Entries tab")
                    return self._handle_enter_key(event)
        except:
            pass
        # If not our tab, don't handle it
        return None

    def _on_tab_changed(self, event=None):
        """Handle notebook tab change to track if this tab is active."""
        try:
            current_tab = self.notebook.select()
            if current_tab:
                current_tab_text = self.notebook.tab(current_tab, 'text')
                was_active = self.is_active_tab
                self.is_active_tab = (current_tab_text == "3. Entries & Results")
                
                # Debug print only when status changes
                if was_active != self.is_active_tab:
                    print(f"Tab changed to: '{current_tab_text}', Entries tab active: {self.is_active_tab}")
        except:
            self.is_active_tab = False
    
    def _on_tab_focus_in(self, event=None):
        """Handle focus entering this tab."""
        # Don't change is_active_tab here - let _on_tab_changed handle it
        print("Entries tab widget got focus")
    
    def _on_tab_focus_out(self, event=None):
        """Handle focus leaving this tab."""
        # Don't change is_active_tab here - let _on_tab_changed handle it  
        print("Entries tab widget lost focus")
    
    def _create_tab(self):
        """Create the combined entries and results interface."""
        # Title
        tk.Label(self.frame, text="Entries & Results", font=FONT_TITLE).pack(pady=10)
        
        # Event selection section
        event_frame = tk.LabelFrame(self.frame, text="Select Event", font=FONT_LABEL)
        event_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Regatta dropdown
        tk.Label(event_frame, text="Regatta:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.regatta_var = tk.StringVar()
        self.regatta_combo = ttk.Combobox(event_frame, textvariable=self.regatta_var, 
                                         state='readonly', font=FONT_ENTRY)
        self.regatta_combo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.regatta_combo.bind('<<ComboboxSelected>>', self._on_regatta_combo_select)
        
        # Event dropdown
        tk.Label(event_frame, text="Event:", font=FONT_LABEL).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.event_var = tk.StringVar()
        self.event_combo = ttk.Combobox(event_frame, textvariable=self.event_var, 
                                       state='readonly', font=FONT_ENTRY)
        self.event_combo.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        self.event_combo.bind('<<ComboboxSelected>>', self._on_event_combo_select)
        
        # Configure column to expand
        event_frame.columnconfigure(1, weight=1)
        
        # Selected event display
        self.selected_event_label = tk.Label(self.frame, text="No event selected", font=FONT_LABEL, fg='red')
        self.selected_event_label.pack(pady=5)
        
        # Entry form section
        self.entry_form_frame = tk.LabelFrame(self.frame, text="Enter Results (in finishing order)", font=FONT_LABEL)
        self.entry_form_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Add helpful instruction for time entry
        instruction_frame = tk.Frame(self.entry_form_frame)
        instruction_frame.pack(fill='x', pady=(5, 0))
        
        instruction_text = "💡 Time entry: Use digits (704 = 7:04.000) or standard format (7:04.123)"
        tk.Label(instruction_frame, text=instruction_text, font=("Helvetica", 10), fg='blue').pack()
        
        # HARDCODED WIDTH CONFIGURATION - MODIFY THESE VALUES TO ADJUST COLUMN WIDTHS
        
        # HEADER WIDTHS (characters)
        self.HEADER_LANE_WIDTH = 8        # Lane header width
        self.HEADER_POS_WIDTH = 6         # Position header width  
        self.HEADER_SCHOOL_WIDTH = 59     # School header width (reduced to make room for notes)
        self.HEADER_BOAT_CLASS_WIDTH = 12 # Boat class header width (reduced)
        self.HEADER_TIME_WIDTH = 12       # Time header width
        self.HEADER_NOTES_WIDTH = 20      # NEW: Notes header width
        
        # FIELD WIDTHS (characters) 
        self.FIELD_LANE_WIDTH = 8         # Lane field width
        self.FIELD_POS_WIDTH = 6          # Position field width
        self.FIELD_SCHOOL_WIDTH = 67      # School field width (reduced)
        self.FIELD_BOAT_CLASS_WIDTH = 14  # Boat class field width (reduced)
        self.FIELD_TIME_WIDTH = 13        # Time field width
        self.FIELD_NOTES_WIDTH = 22       # NEW: Notes field width
        
        # Headers with hardcoded widths
        headers_frame = tk.Frame(self.entry_form_frame)
        headers_frame.pack(fill='x', pady=(5, 0), padx=10)
        
        tk.Label(headers_frame, text="Lane", font=FONT_LABEL, width=self.HEADER_LANE_WIDTH, 
                anchor='center', bg='#e8e8e8', relief='ridge', bd=1).pack(side='left')
        tk.Label(headers_frame, text="Pos", font=FONT_LABEL, width=self.HEADER_POS_WIDTH, 
                anchor='center', bg='#e8e8e8', relief='ridge', bd=1).pack(side='left')
        tk.Label(headers_frame, text="School", font=FONT_LABEL, width=self.HEADER_SCHOOL_WIDTH, 
                anchor='center', bg='#e8e8e8', relief='ridge', bd=1).pack(side='left')
        tk.Label(headers_frame, text="Boat Class", font=FONT_LABEL, width=self.HEADER_BOAT_CLASS_WIDTH, 
                anchor='center', bg='#e8e8e8', relief='ridge', bd=1).pack(side='left')
        tk.Label(headers_frame, text="Time", font=FONT_LABEL, width=self.HEADER_TIME_WIDTH, 
                anchor='center', bg='#e8e8e8', relief='ridge', bd=1).pack(side='left')
        tk.Label(headers_frame, text="Notes", font=FONT_LABEL, width=self.HEADER_NOTES_WIDTH, 
                anchor='center', bg='#e8e8e8', relief='ridge', bd=1).pack(side='left')
        
        # Scrollable entry area
        self.canvas_frame = tk.Frame(self.entry_form_frame)
        self.canvas_frame.pack(fill='both', expand=True, padx=10, pady=(0, 5))
        self.canvas = tk.Canvas(self.canvas_frame, highlightthickness=0, height=150)

        self.scrollbar = tk.Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas)
        
        self.scroll_frame.bind("<Configure>", 
                              lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Buttons
        button_frame = tk.Frame(self.entry_form_frame)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="+ Add Entry", font=FONT_BUTTON,
                 command=self._add_entry_row).pack(side='left', padx=5)
        
        self.btn_submit = tk.Button(button_frame, text="Submit Results", font=FONT_BUTTON,
                 command=self._submit_results)
        self.btn_submit.pack(side='left', padx=5)
        self.btn_submit.configure(default="active")
                
        # Results preview
        preview_frame = tk.LabelFrame(self.frame, text="Current Entries", font=FONT_LABEL)
        preview_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create results treeview with Notes column
        result_columns = ('Position', 'Lane', 'School', 'Boat Class', 'Time', 'Margin', 'Notes')
        self.results_tree = ttk.Treeview(preview_frame, columns=result_columns, show='headings', height=8)
        
        # Define column headings
        for col in result_columns:
            self.results_tree.heading(col, text=col)
        for col in result_columns:
            self.results_tree.column(col, anchor='center')
        
        # Add scrollbar
        results_scrollbar = ttk.Scrollbar(preview_frame, orient='vertical', command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_tree.pack(side='left', fill='both', expand=True, padx=10, pady=5)
        results_scrollbar.pack(side='right', fill='y', pady=5)
        
        # Make results table sortable
        make_treeview_sortable(self.results_tree, result_columns)
    
    def _handle_enter_key(self, event):
        """Common handler for Enter key presses."""
        focused = event.widget
        
        print(f"Enter key pressed, focused widget: {type(focused).__name__}")
        
        # Check if focus is on an AutoCompleteEntry that has an active listbox
        if isinstance(focused, AutoCompleteEntry):
            if hasattr(focused, 'lb') and focused.lb and focused.lb.winfo_exists():
                print("AutoComplete listbox is active, letting it handle Enter")
                return  # Let autocomplete handle it
        
        # Check if focus is on a listbox (part of autocomplete)
        if isinstance(focused, tk.Listbox):
            print("Focus is on Listbox, letting it handle Enter")
            return  # Let autocomplete handle it
        
        # Check if focus is on TimeEntry and it's currently editing
        if hasattr(focused, '_is_editing') and focused._is_editing:
            print("TimeEntry is being edited, letting it handle Enter")
            return  # Let TimeEntry finish editing
        
        # For any other widget (including TimeEntry when not editing), submit the form
        print("Submitting results form")
        self._submit_results()
        return "break"  # Consume the event



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
            self._populate_event_combo(regatta_id)
    
    def _populate_event_combo(self, regatta_id=None):
        """Populate the event dropdown for the selected regatta."""
        if regatta_id is None:
            self.event_combo['values'] = []
            return
            
        events = self.db.get_events_for_regatta(regatta_id)
        event_options = []
        self.event_id_map = {}
        
        for event_id, boat_type, event_boat_class, gender, weight, round_name, scheduled_at in events:
            display_text = format_event_display_name(gender, weight, event_boat_class, boat_type, round_name, scheduled_at)
            event_options.append(display_text)
            self.event_id_map[display_text] = event_id
        
        self.event_combo['values'] = event_options
        # Clear selection when regatta changes
        self.event_var.set("")
        self.selected_event_label.config(text="No event selected", fg='red')
        self._clear_form()
        
    def _on_event_combo_select(self, event):
        """Handle event selection with temporal school filtering."""
        selected_text = self.event_var.get()
        if selected_text in self.event_id_map:
            event_id = self.event_id_map[selected_text]
            
            # Get event details
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT gender, weight, event_boat_class FROM events WHERE event_id = ?", (event_id,))
            event_info = cursor.fetchone()
            
            if event_info:
                gender, weight, event_boat_class = event_info
                
                # Set current event in app
                self.app.set_current_event(event_id, event_boat_class)
                self.current_event_boat_class = event_boat_class
                
                # *** ENHANCED: Get event date and use temporal school filtering ***
                event_date = self.db.get_event_date(event_id)
                print(f"🔍 Event date for temporal filtering: {event_date}")
                
                # Get schools that were participating in D1 on the event date
                participating_schools = self.db.get_schools_participating_at_date(gender, weight, event_date)
                self.current_school_choices = participating_schools
                self._update_existing_autocomplete_widgets()
                
                print(f"📚 Available schools for {gender} {weight} on {event_date}: {len(participating_schools)} schools")
                print(f"   Sample schools: {participating_schools[:5]}..." if participating_schools else "   No schools found")
                
                # Update selected event display
                self.selected_event_label.config(
                    text=f"Selected Event: {selected_text}",
                    fg='green'
                )
                
                # Load existing entries if any
                self._load_existing_entries()
                
                # If no existing entries, start with empty form
                if not self.entry_rows:
                    for _ in range(6):  # Start with 6 rows like Race Ranker
                        self._add_entry_row()
                
                # Focus on first school entry
                if self.entry_rows:
                    self.entry_rows[0][2].focus_set()

    def on_event_changed(self, event_id: int, event_boat_class: str = None):
        """Handle event change notification from main app with temporal filtering."""
        self.app.current_event_id = event_id
        if event_boat_class:
            self.current_event_boat_class = event_boat_class
        
        # Find and set the corresponding event in the dropdown
        # First, we need to find which regatta this event belongs to
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT r.regatta_id, r.name, r.location, r.start_date, 
                e.gender, e.weight, e.event_boat_class, e.boat_type, e.round, e.scheduled_at
            FROM events e
            JOIN regattas r ON e.regatta_id = r.regatta_id
            WHERE e.event_id = ?
        """, (event_id,))
        
        result = cursor.fetchone()
        if not result:
            return
        
        regatta_id, regatta_name, location, start_date, gender, weight, event_boat_class, boat_type, round_name, scheduled_at = result
        
        # Set the regatta dropdown
        regatta_display = format_regatta_display_name(regatta_name, location, start_date)
        if regatta_display in self.regatta_id_map:
            self.regatta_var.set(regatta_display)
            self._populate_event_combo(regatta_id)
        
        # Set the event dropdown
        event_display = format_event_display_name(gender, weight, event_boat_class, boat_type, round_name, scheduled_at)
        if event_display in self.event_id_map:
            self.event_var.set(event_display)
            
            # Update the current event info
            self.current_event_boat_class = event_boat_class
            
            # *** ENHANCED: Use temporal school filtering ***
            event_date = self.db.get_event_date(event_id)
            participating_schools = self.db.get_schools_participating_at_date(gender, weight, event_date)
            self.current_school_choices = participating_schools
            self._update_existing_autocomplete_widgets()
            
            print(f"🔄 Event changed: {len(participating_schools)} schools available for {gender} {weight} on {event_date}")
            
            # Update selected event display
            self.selected_event_label.config(
                text=f"Selected Event: {event_display}",
                fg='green'
            )
            
            # Load existing entries if any
            self._load_existing_entries()
            
            # If no existing entries, start with empty form
            if not self.entry_rows:
                for _ in range(6):  # Start with 6 rows like Race Ranker
                    self._add_entry_row()
                
                # Focus on first school entry
                if self.entry_rows:
                    self.entry_rows[0][2].focus_set()


    def _load_existing_entries(self):
        """Load existing entries for the current event."""
        self._clear_form()
        
        if not self.app.current_event_id:
            return
        
        # Get existing entries with any results AND NOTES
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT e.entry_id, s.crr_name, e.entry_boat_class, r.lane, r.position, r.elapsed_sec, e.notes
            FROM entries e
            JOIN teams t ON e.team_id = t.team_id
            JOIN schools s ON t.school_id = s.school_id
            LEFT JOIN results r ON e.entry_id = r.entry_id
            WHERE e.event_id = ?
            ORDER BY COALESCE(r.position, 999), s.crr_name
        """, (self.app.current_event_id,))
        
        entries = cursor.fetchall()
        
        for entry_id, school_name, boat_class, lane, position, elapsed_sec, notes in entries:
            self._add_entry_row()
            row = self.entry_rows[-1]
            
            # Fill in the data using safe methods that don't trigger autocomplete
            if lane:
                row[0].insert(0, str(lane))
            
            # Use set_text method to avoid triggering autocomplete
            row[2].set_text(school_name)  # This is the AutoCompleteEntry
            
            if boat_class:
                row[3].delete(0, tk.END)
                row[3].insert(0, boat_class)
            if elapsed_sec:
                # Use the helper function to format time consistently
                time_str = format_time_seconds(elapsed_sec)
                row[4].insert(0, time_str)
            if notes:  # NEW: Load notes
                row[5].delete(0, tk.END)
                row[5].insert(0, notes)
        
        self._update_positions()
        self._update_preview()  


    def _update_existing_autocomplete_widgets(self):
        """Update autocomplete choices in existing school entry widgets."""
        if not hasattr(self, 'entry_rows'):
            return
        
        # Update all AutoCompleteEntry widgets with new school choices
        updated_count = 0
        for row_data in self.entry_rows:
            if len(row_data) >= 3:  # Make sure we have school_entry
                school_entry = row_data[2]  # school_entry is at index 2
                if hasattr(school_entry, 'update_choices'):
                    school_entry.update_choices(self.current_school_choices)
                    updated_count += 1
        
        if updated_count > 0:
            print(f"✅ Updated {updated_count} autocomplete widgets with new school choices")

    def _add_entry_row(self, school="", time="", notes=""):
        """Add a new entry row to the form with updated autocomplete choices."""
        row_num = len(self.entry_rows) + 1
        row_frame = tk.Frame(self.scroll_frame)
        row_frame.pack(fill='x', pady=1, padx=2)
        
        # HARDCODED WIDTHS - Use field width values for entry widgets
        lane_entry = tk.Entry(row_frame, font=FONT_ENTRY, width=self.FIELD_LANE_WIDTH, justify='center')
        lane_entry.pack(side='left')
        
        position_label = tk.Label(row_frame, text=str(row_num), font=FONT_ENTRY, width=self.FIELD_POS_WIDTH, 
                                anchor='center', relief='flat', bg='#f8f8f8')
        position_label.pack(side='left')
        
        # *** ENHANCED: Use current school choices (which are now temporally filtered) ***
        school_entry = AutoCompleteEntry(row_frame, self.current_school_choices, width=self.FIELD_SCHOOL_WIDTH)
        school_entry.pack(side='left')
        school_entry.insert(0, school)
        
        boat_class_entry = tk.Entry(row_frame, font=FONT_ENTRY, width=self.FIELD_BOAT_CLASS_WIDTH, justify='center')
        boat_class_entry.pack(side='left')
        boat_class_entry.insert(0, self.current_event_boat_class)
        
        time_entry = TimeEntry(row_frame, width=self.FIELD_TIME_WIDTH)
        time_entry.pack(side='left')
        time_entry.insert(0, time)
        
        # Notes entry field
        notes_entry = tk.Entry(row_frame, font=FONT_ENTRY, width=self.FIELD_NOTES_WIDTH)
        notes_entry.pack(side='left')
        notes_entry.insert(0, notes)
        
        # *** ENHANCED: Update autocomplete choices when schools change ***
        def on_school_choices_update():
            """Update autocomplete choices if they've changed."""
            if hasattr(school_entry, 'update_choices'):
                school_entry.update_choices(self.current_school_choices)
        
        # Store the update function for potential future use
        school_entry._update_choices_callback = on_school_choices_update
        
        # Bind events for automatic updates - INCLUDING notes_entry
        for widget in [lane_entry, school_entry, boat_class_entry, notes_entry]:
            widget.bind('<KeyRelease>', self._on_field_change)
            widget.bind('<FocusOut>', self._on_field_change)
        
        # For time_entry, bind only KeyRelease to update preview, but preserve FocusOut for normalization
        def time_entry_focus_out_handler(event):
            # TimeEntry's own _normalize will be called first (it's bound first)
            # Then we update the preview after a small delay
            self.frame.after(10, self._on_field_change)
        
        time_entry.bind('<KeyRelease>', self._on_field_change)
        time_entry.bind('<FocusOut>', time_entry_focus_out_handler, '+')  # '+' means ADD this binding, don't replace
        
        # Store all components including notes_entry
        self.entry_rows.append((lane_entry, position_label, school_entry, boat_class_entry, time_entry, notes_entry, row_frame))
        
        # Update canvas scroll region
        self.scroll_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        return self.entry_rows[-1]



    def _on_field_change(self, event=None):
        """Handle field changes to update positions and preview."""
        self._update_positions()
        self._update_preview()
    
    def _update_positions(self):
        """Update position numbers based on current order."""
        for i, (lane_entry, position_label, school_entry, boat_class_entry, time_entry, notes_entry, row_frame) in enumerate(self.entry_rows):
            position_label.config(text=str(i + 1))
    
    def _update_preview(self):
        """Update the results preview table."""
        # Clear existing preview
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        if not self.entry_rows:
            return
        
        # Collect valid entries with times
        results = []
        for i, (lane_entry, position_label, school_entry, boat_class_entry, time_entry, notes_entry, row_frame) in enumerate(self.entry_rows):
            school = school_entry.get().strip()
            time_text = time_entry.get().strip()
            lane = lane_entry.get().strip()
            boat_class = boat_class_entry.get().strip()
            notes = notes_entry.get().strip()  # NEW: Get notes
            
            if school and time_text:
                try:
                    time_seconds = time_entry.get_seconds()
                    results.append({
                        'position': i + 1,
                        'lane': lane,
                        'school': school,
                        'boat_class': boat_class,
                        'time_display': time_text,
                        'time_seconds': time_seconds,
                        'notes': notes  # NEW: Include notes
                    })
                except:
                    # Invalid time, skip
                    continue
        
        if not results:
            return
        
        # Calculate margins
        fastest_time = min(r['time_seconds'] for r in results)
        
        # Display results
        display_data = []
        for result in results:
            margin = result['time_seconds'] - fastest_time
            margin_display = "0.000" if margin == 0 else f"+{margin:.3f}"
            
            # Truncate notes for display
            notes_display = result['notes'][:20] + "..." if len(result['notes']) > 20 else result['notes']
            
            row_data = (
                result['position'],
                result['lane'],
                result['school'],
                result['boat_class'],
                result['time_display'],
                margin_display,
                notes_display  # NEW: Include notes in display
            )
            display_data.append(row_data)
            self.results_tree.insert('', 'end', values=row_data)
        
        # Auto-size columns
        column_headers = {
            'Position': 'Position',
            'Lane': 'Lane', 
            'School': 'School',
            'Boat Class': 'Boat Class',
            'Time': 'Time',
            'Margin': 'Margin',
            'Notes': 'Notes'  # NEW: Add notes header
        }
        
        min_widths = {
            'Position': 70,
            'Lane': 60,
            'School': 170,  # Reduced to make room for notes
            'Boat Class': 90,  # Reduced
            'Time': 100,
            'Margin': 80,
            'Notes': 150  # NEW: Set minimum width for notes
        }
        
        auto_size_treeview_columns(self.results_tree, display_data, column_headers, min_widths)
    


    def _submit_results(self):
        """Submit all entries and results to the database with enhanced validation."""
        if not self.app.current_event_id:
            messagebox.showerror("Error", "Please select an event first")
            return
        
        # Collect valid entries
        entries = []
        for i, (lane_entry, position_label, school_entry, boat_class_entry, time_entry, notes_entry, row_frame) in enumerate(self.entry_rows):
            school = school_entry.get().strip()
            time_text = time_entry.get().strip()
            lane = lane_entry.get().strip()
            boat_class = boat_class_entry.get().strip()
            notes = notes_entry.get().strip()
            
            if not school:
                continue
            
            # *** ENHANCED: Validate school against temporally filtered choices ***
            if school not in self.current_school_choices:
                # Get event date for better error message
                event_date = self.db.get_event_date(self.app.current_event_id)
                messagebox.showerror("Invalid School", 
                    f"'{school}' was not participating in D1 for this team category on {event_date}.\n\n"
                    f"Only schools with active D1 participation on the event date are valid entries.")
                return
            
            entry_data = {
                'position': i + 1,
                'school': school,
                'boat_class': boat_class,
                'lane': int(lane) if lane else None,
                'time_text': time_text,
                'notes': notes
            }
            
            if time_text:
                try:
                    entry_data['time_seconds'] = time_entry.get_seconds()
                except ValueError:
                    messagebox.showerror("Error", f"Invalid time for {school}: {time_text}")
                    return
            
            entries.append(entry_data)
        
        if not entries:
            messagebox.showerror("Error", "Please enter at least one school")
            return
        
        # Check for duplicates
        schools_entered = [e['school'] for e in entries]
        if len(schools_entered) != len(set(schools_entered)):
            messagebox.showerror("Error", "Duplicate schools entered")
            return
        
        # Validate time order - ensure non-decreasing times in finishing order
        entries_with_times = [e for e in entries if 'time_seconds' in e]
        if len(entries_with_times) > 1:
            for i in range(1, len(entries_with_times)):
                current_entry = entries_with_times[i]
                previous_entry = entries_with_times[i - 1]
                
                if current_entry['time_seconds'] < previous_entry['time_seconds']:
                    messagebox.showerror(
                        "Time Order Error",
                        f"Position {current_entry['position']} ({current_entry['school']}) "
                        f"has a faster time than position {previous_entry['position']} "
                        f"({previous_entry['school']}). Results must be entered in finishing order "
                        f"with slower boats having higher times."
                    )
                    return
        
        try:
            # Clear existing entries for this event
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM results WHERE entry_id IN (SELECT entry_id FROM entries WHERE event_id = ?)", (self.app.current_event_id,))
            cursor.execute("DELETE FROM entries WHERE event_id = ?", (self.app.current_event_id,))
            
            # Add entries and results
            for entry_data in entries:
                # *** ENHANCED: Get team_id using temporally filtered teams ***
                cursor.execute("SELECT gender, weight FROM events WHERE event_id = ?", (self.app.current_event_id,))
                gender, weight = cursor.fetchone()
                
                event_date = self.db.get_event_date(self.app.current_event_id)
                teams = self.db.get_teams_for_category_at_date(gender, weight, event_date)
                team_id = None
                for tid, school_name, conference in teams:
                    if school_name == entry_data['school']:
                        team_id = tid
                        break
                
                if not team_id:
                    raise Exception(f"Team not found for {entry_data['school']} on {event_date}")
                
                # Add entry WITH NOTES
                entry_id = self.db.add_entry(
                    self.app.current_event_id, 
                    team_id, 
                    entry_data['boat_class'],
                    entry_data['notes']
                )
                
                # Add result if time provided
                if 'time_seconds' in entry_data:
                    # Calculate margin from fastest time
                    times_with_values = [e['time_seconds'] for e in entries if 'time_seconds' in e]
                    fastest_time = min(times_with_values) if times_with_values else 0
                    margin = entry_data['time_seconds'] - fastest_time
                    
                    self.db.add_result(
                        entry_id,
                        lane=entry_data['lane'],
                        position=entry_data['position'],
                        elapsed_sec=entry_data['time_seconds'],
                        margin_sec=margin
                    )
            
            messagebox.showinfo("Success", f"Submitted {len(entries)} entries and results!")
            
            # Refresh the display
            self._load_existing_entries()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit: {str(e)}")

    def _clear_form(self):
        """Clear the entry form."""
        for lane_entry, position_label, school_entry, boat_class_entry, time_entry, notes_entry, row_frame in self.entry_rows:
            row_frame.destroy()
        self.entry_rows.clear()
        
        # Clear preview
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
    
    def refresh(self):
        """Refresh this tab's data (called by main app)."""
        self._populate_regatta_combo()