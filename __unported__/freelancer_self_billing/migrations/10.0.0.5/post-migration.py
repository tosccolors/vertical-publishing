# -*- coding: utf-8 -*-
from openupgradelib import openupgrade

# from openerp.modules.registry import RegistryManager
from odoo import SUPERUSER_ID

@openupgrade.migrate(use_env=True)
def migrate(env, version):
    cr = env.cr

    env['ir.module.module'].sudo(SUPERUSER_ID).update_list()


    #---------------------------------------------------------------
    # Removing deprecated / Clubbed modules
    cr.execute("""
        UPDATE ir_module_module set state = 'to remove'
        WHERE name in ('nsm_supportal_extension') and state ='to upgrade';
    """)

