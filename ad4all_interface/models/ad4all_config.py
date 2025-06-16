from odoo import fields, models


class Ad4allConfig(models.Model):
    _name = "ad4all.config"
    _description = "Ad4all Config"
    _rec_name = "username"

    active = fields.Boolean(default=True)
    host = fields.Char(
        "URL", required=True, help="This is the URL that the system can be reached at."
    )
    username = fields.Char(
        required=True,
        help="This is the username that is used for authenticating to this "
        "system, if applicable.",
    )
    password = fields.Char(
        required=True,
        help="This is the password that is used for authenticating to this "
        "system, if applicable.",
    )
    portal = fields.Char()
    deliverer = fields.Char()
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
