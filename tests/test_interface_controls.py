import unittest
from pathlib import Path


class InterfaceControlsTests(unittest.TestCase):
    def test_sidebar_toggle_and_calendar_controls_exist(self):
        template = Path(__file__).parents[1].joinpath('templates/index.html').read_text()
        self.assertIn('id=\"sidebar-toggle\"', template)
        self.assertIn('id=\"start-date\"', template)
        self.assertIn('id=\"end-date\"', template)
        self.assertIn('sidebar-collapsed', template)
        self.assertIn("startDate + 'T00:00:00'", template)
        self.assertIn("endDate + 'T23:59:59'", template)


if __name__ == '__main__':
    unittest.main()
