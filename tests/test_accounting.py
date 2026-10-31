"""Authored measurement/identity/calendar boundaries; not empirical performance tests."""

from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import sys, unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from accounting import account, rank_queues, calendar
from project_source import money
from exercise import interpret


class AccountingBoundaries(unittest.TestCase):
    def case(self, **changes):
        return dict(case="C01", base_date="2024-01-01", **changes)

    def row(self, key="T1", day="2024-01-01", value="100", **changes):
        result = dict(
            source_row="1",
            transaction_id=key,
            action_date=day,
            money_token=value,
            money_state="FINITE",
            modification_token="0000",
        )
        result.update(changes)
        return result

    def result(self, rows, horizon=365):
        return account(self.case(), rows, horizon)[0]

    def test_signed_obligations_and_zero_actions(self):
        r = self.result(
            [
                self.row("A", value="100"),
                self.row("B", value="-40"),
                self.row("C", value="0"),
            ]
        )
        self.assertEqual(
            (
                r["window_actions"],
                r["positive_actions"],
                r["negative_actions"],
                r["zero_actions"],
            ),
            (3, 1, 1, 1),
        )
        self.assertEqual(
            (
                Fraction(r["net_usd"]),
                Fraction(r["gross_absolute_usd"]),
                r["net_offset_fraction"],
            ),
            (60, 140, "4/7"),
        )

    def test_whole_duplicate_identity_group_quarantined(self):
        r = self.result(
            [
                self.row("A", value="100"),
                self.row("A", value="200"),
                self.row("B", value="-3"),
            ]
        )
        self.assertEqual(
            (r["duplicate_key_records"], r["window_actions"], r["money_complete"]),
            (2, 1, False),
        )
        self.assertEqual(r["net_usd"], "")

    def test_missing_key_retained_but_not_counted_as_action(self):
        r = self.result([self.row(""), self.row("A")])
        self.assertEqual(
            (r["all_source_records"], r["missing_key_records"], r["window_actions"]),
            (2, 1, 1),
        )
        self.assertFalse(r["money_complete"])

    def test_day_364_included_and_day_365_excluded_in_leap_year(self):
        r = self.result([self.row("A", "2024-12-30"), self.row("B", "2024-12-31")])
        self.assertEqual(
            (r["window_actions"], r["at_or_after_horizon_records"]), (1, 1)
        )

    def test_origin_day_included(self):
        self.assertEqual(self.result([self.row()])["origin_day_actions"], 1)

    def test_before_origin_retained(self):
        r = self.result([self.row(day="2023-12-31")])
        self.assertEqual((r["before_origin_records"], r["window_actions"]), (1, 0))
        self.assertEqual(r["net_usd"], "")

    def test_invalid_calendar_date_not_a_future_record(self):
        r = self.result([self.row(day="2024-02-30")])
        self.assertEqual(
            (r["unknown_date_records"], r["at_or_after_horizon_records"]), (1, 0)
        )

    def test_missing_date_makes_window_incomplete(self):
        r = self.result([self.row("A", day=""), self.row("B")])
        self.assertEqual(r["window_actions"], 1)
        self.assertFalse(r["money_complete"])

    def test_compact_and_timestamp_tokens_rejected_as_calendar_dates(self):
        self.assertIsNone(calendar("20240101"))
        self.assertIsNone(calendar("2024-01-01T00:00:00Z"))

    def test_unknown_money_not_zero(self):
        r = self.result([self.row(value="", money_state="MISSING")])
        self.assertEqual(
            (r["window_actions"], r["unknown_money_actions"], r["zero_actions"]),
            (1, 1, 0),
        )
        self.assertEqual(r["net_usd"], "")

    def test_all_zero_money_has_unavailable_offset_ratio(self):
        r = self.result([self.row(value="0")])
        self.assertTrue(r["money_complete"])
        self.assertEqual(r["net_usd"], "0")
        self.assertEqual(r["net_offset_fraction"], "")

    def test_empty_window_not_zero_money(self):
        r = self.result([])
        self.assertEqual(r["window_actions"], 0)
        self.assertFalse(r["money_complete"])
        self.assertEqual(r["net_usd"], "")

    def test_full_positive_negative_offset(self):
        r = self.result([self.row("A", value="7.25"), self.row("B", value="-7.25")])
        self.assertEqual(Fraction(r["net_usd"]), 0)
        self.assertEqual(r["net_offset_fraction"], "1")

    def test_all_negative_values_preserve_sign(self):
        r = self.result([self.row(value="-19.123")])
        self.assertEqual(Fraction(r["net_usd"]), Fraction("-19.123"))
        self.assertEqual(r["net_offset_fraction"], "0")

    def test_large_decimal_exponent_span_not_rounded(self):
        r = self.result(
            [
                self.row("A", value="1E+100"),
                self.row("B", value="-1E+100"),
                self.row("C", value="0.000000000000000000000000000000000000000001"),
            ]
        )
        self.assertEqual(Fraction(r["net_usd"]), Fraction(1, 10**42))
        self.assertEqual(
            Fraction(r["gross_absolute_usd"]), 2 * 10**100 + Fraction(1, 10**42)
        )

    def test_shared_day_count_retains_unorderable_actions(self):
        r = self.result([self.row("A"), self.row("B"), self.row("C", day="2024-01-02")])
        self.assertEqual(
            (r["origin_day_actions"], r["shared_calendar_day_actions"]), (2, 2)
        )

    def test_modification_tokens_are_opaque_not_sequence_numbers(self):
        r = self.result(
            [
                self.row("A", modification_token="P0002"),
                self.row("B", modification_token="A1"),
                self.row("C", modification_token=""),
            ]
        )
        self.assertEqual(
            (r["distinct_modification_tokens"], r["missing_modification_tokens"]),
            (2, 1),
        )

    def test_fixed_cumulative_boundary(self):
        rows = [self.row("A", "2024-01-30"), self.row("B", "2024-01-31")]
        self.assertEqual(self.result(rows, 30)["window_actions"], 1)
        self.assertEqual(self.result(rows, 90)["window_actions"], 2)

    def test_invalid_horizon_rejected(self):
        with self.assertRaises(AssertionError):
            self.result([], 0)
        with self.assertRaises(AssertionError):
            self.result([], True)

    def test_boolean_not_source_money(self):
        self.assertEqual(money(True), ("", "NONNUMERIC"))

    def test_numeric_string_not_source_numeric_token(self):
        self.assertEqual(money("1.2"), ("", "NONNUMERIC"))

    def test_nonfinite_money_unavailable(self):
        self.assertEqual(money(Decimal("NaN")), ("", "NONFINITE"))


