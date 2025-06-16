# Copyright 2017 Magnus ((www.magnus.nl).)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Ad4all REST Interface",
    "version": "16.0.1.0.0",
    "author": "The Open Source Company (TOSC)",
    "website": "https://github.com/OCA/l10n-netherlands",
    "license": "AGPL-3",
    "category": "integration",
    "summary": "This module transfers advertising orders from Odoo to Ad4all "
    "via a REST interface",
    "depends": ["sale_advertising_order"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "templates/rest_payload.xml",
        "data/ir_sequence_data.xml",
        "views/sale_order.xml",
        "views/sale_order_line.xml",
        "views/sale_order_line_ad4all.xml",
        "views/ad4all_config_view.xml",
        "views/product_category.xml",
        "views/product_template.xml",
        "wizards/sale_order_ad4all.xml",
    ],
    "demo": [
        "demo/ad4all_config.xml",
        "demo/res_partner.xml",
        "demo/product_category.xml",
    ],
}
