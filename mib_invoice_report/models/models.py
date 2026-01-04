# -*- coding: utf-8 -*-

from odoo import models, fields, api
from reportlab.graphics import barcode
from base64 import b64encode


class mib_invoice_report(models.AbstractModel):
	_name = 'report.mib_invoice_report.mib_invoice_report'
	_description = "Report"

	@api.model
	def _get_report_values(self, docids, data=None):
		record = self.env['account.move'].browse(docids)

		return {
			'doc_ids': docids,
			'doc_model': 'account.move',
			'docs': record,
			'data': data,
			}

