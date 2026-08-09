import unittest

from lab.day4_price_semantics import (
    executable_close_pnl,
    ema_step,
    load_snapshot,
    unrealized_pnl,
)


class Day4PriceSemanticsTests(unittest.TestCase):
    def test_snapshot_preserves_unknown_fields(self):
        data = load_snapshot()
        self.assertIn("oracle_price", data["unknown_in_current_snapshot"])
        self.assertIn("mid_price", data["unknown_in_current_snapshot"])
        self.assertEqual(data["markets"]["WTI"]["mark_minus_index"], "0.022")

    def test_ema_tau_controls_reaction_speed(self):
        slow = ema_step(75.0, 76.0, 1.0, 30.0)
        fast = ema_step(75.0, 76.0, 1.0, 2.0)
        self.assertAlmostEqual(slow, 75.0327838995, places=10)
        self.assertAlmostEqual(fast, 75.3934693403, places=10)
        self.assertGreater(fast, slow)

    def test_mark_valuation_differs_from_long_bid_exit(self):
        self.assertAlmostEqual(unrealized_pnl(75.0, 75.03, 1.0), 0.03)
        self.assertAlmostEqual(executable_close_pnl(75.0, 74.90, 75.10, 1.0, "long"), -0.10)

    def test_short_close_uses_ask(self):
        self.assertAlmostEqual(executable_close_pnl(75.0, 74.90, 75.10, 1.0, "short"), -0.10)


if __name__ == "__main__":
    unittest.main()
