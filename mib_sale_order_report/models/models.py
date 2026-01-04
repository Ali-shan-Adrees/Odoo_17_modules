# -*- coding: utf-8 -*-

from odoo import models, fields, api
from reportlab.graphics import barcode
from base64 import b64encode


class mib_sale_order_report(models.AbstractModel):
	_name = 'report.mib_sale_order_report.mib_sale_order_report'
	_description = "Report"

	@api.model
	def _get_report_values(self, docids, data=None):
		record = self.env['sale.order'].browse(docids)

		return {
			'doc_ids': docids,
			'doc_model': 'sale.order',
			'docs': record,
			'data': data,
			}

