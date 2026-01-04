# -*- coding: utf-8 -*-

from odoo import models, fields, api
from reportlab.graphics import barcode
from base64 import b64encode


class mib_delivery_report(models.AbstractModel):
	_name = 'report.mib_delivery_report.mib_delivery_report'
	_description = "Report"

	@api.model
	def _get_report_values(self, docids, data=None):
		record = self.env['stock.picking'].browse(docids)

		return {
			'doc_ids': docids,
			'doc_model': 'stock.picking',
			'docs': record,
			'data': data,
			}