# Copyright (c) 2026, AgriTheory and Contributors
# See license.txt

import frappe
import pytest

from shipstation_integration.api.labels import (
	is_military_address,
	validate_military_delivery,
)
from shipstation_integration.api.rates import get_state_code


def test_armed_forces_states_map_to_codes():
	assert get_state_code("Armed Forces Americas") == "AA"
	assert get_state_code("Armed Forces Europe") == "AE"
	assert get_state_code("Armed Forces Pacific") == "AP"
	assert get_state_code("AE") == "AE"


@pytest.mark.parametrize(
	"address",
	[
		{"address_line1": "PSC 1234 Box 5678", "city": "APO", "state": "AE"},
		{"address_line1": "Unit 2050 Box 4190", "city": "fpo", "state": "Armed Forces Pacific"},
		{"address_line1": "CMR 400 Box 1", "city": "Unit 1234", "state": "aa"},
		{"address_line1": "DPO", "city": "DPO", "state": ""},
	],
)
def test_detects_military_addresses(address):
	assert is_military_address(frappe._dict(address))


@pytest.mark.parametrize(
	"address",
	[
		{"address_line1": "6049 Slauson Ave", "city": "Commerce", "state": "CA"},
		{"address_line1": "1 Main St", "city": "Apopka", "state": "Florida"},
	],
)
def test_ignores_domestic_addresses(address):
	assert not is_military_address(frappe._dict(address))


def test_ignores_foreign_two_letter_regions(monkeypatch):
	# Italy's Ascoli Piceno province is also "AP"; the country check must win.
	monkeypatch.setattr(frappe.db, "get_value", lambda *a, **k: "IT")
	address = frappe._dict(
		{"address_line1": "Via Roma 1", "city": "Ascoli", "state": "AP", "country": "Italy"}
	)
	assert not is_military_address(address)


def test_usps_allowed_others_blocked():
	address = frappe._dict({"address_line1": "PSC 1234 Box 5678", "city": "APO", "state": "AE"})
	validate_military_delivery(address, "usps_priority_mail", "USPS")
	with pytest.raises(frappe.ValidationError):
		validate_military_delivery(address, "ups_ground", "UPS")
	with pytest.raises(frappe.ValidationError):
		validate_military_delivery(address, "fedex_ground", None)
