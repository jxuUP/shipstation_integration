# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest

from shipstation_integration.api.addresses import apply_validated_address, validate_address


def any_us_address():
	name = frappe.db.get_value("Address", {"country": "United States"}, "name")
	assert name, "the test site needs one US Address"
	return name


@pytest.mark.order(60)
def test_address_check_reports_the_carriers_corrections(shipstation_api_client_mock):
	"""The dialog shows the verdict and the lines the carriers would change; applying
	them writes exactly those lines."""
	address = any_us_address()
	doc = frappe.get_doc("Address", address)
	before = {"address_line1": doc.address_line1, "city": doc.city, "pincode": doc.pincode}
	shipstation_api_client_mock.validate_addresses.return_value = [
		{
			"status": "warning",
			"messages": [{"message": "Address was corrected."}],
			"matched_address": {
				"address_line1": (doc.address_line1 or "").upper(),
				"address_line2": doc.address_line2 or "",
				"city_locality": doc.city or "",
				"state_province": doc.state or "",
				"postal_code": "90040-1234",
				"address_residential_indicator": "no",
			},
		}
	]

	result = validate_address(address)
	assert result["status"] == "warning"
	assert result["messages"] == ["Address was corrected."]
	changed = {c["field"]: c["to"] for c in result["changes"]}
	assert changed.get("pincode") == "90040-1234"
	sent = shipstation_api_client_mock.validate_addresses.call_args[0][0][0]
	assert sent["address_line1"] == (doc.address_line1 or "")
	assert sent["country_code"] == "US"

	try:
		apply_validated_address(address, [c for c in result["changes"] if c["field"] == "pincode"])
		assert frappe.db.get_value("Address", address, "pincode") == "90040-1234"
	finally:
		frappe.db.set_value("Address", address, before)
