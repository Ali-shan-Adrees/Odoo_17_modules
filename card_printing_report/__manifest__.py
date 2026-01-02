{
    'name': "Printing Card Report",
    'description': "Printing Card Report",
    'author': 'Ali shan',
    'website': "http://www.eusol.net",
    'category': 'Gate Pass',
    'license': 'LGPL-3',
    'version': '0.1',
    'application': True,
    'depends': ['base','product','product_extension','card_printing'],
# __manifest__.py
    'external_dependencies': {
        'python': ['qrcode','pillow']
    },
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'template.xml',
        'views/module_report.xml',
    ],
}