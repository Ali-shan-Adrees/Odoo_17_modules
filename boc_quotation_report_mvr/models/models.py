from odoo import models, fields, api
from num2words import num2words
from decimal import Decimal


class BocQuotationReportMVR(models.AbstractModel):
	_name = 'report.boc_quotation_report_mvr.boc_quotation_report_mvr'  # ← Updated
	_description = "Quotation report (show values in MVR)"

	@api.model
	def _get_report_values(self, docids, data=None):
		records = self.env['sale.order'].sudo().browse(docids)

		converted_values = {}
		line_converted_values = {}
		mvr = self.env.ref('base.MVR')

		for rec in records:
			date = rec.date_order.date() if rec.date_order else fields.Date.context_today(self)

			# Debug
			print(f"Converting quotation {rec.name}: {rec.amount_total} {rec.currency_id.name} → MVR on {date}")

			try:
				amount_total_mvr = rec.currency_id._convert(rec.amount_total, mvr, rec.company_id, date)
				amount_untaxed_mvr = rec.currency_id._convert(rec.amount_untaxed, mvr, rec.company_id, date)
				amount_tax_mvr = rec.currency_id._convert(rec.amount_tax, mvr, rec.company_id, date)
			except Exception as e:
				print(f"Total conversion failed for {rec.name}: {e}")
				amount_total_mvr = rec.amount_total
				amount_untaxed_mvr = rec.amount_untaxed
				amount_tax_mvr = rec.amount_tax

			converted_values[rec.id] = {
				'amount_total_mvr': round(float(amount_total_mvr), 2),
				'amount_tax_mvr': round(float(amount_tax_mvr), 2),
				'amount_untaxed_mvr': round(float(amount_untaxed_mvr), 2),
			}

			line_converted_values[rec.id] = {}
			for line in rec.order_line:
				try:
					discounted_price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100)
					discounted_subtotal = discounted_price_unit * line.product_uom_qty

					price_unit_mvr = rec.currency_id._convert(discounted_price_unit, mvr, rec.company_id, date)
					price_subtotal_mvr = rec.currency_id._convert(discounted_subtotal, mvr, rec.company_id, date)

				except Exception as e:
					print(f"Line conversion failed for quotation {rec.name}, line {line.id}: {e}")
					discounted_price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100)
					discounted_subtotal = discounted_price_unit * line.product_uom_qty
					price_unit_mvr = discounted_price_unit
					price_subtotal_mvr = discounted_subtotal

				# Store values rounded to 2 decimals
				line_converted_values[rec.id][line.id] = {
					'price_unit_mvr': round(float(price_unit_mvr), 2),
					'price_subtotal_mvr': round(float(price_subtotal_mvr), 2),
				}


		return {
			'doc_ids': docids,
			'docs': records,
			'convert_to_words': self.convert_to_words,
			'converted_values': converted_values,
			'line_converted_values': line_converted_values,
		}

	@staticmethod
	def convert_to_words(amount):
		try:
			amount = Decimal(str(amount))
			integer_part = int(amount)
			fractional_part = round((amount - integer_part) * 100)
			integer_words = num2words(integer_part, lang='en')
			if fractional_part == 0:
				result = f"{integer_words.title()}"
			else:
				fractional_words = num2words(fractional_part, lang='en')
				result = f"{integer_words.title()} and {fractional_words.title()}"
			return result
		except Exception as e:
			return f"Conversion Error: {str(e)}"