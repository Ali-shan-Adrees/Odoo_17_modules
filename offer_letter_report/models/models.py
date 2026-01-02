from odoo import models, fields, api


class offer_letter_report(models.AbstractModel):
	_name = 'report.offer_letter_report.offer_letter_report'  
	_description = "Offer Letter Report"

	@api.model
	def _get_report_values(self, docids, data=None):
		letters = self.env['hr.offer.letter'].browse(docids)
		return {
			'doc_ids': docids,
			'doc_model': 'hr.offer.letter',
			'docs': letters
		}