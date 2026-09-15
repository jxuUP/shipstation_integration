# Copyright (c) 2026, AgriTheory and Contributors
# See license.txt

import frappe

from shipstation_integration.api import labels


class Order(frappe._dict):
	"""Enough of a Delivery Note for get_label_messages: header fields plus one item row."""

	items = [frappe._dict(against_sales_order="1104534")]


def order(**kwargs):
	return Order(kwargs)


def test_references_lead_with_the_customer_po():
	messages = labels.get_label_messages(
		frappe._dict(), order(po_no="TRAIN-0723-TARGETPLUS", up_sales_channel="Target Plus")
	)
	assert messages == {
		"reference1": "TRAIN-0723-TARGETPLUS",
		"reference2": "1104534",
		"reference3": "Target Plus",
	}


def test_keyed_order_without_a_po_still_names_the_channel():
	messages = labels.get_label_messages(frappe._dict(), order(up_sales_channel="Shopify"))
	assert messages == {"reference1": "Shopify", "reference2": "1104534"}


def test_packing_slip_overrides_win():
	messages = labels.get_label_messages(
		frappe._dict(label_reference_3="dock 4"), order(po_no="PO-1", up_sales_channel="EDI")
	)
	assert messages["reference3"] == "dock 4"


def test_ups_gets_two_references(monkeypatch):
	# UPS rejects the whole purchase over a reference3, so the channel is the one to go.
	monkeypatch.setattr(labels, "get_carrier_code_for_id", lambda carrier_id: "ups")
	three = {"reference1": "PO-1", "reference2": "1104534", "reference3": "Target Plus"}
	assert labels.fit_label_messages(three, "se-2975921") == {
		"reference1": "PO-1",
		"reference2": "1104534",
	}


def test_fedex_keeps_all_three(monkeypatch):
	monkeypatch.setattr(labels, "get_carrier_code_for_id", lambda carrier_id: "fedex")
	three = {"reference1": "PO-1", "reference2": "1104534", "reference3": "Target Plus"}
	assert labels.fit_label_messages(three, "se-5302076") == three


def test_unknown_carrier_and_empty_messages(monkeypatch):
	monkeypatch.setattr(labels, "get_carrier_code_for_id", lambda carrier_id: None)
	assert labels.fit_label_messages(None, "se-1") == {}
	assert labels.fit_label_messages({"reference1": "PO-1"}, None) == {"reference1": "PO-1"}


def test_create_label_puts_the_fitted_references_on_every_package(
	monkeypatch, shipstation_api_client_mock
):
	monkeypatch.setattr(labels, "get_carrier_code_for_id", lambda carrier_id: "ups")
	monkeypatch.setattr(labels, "format_label_response", lambda response: response)
	shipstation_api_client_mock.create_label_from_shipment.return_value = {"label_id": "se-1"}

	labels.create_label(
		{
			"carrier_id": "se-2975921",
			"service_code": "ups_ground",
			"packages": [{"weight": {"value": 1, "unit": "pound"}}],
			"label_messages": {"reference1": "PO-1", "reference2": "1104534", "reference3": "Target Plus"},
		}
	)

	sent = shipstation_api_client_mock.create_label_from_shipment.call_args[0][0]["shipment"]
	assert "label_messages" not in sent
	assert sent["packages"][0]["label_messages"] == {"reference1": "PO-1", "reference2": "1104534"}
