// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

// Check Address: what the carriers make of an address before a label is bought. On the
// Address form it checks that address; on a Delivery Note or Packing Slip it checks the
// ship-to. The dialog shows the verdict, the carriers' remarks and the lines they would
// change, and applies those lines only when asked.

frappe.provide('shipstation.address_check')

shipstation.address_check.run = function (frm, address_name) {
	if (!address_name) return
	frappe.call({
		method: 'shipstation_integration.api.addresses.validate_address',
		args: { address: address_name },
		freeze: true,
		freeze_message: __('Asking the carriers about {0}', [address_name]),
		callback: r => r.message && shipstation.address_check.show(frm, address_name, r.message),
	})
}

shipstation.address_check.show = function (frm, address_name, result) {
	const esc = frappe.utils.escape_html
	const verdict = {
		verified: [__('Verified'), 'green', __('The carriers find this address as written.')],
		warning: [__('Verified with changes'), 'orange', __('The carriers find it, with the corrections below.')],
		unverified: [__('Not verified'), 'red', __('The carriers could not confirm this address.')],
		error: [__('Not checked'), 'red', __('The address could not be checked.')],
	}[result.status] || [result.status, 'gray', '']
	let html = `<p><span class="indicator-pill ${verdict[1]}">${esc(verdict[0])}</span> ${esc(verdict[2])}</p>`
	if (result.residential === 'yes') html += `<p class="text-muted">${__('Residential address.')}</p>`
	if (result.messages.length) {
		html += `<ul>${result.messages.map(m => `<li>${esc(m)}</li>`).join('')}</ul>`
	}
	if (result.changes.length) {
		html += `<table class="table table-bordered table-condensed" style="margin-bottom:0"><thead><tr><th>${__('Line')}</th><th>${__('As entered')}</th><th>${__('Carriers say')}</th></tr></thead><tbody>`
		html += result.changes
			.map(
				c =>
					`<tr><td>${esc(c.label)}</td><td>${esc(c.from) || '<span class="text-muted">blank</span>'}</td><td><b>${esc(c.to) || '<span class="text-muted">blank</span>'}</b></td></tr>`
			)
			.join('')
		html += '</tbody></table>'
	}
	const d = new frappe.ui.Dialog({
		title: __('Address check: {0}', [address_name]),
		fields: [{ fieldtype: 'HTML', options: html }],
	})
	if (result.changes.length) {
		d.set_primary_action(__('Use the corrected lines'), () => {
			d.hide()
			frappe.call({
				method: 'shipstation_integration.api.addresses.apply_validated_address',
				args: { address: address_name, changes: result.changes },
				freeze: true,
				callback: () => {
					frappe.show_alert({ message: __('{0} updated.', [address_name]), indicator: 'green' }, 6)
					frm.reload_doc()
				},
			})
		})
	}
	d.show()
}

frappe.ui.form.on('Address', {
	refresh(frm) {
		if (frm.is_new()) return
		frm.add_custom_button(__('Check Address'), () => shipstation.address_check.run(frm, frm.doc.name))
	},
})

frappe.ui.form.on('Delivery Note', {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.shipping_address_name) return
		frm.add_custom_button(
			__('Check Address'),
			() => shipstation.address_check.run(frm, frm.doc.shipping_address_name),
			__('Shipping')
		)
	},
})
