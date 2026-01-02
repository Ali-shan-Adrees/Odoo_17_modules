# #-*- coding:utf-8 -*-

import os
from datetime import date, datetime, timedelta
import time
from odoo import api, models, fields
from odoo.exceptions import ValidationError, UserError
import base64

class gatepass(models.TransientModel):
    _name = "card.printing.report"
    _description = "Card Printing Report"

    product_id = fields.Many2one('product.template', string="Product")
    # card_printing_id isn't used - keeping for potential future use
    card_printing_id = fields.Many2one('card.printing', string="Card Printing")

    def generate_report(self):
        data = {}
        data['form'] = self.read(['product_id'])[0]
        return self._print_report(data)

    def _print_report(self, data):
        data['form'].update(self.read(['product_id'])[0])
        self.card_printing_id.write({
            'is_report_created': True,
            'reprint_approved': False,  
        })
        return self.env.ref('card_printing_report.card_printing_report_id').report_action(self, data=data)