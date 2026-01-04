from odoo import models, api, fields, _


class invoice_report(models.Model):
	_name = 'report.invoice_report.invoice_report'
	_description = "Report"

	@api.model
	def _get_report_values(self, docids, data=None):
		record = self.env['account.move'].browse(docids)
		# bank = self.env['account.journal'].search([('type','=','bank'),(('boolean_type','=',True))])

		
		# bank_acc_num1 =''
		# bank_acc_num2 =''
		# for x in bank:
		# 	bank_acc_num1 =''
		# 	bank_acc_num2 =''
		# 	if x.bank_acc_number:
		# 		bank_acc = x.bank_acc_number.split()
		# 		bank_acc_num1 = bank_acc[0]
		# 		bank_acc_num2 = bank_acc[2]
		# 	else:
		# 		bank_acc = ''

		return {
			'doc_ids': docids,
			'doc_model': 'account.move',
			'docs': record,
			'data': data,
			# 'bank': bank,
			# 'bank_acc_num1':bank_acc_num1,
			# 'bank_acc_num2':bank_acc_num2,
			}