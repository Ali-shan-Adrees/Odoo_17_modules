from odoo import models, api
from odoo.exceptions import UserError
from odoo import api, models
from odoo.exceptions import ValidationError

class DollarPurchaseReceiptReport(models.AbstractModel):
	_name = 'report.dollar_purchase_report.dollar_purchase_report'  # Must match your report_name in XML
	_description = 'Dollar Purchase Receipt Report'

	@api.model
	def _get_report_values(self, docids, data=None):
		docs = self.env['dollar.purchase'].browse(docids)
		for doc in docs:
			if doc.state != 'validate':
				raise ValidationError('You can only print this receipt when the record is in the validated state.')
		return {
			'doc_ids': docids,
			'doc_model': 'dollar.purchase',
			'docs': docs,
			# Add any other data your QWeb template needs here
		}