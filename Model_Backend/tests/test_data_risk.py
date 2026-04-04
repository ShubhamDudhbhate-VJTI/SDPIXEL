"""Tests for utils/data_risk.py"""

import pytest
from utils.data_risk import (
    IMPORTER_RISK,
    compute_country_risk,
    compute_data_risk,
    compute_hs_risk,
    compute_value_anomaly,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_item(name="Widget", quantity=1, category="electronics", hs_code="8471"):
    return {"name": name, "quantity": quantity, "category": category, "hs_code": hs_code}


# ---------------------------------------------------------------------------
# compute_value_anomaly
# ---------------------------------------------------------------------------

class TestComputeValueAnomaly:
    def test_none_declared_value_returns_zero(self):
        items = [make_item(quantity=1, category="electronics")]
        assert compute_value_anomaly(items, None) == 0.0

    def test_empty_items_returns_zero(self):
        assert compute_value_anomaly([], 1000.0) == 0.0

    def test_declared_within_range_returns_zero(self):
        # electronics: (50, 2500), 1 unit declared at $500 → in range
        items = [make_item(quantity=1, category="electronics")]
        assert compute_value_anomaly(items, 500.0) == 0.0

    def test_declared_below_min_returns_positive(self):
        # electronics: (50, 2500), 1 unit declared at $10 → under min
        items = [make_item(quantity=1, category="electronics")]
        result = compute_value_anomaly(items, 10.0)
        expected = (50.0 - 10.0) / 50.0  # 0.8
        assert result == pytest.approx(expected)

    def test_declared_above_max_returns_positive(self):
        # electronics: (50, 2500), 1 unit declared at $3000 → over max
        items = [make_item(quantity=1, category="electronics")]
        result = compute_value_anomaly(items, 3000.0)
        expected = (3000.0 - 2500.0) / 2500.0  # 0.2
        assert result == pytest.approx(expected)

    def test_multiple_items_summed(self):
        # 2 electronics (50–2500 each) + 1 clothing (5–300)
        # total_min = 2*50 + 5 = 105, total_max = 2*2500 + 300 = 5300
        items = [
            make_item(quantity=2, category="electronics"),
            make_item(quantity=1, category="clothing"),
        ]
        # Declared exactly at min → anomaly = 0
        assert compute_value_anomaly(items, 105.0) == 0.0

    def test_unknown_category_uses_other(self):
        items = [{"name": "Gizmo", "quantity": 1, "category": "unknown_xyz", "hs_code": None}]
        # Should not raise, should use "other" fallback
        result = compute_value_anomaly(items, 500.0)
        assert 0.0 <= result <= 1.0

    def test_result_clamped_to_one(self):
        # Declare $1 for 10 laptops (min = 3000 each = 30000 total)
        items = [make_item(quantity=10, category="laptops", hs_code="8471")]
        result = compute_value_anomaly(items, 1.0)
        assert result <= 1.0

    def test_quantity_defaults_to_one_if_missing(self):
        item = {"name": "Widget", "category": "electronics", "hs_code": "8471"}
        # Missing quantity — should default to 1, not raise
        result = compute_value_anomaly([item], 500.0)
        assert 0.0 <= result <= 1.0


# ---------------------------------------------------------------------------
# compute_hs_risk
# ---------------------------------------------------------------------------

class TestComputeHsRisk:
    def test_empty_items_returns_zero(self):
        assert compute_hs_risk([]) == 0.0

    def test_no_hs_code_returns_neutral(self):
        items = [{"name": "Item", "quantity": 1, "category": "electronics", "hs_code": None}]
        assert compute_hs_risk(items) == pytest.approx(0.4)

    def test_valid_hs_code_no_mismatch(self):
        # electronics category + HS 8471 (prefix "84") → no penalty
        items = [make_item(category="electronics", hs_code="8471")]
        result = compute_hs_risk(items)
        from utils.risk_tables import HS_RISK_TABLE
        expected = HS_RISK_TABLE["84"]  # 0.45
        assert result == pytest.approx(expected)

    def test_mismatch_adds_penalty(self):
        # clothing category + HS 8471 (electronics chapter) → +0.2 penalty
        items = [make_item(category="clothing", hs_code="8471")]
        result = compute_hs_risk(items)
        from utils.risk_tables import HS_RISK_TABLE
        base = HS_RISK_TABLE["84"]
        expected = min(base + 0.2, 1.0)
        assert result == pytest.approx(expected)

    def test_weapons_hs_code_is_high_risk(self):
        items = [make_item(category="weapons", hs_code="9302")]
        result = compute_hs_risk(items)
        assert result >= 0.8

    def test_hs_code_with_dots_normalised(self):
        # "84.71" should normalise to prefix "84"
        items = [make_item(category="electronics", hs_code="84.71")]
        from utils.risk_tables import HS_RISK_TABLE
        expected = HS_RISK_TABLE["84"]
        assert compute_hs_risk(items) == pytest.approx(expected)

    def test_hs_code_with_spaces_normalised(self):
        items = [make_item(category="electronics", hs_code=" 8471 ")]
        from utils.risk_tables import HS_RISK_TABLE
        expected = HS_RISK_TABLE["84"]
        assert compute_hs_risk(items) == pytest.approx(expected)

    def test_average_across_multiple_items(self):
        items = [
            make_item(category="electronics", hs_code="8471"),   # no mismatch
            make_item(category="weapons",     hs_code="9302"),   # no mismatch, high risk
        ]
        from utils.risk_tables import HS_RISK_TABLE
        expected = (HS_RISK_TABLE["84"] + HS_RISK_TABLE["93"]) / 2
        assert compute_hs_risk(items) == pytest.approx(expected)

    def test_result_clamped_to_one(self):
        # Force mismatch on already-high chapter
        items = [make_item(category="clothing", hs_code="9302")]
        result = compute_hs_risk(items)
        assert result <= 1.0

    def test_other_category_no_mismatch_penalty(self):
        # "other" category has empty valid set → no mismatch penalty ever
        items = [make_item(category="other", hs_code="9302")]
        from utils.risk_tables import HS_RISK_TABLE
        expected = HS_RISK_TABLE["93"]
        assert compute_hs_risk(items) == pytest.approx(expected)


# ---------------------------------------------------------------------------
# compute_country_risk
# ---------------------------------------------------------------------------

class TestComputeCountryRisk:
    def test_none_returns_default(self):
        from utils.risk_tables import COUNTRY_RISK_TABLE
        assert compute_country_risk(None) == COUNTRY_RISK_TABLE["_default"]

    def test_empty_string_returns_default(self):
        from utils.risk_tables import COUNTRY_RISK_TABLE
        assert compute_country_risk("") == COUNTRY_RISK_TABLE["_default"]

    def test_known_low_risk_country(self):
        assert compute_country_risk("canada") <= 0.2

    def test_known_high_risk_country(self):
        assert compute_country_risk("north korea") >= 0.7

    def test_case_insensitive(self):
        lower = compute_country_risk("canada")
        upper = compute_country_risk("CANADA")
        mixed = compute_country_risk("Canada")
        assert lower == upper == mixed

    def test_leading_trailing_whitespace_stripped(self):
        assert compute_country_risk("  canada  ") == compute_country_risk("canada")

    def test_unknown_country_returns_default(self):
        from utils.risk_tables import COUNTRY_RISK_TABLE
        result = compute_country_risk("Narnia")
        assert result == COUNTRY_RISK_TABLE["_default"]

    def test_uae_alias(self):
        """Both 'uae' and 'united arab emirates' should return the same risk."""
        assert compute_country_risk("uae") == compute_country_risk("united arab emirates")


# ---------------------------------------------------------------------------
# compute_data_risk (integration)
# ---------------------------------------------------------------------------

class TestComputeDataRisk:
    def test_returns_all_keys(self):
        result = compute_data_risk([], None, None)
        expected_keys = {
            "data_risk", "value_anomaly", "hs_code_risk",
            "country_risk", "importer_risk",
        }
        assert set(result.keys()) == expected_keys

    def test_importer_risk_always_fixed(self):
        result = compute_data_risk([], None, None)
        assert result["importer_risk"] == IMPORTER_RISK

    def test_empty_inputs_produce_valid_result(self):
        result = compute_data_risk([], None, None)
        assert 0.0 <= result["data_risk"] <= 1.0

    def test_formula_with_known_inputs(self):
        # Use a fully known scenario so we can verify the formula manually:
        #   items = 1 electronics (HS 8471) at declared $500 → value_anomaly = 0
        #   origin = canada → country_risk = 0.1
        #   hs_code_risk = HS_RISK_TABLE["84"] = 0.45 (no mismatch)
        #   importer_risk = 0.5
        #   Data_Risk = 0.3*0 + 0.3*0.45 + 0.2*0.5 + 0.2*0.1
        #             = 0 + 0.135 + 0.1 + 0.02 = 0.255
        from utils.risk_tables import COUNTRY_RISK_TABLE, HS_RISK_TABLE
        items = [make_item(quantity=1, category="electronics", hs_code="8471")]
        result = compute_data_risk(items, 500.0, "canada")

        hs_base = HS_RISK_TABLE["84"]
        country = COUNTRY_RISK_TABLE["canada"]
        expected = 0.3 * 0.0 + 0.3 * hs_base + 0.2 * 0.5 + 0.2 * country
        assert result["data_risk"] == pytest.approx(expected, abs=1e-4)

    def test_result_clamped_to_one(self):
        # Worst-case: weapons from north korea, declared way below range
        items = [make_item(quantity=100, category="weapons", hs_code="9302")]
        result = compute_data_risk(items, 0.01, "north korea")
        assert result["data_risk"] <= 1.0

    def test_result_never_negative(self):
        result = compute_data_risk([], None, "canada")
        assert result["data_risk"] >= 0.0

    def test_high_risk_scenario(self):
        # Weapons, declared too low, from Iran
        items = [make_item(quantity=5, category="weapons", hs_code="9302")]
        result = compute_data_risk(items, 1.0, "iran")
        assert result["data_risk"] > 0.5

    def test_low_risk_scenario(self):
        # Books from Canada, reasonable price
        items = [make_item(quantity=10, category="books", hs_code="4901")]
        result = compute_data_risk(items, 200.0, "canada")
        assert result["data_risk"] < 0.5

    def test_sub_scores_match_individual_functions(self):
        items = [make_item(quantity=2, category="clothing", hs_code="6101")]
        result = compute_data_risk(items, 100.0, "china")
        assert result["value_anomaly"] == pytest.approx(
            compute_value_anomaly(items, 100.0), abs=1e-4
        )
        assert result["hs_code_risk"] == pytest.approx(
            compute_hs_risk(items), abs=1e-4
        )
        assert result["country_risk"] == pytest.approx(
            compute_country_risk("china"), abs=1e-4
        )
