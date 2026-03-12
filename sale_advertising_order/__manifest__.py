##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2022 Magnus (<http://www.magnus.nl>). All Rights Reserved
#    Copyright (C) 2022-present TOSC (<http://www.tosc.nl>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name": "Sale Advertising Order",
    "version": "16.0.13.0.0",
    "category": "Sale",
    "author": "Deepa Venkatesh (DK), " "Willem Hulsof, The Open Source Company (TOSC)",
    "website": "https://github.com/OCA/l10n-netherlands",
    "depends": [
        "sale",
        "sale_order_type",
        "partner_manual_rank",
        "account",
        "account_analytic_tag",
        "partner_firstname",
        "base_address_extended",
        "report_xlsx_helper",
        "account_payment_partner",
        "calendar",
        "web_action_conditionable",
    ],
    "data": [
        "data/product_data.xml",
        "data/sale_order_type.xml",
        "data/config_data.xml",
        "data/mail_template_data.xml",
        "data/decimal_precision.xml",
        "security/security.xml",
        "security/ir.model.access.csv",
        "report/invoice_report_template.xml",
        "report/sale_report_template.xml",
        "report/proof_number_delivery_list_xslx.xml",
        "report/report_indeellijst_list_views.xml",
        "wizard/make_invoice_views.xml",
        "wizard/update_order_line_view.xml",
        "wizard/sale_line_create_multi.xml",
        "views/res_config_views.xml",
        "views/res_partner.xml",
        "views/product_views.xml",
        "views/ir_qweb_widget_templates.xml",
        "views/issue_views.xml",
        "views/sale_order_views.xml",
        "views/account_invoice_views.xml",
        "views/proof_delivery_list_views.xml",
        "views/menu_views.xml",
    ],
    "qweb": [],
    "demo": [
        "demo/discount_reason.xml",
        "demo/product_attribute_value.xml",
        "demo/product_category.xml",
        "demo/product_template.xml",
        "demo/res_partner.xml",
        "demo/sale_advertising_issue.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
