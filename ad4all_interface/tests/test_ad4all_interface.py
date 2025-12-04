from unittest.mock import Mock

from odoo import exceptions
from odoo.addons.sale_advertising_order.tests import common
from odoo.tests.common import Form


class TestAd4allInterface(common.CommonSaleAdvertisingOrder):
    def test_wizard(self):

        wizard = (
            self.env["sale.order.ad4all"]
            .with_context(
                active_model=self.order._name,
                active_ids=self.order.ids,
            )
            .create({})
        )

        with self.assertRaises(exceptions.UserError):
            wizard.sale_order_update_ad4all()

        with Form(self.order, self.order_view) as order_form:
            with order_form.order_line.new() as line_form:
                line_form.medium = self.product_category_main
                line_form.title_ids.add(self.title1)
                line_form.product_template_id = self.product_template_digital1

        self.assertTrue(self.order.order_ad4all_allow)

        self.order.write({"state": "sale"})
        with self.assertRaisesRegex(exceptions.UserError, "material contact person"):
            wizard.sale_order_update_ad4all()

        self.order.material_contact_person = self.env.ref(
            "sale_advertising_order.partner_ad_agency_contact"
        )

        email = self.order.material_contact_person.email
        self.order.material_contact_person.email = False

        with self.assertRaisesRegex(exceptions.UserError, "missing"):
            wizard.sale_order_update_ad4all()

        self.order.material_contact_person.email = email
        requests = self.patch_requests()
        requests.side_effect = lambda *args, **kwargs: Mock(
            json=lambda: {"code": "200"}
        )
        wizard.sale_order_update_ad4all()
        self.assertEqual(self.order.order_line.publog_id.status, "successful")
        self.assertEqual(
            self.order.order_line.publog_id.deliverer, "deliverer with company"
        )
