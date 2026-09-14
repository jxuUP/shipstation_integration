# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Address validation through ShipEngine.

The carriers correct or refuse an address at label time, when the box is packed and the
driver is waiting. Asking first costs nothing (validation is free on the account), so the
Address form and the Delivery Note offer a check that says whether the carriers find the
address and what they would change, and lets the person apply the corrected lines.
Nothing is written unless they do.
"""

import frappe
from frappe import _

from shipstation_integration.api.rates import format_address, get_state_code
from shipstation_integration.utils import get_error_message, get_shipstation_settings

FIELDS = (
	("address_line1", "address_line1"),
	("address_line2", "address_line2"),
	("city_locality", "city"),
	("state_province", "state"),
	("postal_code", "pincode"),
)


@frappe.whitelist()
def validate_address(address: str, settings_name: str | None = None) -> dict:
	"""What ShipEngine makes of one Address: ``status`` (verified, warning, unverified,
	error), the carriers' messages, and the lines it would change."""
	doc = frappe.get_doc("Address", address)
	country = frappe.db.get_value("Country", doc.country, "code") or "US"
	sent = {
		"name": doc.address_title or "",
		"street1": doc.address_line1 or "",
		"street2": doc.address_line2 or "",
		"city": doc.city or "",
		"state": get_state_code(doc.state or "", country),
		"postal_code": doc.pincode or "",
		"country": country,
		"phone": doc.phone or "0000000000",
	}
	settings = get_shipstation_settings(settings_name)
	try:
		results = settings.shipstation_api_client().validate_addresses([format_address(sent)])
	except Exception as e:
		frappe.throw(_("Address validation failed: {0}").format(get_error_message(e)))

	result = results[0] if isinstance(results, list) and results else {}
	matched = result.get("matched_address") or {}
	changes = []
	for their_key, our_field in FIELDS:
		theirs = (matched.get(their_key) or "").strip()
		ours = (doc.get(our_field) or "").strip()
		if matched and theirs.upper() != ours.upper():
			changes.append(
				{"field": our_field, "label": doc.meta.get_label(our_field), "from": ours, "to": theirs}
			)
	return {
		"status": result.get("status") or "error",
		"messages": [m.get("message") for m in result.get("messages") or [] if m.get("message")],
		"residential": matched.get("address_residential_indicator"),
		"changes": changes,
	}


@frappe.whitelist()
def apply_validated_address(address: str, changes: list | str) -> None:
	"""Write the corrected lines the person accepted onto the Address."""
	rows = frappe.parse_json(changes) if isinstance(changes, str) else changes
	allowed = {our_field for _their, our_field in FIELDS}
	doc = frappe.get_doc("Address", address)
	doc.check_permission("write")
	for row in rows or []:
		if row.get("field") in allowed:
			doc.set(row["field"], row.get("to") or "")
	doc.save()
