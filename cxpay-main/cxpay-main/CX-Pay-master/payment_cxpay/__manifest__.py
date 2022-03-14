# -*- coding: utf-8 -*-

{
    'name': 'CX Pay Payment Acquirer',
    'category': 'Accounting/Payment',
    'summary': 'Payment Acquirer: CX pay Implementation',
    'version': '13.0.0.1.3',
    'description': """CX pay Payment Acquirer""",
    'depends': ['payment', 'website_sale'],
    'data': [
        'views/payment_views.xml',
        'views/payment_authorize_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    'installable': True,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'uninstall_hook': 'uninstall_hook',
}
