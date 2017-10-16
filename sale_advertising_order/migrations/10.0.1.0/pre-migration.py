# -*- coding: utf-8 -*-

from openupgradelib import openupgrade

# V10 modules that don't exist in v9 and are dependent of

def install_new_modules(cr):
    sql = """
    UPDATE ir_module_module
    SET state='to install'
    WHERE name = '%s' AND state='uninstalled'
    """ %('publishing_accounts')
    openupgrade.logged_query(cr, sql)


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    install_new_modules(env.cr)
