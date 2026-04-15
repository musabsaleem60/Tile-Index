
import tkinter as tk
from tkinter import ttk

class SearchableCombobox(ttk.Combobox):
    """
    A professional-grade searchable Combobox that filters values as you type.
    """
    def __init__(self, master, **kwargs):
        # Ensure state is 'normal' so user can type
        kwargs['state'] = 'normal'
        super().__init__(master, **kwargs)
        self._all_values = []
        
        # Bind events
        self.bind('<KeyRelease>', self._on_keyrelease)
        self.bind('<FocusOut>', self._on_focus_out)
        self.bind('<<ComboboxSelected>>', self._on_select)

    def set_completion_list(self, completion_list):
        """Set the source list for search."""
        self._all_values = sorted([str(i) for i in completion_list])
        self['values'] = self._all_values

    def _on_keyrelease(self, event):
        """Filter list and perform autocomplete without stealing focus."""
        # Handle navigation and special keys
        if event.keysym in ('Up', 'Down', 'Return', 'Escape', 'Tab', 'BackSpace', 'Delete', 'Control_L', 'Control_R', 'Shift_L', 'Shift_R'):
            return

        pos = self.index(tk.INSERT)
        query = self.get().lower()
        
        if not query:
            self['values'] = self._all_values
            return

        # Find matches
        matches = [v for v in self._all_values if query in v.lower()]
        self['values'] = matches
        
        # Professional Autocomplete: 
        # Find the first match that STARTS with the query for auto-completion
        start_matches = [v for v in matches if v.lower().startswith(query)]
        
        if start_matches:
            full_match = start_matches[0]
            # Set the text to the full match
            self.set(full_match)
            # Select the auto-completed part so next key overwrites it
            self.selection_range(pos, tk.END)
            # Keep cursor at original typing position
            self.icursor(pos)
            
    def _on_select(self, event):
        """Reset values to full list after a selection is made."""
        self.after(100, lambda: self.configure(values=self._all_values))

    def _on_focus_out(self, event):
        """Validate input when focus is lost."""
        val = self.get()
        # Optional: if you want to force selection from list:
        # if val and val not in self._all_values:
        #    self.set('')
