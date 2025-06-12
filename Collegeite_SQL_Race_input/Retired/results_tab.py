"""
Results entry tab for recording race results.
"""

import tkinter as tk
from tkinter import messagebox, ttk

from Collegeite_SQL_Race_input.config.constants import FONT_LABEL, FONT_ENTRY, FONT_BUTTON, FONT_TITLE
from Collegeite_SQL_Race_input.widgets import TimeEntry
from Collegeite_SQL_Race_input.utils import format_event_display_name, format_regatta_display_name, auto_size_treeview_columns


class ResultsTab:
    """Handles race results entry with intuitive workflow."""
    
    def __init__(self, parent_notebook, app):
        self.notebook = parent_notebook
        self.app = app
        self.db = app.get_database()
        
        # Create the tab
        self.frame = ttk.Frame(self.notebook)
        self.notebook.add(self.frame, text="4. Results")
        
        # UI components
        self.regatta_var = None
        self.regatta_combo = None
        self.regatta_id_map = {}
        self.results_event_var = None
        self.results_event_combo = None
        self.results_event_id_map = {}
        self.selected_event_results_label = None
        self.results_tree = None
        self.submit_results_button = None
        
        # Entry form components
        self.entry_widgets = []  # List of (school_label, lane_entry, time_entry, entry_id)
        
        self._create_tab()
        self._populate_regatta_combo()
    
    def _create_tab(self):
        """Create the results entry interface."""
        # Title
        tk.Label(self.frame, text="Race Results", font=FONT_TITLE).pack(pady=10)
        
        # Event selection section
        event_selection_frame = tk.LabelFrame(self.frame, text="Select Event for Results", font=FONT_LABEL)
        event_selection_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Regatta dropdown
        tk.Label(event_selection_frame, text="Regatta:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.regatta_var = tk.StringVar()
        self.regatta_combo = ttk.Combobox(event_selection_frame, textvariable=self.regatta_var, 
                                         state='readonly', font=FONT_ENTRY)
        self.regatta_combo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.regatta_combo.bind('<<ComboboxSelected>>', self._on_regatta_combo_select)
        
        # Event dropdown
        tk.Label(event_selection_frame, text="Event:", font=FONT_LABEL).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.results_event_var = tk.StringVar()
        self.results_event_combo = ttk.Combobox(event_selection_frame, textvariable=self.results_event_var, 
                                               state='readonly', font=FONT_ENTRY)
        self.results_event_combo.grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        self.results_event_combo.bind('<<ComboboxSelected>>', self._on_results_event_combo_select)
        
        # Configure column to expand
        event_selection_frame.columnconfigure(1, weight=1)
        
        # Selected event display
        self.selected_event_results_label = tk.Label(self.frame, text="No event selected for results", font=FONT_LABEL, fg='red')
        self.selected_event_results_label.pack(pady=5)
        
        # Results entry section
        self.results_input_frame = tk.LabelFrame(self.frame, text="Enter Results", font=FONT_LABEL)
        self.results_input_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Entry form will be created dynamically when event is selected
        
        # Results preview section
        preview_frame = tk.LabelFrame(self.frame, text="Results Preview", font=FONT_LABEL)
        preview_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))
        
        # Create results treeview
        result_columns = ('Position', 'School', 'Lane', 'Time', 'Margin')
        self.results_tree = ttk.Treeview(preview_frame, columns=result_columns, show='headings', height=8)
        
        # Define column headings and widths
        self.results_tree.heading('Position', text='Pos')
        self.results_tree.heading('School', text='School')
        self.results_tree.heading('Lane', text='Lane')
        self.results_tree.heading('Time', text='Time')
        self.results_tree.heading('Margin', text='Margin')
        
        self.results_tree.column('Position', width=50, anchor='center')
        self.results_tree.column('School', width=200, anchor='w')
        self.results_tree.column('Lane', width=60, anchor='center')
        self.results_tree.column('Time', width=100, anchor='center')
        self.results_tree.column('Margin', width=80, anchor='center')
        
        # Add scrollbar
        results_scrollbar = ttk.Scrollbar(preview_frame, orient='vertical', command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_tree.pack(side='left', fill='both', expand=True, padx=10, pady=5)
        results_scrollbar.pack(side='right', fill='y', pady=5)
        
        # Submit button
        button_frame = tk.Frame(self.frame)
        button_frame.pack(pady=10)
        
        self.submit_results_button = tk.Button(button_frame, text="Submit Results", font=FONT_BUTTON, 
                                              command=self._submit_results, state='disabled')
        self.submit_results_button.pack()
    
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
            self._populate_results_event_combo(regatta_id)
    
    def _populate_results_event_combo(self, regatta_id=None):
        """Populate the event dropdown for the selected regatta."""
        if regatta_id is None:
            self.results_event_combo['values'] = []
            return
            
        events = self.db.get_events_for_regatta(regatta_id)
        event_options = []
        self.results_event_id_map = {}
        
        for event_id, boat_type, event_boat_class, gender, weight, round_name, scheduled_at in events:
            display_text = format_event_display_name(gender, weight, event_boat_class, boat_type, round_name, scheduled_at)
            event_options.append(display_text)
            self.results_event_id_map[display_text] = event_id
        
        self.results_event_combo['values'] = event_options
        # Clear selection when regatta changes
        self.results_event_var.set("")
        self.selected_event_results_label.config(text="No event selected for results", fg='red')
        self.submit_results_button.config(state='disabled')
        self._clear_results_form()
    
    def _on_results_event_combo_select(self, event):
        """Handle event selection in Results tab."""
        selected_text = self.results_event_var.get()
        if selected_text in self.results_event_id_map:
            event_id = self.results_event_id_map[selected_text]
            self.app.set_current_event(event_id)
            
            self.selected_event_results_label.config(
                text=f"Selected Event: {selected_text}",
                fg='green'
            )
            self.submit_results_button.config(state='normal')
            self._setup_results_form()
    
    def _setup_results_form(self):
        """Set up the results entry form based on current entries."""
        self._clear_results_form()
        
        if not self.app.current_event_id:
            return
        
        # Get entries for current event
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT e.entry_id, s.name, e.entry_boat_class
            FROM entries e
            JOIN teams t ON e.team_id = t.team_id
            JOIN schools s ON t.school_id = s.school_id
            WHERE e.event_id = ?
            ORDER BY s.name
        """, (self.app.current_event_id,))
        
        entries = cursor.fetchall()
        
        if not entries:
            tk.Label(self.results_input_frame, text="No entries found for this event", 
                    font=FONT_LABEL, fg='red').pack(pady=20)
            return
        
        # Create header
        header_frame = tk.Frame(self.results_input_frame)
        header_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(header_frame, text="School", font=FONT_LABEL, width=25, anchor='w').grid(row=0, column=0, padx=5)
        tk.Label(header_frame, text="Lane", font=FONT_LABEL, width=8).grid(row=0, column=1, padx=5)
        tk.Label(header_frame, text="Time", font=FONT_LABEL, width=15).grid(row=0, column=2, padx=5)
        
        # Create entry form for each school
        for i, (entry_id, school_name, boat_class) in enumerate(entries):
            row_frame = tk.Frame(self.results_input_frame)
            row_frame.pack(fill='x', padx=10, pady=2)
            
            # School name (read-only)
            school_text = f"{school_name}"
            if boat_class:
                school_text += f" ({boat_class})"
            school_label = tk.Label(row_frame, text=school_text, font=FONT_ENTRY, width=25, anchor='w')
            school_label.grid(row=0, column=0, padx=5, sticky='w')
            
            # Lane entry
            lane_entry = tk.Entry(row_frame, font=FONT_ENTRY, width=8, justify='center')
            lane_entry.grid(row=0, column=1, padx=5)
            
            # Time entry with smart parsing
            time_entry = TimeEntry(row_frame, width=15)
            time_entry.grid(row=0, column=2, padx=5)
            
            # Bind time entry changes to update preview
            time_entry.bind('<KeyRelease>', self._update_results_preview)
            time_entry.bind('<FocusOut>', self._update_results_preview)
            
            self.entry_widgets.append((school_label, lane_entry, time_entry, entry_id, school_name))
        
        # Focus on first time entry
        if self.entry_widgets:
            self.entry_widgets[0][2].focus_set()
        
        # Initial preview update
        self._update_results_preview()
    
    def _update_results_preview(self, event=None):
        """Update the results preview based on current times."""
        # Clear existing preview
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        if not self.entry_widgets:
            return
        
        # Collect times and create results
        results = []
        for school_label, lane_entry, time_entry, entry_id, school_name in self.entry_widgets:
            time_text = time_entry.get().strip()
            lane_text = lane_entry.get().strip()
            lane = lane_text if lane_text else ""
            
            if time_text:
                try:
                    time_seconds = time_entry.get_seconds()
                    results.append({
                        'school': school_name,
                        'lane': lane,
                        'time_seconds': time_seconds,
                        'time_display': time_text,
                        'entry_id': entry_id
                    })
                except:
                    # Invalid time, skip
                    continue
        
        # Sort by time (fastest first)
        results.sort(key=lambda x: x['time_seconds'])
        
        # Calculate margins and display
        fastest_time = results[0]['time_seconds'] if results else 0
        
        for position, result in enumerate(results, 1):
            margin = result['time_seconds'] - fastest_time
            margin_display = "0.000" if margin == 0 else f"+{margin:.3f}"
            
            self.results_tree.insert('', 'end', values=(
                position,
                result['school'],
                result['lane'],
                result['time_display'],
                margin_display
            ))
        
        # Auto-size columns
        if results:
            display_data = [(
                position,
                result['school'],
                result['lane'],
                result['time_display'],
                f"+{result['time_seconds'] - fastest_time:.3f}" if result['time_seconds'] != fastest_time else "0.000"
            ) for position, result in enumerate(results, 1)]
            
            column_headers = {
                'Position': 'Pos',
                'School': 'School',
                'Lane': 'Lane',
                'Time': 'Time',
                'Margin': 'Margin'
            }
            
            min_widths = {
                'Position': 50,
                'School': 200,
                'Lane': 60,
                'Time': 100,
                'Margin': 80
            }
            
            auto_size_treeview_columns(self.results_tree, display_data, column_headers, min_widths)
    
    def _submit_results(self):
        """Submit all results to the database."""
        if not self.entry_widgets:
            messagebox.showerror("Error", "No entries to submit results for")
            return
        
        # Collect and validate results
        results = []
        for school_label, lane_entry, time_entry, entry_id, school_name in self.entry_widgets:
            time_text = time_entry.get().strip()
            
            if not time_text:
                continue  # Skip entries without times
            
            try:
                time_seconds = time_entry.get_seconds()
                lane_text = lane_entry.get().strip()
                lane = int(lane_text) if lane_text else None
                
                results.append({
                    'entry_id': entry_id,
                    'school': school_name,
                    'time_seconds': time_seconds,
                    'lane': lane
                })
            except ValueError:
                messagebox.showerror("Error", f"Invalid time for {school_name}")
                return
        
        if len(results) < 2:
            messagebox.showerror("Error", "Need at least 2 boats with times to submit results")
            return
        
        # Sort by time to assign positions
        results.sort(key=lambda x: x['time_seconds'])
        fastest_time = results[0]['time_seconds']
        
        try:
            # Submit results to database
            for position, result in enumerate(results, 1):
                margin = result['time_seconds'] - fastest_time
                
                self.db.add_result(
                    result['entry_id'],
                    lane=result['lane'],
                    position=position,
                    elapsed_sec=result['time_seconds'],
                    margin_sec=margin
                )
            
            messagebox.showinfo("Success", f"Results submitted for {len(results)} boats!")
            
            # Clear the form
            self._clear_results_form()
            
            # Reset selections
            self.results_event_var.set("")
            self.selected_event_results_label.config(text="No event selected for results", fg='red')
            self.submit_results_button.config(state='disabled')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit results: {str(e)}")
    
    def _clear_results_form(self):
        """Clear the results form."""
        # Clear entry widgets
        self.entry_widgets.clear()
        
        # Clear the input frame
        for widget in self.results_input_frame.winfo_children():
            widget.destroy()
        
        # Clear preview
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
    
    def refresh(self):
        """Refresh this tab's data (called by main app)."""
        self._populate_regatta_combo()