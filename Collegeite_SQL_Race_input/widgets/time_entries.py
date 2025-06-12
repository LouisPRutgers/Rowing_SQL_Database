"""
Custom input widgets with smart parsing for rowing race times and autocomplete functionality.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Tuple, Optional, List
from Collegeite_SQL_Race_input.config.constants import FONT_ENTRY
from Collegeite_SQL_Race_input.utils.helpers import parse_time_input, format_time_seconds


class AutoCompleteEntry(tk.Entry):
    """Entry with autosuggest listbox that supports team-specific school lists."""

    def __init__(self, master: tk.Widget, choices: List[str], **kw):
        super().__init__(master, font=FONT_ENTRY, **kw)
        self.choices = sorted(choices, key=str.lower)
        self.var = tk.StringVar()
        self.config(textvariable=self.var)
        self.lb: Optional[tk.Listbox] = None
        self._updating = False  # Prevent autocomplete during programmatic updates
        
        # Bind trace AFTER setup to avoid triggering during initialization
        self.var.trace_add("write", self._on_text_change)

        self.bind("<KeyPress-Tab>", self._on_tab)
        self.bind("<Return>", self._on_enter)
        self.bind("<Right>", self._complete)
        self.bind("<Down>", self._lb_down)
        self.bind("<Up>", self._lb_up)
        self.bind("<Escape>", self._destroy)
        self.bind("<FocusOut>", self._on_focus_out)

    def insert(self, index, string):
        """Override insert to prevent autocomplete during programmatic insertion."""
        self._updating = True
        super().insert(index, string)
        self._updating = False

    def delete(self, first, last=None):
        """Override delete to prevent autocomplete during programmatic deletion."""
        self._updating = True
        super().delete(first, last)
        self._updating = False

    def set_text(self, text):
        """Safely set text without triggering autocomplete."""
        self._updating = True
        self.delete(0, tk.END)
        if text:
            super().insert(0, text)
        self._updating = False

    def update_choices(self, new_choices: List[str]):
        """Update the choices list for autocomplete."""
        self.choices = sorted(new_choices, key=str.lower)
        self._destroy()

    def _on_text_change(self, *_):
        """Handle text changes - only show autocomplete for user typing."""
        if self._updating:
            return
        self.after_idle(self._update)

    def _update(self, *_):
        """Show autocomplete dropdown for user input."""
        if self._updating:
            return
            
        txt = self.var.get()
        self._destroy()
        
        if not txt or not self.focus_get() == self or txt in self.choices:
            return
            
        matches = [s for s in self.choices if txt.lower() in s.lower()]
        if not matches:
            return

        try:
            top = self.winfo_toplevel()
            self.lb = tk.Listbox(top, height=min(len(matches), 6), font=FONT_ENTRY)
            
            self.lb.bind("<<ListboxSelect>>", self._select)
            self.lb.bind("<Button-1>", self._on_click)
            self.lb.bind("<Double-Button-1>", self._on_double_click)
            self.lb.bind("<Return>", self._lb_enter)
            self.lb.bind("<Tab>", self._lb_tab)
            self.lb.bind("<Escape>", self._lb_escape)

            x = self.winfo_rootx() - top.winfo_rootx()
            y = self.winfo_rooty() - top.winfo_rooty() + self.winfo_height()
            self.lb.place(x=x, y=y, width=self.winfo_width())
            
            for w in matches:
                self.lb.insert(tk.END, w)
            
            if matches:
                self.lb.selection_set(0)
                self.lb.activate(0)
                
        except tk.TclError:
            self._destroy()

    def _destroy(self, *_):
        if self.lb:
            try:
                self.lb.destroy()
            except tk.TclError:
                pass
            self.lb = None

    def _complete(self, *_):
        if not self.lb or not self.lb.size():
            return "break"
            
        try:
            selection = self.lb.curselection()
            if selection:
                selected_text = self.lb.get(selection[0])
            else:
                selected_text = self.lb.get(tk.ACTIVE)
            
            self._updating = True
            self.var.set(selected_text)
            self.icursor(tk.END)
            self._updating = False
            
            self._destroy()
            
            try:
                self.tk_focusNext().focus_set()
            except (tk.TclError, AttributeError):
                pass
                
        except tk.TclError:
            self._destroy()
        return "break"

    def _on_tab(self, e):
        if self.lb:
            self._complete()
            return "break"
        return None

    def _lb_down(self, e):
        if not self.lb:
            return "break"
        try:
            self.lb.focus_set()
            current = self.lb.curselection()
            next_index = min(current[0] + 1, self.lb.size() - 1) if current else 0
            self.lb.selection_clear(0, tk.END)
            self.lb.selection_set(next_index)
            self.lb.activate(next_index)
            self.lb.see(next_index)
        except tk.TclError:
            self._destroy()
        return "break"

    def _lb_up(self, e):
        if not self.lb:
            return "break"
        try:
            self.lb.focus_set()
            current = self.lb.curselection()
            prev_index = max(current[0] - 1, 0) if current else self.lb.size() - 1
            self.lb.selection_clear(0, tk.END)
            self.lb.selection_set(prev_index)
            self.lb.activate(prev_index)
            self.lb.see(prev_index)
        except tk.TclError:
            self._destroy()
        return "break"

    def _on_enter(self, e):
        if self.lb:
            self._complete()
            return "break"
        return None

    def _on_click(self, e):
        if self.lb:
            self.lb.after_idle(self._complete)

    def _on_double_click(self, e):
        if self.lb:
            self._complete()

    def _select(self, *_):
        pass

    def _lb_enter(self, e):
        if self.lb:
            self._complete()
            return "break"

    def _lb_tab(self, e):
        if self.lb:
            self._complete()
            return "break"

    def _lb_escape(self, e):
        if self.lb:
            self._destroy()
            self.focus_set()
            return "break"

    def _on_focus_out(self, e):
        if self.lb:
            self.after(100, self._check_focus)

    def _check_focus(self):
        if self.lb:
            try:
                focused = self.focus_get()
                if focused != self.lb:
                    self._destroy()
            except tk.TclError:
                self._destroy()

class ScheduleTimeEntry(tk.Entry):
    """Entry widget for schedule time input with smart parsing."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, font=FONT_ENTRY, **kwargs)
        self.bind("<FocusOut>", self._normalize)
        self.bind("<Return>", self._normalize)
        
        # Add placeholder text
        self._add_placeholder()
    
    def _add_placeholder(self):
        """Add placeholder text to guide user input."""
        self.insert(0, "e.g. 9:30, 1400")
        self.config(fg='gray')
        self.bind('<FocusIn>', self._clear_placeholder)
    
    def _clear_placeholder(self, event):
        """Clear placeholder text when user starts typing."""
        if self.get() == "e.g. 9:30, 1400":
            self.delete(0, tk.END)
            self.config(fg='black')
        self.unbind('<FocusIn>')
    
    def _normalize(self, *_):
        """Normalize time input to HH:MM format."""
        text = self.get().strip()
        
        # Handle empty or placeholder text
        if not text or text == "e.g. 9:30, 1400":
            return  # Leave empty - this means optional
        
        try:
            normalized = self._parse_schedule_time(text)
            self.delete(0, tk.END)
            self.insert(0, normalized)
            self.config(fg='black')
        except ValueError as e:
            messagebox.showerror("Invalid Time", str(e))
            self.focus_set()
    
    @staticmethod
    def _parse_schedule_time(text: str) -> str:
        """Parse various time formats and return HH:MM format."""
        text = text.strip().upper()
        
        # Handle common formats
        if not text:
            return ""
        
        # Handle AM/PM format
        am_pm = None
        if text.endswith('AM') or text.endswith('PM'):
            am_pm = text[-2:]
            text = text[:-2].strip()
        
        # Handle colon format (e.g., "9:30", "14:00")
        if ':' in text:
            try:
                parts = text.split(':')
                hours = int(parts[0])
                minutes = int(parts[1]) if len(parts) > 1 else 0
                
                # Handle AM/PM
                if am_pm:
                    if am_pm == 'PM' and hours != 12:
                        hours += 12
                    elif am_pm == 'AM' and hours == 12:
                        hours = 0
                
                if hours > 23 or minutes > 59:
                    raise ValueError("Hours must be 0-23, minutes 0-59")
                
                return f"{hours:02d}:{minutes:02d}"
            except (ValueError, IndexError):
                raise ValueError("Invalid time format. Use HH:MM or H:MM")
        
        # Handle 24-hour format without colon (e.g., "1430", "900")
        if text.isdigit():
            if len(text) <= 2:
                # Just hours (e.g., "9" -> "09:00")
                hours = int(text)
                minutes = 0
            elif len(text) == 3:
                # HMM format (e.g., "930" -> "09:30")
                hours = int(text[0])
                minutes = int(text[1:3])
            elif len(text) == 4:
                # HHMM format (e.g., "1430" -> "14:30")
                hours = int(text[0:2])
                minutes = int(text[2:4])
            else:
                raise ValueError("Invalid time format")
            
            # Handle AM/PM for digit-only input
            if am_pm:
                if am_pm == 'PM' and hours != 12:
                    hours += 12
                elif am_pm == 'AM' and hours == 12:
                    hours = 0
            
            if hours > 23 or minutes > 59:
                raise ValueError("Hours must be 0-23, minutes 0-59")
            
            return f"{hours:02d}:{minutes:02d}"
        
        # Handle text formats
        text_lower = text.lower()
        if 'noon' in text_lower or text_lower == '12pm':
            return "12:00"
        elif 'midnight' in text_lower or text_lower == '12am':
            return "00:00"
        
        raise ValueError("Invalid time format. Examples: 9:30, 1430, 9:30AM, noon")
    
    def get_time_or_none(self) -> Optional[str]:
        """Get the time in HH:MM format, or None if empty/placeholder."""
        text = self.get().strip()
        if not text or text == "e.g. 9:30, 1400":
            return None
        return text


