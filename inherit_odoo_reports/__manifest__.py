
# -*- coding: utf-8 -*-
{
    'name': "Inherit Odoo Report",

    'summary': "Inherit Odoo Report",

    'description': "Inherit Odoo Report",

    'author': "Ali shan",
    'license': 'LGPL-3',
    'version': '0.1',

    'depends': ['base', 'web','sale','account'],
    'data': [
        'views/purchase_order_report.xml',
        'views/sale_order_report.xml',
        'views/invoice_order_report.xml',
    ],
}
