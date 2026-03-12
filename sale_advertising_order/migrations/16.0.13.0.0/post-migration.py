from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version=None):
    env.cr.execute(
        """
        update sale_order set was_confirmed_before=True
        where state in ('sale', 'done')
        """
    )
