"""
Conference management tab for viewing and updating team conference affiliations by season.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

from Collegeite_SQL_Race_input.config.constants import FONT_LABEL, FONT_ENTRY, FONT_BUTTON, FONT_TITLE
from Collegeite_SQL_Race_input.widgets import AutoCompleteEntry


class ConferenceTab:
    """Handles season-based conference affiliation management for teams."""
    
    def __init__(self, parent_notebook, app):
        self.notebook = parent_notebook
        self.app = app
        self.db = app.get_database()
        
        # Create the tab
        self.frame = ttk.Frame(self.notebook)
        self.notebook.add(self.frame, text="4. Conferences")
        
        # UI components
        self.team_var = None
        self.team_combo = None
        self.team_categories = []
        self.selected_team_category = None
        
        # Season management
        self.season_notebook = None
        self.seasons = []
        self.current_season = None
        
        # Conference table components
        self.conference_tables = {}  # Maps season to table data
        self.current_table_frame = None
        self.selected_cell = None
        self.selected_conference = None  # Track selected conference
        self.selected_season = None  # NEW: Track selected season tab
        self.scroll_position = {'x': 0, 'y': 0}  # Track scroll position
        
        # Available schools for autocomplete
        self.available_schools = []
        
        self._create_tab()
        self._populate_team_combo()
    
    def _create_tab(self):
        """Create the conference management interface."""
        # Title
        tk.Label(self.frame, text="Conference Management", font=FONT_TITLE).pack(pady=10)
        
        # Team Selection section
        team_frame = tk.LabelFrame(self.frame, text="Team Selection", font=FONT_LABEL)
        team_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        tk.Label(team_frame, text="Select Team Category:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.team_var = tk.StringVar()
        self.team_combo = ttk.Combobox(team_frame, textvariable=self.team_var, 
                                      state='readonly', font=FONT_ENTRY, width=40)
        self.team_combo.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        self.team_combo.bind('<<ComboboxSelected>>', self._on_team_combo_select)
        
        team_frame.columnconfigure(1, weight=1)
        
        # Season tabs container
        self.seasons_frame = tk.LabelFrame(self.frame, text="Conference Management by Season", font=FONT_LABEL)
        self.seasons_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Initially show instruction
        self.instruction_label = tk.Label(self.seasons_frame, 
                                         text="Select a team category above to manage conferences",
                                         font=FONT_LABEL, fg='gray')
        self.instruction_label.pack(pady=50)
    
    def _populate_team_combo(self):
        """Populate the team category dropdown."""
        # Define team categories
        self.team_categories = [
            ("W", "OW", "Women's Openweight Crew"),
            ("W", "LW", "Women's Lightweight Crew"), 
            ("M", "HW", "Men's Heavyweight Crew"),
            ("M", "LW", "Men's Lightweight Crew")
        ]
        
        team_options = [display_name for _, _, display_name in self.team_categories]
        self.team_combo['values'] = team_options
    
    def _on_team_combo_select(self, event):
        """Handle team category selection."""
        selected_display = self.team_var.get()
        
        # Find the selected team category
        for gender, weight, display_name in self.team_categories:
            if display_name == selected_display:
                self.selected_team_category = (gender, weight)
                break
        
        if self.selected_team_category:
            self._load_available_schools()
            self._create_season_interface()
    
    def _load_available_schools(self):
        """Load available schools for the selected team category and current season."""
        if not self.selected_team_category:
            return
        
        # *** ENHANCED: Use temporal filtering if we have a current season ***
        if self.current_season:
            gender, weight = self.selected_team_category
            participating_schools = self.db.get_schools_participating_in_season(gender, weight, self.current_season)
            self.available_schools = participating_schools
            
            print(f"🏫 Loaded {len(participating_schools)} schools for {gender} {weight} in season {self.current_season}")
            print(f"   Sample schools: {participating_schools[:5]}..." if participating_schools else "   No schools found")
        else:
            # Fallback to all teams if no season selected yet
            gender, weight = self.selected_team_category
            teams = self.db.get_teams_for_category(gender, weight)
            self.available_schools = [school_name for _, school_name, _ in teams]
            
            print(f"📚 Fallback: Loaded {len(self.available_schools)} schools (all teams for {gender} {weight})")

    
    def _create_season_interface(self):
        """Create the season tabs and conference table interface."""
        # Clear existing content
        for widget in self.seasons_frame.winfo_children():
            widget.destroy()
        
        # Create seasons container
        seasons_container = tk.Frame(self.seasons_frame)
        seasons_container.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Season tabs frame
        tabs_frame = tk.Frame(seasons_container)
        tabs_frame.pack(fill='x', pady=(0, 10))
        
        # Create season notebook
        self.season_notebook = ttk.Notebook(tabs_frame)
        self.season_notebook.pack(side='left', fill='x', expand=True)
        self.season_notebook.bind('<<NotebookTabChanged>>', self._on_season_tab_change)
        
        # Add Conference button (pack first to be rightmost)
        tk.Button(tabs_frame, text="Add Conference", font=FONT_BUTTON,
                 command=self._add_new_conference).pack(side='right', padx=(10, 0))
        
        # Add Season button (pack second to be left of Add Conference)
        tk.Button(tabs_frame, text="Add New Season", font=FONT_BUTTON,
                 command=self._add_new_season).pack(side='right', padx=(5, 0))
        
        # Table container (will hold the conference table)
        self.table_container = tk.Frame(seasons_container)
        self.table_container.pack(fill='both', expand=True)
        
        # Control buttons frame
        controls_frame = tk.Frame(seasons_container)
        controls_frame.pack(fill='x', pady=(10, 0))
        
        tk.Button(controls_frame, text="Delete Selected", font=FONT_BUTTON, fg='red',
                 command=self._delete_selected).pack(side='left')
        
        tk.Label(controls_frame, text="💡 Right-click season tabs to select for deletion | Click school cells or conference headers to select",
                font=("Helvetica", 9), fg='blue').pack(side='right')
        
        # Load existing seasons
        self._load_seasons()
    
    def _load_seasons(self):
        """Load existing seasons for the selected team category."""
        if not self.selected_team_category:
            return
        
        # Get unique seasons from conference_affiliations
        gender, weight = self.selected_team_category
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT SUBSTR(ca.start_date, 1, 4) as season_year
            FROM conference_affiliations ca
            JOIN teams t ON ca.team_id = t.team_id
            WHERE t.gender = ? AND t.weight = ?
            ORDER BY season_year DESC
        """, (gender, weight))
        
        seasons = cursor.fetchall()
        self.seasons = [f"{row[0]}-{str(int(row[0]) + 1)}" for row in seasons]
        
        # If no seasons exist, create current season
        if not self.seasons:
            current_year = datetime.now().year
            current_season = f"{current_year}-{current_year + 1}"
            self.seasons = [current_season]
        
        # Create tabs for each season
        for season in self.seasons:
            frame = ttk.Frame(self.season_notebook)
            self.season_notebook.add(frame, text=season)
            
            # NEW: Bind right-click to season tab for selection
            tab_id = self.season_notebook.tabs()[-1]  # Get the ID of the just-added tab
            self.season_notebook.bind('<Button-3>', self._on_season_tab_right_click)  # Right-click
            # Also bind regular click to clear season selection when switching tabs normally
            self.season_notebook.bind('<Button-1>', self._on_season_tab_left_click)  # Left-click
        
        # Select first season
        if self.seasons:
            self.season_notebook.select(0)
            self.current_season = self.seasons[0]
            self._load_season_data()
    
    def _on_season_tab_change(self, event):
        """Handle season tab change with school list update."""
        selected_tab = self.season_notebook.select()
        if selected_tab:
            tab_index = self.season_notebook.index(selected_tab)
            if 0 <= tab_index < len(self.seasons):
                old_season = self.current_season
                self.current_season = self.seasons[tab_index]
                
                # *** ENHANCED: Update available schools when season changes ***
                if old_season != self.current_season:
                    print(f"🔄 Season changed from '{old_season}' to '{self.current_season}' - updating school choices")
                    self._load_available_schools()
                    self._update_existing_autocomplete_widgets()
                
                self._load_season_data()
                # Clear season selection when switching tabs normally
                self._clear_season_selection()
    
    def _update_existing_autocomplete_widgets(self):
        """Update autocomplete choices in existing school entry widgets."""
        if not hasattr(self, 'school_cells'):
            return
        
        # Update all AutoCompleteEntry widgets with new school choices
        updated_count = 0
        for (row, col), cell_data in self.school_cells.items():
            widget = cell_data.get('widget')
            if widget and hasattr(widget, 'update_choices'):
                widget.update_choices(self.available_schools)
                updated_count += 1
        
        if updated_count > 0:
            print(f"✅ Updated {updated_count} autocomplete widgets with new school choices")


    def _on_season_tab_right_click(self, event):
        """Handle right-click on season tab to select it for deletion."""
        # Identify which tab was clicked
        clicked_tab = self.season_notebook.tk.call(self.season_notebook._w, "identify", "tab", event.x, event.y)
        if clicked_tab != '':
            tab_index = int(clicked_tab)
            if 0 <= tab_index < len(self.seasons):
                # Clear other selections
                self._clear_selections()
                
                # Select the season tab
                self.selected_season = self.seasons[tab_index]
                
                # Visual feedback - highlight the tab
                self._highlight_season_tab(tab_index)
                
                # Update status
                self._update_selection_status()
    
    def _on_season_tab_left_click(self, event):
        """Handle left-click on season tab (normal navigation)."""
        # Clear season selection when clicking normally
        self._clear_season_selection()
    
    def _highlight_season_tab(self, tab_index):
        """Highlight a season tab to show it's selected for deletion."""
        # Note: tkinter ttk.Notebook doesn't provide easy way to change individual tab colors
        # We'll rely on the status message and selection state for now
        # In a more advanced implementation, you could create custom tab styling
        pass
    
    def _clear_season_selection(self):
        """Clear season tab selection."""
        if self.selected_season:
            self.selected_season = None
            self._update_selection_status()
    
    def _update_selection_status(self):
        """Update the UI to reflect current selection status."""
        # This could be expanded to show selection status in a status bar
        # For now, the Delete Selected button behavior will indicate what's selected
        pass
    
    def _load_season_data(self):
        """Load conference data for the current season with enhanced school filtering."""
        if not self.current_season or not self.selected_team_category:
            return
        
        # *** ENHANCED: Always refresh available schools when loading season data ***
        self._load_available_schools()
        
        # Save current scroll position before reloading
        if hasattr(self, 'current_canvas') and self.current_canvas:
            try:
                self.scroll_position['x'] = self.current_canvas.canvasx(0)
                self.scroll_position['y'] = self.current_canvas.canvasy(0)
            except:
                pass  # Canvas might not be ready yet
        
        # Clear table container
        for widget in self.table_container.winfo_children():
            widget.destroy()
        
        season_year = self.current_season.split('-')[0]
        gender, weight = self.selected_team_category
        
        # *** ENHANCED: Get conference data using CRR names ***
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT s.crr_name, ca.conference
            FROM conference_affiliations ca
            JOIN teams t ON ca.team_id = t.team_id
            JOIN schools s ON t.school_id = s.school_id
            WHERE t.gender = ? AND t.weight = ?
            AND SUBSTR(ca.start_date, 1, 4) = ?
            AND (ca.end_date IS NULL OR SUBSTR(ca.end_date, 1, 4) > ?)
            ORDER BY ca.conference, s.crr_name
        """, (gender, weight, season_year, season_year))
        
        affiliations = cursor.fetchall()
        
        # Organize data by conference
        conference_data = {}
        for school, conference in affiliations:
            if conference not in conference_data:
                conference_data[conference] = []
            conference_data[conference].append(school)
        
        print(f"📊 Loaded conference data for {self.current_season}: {len(affiliations)} affiliations across {len(conference_data)} conferences")
        
        # Create the conference table
        self._create_conference_table(conference_data)



    def _create_conference_table(self, conference_data):
        """Create the conference table with editable cells."""
        # Create scrollable frame with both vertical and horizontal scrollbars
        canvas = tk.Canvas(self.table_container)
        v_scrollbar = ttk.Scrollbar(self.table_container, orient="vertical", command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(self.table_container, orient="horizontal", command=canvas.xview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _on_shift_mousewheel(event):
            canvas.xview_scroll(int(-1*(event.delta/120)), "units")
        
        def _on_ctrl_mousewheel(event):
            canvas.xview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Shift-MouseWheel>", _on_shift_mousewheel)
        canvas.bind("<Control-MouseWheel>", _on_ctrl_mousewheel)
        
        # Store canvas reference for scroll position tracking
        self.current_canvas = canvas
        
        # Determine conferences and max schools per conference
        conferences = list(conference_data.keys()) if conference_data else []
        if not conferences:
            conferences = ["Conference 1", "Conference 2", "Conference 3"]
        
        max_schools = max([len(schools) for schools in conference_data.values()] + [10])
        max_schools = max(max_schools + 5, 15)  # Add buffer and minimum
        
        # FIXED: Create main container with uniform grid
        main_container = tk.Frame(scrollable_frame)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # FIXED: Define consistent cell dimensions
        self.CELL_WIDTH = 180  # Fixed pixel width for all cells
        self.CELL_HEIGHT = 25  # Fixed pixel height for all cells
        
        # FIXED: Create headers with exact pixel sizing and click handlers
        for col, conference in enumerate(conferences):
            header_label = tk.Label(main_container, text=conference, font=FONT_LABEL,
                                   bg='#e8e8e8', relief='ridge', bd=1, cursor='hand2')
            header_label.place(x=col * self.CELL_WIDTH, y=0, 
                              width=self.CELL_WIDTH, height=self.CELL_HEIGHT)
            # NEW: Bind click event to select entire conference
            header_label.bind('<Button-1>', lambda e, conf=conference, c=col: self._select_conference(conf, c))
        
        # FIXED: Create school cells with exact positioning
        self.school_cells = {}
        
        for row in range(max_schools):
            for col, conference in enumerate(conferences):
                school = ""
                if conference in conference_data and row < len(conference_data[conference]):
                    school = conference_data[conference][row]
                
                cell = self._create_school_cell(main_container, row + 1, col, conference, school)  # +1 for header
                self.school_cells[(row, col)] = {
                    'widget': cell,
                    'conference': conference,
                    'school': school,
                    'original_school': school
                }
        
        # FIXED: Set container size based on content
        container_width = len(conferences) * self.CELL_WIDTH
        container_height = (max_schools + 1) * self.CELL_HEIGHT  # +1 for header
        main_container.configure(width=container_width, height=container_height)
        
        # Pack scrollbars
        canvas.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights for the table container
        self.table_container.grid_rowconfigure(0, weight=1)
        self.table_container.grid_columnconfigure(0, weight=1)
        
        # FIXED: Restore scroll position after table is built
        if hasattr(self, 'scroll_position'):
            def restore_scroll():
                try:
                    canvas.xview_moveto(self.scroll_position['x'] / max(container_width, 1))
                    canvas.yview_moveto(self.scroll_position['y'] / max(container_height, 1))
                except:
                    pass  # Ignore errors during scroll restoration
            
            # Use after_idle to ensure canvas is fully rendered
            canvas.after_idle(restore_scroll)
        
        # Store current data
        self.current_conference_data = conference_data
    
    def _create_school_cell(self, parent, row, col, conference, school):
        """Create an editable school cell with exact positioning and temporal autocomplete."""
        y_pos = row * self.CELL_HEIGHT
        x_pos = col * self.CELL_WIDTH
        
        if school:
            # FIXED: Existing school - create label with exact same dimensions
            cell = tk.Label(parent, text=school, bg='white', relief='solid', bd=1,
                        font=FONT_ENTRY, anchor='w')
            cell.place(x=x_pos, y=y_pos, width=self.CELL_WIDTH, height=self.CELL_HEIGHT)
            cell.bind('<Button-1>', lambda e, r=row-1, c=col: self._select_cell(r, c))  # -1 because row includes header
        else:
            # *** ENHANCED: Empty cell - create entry with current available schools ***
            cell = AutoCompleteEntry(parent, self.available_schools)
            cell.place(x=x_pos, y=y_pos, width=self.CELL_WIDTH, height=self.CELL_HEIGHT)
            
            # FIXED: Different timing for Tab vs Enter
            def on_focus_out(event, r=row-1, c=col, conf=conference):
                # Tab key - immediate processing works fine
                parent.after_idle(lambda: self._on_cell_edit(r, c, conf))
            
            cell.bind('<FocusOut>', on_focus_out)
        
        return cell
    
    def _select_cell(self, row, col):
        """Select a cell for deletion."""
        # Clear conference selection
        self._clear_selections()
        
        # Select new cell
        self.selected_cell = (row, col)
        widget = self.school_cells.get((row, col), {}).get('widget')
        if widget and isinstance(widget, tk.Label):
            widget.config(bg='lightblue')
    
    def _select_conference(self, conference_name, col):
        """Select an entire conference for deletion."""
        # Clear cell selection
        self._clear_selections()
        
        # Select entire conference
        self.selected_conference = conference_name
        
        # Highlight all schools in this conference
        for (row, column), cell_data in self.school_cells.items():
            if column == col and cell_data['school']:  # Only highlight filled cells
                widget = cell_data['widget']
                if isinstance(widget, tk.Label):
                    widget.config(bg='lightcoral')  # Different color for conference selection
    
    def _clear_selections(self):
        """Clear all selections (cells, conferences, and seasons)."""
        # Clear cell selection
        if self.selected_cell:
            prev_row, prev_col = self.selected_cell
            prev_widget = self.school_cells.get((prev_row, prev_col), {}).get('widget')
            if prev_widget and isinstance(prev_widget, tk.Label):
                prev_widget.config(bg='white')
        self.selected_cell = None
        
        # Clear conference selection
        if self.selected_conference:
            for (row, col), cell_data in self.school_cells.items():
                if cell_data['conference'] == self.selected_conference and cell_data['school']:
                    widget = cell_data['widget']
                    if isinstance(widget, tk.Label):
                        widget.config(bg='white')
        self.selected_conference = None
        
        # Clear season selection
        self._clear_season_selection()
    
    def _on_cell_edit(self, row, col, conference):
        """Handle cell editing completion with enhanced validation."""
        cell_data = self.school_cells.get((row, col))
        if not cell_data:
            return
        
        widget = cell_data['widget']
        if not isinstance(widget, AutoCompleteEntry):
            return
        
        new_school = widget.get().strip()
        old_school = cell_data['original_school']
        
        if new_school and new_school in self.available_schools:
            if new_school != old_school:
                # Save to database
                self._save_school_to_conference(new_school, conference)
                # Refresh the display
                self._load_season_data()
        elif new_school:
            # *** ENHANCED: Better error message with season context ***
            messagebox.showerror("Invalid School", 
                f"'{new_school}' was not participating in D1 for this team category in season {self.current_season}.\n\n"
                f"Only schools with active D1 participation during the selected season can be added to conferences.")
            widget.delete(0, tk.END)


    def _save_school_to_conference(self, school_name, conference):
        """Save a school's conference affiliation with enhanced validation."""
        if not self.selected_team_category or not self.current_season:
            return
        
        # *** ENHANCED: Validate school is actually available for this season ***
        if school_name not in self.available_schools:
            messagebox.showerror("Invalid School", 
                f"'{school_name}' is not available for this team category in season {self.current_season}")
            return
        
        gender, weight = self.selected_team_category
        season_year = self.current_season.split('-')[0]
        start_date = f"{season_year}-09-01"  # Academic year start
        end_date = f"{int(season_year) + 1}-08-31"  # Academic year end
        
        # *** ENHANCED: Get team_id using CRR name (from enhanced db) ***
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT t.team_id FROM teams t
            JOIN schools s ON t.school_id = s.school_id
            WHERE s.crr_name = ? AND t.gender = ? AND t.weight = ?
        """, (school_name, gender, weight))
        
        result = cursor.fetchone()
        if not result:
            messagebox.showerror("Error", f"Team not found for {school_name}")
            return
        
        team_id = result[0]
        
        try:
            # End any existing affiliation for this season
            cursor.execute("""
                UPDATE conference_affiliations 
                SET end_date = ?
                WHERE team_id = ? AND SUBSTR(start_date, 1, 4) = ?
            """, (f"{season_year}-08-31", team_id, season_year))
            
            # Add new affiliation with proper end date
            cursor.execute("""
                INSERT INTO conference_affiliations (team_id, conference, start_date, end_date)
                VALUES (?, ?, ?, ?)
            """, (team_id, conference, start_date, end_date))
            
            self.db.conn.commit()
            print(f"✅ Added {school_name} to {conference} for season {self.current_season}")
            
        except Exception as e:
            self.db.conn.rollback()
            messagebox.showerror("Database Error", f"Failed to save: {str(e)}")



    def _delete_selected(self):
        """Delete the selected school, conference, or season."""
        if self.selected_season:
            # Delete entire season
            self._delete_season()
        elif self.selected_conference:
            # Delete entire conference
            self._delete_conference()
        elif self.selected_cell:
            # Delete single school
            self._delete_single_school()
        else:
            messagebox.showwarning("No Selection", 
                                  "Please select a season (right-click tab), conference (click header), or school (click cell) to delete.")
    
    def _delete_season(self):
        """Delete an entire season and all its conference affiliations."""
        if not self.selected_season:
            return
        
        season_to_delete = self.selected_season
        season_year = season_to_delete.split('-')[0]
        
        if not self.selected_team_category:
            messagebox.showerror("Error", "No team category selected.")
            return
        
        gender, weight = self.selected_team_category
        
        # Get count of affiliations that will be deleted
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM conference_affiliations ca
            JOIN teams t ON ca.team_id = t.team_id
            WHERE t.gender = ? AND t.weight = ?
            AND SUBSTR(ca.start_date, 1, 4) = ?
        """, (gender, weight, season_year))
        
        affiliation_count = cursor.fetchone()[0]
        
        if affiliation_count == 0:
            messagebox.showwarning("Empty Season", f"Season '{season_to_delete}' has no conference affiliations to delete.")
            return
        
        # Get list of conferences that will be affected
        cursor.execute("""
            SELECT DISTINCT ca.conference FROM conference_affiliations ca
            JOIN teams t ON ca.team_id = t.team_id
            WHERE t.gender = ? AND t.weight = ?
            AND SUBSTR(ca.start_date, 1, 4) = ?
        """, (gender, weight, season_year))
        
        affected_conferences = [row[0] for row in cursor.fetchall()]
        conference_list = ", ".join(affected_conferences)
        
        # Confirm deletion
        confirm_msg = (f"Delete entire season '{season_to_delete}'?\n\n"
                      f"This will permanently remove:\n"
                      f"• {affiliation_count} conference affiliations\n"
                      f"• Affecting conferences: {conference_list}\n\n"
                      f"This action cannot be undone!\n\n"
                      f"Are you sure you want to proceed?")
        
        if not messagebox.askyesno("Confirm Season Deletion", confirm_msg, icon='warning'):
            return
        
        try:
            # Delete all conference affiliations for this season and team category
            cursor.execute("""
                DELETE FROM conference_affiliations 
                WHERE team_id IN (
                    SELECT team_id FROM teams 
                    WHERE gender = ? AND weight = ?
                )
                AND SUBSTR(start_date, 1, 4) = ?
            """, (gender, weight, season_year))
            
            deleted_count = cursor.rowcount
            self.db.conn.commit()
            
            # Remove season from local list
            self.seasons.remove(season_to_delete)
            
            # Clear selection
            self.selected_season = None
            
            # Recreate the interface
            self._create_season_interface()
            
            messagebox.showinfo("Season Deleted", 
                               f"Season '{season_to_delete}' deleted successfully.\n"
                               f"Removed {deleted_count} conference affiliations.")
            
        except Exception as e:
            self.db.conn.rollback()
            messagebox.showerror("Database Error", f"Failed to delete season: {str(e)}")
    
    def _delete_conference(self):
        """Delete an entire conference and all its schools."""
        if not self.selected_conference:
            return
        
        # Get schools in this conference
        schools_in_conference = []
        for (row, col), cell_data in self.school_cells.items():
            if (cell_data['conference'] == self.selected_conference and 
                cell_data['school'] and cell_data['school'].strip()):
                schools_in_conference.append(cell_data['school'])
        
        if not schools_in_conference:
            messagebox.showwarning("Empty Conference", "Selected conference has no schools to delete.")
            return
        
        # Confirm deletion
        school_list = "\n".join([f"• {school}" for school in schools_in_conference])
        confirm_msg = (f"Delete entire conference '{self.selected_conference}'?\n\n"
                      f"This will remove {len(schools_in_conference)} schools:\n"
                      f"{school_list}\n\n"
                      f"This action cannot be undone!")
        
        if not messagebox.askyesno("Confirm Conference Deletion", confirm_msg, icon='warning'):
            return
        
        # Delete all schools in the conference
        deleted_count = 0
        for school in schools_in_conference:
            try:
                self._remove_school_from_conference(school)
                deleted_count += 1
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove {school}: {str(e)}")
        
        if deleted_count > 0:
            messagebox.showinfo("Conference Deleted", 
                               f"Successfully removed {deleted_count} schools from {self.selected_conference}")
            self._clear_selections()
            # Refresh will be called by _remove_school_from_conference
    
    def _delete_single_school(self):
        """Delete a single selected school."""
        if not self.selected_cell:
            return
        
        row, col = self.selected_cell
        cell_data = self.school_cells.get((row, col))
        if not cell_data or not cell_data['school']:
            messagebox.showwarning("No School", "Selected cell is empty.")
            return
        
        school = cell_data['school']
        conference = cell_data['conference']
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion", 
                                  f"Remove {school} from {conference}?"):
            return
        
        self._remove_school_from_conference(school)
    
    def _remove_school_from_conference(self, school_name):
        """Remove a school from its conference for the current season with enhanced validation."""
        if not self.selected_team_category or not self.current_season:
            return
        
        gender, weight = self.selected_team_category
        season_year = self.current_season.split('-')[0]
        end_date = f"{season_year}-08-31"  # End of previous academic year
        
        # *** ENHANCED: Get team_id using CRR name ***
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT t.team_id FROM teams t
            JOIN schools s ON t.school_id = s.school_id
            WHERE s.crr_name = ? AND t.gender = ? AND t.weight = ?
        """, (school_name, gender, weight))
        
        result = cursor.fetchone()
        if not result:
            print(f"⚠️ Team not found for {school_name} when removing from conference")
            return
        
        team_id = result[0]
        
        try:
            # End the affiliation for this season
            cursor.execute("""
                UPDATE conference_affiliations 
                SET end_date = ?
                WHERE team_id = ? AND SUBSTR(start_date, 1, 4) = ? AND end_date IS NULL
            """, (end_date, team_id, season_year))
            
            self.db.conn.commit()
            print(f"✅ Removed {school_name} from conference for season {self.current_season}")
            
            # Refresh display
            self._load_season_data()
            self.selected_cell = None
            self.selected_conference = None
            
        except Exception as e:
            self.db.conn.rollback()
            messagebox.showerror("Database Error", f"Failed to delete: {str(e)}")
    


    def _add_new_conference(self):
        """Add a new conference column to the current season."""
        if not self.current_season or not self.selected_team_category:
            messagebox.showwarning("No Season Selected", "Please select a team category and season first.")
            return
        
        # Create popup dialog for conference name
        self._show_conference_name_dialog()
    
    def _show_conference_name_dialog(self):
        """Show popup dialog to get new conference name."""
        # Create popup window
        dialog = tk.Toplevel(self.frame)
        dialog.title("Add New Conference")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Dialog content
        tk.Label(dialog, text="Enter Conference Name:", font=FONT_LABEL).pack(pady=10)
        
        conference_entry = tk.Entry(dialog, font=FONT_ENTRY, width=30)
        conference_entry.pack(pady=5)
        conference_entry.focus_set()
        
        # Button frame
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        def on_create():
            conference_name = conference_entry.get().strip()
            if not conference_name:
                messagebox.showerror("Invalid Name", "Please enter a conference name.")
                return
            
            # Check if conference already exists
            if hasattr(self, 'current_conference_data') and conference_name in self.current_conference_data:
                messagebox.showerror("Conference Exists", f"Conference '{conference_name}' already exists in this season.")
                return
            
            dialog.destroy()
            self._create_new_conference(conference_name)
        
        def on_cancel():
            dialog.destroy()
        
        tk.Button(button_frame, text="Create", font=FONT_BUTTON, 
                 command=on_create, default='active').pack(side='left', padx=5)
        tk.Button(button_frame, text="Cancel", font=FONT_BUTTON, 
                 command=on_cancel).pack(side='left', padx=5)
        
        # Bind Enter key to create
        conference_entry.bind('<Return>', lambda e: on_create())
        dialog.bind('<Escape>', lambda e: on_cancel())
    
    def _create_new_conference(self, conference_name):
        """Create a new conference column with the given name."""
        if not hasattr(self, 'current_conference_data'):
            self.current_conference_data = {}
        
        # Add empty conference to current data
        self.current_conference_data[conference_name] = []
        
        # Refresh the table to show the new conference
        self._create_conference_table(self.current_conference_data)
        
        messagebox.showinfo("Conference Added", f"Conference '{conference_name}' has been created.\nYou can now add schools to it.")
    
    def _add_new_season(self):
        """Add a new season tab with popup for year selection and optional copying."""
        if not self.selected_team_category:
            messagebox.showwarning("No Team Selected", "Please select a team category first.")
            return
        
        self._show_add_season_dialog()
    
    def _show_add_season_dialog(self):
        """Show popup dialog to select new season year and optional copy source."""
        # Create popup window
        dialog = tk.Toplevel(self.frame)
        dialog.title("Add New Season")
        dialog.geometry("450x200")
        dialog.resizable(False, False)
        dialog.transient(self.frame.winfo_toplevel())
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Main frame
        main_frame = tk.Frame(dialog)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Season selection
        tk.Label(main_frame, text="Select Season:", font=FONT_LABEL).grid(row=0, column=0, sticky='e', padx=5, pady=10)
        
        season_var = tk.StringVar()
        season_combo = ttk.Combobox(main_frame, textvariable=season_var, 
                                   state='readonly', font=FONT_ENTRY, width=15)
        
        # Generate season options programmatically (2000-2001 to 2050-2051)
        # but exclude seasons that already exist
        all_possible_seasons = []
        for year in range(2000, 2051):
            all_possible_seasons.append(f"{year}-{year + 1}")
        
        # Filter out existing seasons
        available_seasons = [season for season in all_possible_seasons if season not in self.seasons]
        
        season_combo['values'] = available_seasons
        season_combo.grid(row=0, column=1, padx=5, pady=10, sticky='w')
        
        # Set default to current year or next available year
        current_year = datetime.now().year
        if self.seasons:
            # Find the latest season and suggest the next one
            latest_season = max(self.seasons)
            latest_year = int(latest_season.split('-')[0])
            suggested_year = max(latest_year + 1, current_year)
        else:
            suggested_year = current_year
        
        default_season = f"{suggested_year}-{suggested_year + 1}"
        if default_season in available_seasons:
            season_combo.set(default_season)
        elif available_seasons:  # If suggested season exists, pick first available
            season_combo.set(available_seasons[0])
        
        # Copy source selection
        tk.Label(main_frame, text="Copy from season:", font=FONT_LABEL).grid(row=1, column=0, sticky='e', padx=5, pady=10)
        
        copy_var = tk.StringVar()
        copy_combo = ttk.Combobox(main_frame, textvariable=copy_var, 
                                 state='readonly', font=FONT_ENTRY, width=15)
        
        # Available seasons for copying (including None option)
        copy_options = ["None"] + self.seasons
        copy_combo['values'] = copy_options
        copy_combo.set("None")  # Default to no copying
        copy_combo.grid(row=1, column=1, padx=5, pady=10, sticky='w')
        
        # Button frame
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        def on_create():
            selected_season = season_var.get().strip()
            copy_from_season = copy_var.get().strip()
            
            if not selected_season:
                messagebox.showerror("Invalid Season", "Please select a season.")
                return
            
            # Double-check that season doesn't already exist (should be prevented by dropdown filtering)
            if selected_season in self.seasons:
                messagebox.showerror("Season Exists", f"Season '{selected_season}' already exists.")
                return
            
            dialog.destroy()
            
            # Create the new season
            if copy_from_season == "None":
                self._create_new_season(selected_season, copy_from=None)
            else:
                self._create_new_season(selected_season, copy_from=copy_from_season)
        
        def on_cancel():
            dialog.destroy()
        
        tk.Button(button_frame, text="Create Season", font=FONT_BUTTON, 
                 command=on_create, default='active').pack(side='left', padx=5)
        tk.Button(button_frame, text="Cancel", font=FONT_BUTTON, 
                 command=on_cancel).pack(side='left', padx=5)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        
        # Bind Enter key to create
        dialog.bind('<Return>', lambda e: on_create())
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        # Focus on season combo
        season_combo.focus_set()
    
    def _create_new_season(self, new_season: str, copy_from: str = None):
        """Create a new season, optionally copying conference data from an existing season."""
        print(f"Creating new season: {new_season}")
        if copy_from:
            print(f"Copying data from: {copy_from}")
        
        # Add to seasons list
        self.seasons.append(new_season)
        self.seasons.sort(reverse=True)
        
        # If copying from another season, copy the conference affiliations
        if copy_from and self.selected_team_category:
            self._copy_season_data(copy_from, new_season)
        
        # Recreate the season interface to include the new tab
        self._create_season_interface()
        
        # Select the new season tab
        try:
            new_season_index = self.seasons.index(new_season)
            self.season_notebook.select(new_season_index)
            self.current_season = new_season
            self._load_season_data()
        except (ValueError, AttributeError):
            pass  # If selection fails, just continue
        
        if copy_from:
            messagebox.showinfo("Season Created", 
                               f"Season '{new_season}' created successfully with data copied from '{copy_from}'.")
        else:
            messagebox.showinfo("Season Created", 
                               f"Season '{new_season}' created successfully as an empty season.")
    
    def _copy_season_data(self, source_season: str, target_season: str):
        """Copy conference affiliation data from one season to another."""
        if not self.selected_team_category:
            return
        
        gender, weight = self.selected_team_category
        source_year = source_season.split('-')[0]
        target_year = target_season.split('-')[0]
        
        # Create new start and end dates for the target season
        target_start_date = f"{target_year}-09-01"
        target_end_date = f"{int(target_year) + 1}-08-31"
        
        cursor = self.db.conn.cursor()
        
        try:
            # Get all conference affiliations from the source season
            cursor.execute("""
                SELECT t.team_id, ca.conference
                FROM conference_affiliations ca
                JOIN teams t ON ca.team_id = t.team_id
                WHERE t.gender = ? AND t.weight = ?
                AND SUBSTR(ca.start_date, 1, 4) = ?
                AND (ca.end_date IS NULL OR SUBSTR(ca.end_date, 1, 4) > ?)
            """, (gender, weight, source_year, source_year))
            
            source_affiliations = cursor.fetchall()
            
            copied_count = 0
            for team_id, conference in source_affiliations:
                # Check if affiliation already exists for target season
                cursor.execute("""
                    SELECT COUNT(*) FROM conference_affiliations
                    WHERE team_id = ? AND SUBSTR(start_date, 1, 4) = ?
                """, (team_id, target_year))
                
                if cursor.fetchone()[0] == 0:  # No existing affiliation
                    # Create new affiliation for target season
                    cursor.execute("""
                        INSERT INTO conference_affiliations (team_id, conference, start_date, end_date)
                        VALUES (?, ?, ?, ?)
                    """, (team_id, conference, target_start_date, target_end_date))
                    copied_count += 1
            
            self.db.conn.commit()
            print(f"✓ Copied {copied_count} conference affiliations from {source_season} to {target_season}")
            
        except Exception as e:
            self.db.conn.rollback()
            print(f"❌ Error copying season data: {str(e)}")
            messagebox.showerror("Copy Error", f"Failed to copy season data: {str(e)}")
    
    def refresh(self):
        """Refresh this tab's data with enhanced temporal awareness."""
        if self.selected_team_category:
            # Refresh available schools for current season
            self._load_available_schools()
            
            # Update any existing autocomplete widgets
            self._update_existing_autocomplete_widgets()
            
            # Reload season data if we have a current season
            if self.current_season:
                self._load_season_data()
                
            print(f"🔄 Conference tab refreshed for {self.selected_team_category} in season {self.current_season}")