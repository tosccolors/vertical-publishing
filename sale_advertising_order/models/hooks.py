# -*- coding: utf-8 -*-

def post_init_hook(cr, registry):
    """
    Updates existing codes matching the default '/' or
    empty. Primarily this ensures installation does not
    fail for demo data.
    :param cr: database cursor
    :return: void
    """
    cr.execute("UPDATE product_template "
               "SET default_code = '!!mig!!' || id "
               "WHERE default_code IS NULL OR default_code = '/';")

    cr.execute("UPDATE product_product "
               "SET default_code = '!!mig!!' || id "
               "WHERE default_code IS NULL OR default_code = '/';")