from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version=None):
    env.cr.execute(
        """
        insert into sale_order_material_contact_person_rel
        (sale_order_id, res_partner_id)
        select id, material_contact_person from sale_order
        where material_contact_person is not null
        """
    )