class QueueAndInterfaceBoundaries(unittest.TestCase):
    def row(self, key, actions, net, complete=True):
        return dict(
            case=key, window_actions=actions, net_usd=net, money_complete=complete
        )

    def test_count_and_dollar_ranks_can_disagree(self):
        q, r = rank_queues([self.row("A", 10, "1"), self.row("B", 1, "100")], 1)
        self.assertEqual(
            (q["action_count_queue"], q["net_obligation_queue"], q["jaccard_fraction"]),
            (["A"], ["B"], "0"),
        )

    def test_ties_use_fixed_case_id(self):
        q, r = rank_queues([self.row("B", 2, "1"), self.row("A", 2, "1")], 1)
        self.assertEqual(q["action_count_queue"], ["A"])
        self.assertEqual(q["net_obligation_queue"], ["A"])

    def test_incomplete_money_excluded_from_both_comparison_queues(self):
        q, r = rank_queues([self.row("A", 99, "", False), self.row("B", 1, "-5")], 5)
        self.assertEqual(q["joint_eligible_cases"], 1)
        self.assertEqual(q["action_count_queue"], ["B"])

    def test_empty_joint_cohort_has_unavailable_overlap_ratio(self):
        q, r = rank_queues([self.row("A", 0, "", False)])
        self.assertEqual(q["selected_per_queue"], 0)
        self.assertEqual(q["jaccard_fraction"], "")

    def test_exact_money_rank_beyond_default_decimal_precision(self):
        q, _ = rank_queues(
            [
                self.row("A", 1, "1.00000000000000000000000000001"),
                self.row("B", 1, "1.00000000000000000000000000002"),
            ],
            1,
        )
        self.assertEqual(q["net_obligation_queue"], ["B"])

    def test_invalid_capacity_rejected(self):
        with self.assertRaises(AssertionError):
            rank_queues([], 0)

    def test_qualified_current_action_account(self):
        answer = interpret(
            dict(case="C01", measure="CURRENT_ACTION_ACCOUNT"),
            [dict(case="C01", window_actions="3", money_complete="True", net_usd="10")],
        )
        self.assertTrue(answer["accepted"])
        self.assertEqual(answer["value"], "3")
        self.assertFalse(answer["historical_publication_known"])

    def test_incomplete_obligation_account_rejected(self):
        answer = interpret(
            dict(case="C01", measure="CURRENT_OBLIGATION_ACCOUNT"),
            [dict(case="C01", window_actions="3", money_complete="False", net_usd="")],
        )
        self.assertFalse(answer["accepted"])
        self.assertEqual(answer["reason"], "INCOMPLETE_MONEY_OR_WINDOW")

    def test_unsupported_measurement_conversions_rejected(self):
        accounts = [
            dict(case="C01", window_actions="3", money_complete="True", net_usd="10")
        ]
        for measure in [
            "PREAWARD_FEATURES",
            "ESTIMATE_STAFF_HOURS",
            "RANK_VENDOR_RISK",
            "DOLLARS_AS_ACTION_COUNT",
            "PREDICT_FUTURE_MODIFICATIONS",
        ]:
            self.assertFalse(
                interpret(dict(case="C01", measure=measure), accounts)["accepted"]
            )

    def test_duplicate_or_unknown_case_rejected(self):
        request = dict(case="C01", measure="CURRENT_ACTION_ACCOUNT")
        self.assertEqual(interpret(request, [])["reason"], "CASE_NOT_ESTABLISHED")
        self.assertEqual(
            interpret(request, [dict(case="C01"), dict(case="C01")])["reason"],
            "CASE_NOT_ESTABLISHED",
        )

    def test_invalid_request_rejected(self):
        self.assertEqual(interpret(None, [])["reason"], "INVALID_REQUEST")


if __name__ == "__main__":
    unittest.main()