# Add this debugging version to your TimeEntry widget temporarily

# Add this debugging version to your TimeEntry widget temporarily

class TimeEntry(tk.Entry):
    """Entry widget for race time input with smart digit parsing from Race Ranker."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, font=FONT_ENTRY, **kwargs)
        self.bind("<FocusOut>", self._normalize)
        self.bind("<Return>", self._normalize)
        self.bind("<KeyRelease>", self._on_key_release)  # Additional debug
    
    def _on_key_release(self, event):
        """Debug: Track key releases."""
        print(f"Key released in TimeEntry: '{event.keysym}' - Current text: '{self.get()}'")
        # Auto-normalize on certain keys for testing
        if event.keysym in ['Tab', 'Return']:
            self._normalize()
    
    def _normalize(self, *_):
        """Normalize time input to mm:ss.fff format using smart parsing."""
        text = self.get().strip()
        print(f"_normalize called with: '{text}'")  # Debug print
        
        if not text:
            return
        
        try:
            minutes, seconds, milliseconds = parse_time_input(text)
            normalized = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
            print(f"Parsed '{text}' -> {minutes}m {seconds}s {milliseconds}ms -> '{normalized}'")  # Debug print
            
            self.delete(0, tk.END)
            self.insert(0, normalized)
            print(f"Field updated to: '{self.get()}'")  # Debug print
            
        except Exception as e:
            print(f"Error in _normalize: {e}")  # Debug print
            messagebox.showerror(
                "Invalid Time", 
                f"Enter time as digits (e.g., 704 for 7:04.000) or mm:ss.fff format\nError: {e}"
            )
            self.after(10, self.focus_set)
    
    def get_seconds(self) -> float:
        """Get the time as total seconds."""
        text = self.get().strip()
        if not text:
            return 0.0
        try:
            from Collegeite_SQL_Race_input.utils.helpers import parse_time_input
            minutes, seconds, milliseconds = parse_time_input(text)
            return minutes * 60 + seconds + milliseconds / 1000.0
        except ValueError:
            return 0.0