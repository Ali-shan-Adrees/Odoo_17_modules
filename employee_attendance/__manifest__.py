# -*- coding: utf-8 -*-
{
    'name': "HR Salary Rules",

    'summary': "Employee Attendance",

    'description': """
    """,

    'author': "Ali Shan",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base','hr_attendance','hr_holidays','hr_payroll','employee_hr_portal'],

    'data': [
        # 'security/ir.model.access.csv',
        'security/security.xml',
        'views/views.xml',
    ],
   
}