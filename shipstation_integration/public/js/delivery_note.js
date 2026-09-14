// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Note', {
	refresh: frm => {
		shipping.shipstation(frm)

		if (frm.doc.docstatus === 1 && frm.doc.shipstation_order_id) {
			frm
				.add_custom_button(__('Fetch Shipment'), () => {
					frappe.call({
						method: 'shipstation_integration.api.shipping.fetch_shipment',
						args: {
							delivery_note: frm.doc.name,
						},
						freeze: true,
						callback: function (r) {
							if (r.message) {
								frappe.msgprint(`A shipment was fetched from Shipstation and created at ${r.message}`)
							} else {
								frappe.msgprint(
									`No new shipment(s) were found against Shipstation ID: ${frm.doc.shipstation_order_id.bold()}`
								)
							}
						},
					})
				})
				.removeClass('btn-default')
				.addClass('btn-primary')
		}

		// Add rate shopping button for submitted Delivery Notes with shipping address
		if (frm.doc.docstatus === 1 && frm.doc.shipping_address_name && !frm.doc.tracking_number) {
			add_rate_shopping_button(frm)
		}
	},
})

function add_rate_shopping_button(frm) {
	frm.add_custom_button(
		__('Get Shipping Rates'),
		() => {
			frappe.call({
				method: 'shipstation_integration.api.rates.get_rates_for_delivery_note',
				args: {
					delivery_note: frm.doc.name,
				},
				freeze: true,
				freeze_message: __('Fetching shipping rates...'),
				callback: function (r) {
					if (r.message && r.message.length > 0) {
						show_rate_selection_dialog(frm, r.message)
					} else {
						frappe.msgprint(__('No shipping rates found for this delivery.'))
					}
				},
				error: function (r) {
					frappe.msgprint(__('Failed to fetch shipping rates. Please check your ShipStation API configuration.'))
				},
			})
		},
		__('ShipStation')
	)
}

function show_rate_selection_dialog(frm, rates) {
	shipstation.rates.pick(frm, rates, rate => create_label_from_rate(frm, rate))
}

function create_label_from_rate(frm, rate) {
	frappe.call({
		method: 'shipstation_integration.api.labels.create_label_for_delivery_note',
		args: {
			delivery_note: frm.doc.name,
			rate_id: rate.rate_id,
		},
		freeze: true,
		freeze_message: __('Creating shipping label...'),
		callback: function (r) {
			if (r.message) {
				const tracking = r.message.tracking_number || ''
				frappe.show_alert({
					message: __('Label created! Tracking: {0}', [tracking]),
					indicator: 'green',
				})
				frm.reload_doc()
			}
		},
		error: function (r) {
			frappe.msgprint(__('Failed to create shipping label.'))
		},
	})
}
