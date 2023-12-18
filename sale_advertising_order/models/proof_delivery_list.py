# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools

class ProofNumberDeliveryList(models.Model):
    _name = 'proof.number.delivery.list'
    _auto = False
    _rec_name = 'line_id'
    _description = 'Proof Number Delivery List'

    @api.depends('proof_number_payer')
    def _get_proof_data(self):
        for line in self:
            proof_payer = line.proof_number_payer
            line.proof_parent_name = proof_payer.parent_id and proof_payer.parent_id.name or False
            line.proof_parent_name = proof_payer.parent_id and proof_payer.parent_id.name or False
            line.proof_initials = proof_payer.initials or ''
            line.proof_infix = proof_payer.infix or ''
            line.proof_lastname = proof_payer.lastname or ''
            line.proof_country_code = proof_payer.country_id.code or ''
            line.proof_zip = proof_payer.zip or ''
            line.proof_email = proof_payer.email or ''
            line.proof_street_number = proof_payer.street_number or ''
            line.proof_street_name = proof_payer.street_name or ''
            line.proof_city = proof_payer.city or ''
            line.proof_partner_name = proof_payer.name or ''
            order_line = line.line_id
            amt = 0
            if order_line.proof_number_payer_id and proof_payer == order_line.proof_number_payer_id:
                amt += order_line.proof_number_amt_payer
            if proof_payer.id in order_line.proof_number_adv_customer.ids:
                amt += order_line.proof_number_amt_adv_customer
            line.proof_number_amt = amt

    line_id = fields.Many2one('sale.order.line', 'Order line', readonly=True)
    proof_number_payer = fields.Many2one('res.partner', 'Name', readonly=True)
    title = fields.Many2one('sale.advertising.issue', 'Title', readonly=True)
    adv_issue = fields.Many2one('sale.advertising.issue', 'Advertising Issue', readonly=True)
    issue_date = fields.Date(string='Issue Date', readonly=True)
    proof_parent_name = fields.Char(compute='_get_proof_data', readonly=True, store=False, string="Parent")
    proof_initials = fields.Char(compute='_get_proof_data', readonly=True, store=False, string="Initials")
    proof_infix = fields.Char(compute='_get_proof_data', readonly=True, store=False, string="Infix")
    proof_lastname = fields.Char(compute='_get_proof_data', readonly=True, store=False, string="Last Name")
    proof_country_code = fields.Char(compute='_get_proof_data', readonly=True, store=False, string="Country Code")
    proof_zip = fields.Char(compute='_get_proof_data', readonly=True, store=False, string="Zip")
    proof_street_number = fields.Char(compute='_get_proof_data', readonly=True, store=False, string="Street Number")
    proof_street_name = fields.Char(compute='_get_proof_data', readonly=True, store=False, string="Street Name")
    proof_city = fields.Char(compute='_get_proof_data', readonly=True, store=False, string="City")
    proof_partner_name = fields.Char(compute='_get_proof_data', readonly=True, store=False, string="Name")
    proof_number_amt = fields.Integer(compute='_get_proof_data', readonly=True, store=False, string="Proof Number Amount")
    proof_email = fields.Char(compute='_get_proof_data', readonly=True, store=False, string="Email")

    def init(self):
        """ """
        tools.drop_view_if_exists(self.env.cr, 'proof_number_delivery_list')
        self.env.cr.execute("""
                CREATE OR REPLACE VIEW proof_number_delivery_list AS (   
                                    
                   WITH Q11 AS(
                            SELECT
                                sol.id as id,sol.proof_number_payer_id as partner , sol.title as title, sol.adv_issue as adv_issue, sol.issue_date as issue_date
                            FROM
                                sale_order_line as sol
                            WHERE
                                proof_number_payer_id IS NOT NULL AND sol.advertising = TRUE AND sol.state IN ('sale','done')

                            UNION ALL

                            SELECT
                                ppl.line_id as id, ppl.partner_id as partner, sol.title as title, sol.adv_issue as adv_issue, sol.issue_date as issue_date
                            FROM
                                partner_line_proof_rel as ppl join sale_order_line as sol on (sol.id = ppl.line_id)
                            WHERE
                                sol.advertising = TRUE AND sol.state IN ('sale','done')
                    )
    
                  SELECT 
                      row_number() OVER () AS id, q.id as line_id, q.partner as proof_number_payer, min(q.title) as title, min(q.adv_issue) as adv_issue, min(q.issue_date) as issue_date
                  FROM Q11 as q
                  GROUP BY q.partner, q.id
                )
        """)
        
        
    
    def action_view_order_line(self):
        self.ensure_one()
        action = self.env.ref('sale_advertising_order.all_advertising_order_lines_action')
        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': 'form' if self.line_id else action.view_type,
            'view_mode': 'form' if self.line_id else action.view_mode,
            'target': action.target,
            'res_id': self.line_id.id or False,
            'res_model': action.res_model,
            'domain': [('id', '=', self.line_id.id)],
        }

