# -*- coding: utf-8 -*-
{
	'name': "HR App APIs",
	'summary': "APIs for mobile app integration with HR module in Odoo",
	'description': """
		This module provides secured API endpoints for the HR App, 
		including authentication, employee details, user type, 
		company details, document access, and many more.
	""",
	'author': "Ali Shan.",
	'category': 'API',
	'version': '1.0',

	'depends': ['base', 'mail', 'hr', 'stock','hr_payroll'], 

	'data': [
		'security/ir.model.access.csv',
		'views/views.xml', 
	],
	
	'installable': True,
	'application': True,
	'auto_install': False,
}
