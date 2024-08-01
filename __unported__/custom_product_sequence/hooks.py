# -*- coding: utf-8 -*-

def pre_init_hook(cr):
    """
    Updates existing codes matching the default '/' or
    empty. Primarily this ensures installation does not
    fail for demo data.
    :param cr: database cursor
    :return: void
    """
    cr.execute("UPDATE product_template "
               "SET default_code = '!!temp!!' || id "
               "WHERE default_code IS NULL OR default_code = '/';")

    cr.execute("UPDATE product_product "
               "SET default_code = '!!mig!!' || id "
               "WHERE default_code IS NULL OR default_code = '/';")