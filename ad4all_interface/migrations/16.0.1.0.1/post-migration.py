from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version=None):
    env.cr.execute(
        """
        select
        id,
        customer_contacts_contact_id,
        customer_contacts_contact_name,
        customer_contacts_contact_email,
        customer_contacts_contact_phone,
        customer_contacts_contact_type,
        customer_contacts_contact_language,
        customer_contacts_contact2_id,
        customer_contacts_contact2_name,
        customer_contacts_contact2_email,
        customer_contacts_contact2_phone,
        customer_contacts_contact2_type,
        customer_contacts_contact2_language
        from
        sale_order_line_ad4all
        """
    )
    for (
        line_id,
        contact_id,
        contact_name,
        contact_email,
        contact_phone,
        contact_type,
        contact_language,
        contact2_id,
        contact2_name,
        contact2_email,
        contact2_phone,
        contact2_type,
        contact2_language,
    ) in env.cr.fetchall():
        env["sale.order.line.ad4all"].browse(line_id).write(
            {
                "customer_contacts": [
                    {
                        "id": contact_id,
                        "name": contact_name,
                        "email": contact_email,
                        "phone": contact_phone,
                        "type": contact_type,
                        "language": contact_language,
                    }
                ]
                + (
                    [
                        {
                            "id": contact2_id,
                            "name": contact2_name,
                            "email": contact2_email,
                            "phone": contact2_phone,
                            "type": contact2_type,
                            "language": contact2_language,
                        }
                    ]
                    if contact2_id
                    else []
                )
            }
        )
