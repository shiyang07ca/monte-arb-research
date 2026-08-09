import unittest
from datetime import date, time, timezone

from lab.day5_roll_session import ET, et_to_utc, is_in_window, roll_stage


class Day5RollSessionTests(unittest.TestCase):
    def test_august_2026_daylight_saving_conversion(self):
        wti = et_to_utc(date(2026, 8, 7), 17, 30)
        brent = et_to_utc(date(2026, 8, 7), 19, 0)
        self.assertEqual(wti.hour, 21)
        self.assertEqual(wti.minute, 30)
        self.assertEqual(brent.hour, 23)
        self.assertEqual(brent.minute, 0)
        self.assertEqual(wti.tzinfo, timezone.utc)

    def test_roll_stages(self):
        self.assertEqual(roll_stage(80), "day_1")
        self.assertEqual(roll_stage(0), "post_roll")
        with self.assertRaises(ValueError):
            roll_stage(50)

    def test_underlying_close_windows_are_half_open(self):
        self.assertTrue(is_in_window(time(17, 30), time(17), time(18)))
        self.assertFalse(is_in_window(time(18), time(17), time(18)))
        self.assertTrue(is_in_window(time(19), time(18), time(20)))
        self.assertFalse(is_in_window(time(20), time(18), time(20)))


if __name__ == "__main__":
    unittest.main()
