# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError


class AccountInvoiceRefund(models.TransientModel):
	"""Refunds invoice"""

	_inherit = "account.invoice.refund"
	_description = "Invoice Refund"



	@api.multi
	def compute_refund(self, mode='refund'):
		inv_obj = self.env['account.invoice']
		inv_tax_obj = self.env['account.invoice.tax']
		inv_line_obj = self.env['account.invoice.line']
		context = dict(self._context or {})
		xml_id = False

		for form in self:
			created_inv = []
			date = False
			description = False
			for inv in inv_obj.browse(context.get('active_ids')):
				if inv.state in ['draft', 'proforma2', 'cancel']:
					raise UserError(_('Cannot refund draft/proforma/cancelled invoice.'))
				if inv.reconciled and mode in ('cancel', 'modify'):
					raise UserError(_('Cannot refund invoice which is already reconciled, invoice should be unreconciled first. You can only refund this invoice.'))

				date = form.date or False
				description = form.description or inv.name
				refund = inv.refund(form.date_invoice, date, description, inv.journal_id.id)
				refund.compute_taxes()

				created_inv.append(refund.id)
				if mode in ('cancel', 'modify'):
					movelines = inv.move_id.line_ids
					to_reconcile_ids = {}
					to_reconcile_lines = self.env['account.move.line']
					for line in movelines:
						if line.account_id.id == inv.account_id.id:
							to_reconcile_lines += line
							to_reconcile_ids.setdefault(line.account_id.id, []).append(line.id)
						if line.reconciled:
							line.remove_move_reconcile()
					refund.signal_workflow('invoice_open')
					for tmpline in refund.move_id.line_ids:
						if tmpline.account_id.id == inv.account_id.id:
							to_reconcile_lines += tmpline
							to_reconcile_lines.reconcile()
					if mode == 'modify':
						invoice = inv.read(
									['name', 'type', 'number', 'reference',
									'comment', 'date_due', 'partner_id',
									'partner_insite', 'partner_contact',
									'partner_ref', 'payment_term_id', 'account_id',
									'currency_id', 'invoice_line_ids', 'tax_line_ids',
									'journal_id', 'date'])
						invoice = invoice[0]
						del invoice['id']
						invoice_lines = inv_line_obj.browse(invoice['invoice_line_ids'])
						invoice_lines = inv_obj.with_context(mode='modify')._refund_cleanup_lines(invoice_lines)
						tax_lines = inv_tax_obj.browse(invoice['tax_line_ids'])
						tax_lines = inv_obj._refund_cleanup_lines(tax_lines)
						invoice.update({
							'type': inv.type,
							'date_invoice': form.date_invoice,
							'state': 'draft',
							'number': False,
							'invoice_line_ids': invoice_lines,
							'tax_line_ids': tax_lines,
							'date': date,
							'name': description,
							'origin': inv.origin,
							'published_customer': inv.published_customer.id,
							'customer_contact':inv.customer_contact.id,
							'fiscal_position_id': inv.fiscal_position_id.id,
						})
						for field in ('partner_id', 'account_id', 'currency_id',
										 'payment_term_id', 'journal_id'):
								invoice[field] = invoice[field] and invoice[field][0]
						inv_refund = inv_obj.create(invoice)
						if inv_refund.payment_term_id.id:
							inv_refund._onchange_payment_term_date_invoice()
						created_inv.append(inv_refund.id)
						# code added to update customer contact and advertiser to refund invoice
				for inv_refund_id in created_inv:
					refund_inv = self.env['account.invoice'].search([('id','=',inv_refund_id)])
					if refund_inv:
						for refund_acc in refund_inv:
							refund_acc.update({'published_customer': inv.published_customer.id,
								'customer_contact':inv.customer_contact.id})

				xml_id = (inv.type in ['out_refund', 'out_invoice']) and 'action_invoice_tree1' or \
						 (inv.type in ['in_refund', 'in_invoice']) and 'action_invoice_tree2_standard'
				# Put the reason in the chatter
				subject = _("Invoice refund")
				body = description
				refund.message_post(body=body, subject=subject)

		# Supplier portal: reuse
		for refundInv in inv_obj.browse(created_inv):
			if not refundInv.supplier_id: continue
			refundInv.write({'reuse': refundInv.partner_id.reuse})

		# code added for checking which invoice is used for modifying and refund option and the link is added in sale order line invoice lines
		for inv in inv_obj.browse(context.get('active_ids')):
			for line in inv.invoice_line_ids:
				sale_line_id = self.env['sale.order.line'].search([('id','=',line.so_line_id.id)])
				if sale_line_id:
					for sale_line in sale_line_id:
						if inv.type =='out_invoice':
							if mode == 'modify':
								inv.modify_refund_created = True
							sale_line.invoice_lines = [(4, line.id)]
						if inv.type == 'out_refund':
							sale_line.invoice_lines = [(4, line.id)]
						#fetch the invoice lines to add the removed lines from standard 
						inv_line_ids = self.env['account.invoice.line'].search([('so_line_id','=',sale_line.id)])
						for inv_line in inv_line_ids:
							if inv_line.invoice_id.state != 'cancel':
								sale_line.invoice_lines = [(4, inv_line.id)]

		if xml_id:
			model = 'nsm_supplier_portal' if xml_id == 'action_invoice_tree2_standard' else 'account'
			result = self.env.ref(model+'.%s' % (xml_id)).read()[0]
			invoice_domain = eval(result['domain'])
			invoice_domain.append(('id', 'in', created_inv))
			result['domain'] = invoice_domain
			return result
		return True

