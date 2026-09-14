// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

// One rate picker for the parcel forms (Packing Slip, Shipment, Delivery Note): the rates
// cheapest first with the cheapest already ticked, a click anywhere on a row picks it, and
// one button that buys the label. The forms differ only in what they do with the pick.

frappe.provide('shipstation.rates')

// rates are ShipEngine rate objects; on_pick(rate) runs with the ticked one once the dialog
// has closed. Nothing is bought here.
shipstation.rates.pick = function (frm, rates, on_pick) {
	const esc = frappe.utils.escape_html
	const cost = r => flt(r.shipping_amount?.amount ?? r.shipping_amount ?? r.total_amount)
	const currency = rates[0]?.shipping_amount?.currency || 'USD'
	const sorted = rates.slice().sort((a, b) => cost(a) - cost(b))
	const days = d => (d ? __('{0} day(s)', [cint(d)]) : '')
	const rows = sorted
		.map(
			(r, i) => `
		<tr class="rate-row" style="cursor:pointer">
			<td class="text-center"><input type="radio" name="parcel-rate" class="rate-pick" value="${i}" ${i === 0 ? 'checked' : ''}></td>
			<td>${esc(r.carrier_name || r.carrier_id || '')}</td>
			<td>${esc(r.service_type || r.service_code || '')}</td>
			<td class="text-center">${days(r.delivery_days)}</td>
			<td class="text-right"><strong>${format_currency(cost(r), currency)}</strong></td>
		</tr>`
		)
		.join('')
	const html = `
		<table class="table table-bordered table-condensed" style="margin-bottom:0">
			<thead>
				<tr>
					<th style="width:36px"></th>
					<th>${__('Carrier')}</th>
					<th>${__('Service')}</th>
					<th class="text-center">${__('Transit')}</th>
					<th class="text-right">${__('Cost')}</th>
				</tr>
			</thead>
			<tbody>${rows}</tbody>
		</table>
		<p class="text-muted small" style="margin-top:8px">${__(
			'The cheapest is ticked. Create Label buys the ticked rate and charges the shipping account; closing this buys nothing.'
		)}</p>`

	const d = new frappe.ui.Dialog({
		title: __('{0} rate(s) for {1}', [sorted.length, frm.doc.name]),
		size: 'large',
		fields: [{ fieldtype: 'HTML', fieldname: 'rates_html', options: html }],
		primary_action_label: __('Create Label'),
		primary_action: () => {
			const rate = sorted[cint(d.$body.find('.rate-pick:checked').val())]
			if (!rate) return
			d.hide()
			on_pick(rate)
		},
	})
	d.$body.on('click', '.rate-row', function () {
		$(this).find('.rate-pick').prop('checked', true)
	})
	d.show()
}
