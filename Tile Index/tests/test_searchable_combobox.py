import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from utils.searchable_combobox import SearchableCombobox


class SearchableComboboxTests(unittest.TestCase):
    def test_typed_autocomplete_commits_selection_without_focus_workaround(self):
        class FakeCombo:
            _all_values = ["DHA", "Tile Cera - Korangi", "Tile Index - Korangi"]
            _last_committed_value = ""
            _typed_commit_job = None
            value = "Tile C"
            cursor = 6
            selected_events = 0

            def index(self, _position): return self.cursor
            def get(self): return self.value
            def __setitem__(self, _key, _value): pass
            def set(self, value): self.value = value
            def selection_range(self, *_args): pass
            def icursor(self, position): self.cursor = position
            def after_cancel(self, _job): pass
            def after(self, _delay, callback): callback(); return "job"
            def _commit_typed_value(self):
                return SearchableCombobox._commit_typed_value(self)
            def event_generate(self, event):
                if event == "<<ComboboxSelected>>": self.selected_events += 1

        combo = FakeCombo()
        SearchableCombobox._on_keyrelease(combo, SimpleNamespace(keysym="c"))
        self.assertEqual(combo.value, "Tile Cera - Korangi")
        self.assertEqual(combo.selected_events, 1)

    def test_replacing_completion_list_cancels_old_typed_commit(self):
        class FakeCombo:
            _typed_commit_job = "old-job"
            _last_committed_value = "Old Product"
            cancelled = []
            values = None

            def after_cancel(self, job): self.cancelled.append(job)
            def __setitem__(self, key, value): self.values = value

        combo = FakeCombo()
        SearchableCombobox.set_completion_list(combo, ["Sanitary B", "Sanitary A"])
        self.assertEqual(combo.cancelled, ["old-job"])
        self.assertIsNone(combo._typed_commit_job)
        self.assertEqual(combo._last_committed_value, "")
        self.assertEqual(combo.values, ["Sanitary A", "Sanitary B"])


if __name__ == "__main__":
    unittest.main()
