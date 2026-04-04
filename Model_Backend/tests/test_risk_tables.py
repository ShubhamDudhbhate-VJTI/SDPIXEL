"""Tests for utils/risk_tables.py"""

import pytest
from utils.risk_tables import (
    CATEGORY_HS_GROUP,
    CATEGORY_TABLE,
    COUNTRY_RISK_TABLE,
    HS_RISK_TABLE,
)


class TestCategoryTable:
    def test_has_at_least_20_categories(self):
        assert len(CATEGORY_TABLE) >= 20

    def test_all_prices_are_positive(self):
        for category, (min_p, max_p) in CATEGORY_TABLE.items():
            assert min_p > 0, f"{category}: min_price must be > 0"
            assert max_p > 0, f"{category}: max_price must be > 0"

    def test_min_always_lte_max(self):
        for category, (min_p, max_p) in CATEGORY_TABLE.items():
            assert min_p <= max_p, f"{category}: min_price {min_p} > max_price {max_p}"

    def test_required_categories_present(self):
        required = [
            "electronics", "clothing", "pharmaceuticals", "jewelry",
            "weapons", "food", "machinery", "other",
        ]
        for cat in required:
            assert cat in CATEGORY_TABLE, f"Missing required category: {cat}"

    def test_other_category_is_fallback(self):
        """'other' must exist as a catch-all."""
        assert "other" in CATEGORY_TABLE

    def test_price_values_are_floats(self):
        for _, (min_p, max_p) in CATEGORY_TABLE.items():
            assert isinstance(min_p, float)
            assert isinstance(max_p, float)


class TestHsRiskTable:
    def test_all_keys_are_two_digit_strings(self):
        for key in HS_RISK_TABLE:
            assert isinstance(key, str), f"Key {key!r} is not a string"
            assert len(key) == 2, f"Key {key!r} is not 2 digits"
            assert key.isdigit(), f"Key {key!r} contains non-digits"

    def test_all_risk_scores_in_range(self):
        for key, risk in HS_RISK_TABLE.items():
            assert 0.0 <= risk <= 1.0, f"HS {key}: risk {risk} out of [0, 1]"

    def test_weapons_chapter_is_high_risk(self):
        """Chapter 93 (Arms/Ammunition) must have risk >= 0.8"""
        assert HS_RISK_TABLE.get("93", 0) >= 0.8

    def test_explosives_is_high_risk(self):
        """Chapter 36 (Explosives) must have risk >= 0.7"""
        assert HS_RISK_TABLE.get("36", 0) >= 0.7

    def test_common_chapters_present(self):
        """Core chapters used in CATEGORY_HS_GROUP must be present."""
        for chapter in ("84", "85", "61", "62", "64", "30", "93", "71"):
            assert chapter in HS_RISK_TABLE, f"Missing HS chapter: {chapter}"

    def test_at_least_50_entries(self):
        assert len(HS_RISK_TABLE) >= 50


class TestCountryRiskTable:
    def test_has_at_least_50_countries(self):
        # _default is not a real country
        real_countries = {k for k in COUNTRY_RISK_TABLE if not k.startswith("_")}
        assert len(real_countries) >= 50

    def test_all_risk_scores_in_range(self):
        for country, risk in COUNTRY_RISK_TABLE.items():
            assert 0.0 <= risk <= 1.0, f"{country}: risk {risk} out of [0, 1]"

    def test_default_key_exists(self):
        assert "_default" in COUNTRY_RISK_TABLE

    def test_high_risk_countries(self):
        """Sanctioned / embargoed countries must be high risk."""
        for country in ("north korea", "iran", "syria"):
            assert COUNTRY_RISK_TABLE.get(country, 0) >= 0.7, (
                f"{country} should have risk >= 0.7"
            )

    def test_low_risk_countries(self):
        """Well-governed countries should be low risk."""
        for country in ("canada", "australia", "norway"):
            assert COUNTRY_RISK_TABLE.get(country, 1) <= 0.2, (
                f"{country} should have risk <= 0.2"
            )

    def test_all_keys_are_lowercase(self):
        for key in COUNTRY_RISK_TABLE:
            assert key == key.lower(), f"Key {key!r} is not lowercase"


class TestCategoryHsGroup:
    def test_all_categories_have_set_values(self):
        for category, prefixes in CATEGORY_HS_GROUP.items():
            assert isinstance(prefixes, set), f"{category}: value must be a set"

    def test_all_prefixes_are_two_digit_strings(self):
        for category, prefixes in CATEGORY_HS_GROUP.items():
            for prefix in prefixes:
                assert isinstance(prefix, str), f"{category}/{prefix}: must be str"
                assert len(prefix) == 2, f"{category}/{prefix}: must be 2 chars"
                assert prefix.isdigit(), f"{category}/{prefix}: must be digits"

    def test_all_categories_also_in_category_table(self):
        """Every category in CATEGORY_HS_GROUP should exist in CATEGORY_TABLE."""
        for cat in CATEGORY_HS_GROUP:
            assert cat in CATEGORY_TABLE, (
                f"{cat} in CATEGORY_HS_GROUP but not in CATEGORY_TABLE"
            )

    def test_weapons_maps_to_chapter_93(self):
        assert "93" in CATEGORY_HS_GROUP.get("weapons", set())

    def test_other_category_has_empty_set(self):
        """'other' category must have empty set (no mismatch penalty)."""
        assert CATEGORY_HS_GROUP.get("other") == set()

    def test_electronics_maps_to_84_and_85(self):
        electronics = CATEGORY_HS_GROUP.get("electronics", set())
        assert "84" in electronics
        assert "85" in electronics
