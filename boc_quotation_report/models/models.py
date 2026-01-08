from odoo import models, fields, api
from num2words import num2words
from decimal import Decimal, ROUND_HALF_UP

from odoo.tools import float_round
import logging
_logger = logging.getLogger(__name__)



class BocQuotationReport(models.AbstractModel):
    _name = 'report.boc_quotation_report.boc_quotation_report'  # ← Updated
    _description = "Quotation report (show values in USD)"

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['sale.order'].sudo().browse(docids)

        converted_values = {}
        line_converted_values = {}
        usd = self.env.ref('base.USD')

        for rec in records:
            date = rec.date_order.date() if rec.date_order else fields.Date.context_today(self)

            # Debug
            print(f"Converting quotation {rec.name}: {rec.amount_total} {rec.currency_id.name} → USD on {date}")

            try:
                amount_total_usd = rec.currency_id._convert(rec.amount_total, usd, rec.company_id, date)
                amount_untaxed_usd = rec.currency_id._convert(rec.amount_untaxed, usd, rec.company_id, date)
                amount_tax_usd = rec.currency_id._convert(rec.amount_tax, usd, rec.company_id, date)
            except Exception as e:
                print(f"Total conversion failed for {rec.name}: {e}")
                amount_total_usd = rec.amount_total
                amount_untaxed_usd = rec.amount_untaxed
                amount_tax_usd = rec.amount_tax

            converted_values[rec.id] = {
                'amount_total_usd': round(float(amount_total_usd), 2),
                'amount_tax_usd': round(float(amount_tax_usd), 2),
                'amount_untaxed_usd': round(float(amount_untaxed_usd), 2),
            }

            line_converted_values[rec.id] = {}
            for line in rec.order_line:
                try:
                    discounted_price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100)
                    discounted_subtotal = discounted_price_unit * line.product_uom_qty

                    price_unit_usd = rec.currency_id._convert(discounted_price_unit, usd, rec.company_id, date, round=False)
                    price_unit_usd = float_round(price_unit_usd, precision_digits=4)
                    price_subtotal_usd = rec.currency_id._convert(discounted_subtotal, usd, rec.company_id, date)

                except Exception as e:
                    print(f"Line conversion failed for quotation {rec.name}, line {line.id}: {e}")
                    discounted_price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100)
                    discounted_subtotal = discounted_price_unit * line.product_uom_qty
                    price_unit_usd = discounted_price_unit
                    price_subtotal_usd = discounted_subtotal

                # Store converted & rounded values
                line_converted_values[rec.id][line.id] = {
                    # 'price_unit_usd': Decimal(price_unit_usd).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP),
                    'price_unit_usd': price_unit_usd,
                    'price_subtotal_usd': round(float(price_subtotal_usd), 2),
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