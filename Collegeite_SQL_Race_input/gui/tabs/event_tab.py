"""
Event creation tab for adding events to regattas.
Fixed to prevent regatta selection from changing when creating new events.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry

from Collegeite_SQL_Race_input.config.constants import (BOAT_TYPES, EVENT_BOAT_CLASSES, GENDERS, WEIGHTS, ROUNDS,
                            FONT_LABEL, FONT_ENTRY, FONT_BUTTON, FONT_TITLE)
from Collegeite_SQL_Race_input.widgets import ScheduleTimeEntry
from Collegeite_SQL_Race_input.utils import format_event_display_name, format_regatta_display_name, auto_size_treeview_columns, make_treeview_sortable


class EventTab:
    """Handles event creation within regattas."""
    
    def __init__(self, parent_notebook, app):
        self.notebook = parent_notebook
        self.app = app
        self.db = app.get_database()
        
        # Create the tab
        self.frame = ttk.Frame(self.notebook)
        self.notebook.add(self.frame, text="2. Events")
        
        # UI components
        self.regatta_var = None
        self.regatta_combo = None
        self.regatta_id_map = {}
        self.events_tree = None
        
        # Form variables
        self.boat_type_var = None
        self.event_class_var = None
        self.gender_var = None
        self.weight_var = None
        self.round_var = None
        self.scheduled_date = None
        self.scheduled_time_entry = None
        
        # Store event data for deletion
        self.event_data = {}  # Maps tree item IDs to event data
        
        # Flag to prevent recursive event handling
        self._updating_regatta_combo = False
        
        self._create_tab()
        self._populate_regatta_combo()
    
    def _create_tab(self):
        """Create the event creation interface."""
        # Title
        tk.Label(self.frame, text="Event Creation", font=FONT_TITLE).pack(pady=10)
        
        # Regatta selection section
        regatta_frame = tk.LabelFrame(self.frame, text="Select Regatta", font=FONT_LABEL)
        regatta_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Regatta dropdown
        tk.Label(regatta_frame, text="Regatta:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.regatta_var = tk.StringVar()
        self.regatta_combo = ttk.Combobox(regatta_frame, textvariable=self.regatta_var, 
                                         state='readonly', font=FONT_ENTRY)
        self.regatta_combo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.regatta_combo.bind('<<ComboboxSelected>>', self._on_regatta_combo_select)
        
        # Configure column to expand
        regatta_frame.columnconfigure(1, weight=1)
        
        # Event form
        form_frame = tk.LabelFrame(self.frame, text="Create New Event", font=FONT_LABEL)
        form_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # Boat type
        tk.Label(form_frame, text="Boat Type:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.boat_type_var = tk.StringVar(value=BOAT_TYPES[0])
        boat_type_combo = ttk.Combobox(form_frame, textvariable=self.boat_type_var, 
                                      values=BOAT_TYPES, state='readonly', font=FONT_ENTRY)
        boat_type_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Event boat class
        tk.Label(form_frame, text="Event Class:", font=FONT_LABEL).grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.event_class_var = tk.StringVar(value=EVENT_BOAT_CLASSES[0])
        event_class_combo = ttk.Combobox(form_frame, textvariable=self.event_class_var, 
                                        values=EVENT_BOAT_CLASSES, state='readonly', font=FONT_ENTRY)
        event_class_combo.grid(row=1, column=1, padx=5, pady=5)
        
        # Gender
        tk.Label(form_frame, text="Gender:", font=FONT_LABEL).grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.gender_var = tk.StringVar(value=GENDERS[0][1])
        self.gender_combo = ttk.Combobox(form_frame, textvariable=self.gender_var, 
                                        values=[desc for code, desc in GENDERS], 
                                        state='readonly', font=FONT_ENTRY)
        self.gender_combo.grid(row=2, column=1, padx=5, pady=5)
        self.gender_combo.bind('<<ComboboxSelected>>', self._on_gender_change)
        
        # Weight
        tk.Label(form_frame, text="Weight:", font=FONT_LABEL).grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.weight_var = tk.StringVar()
        self.weight_combo = ttk.Combobox(form_frame, textvariable=self.weight_var, 
                                        state='readonly', font=FONT_ENTRY)
        self.weight_combo.grid(row=3, column=1, padx=5, pady=5)
        self._on_gender_change()
        
        # Round
        tk.Label(form_frame, text="Round:", font=FONT_LABEL).grid(row=4, column=0, sticky='e', padx=5, pady=5)
        self.round_var = tk.StringVar(value=ROUNDS[0])
        round_combo = ttk.Combobox(form_frame, textvariable=self.round_var, 
                                  values=ROUNDS, state='normal', font=FONT_ENTRY)
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
        tk.Button(form_frame, text="Create Event", font=FONT_BUTTON, 
                 command=self._add_event).grid(row=6, column=1, pady=10)
        
        # Events table for selected regatta
        events_frame = tk.LabelFrame(self.frame, text="Events for Selected Regatta", font=FONT_LABEL)
        events_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Create frame for events table and buttons
        events_container = tk.Frame(events_frame)
        events_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create treeview for events
        columns = ('Regatta Name', 'Boat Type', 'Class', 'Gender', 'Weight', 'Round', 'Scheduled')
        self.events_tree = ttk.Treeview(events_container, columns=columns, show='headings', height=8)
        
        # Define column headings and widths
        self.events_tree.heading('Regatta Name', text='Regatta Name')
        self.events_tree.heading('Boat Type', text='Boat Type')
        self.events_tree.heading('Class', text='Class')
        self.events_tree.heading('Gender', text='Gender')
        self.events_tree.heading('Weight', text='Weight')
        self.events_tree.heading('Round', text='Round')
        self.events_tree.heading('Scheduled', text='Scheduled')
        
        self.events_tree.column('Regatta Name', width=150, anchor='center')
        self.events_tree.column('Boat Type', width=80, anchor='center')
        self.events_tree.column('Class', width=60, anchor='center')
        self.events_tree.column('Gender', width=60, anchor='center')
        self.events_tree.column('Weight', width=80, anchor='center')
        self.events_tree.column('Round', width=100, anchor='center')
        self.events_tree.column('Scheduled', width=120, anchor='center')
        
        # Add scrollbar
        events_scrollbar = ttk.Scrollbar(events_container, orient='vertical', command=self.events_tree.yview)
        self.events_tree.configure(yscrollcommand=events_scrollbar.set)
        
        self.events_tree.pack(side='left', fill='both', expand=True)
        events_scrollbar.pack(side='right', fill='y')
        
        # Make the events table sortable
        sortable_columns = ['Regatta Name', 'Boat Type', 'Class', 'Gender', 'Weight', 'Round', 'Scheduled']
        make_treeview_sortable(self.events_tree, sortable_columns)
        
        # DELETION FUNCTIONALITY: Add buttons for event management
        button_frame = tk.Frame(events_frame)
        button_frame.pack(fill='x', padx=10, pady=(0, 5))
        
        # Delete event button
        self.btn_delete_event = tk.Button(button_frame, text="🗑️ Delete Selected Event", 
                                         font=FONT_BUTTON, fg='red',
                                         command=self._delete_selected_event)
        self.btn_delete_event.pack(side='left', padx=5)
        
        # Info label for deletion
        info_label = tk.Label(button_frame, 
                             text="⚠️ Deleting an event will also remove all associated entries and results", 
                             font=("Helvetica", 9), fg='red')
        info_label.pack(side='left', padx=10)
        
        # Bind double-click for selection (helpful for user experience)
        self.events_tree.bind('<Double-1>', self._on_event_double_click)
    
    def _on_gender_change(self, event=None):
        """Update weight options based on selected gender."""
        selected_gender = self.gender_var.get()
        
        if selected_gender == "Men":
            # Men: only LW and HW
            weight_options = ["Heavyweight", "Lightweight"]
        elif selected_gender == "Women":  
            # Women: only OW and LW
            weight_options = ["Openweight", "Lightweight"]
        else:
            # Fallback: all options
            weight_options = [desc for code, desc in WEIGHTS]
        
        self.weight_combo['values'] = weight_options
        
        # Set default weight for the selected gender
        if weight_options:
            self.weight_var.set(weight_options[0])
    
    def _populate_regatta_combo(self):
        """Populate the regatta dropdown with initial data only."""
        self._updating_regatta_combo = True
        try:
            regattas = self.db.get_regattas()
            regatta_options = []
            self.regatta_id_map = {}
            
            for regatta_id, name, location, start_date, end_date in regattas:
                display_text = format_regatta_display_name(name, location, start_date)
                regatta_options.append(display_text)
                self.regatta_id_map[display_text] = regatta_id
            
            # Sort alphabetically
            regatta_options.sort()
            
            self.regatta_combo['values'] = regatta_options
            
            # Only set initial selection if no regatta is currently selected
            if regatta_options and not self.app.current_regatta_id:
                self.regatta_var.set(regatta_options[0])
                # Manually trigger the selection since we're setting it programmatically
                selected_regatta_id = self.regatta_id_map[regatta_options[0]]
                self.app.current_regatta_id = selected_regatta_id
                self._refresh_events_list()
                self._set_default_scheduled_date(selected_regatta_id)
            elif self.app.current_regatta_id:
                # Restore the current selection in the combo
                self._set_regatta_combo_to_current()
        finally:
            self._updating_regatta_combo = False
    
    def _set_regatta_combo_to_current(self):
        """Set the regatta combo to show the current regatta without triggering events."""
        if not self.app.current_regatta_id:
            return
            
        for display_text, regatta_id in self.regatta_id_map.items():
            if regatta_id == self.app.current_regatta_id:
                # Use StringVar.set() to avoid triggering ComboboxSelected event
                self.regatta_var.set(display_text)
                self._refresh_events_list()
                self._set_default_scheduled_date(regatta_id)
                break
    
    def _on_regatta_combo_select(self, event):
        """Handle regatta selection from user interaction."""
        # Prevent recursive calls during programmatic updates
        if self._updating_regatta_combo:
            return
            
        selected_text = self.regatta_var.get()
        if selected_text in self.regatta_id_map:
            regatta_id = self.regatta_id_map[selected_text]
            self.app.set_current_regatta(regatta_id)
            self._refresh_events_list()
            self._set_default_scheduled_date(regatta_id)
    
    def _set_default_scheduled_date(self, regatta_id):
        """Set the scheduled date to the regatta's start date."""
        # Get regatta details to find start date
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT start_date FROM regattas WHERE regatta_id = ?", (regatta_id,))
        result = cursor.fetchone()
        
        if result and result[0]:
            start_date_str = result[0]  # Format: YYYY-MM-DD
            try:
                # Parse the date string and set it in the date picker
                from datetime import datetime
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                self.scheduled_date.set_date(start_date)
            except ValueError:
                # If date parsing fails, just leave it as is
                pass
    
    def _refresh_events_list(self):
        """Refresh the events table for the selected regatta."""
        # Clear existing items and event data mapping
        for item in self.events_tree.get_children():
            self.events_tree.delete(item)
        self.event_data.clear()
        
        if not self.app.current_regatta_id:
            return
        
        # Get regatta name for display
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT name FROM regattas WHERE regatta_id = ?", (self.app.current_regatta_id,))
        regatta_result = cursor.fetchone()
        regatta_name = regatta_result[0] if regatta_result else "Unknown"
        
        events = self.db.get_events_for_regatta(self.app.current_regatta_id)
        
        # Prepare data for display and auto-sizing
        display_data = []
        
        for event_id, boat_type, event_boat_class, gender, weight, round_name, scheduled_at in events:
            # Convert codes to full display names
            gender_display = next((desc for code, desc in GENDERS if code == gender), gender)
            weight_display = next((desc for code, desc in WEIGHTS if code == weight), weight)
            
            scheduled_display = scheduled_at if scheduled_at else ""
            row_data = (regatta_name, boat_type, event_boat_class, gender_display, weight_display, round_name, scheduled_display)
            display_data.append(row_data)
            
            # Insert into tree and store event data for deletion
            item_id = self.events_tree.insert('', 'end', values=row_data)
            self.event_data[item_id] = {
                'event_id': event_id,
                'boat_type': boat_type,
                'event_boat_class': event_boat_class,
                'gender': gender,
                'weight': weight,
                'round_name': round_name,
                'scheduled_at': scheduled_at
            }
        
        # Auto-size columns using the utility function
        column_headers = {
            'Regatta Name': 'Regatta Name',
            'Boat Type': 'Boat Type',
            'Class': 'Class',
            'Gender': 'Gender',
            'Weight': 'Weight',
            'Round': 'Round',
            'Scheduled': 'Scheduled'
        }
        
        min_widths = {
            'Regatta Name': 150,
            'Boat Type': 80,
            'Class': 60,
            'Gender': 60,
            'Weight': 80,
            'Round': 100,
            'Scheduled': 120
        }
        
        auto_size_treeview_columns(self.events_tree, display_data, column_headers, min_widths)
    
    def _on_event_double_click(self, event):
        """Handle double-click on event (for user feedback)."""
        selection = self.events_tree.selection()
        if selection:
            item_id = selection[0]
            if item_id in self.event_data:
                event_info = self.event_data[item_id]
                event_desc = f"{event_info['gender']} {event_info['weight']} {event_info['event_boat_class']} {event_info['boat_type']} - {event_info['round_name']}"
                messagebox.showinfo("Event Selected", f"Selected: {event_desc}\n\nUse the 'Delete Selected Event' button to remove this event.")
    
    def _delete_selected_event(self):
        """Delete the selected event and all associated entries/results."""
        selection = self.events_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select an event to delete.")
            return
        
        item_id = selection[0]
        if item_id not in self.event_data:
            messagebox.showerror("Error", "Could not find event data for selected item.")
            return
        
        event_info = self.event_data[item_id]
        event_id = event_info['event_id']
        
        # Create descriptive event name for confirmation
        event_desc = f"{event_info['gender']} {event_info['weight']} {event_info['event_boat_class']} {event_info['boat_type']} - {event_info['round_name']}"
        if event_info['scheduled_at']:
            event_desc += f" at {event_info['scheduled_at']}"
        
        # Use DatabaseManager method to get entry count
        entry_count = self.db.get_event_entry_count(event_id)
        
        # Create confirmation message
        if entry_count > 0:
            confirm_msg = (f"Are you sure you want to delete this event?\n\n"
                          f"Event: {event_desc}\n\n"
                          f"⚠️ WARNING: This will also permanently delete:\n"
                          f"• {entry_count} team entries\n"
                          f"• All associated race results\n\n"
                          f"This action cannot be undone!")
        else:
            confirm_msg = (f"Are you sure you want to delete this event?\n\n"
                          f"Event: {event_desc}\n\n"
                          f"This action cannot be undone!")
        
        # Show confirmation dialog
        result = messagebox.askyesno("Confirm Event Deletion", confirm_msg, icon='warning')
        if not result:
            return
        
        try:
            # Use DatabaseManager's delete_event method
            results_deleted, entries_deleted, events_deleted = self.db.delete_event(event_id)
            
            if events_deleted > 0:
                # Create success message
                success_msg = f"Successfully deleted event: {event_desc}"
                if entries_deleted > 0 or results_deleted > 0:
                    success_msg += f"\n\nAlso removed:\n"
                    if entries_deleted > 0:
                        success_msg += f"• {entries_deleted} team entries\n"
                    if results_deleted > 0:
                        success_msg += f"• {results_deleted} race results"
                
                messagebox.showinfo("Event Deleted", success_msg)
                
                # Refresh only the events list (not the regatta combo)
                self._refresh_events_list()
                
                # Notify main app to refresh other tabs
                self.app.refresh_all_tabs()
                
            else:
                messagebox.showerror("Error", "Event could not be deleted. It may have already been removed.")
                
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to delete event: {str(e)}")
    
    def _add_event(self):
        """Add a new event to the selected regatta."""
        if not self.app.current_regatta_id:
            messagebox.showerror("Error", "Please select a regatta first")
            return
        
        boat_type = self.boat_type_var.get()
        event_boat_class = self.event_class_var.get()
        gender_display = self.gender_var.get()
        weight_display = self.weight_var.get()

        # Find gender code
        gender = next((code for code, desc in GENDERS if desc == gender_display), "M")
        # Find weight code  
        weight = next((code for code, desc in WEIGHTS if desc == weight_display), "LW")
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
                self.app.current_regatta_id, boat_type, event_boat_class,
                gender, weight, round_name, scheduled_at
            )
            
            event_description = f"{gender_display} {weight_display} {event_boat_class} {boat_type} - {round_name}"
            if scheduled_at:
                event_description += f" at {scheduled_at}"
            
            messagebox.showinfo("Success", f"Created event: {event_description}")
            
            # Reset form for next event
            self.scheduled_time_entry.delete(0, tk.END)
            self.scheduled_time_entry._add_placeholder()
            
            # Refresh ONLY the events display - NOT the regatta combo
            self._refresh_events_list()
            
            # Notify main app about the new event (but don't refresh this tab again)
            # We'll create a more targeted refresh method
            if hasattr(self.app, 'refresh_tabs_except_events'):
                self.app.refresh_tabs_except_events()
            else:
                # Fallback: refresh other tabs manually
                if hasattr(self.app, 'entries_results_tab'):
                    self.app.entries_results_tab.refresh()
                if hasattr(self.app, 'conference_tab'):
                    self.app.conference_tab.refresh()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create event: {str(e)}")
    
    def get_all_events(self):
        """Get all events for use by other tabs."""
        return self.db.get_all_events()
    
    def refresh(self):
        """Refresh this tab's data without changing current regatta selection."""
        # Store the currently selected regatta ID before refreshing
        current_regatta_id = self.app.current_regatta_id
        
        self._updating_regatta_combo = True
        try:
            # Refresh the regatta dropdown options
            regattas = self.db.get_regattas()
            regatta_options = []
            self.regatta_id_map = {}
            
            for regatta_id, name, location, start_date, end_date in regattas:
                display_text = format_regatta_display_name(name, location, start_date)
                regatta_options.append(display_text)
                self.regatta_id_map[display_text] = regatta_id
            
            # Sort alphabetically
            regatta_options.sort()
            
            # Update the combo values
            self.regatta_combo['values'] = regatta_options
            
            # Restore the previous selection if it still exists
            if current_regatta_id and regatta_options:
                # Find the display text for the current regatta ID
                selected_display_text = None
                for display_text, stored_id in self.regatta_id_map.items():
                    if stored_id == current_regatta_id:
                        selected_display_text = display_text
                        break
                
                if selected_display_text:
                    # Set the combo to show the previously selected regatta WITHOUT triggering the event
                    self.regatta_var.set(selected_display_text)
                    # Keep the current regatta ID in the app
                    self.app.current_regatta_id = current_regatta_id
                else:
                    # Current regatta no longer exists, select first available
                    if regatta_options:
                        self.regatta_var.set(regatta_options[0])
                        self.app.current_regatta_id = self.regatta_id_map[regatta_options[0]]
            elif regatta_options and not current_regatta_id:
                # No current selection, select the first one
                self.regatta_var.set(regatta_options[0])
                self.app.current_regatta_id = self.regatta_id_map[regatta_options[0]]
            
            # Refresh the events list for the current regatta
            self._refresh_events_list()
            
        finally:
            self._updating_regatta_combo = False
    
    def refresh_for_regatta(self, regatta_id):
        """Refresh this tab for a specific regatta (called by main app)."""
        # This method is called when regatta selection changes from another tab
        self._updating_regatta_combo = True
        try:
            # Update the combo box to show the selected regatta
            for display_text, stored_id in self.regatta_id_map.items():
                if stored_id == regatta_id:
                    self.regatta_var.set(display_text)
                    self._refresh_events_list()
                    self._set_default_scheduled_date(regatta_id)
                    break
        finally:
            self._updating_regatta_combo = False
    
    def on_regatta_changed(self, regatta_id: int):
        """Handle regatta change notification from main app."""
        self.refresh_for_regatta(regatta_id)