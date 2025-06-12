"""
Regatta management tab for creating and viewing regattas.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry

from Collegeite_SQL_Race_input.config.constants import FONT_LABEL, FONT_ENTRY, FONT_BUTTON, FONT_TITLE


class RegattaTab:
    """Handles regatta creation and management."""
    
    def __init__(self, parent_notebook, app):
        self.notebook = parent_notebook
        self.app = app
        self.db = app.get_database()
        
        # Create the tab
        self.frame = ttk.Frame(self.notebook)
        self.notebook.add(self.frame, text="1. Regattas")
        
        # UI components
        self.regatta_listbox = None
        self.regatta_name_entry = None
        self.regatta_location_entry = None
        self.regatta_start_date = None
        self.regatta_end_date = None
        
        # Store regatta data for deletion
        self.regatta_data = {}  # Maps listbox indices to regatta data
        
        self._create_tab()
        self._refresh_regatta_list()
        
        # Set initial end date to match start date
        self._on_start_date_change(None)
    
    def _create_tab(self):
        """Create the regatta management interface."""
        # Title
        tk.Label(self.frame, text="Regatta Management", font=FONT_TITLE).pack(pady=10)
        
        # New regatta form
        form_frame = tk.LabelFrame(self.frame, text="Add New Regatta", font=FONT_LABEL)
        form_frame.pack(fill='x', padx=20, pady=(0, 10))
        
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
        self.regatta_start_date.bind("<<DateEntrySelected>>", self._on_start_date_change)
        
        tk.Label(form_frame, text="End Date:", font=FONT_LABEL).grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.regatta_end_date = DateEntry(form_frame, font=FONT_ENTRY, date_pattern='yyyy-mm-dd')
        self.regatta_end_date.grid(row=3, column=1, sticky='w', padx=5, pady=5)
        
        # Add button
        tk.Button(form_frame, text="Add Regatta", font=FONT_BUTTON, 
                 command=self._add_regatta).grid(row=4, column=1, pady=10)
        
        # Existing regattas section
        existing_frame = tk.LabelFrame(self.frame, text="Existing Regattas", font=FONT_LABEL)
        existing_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Regatta listbox with scrollbar
        list_container = tk.Frame(existing_frame)
        list_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.regatta_listbox = tk.Listbox(list_container, height=8, font=FONT_ENTRY)
        scrollbar = tk.Scrollbar(list_container, orient='vertical', command=self.regatta_listbox.yview)
        self.regatta_listbox.config(yscrollcommand=scrollbar.set)
        self.regatta_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # DELETION FUNCTIONALITY: Add buttons for regatta management
        button_frame = tk.Frame(existing_frame)
        button_frame.pack(fill='x', padx=10, pady=(0, 5))
        
        # Delete regatta button
        self.btn_delete_regatta = tk.Button(button_frame, text="🗑️ Delete Selected Regatta", 
                                           font=FONT_BUTTON, fg='red',
                                           command=self._delete_selected_regatta)
        self.btn_delete_regatta.pack(side='left', padx=5)
        
        # Info label for deletion
        info_label = tk.Label(button_frame, 
                             text="⚠️ Deleting a regatta will remove ALL events, entries, and results", 
                             font=("Helvetica", 9), fg='red')
        info_label.pack(side='left', padx=10)
        
        # Bind double-click for selection feedback
        self.regatta_listbox.bind('<Double-1>', self._on_regatta_double_click)
    
    def _on_start_date_change(self, event):
        """When start date changes, automatically set end date to match."""
        try:
            start_date = self.regatta_start_date.get_date()
            self.regatta_end_date.set_date(start_date)
        except:
            # If there's any issue getting/setting dates, just continue
            pass
    
    def _refresh_regatta_list(self):
        """Refresh the regatta listbox with current data."""
        self.regatta_listbox.delete(0, tk.END)
        self.regatta_data.clear()
        
        regattas = self.db.get_regattas()
        for index, (regatta_id, name, location, start_date, end_date) in enumerate(regattas):
            display_text = f"{name} - {location} ({start_date})"
            self.regatta_listbox.insert(tk.END, display_text)
            
            # Store regatta data for deletion
            self.regatta_data[index] = {
                'regatta_id': regatta_id,
                'name': name,
                'location': location,
                'start_date': start_date,
                'end_date': end_date
            }
    
    def _on_regatta_double_click(self, event):
        """Handle double-click on regatta (for user feedback)."""
        selection = self.regatta_listbox.curselection()
        if selection:
            index = selection[0]
            if index in self.regatta_data:
                regatta_info = self.regatta_data[index]
                regatta_desc = f"{regatta_info['name']} - {regatta_info['location']} ({regatta_info['start_date']})"
                messagebox.showinfo("Regatta Selected", f"Selected: {regatta_desc}\\n\\nUse the 'Delete Selected Regatta' button to remove this regatta.")
    
    def _delete_selected_regatta(self):
        """Delete the selected regatta and all associated events/entries/results."""
        selection = self.regatta_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a regatta to delete.")
            return
        
        index = selection[0]
        if index not in self.regatta_data:
            messagebox.showerror("Error", "Could not find regatta data for selected item.")
            return
        
        regatta_info = self.regatta_data[index]
        regatta_id = regatta_info['regatta_id']
        
        # Create descriptive regatta name for confirmation
        regatta_desc = f"{regatta_info['name']} - {regatta_info['location']}"
        if regatta_info['start_date'] == regatta_info['end_date']:
            regatta_desc += f" ({regatta_info['start_date']})"
        else:
            regatta_desc += f" ({regatta_info['start_date']} to {regatta_info['end_date']})"
        
        # Use DatabaseManager methods to get counts for confirmation
        event_count = self.db.get_regatta_event_count(regatta_id)
        entry_count = self.db.get_regatta_entry_count(regatta_id)
        
        # Create confirmation message
        if event_count > 0 or entry_count > 0:
            confirm_msg = (f"Are you sure you want to delete this regatta?\\n\\n"
                          f"Regatta: {regatta_desc}\\n\\n"
                          f"⚠️ WARNING: This will also permanently delete:\\n")
            
            if event_count > 0:
                confirm_msg += f"• {event_count} events\\n"
            if entry_count > 0:
                confirm_msg += f"• {entry_count} team entries\\n"
                confirm_msg += f"• All associated race results\\n"
            
            confirm_msg += f"\\nThis action cannot be undone!"
        else:
            confirm_msg = (f"Are you sure you want to delete this regatta?\\n\\n"
                          f"Regatta: {regatta_desc}\\n\\n"
                          f"This action cannot be undone!")
        
        # Show confirmation dialog
        result = messagebox.askyesno("Confirm Regatta Deletion", confirm_msg, icon='warning')
        if not result:
            return
        
        try:
            # Use DatabaseManager's delete_regatta method
            results_deleted, entries_deleted, events_deleted, regattas_deleted = self.db.delete_regatta(regatta_id)
            
            if regattas_deleted > 0:
                # Create success message
                success_msg = f"Successfully deleted regatta: {regatta_desc}"
                if events_deleted > 0 or entries_deleted > 0 or results_deleted > 0:
                    success_msg += f"\\n\\nAlso removed:\\n"
                    if events_deleted > 0:
                        success_msg += f"• {events_deleted} events\\n"
                    if entries_deleted > 0:
                        success_msg += f"• {entries_deleted} team entries\\n"
                    if results_deleted > 0:
                        success_msg += f"• {results_deleted} race results"
                
                messagebox.showinfo("Regatta Deleted", success_msg)
                
                # Refresh the regatta list
                self._refresh_regatta_list()
                
                # Notify main app to refresh other tabs
                self.app.refresh_all_tabs()
                
            else:
                messagebox.showerror("Error", "Regatta could not be deleted. It may have already been removed.")
                
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to delete regatta: {str(e)}")
    
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
            
            # Refresh data
            self._refresh_regatta_list()
            
            # Notify main app to refresh other tabs
            self.app.refresh_all_tabs()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add regatta: {str(e)}")
    
    def get_regattas(self):
        """Get all regattas for use by other tabs."""
        return self.db.get_regattas()
    
    def refresh(self):
        """Refresh this tab's data (called by main app)."""
        self._refresh_regatta_list()