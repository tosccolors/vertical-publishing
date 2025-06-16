# Copyright 2017 Willem hulshof - <w.hulshof@magnus.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    ad4all = fields.Boolean("Ads to Ad4all", default=False)
    ad4all_material_type = fields.Selection(
        [
            ("PRINT", "Print"),
            ("ONLINE", "Online"),
            ("DEEL", "Share"),
        ],
        string="Ad4all Type",
        readonly=False,
    )
