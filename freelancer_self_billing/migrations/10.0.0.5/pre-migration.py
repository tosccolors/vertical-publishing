# -*- coding: utf-8 -*-
# Copyright 2017 Onestein (<http://www.onestein.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


def install_new_modules(cr):
    sql = """
    UPDATE ir_module_module
    SET state='to install'
    WHERE name = '%s' AND state='uninstalled'
    """ %('publishing_accounts')
    openupgrade.logged_query(cr, sql)


@openupgrade.migrate(use_env=True)
def migrate(env, version):
    cr = env.cr
    install_new_modules(env.cr)
