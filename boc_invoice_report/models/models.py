from odoo import models, fields, api
from num2words import num2words
from decimal import Decimal

from odoo.tools import float_round
import logging
_logger = logging.getLogger(__name__)

class BocInvoiceReport(models.AbstractModel):
    _name = 'report.boc_invoice_report.boc_invoice_report'
    _description = "Invoice report (show values in USD)"

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['account.move'].sudo().browse(docids)

        sale_orders = {}
        delivery_orders = {}
        payment_terms = {}

        for record in records:
            sos = self.env['sale.order'].sudo().search([('name', '=', record.invoice_origin)])
            sale_orders[record.id] = ', '.join(sos.mapped('name')) if sos else 'N/A'

            related_sales = self.env['sale.order'].sudo().search([('name', '=', record.invoice_origin)])
            related_deliveries = self.env['stock.picking'].sudo().search([
                ('picking_type_code', '!=', 'incoming'),
                ('sale_id', 'in', related_sales.ids),
                ('state', '!=', 'cancel')
            ])
            delivery_orders[record.id] = ', '.join(related_deliveries.mapped('name')) if related_deliveries else 'N/A'
            payment_terms[record.id] = ', '.join(related_sales.mapped('payment_term_id.name')) if related_sales else 'N/A'

        converted_values = {}
        line_converted_values = {}  # NEW: for line-level USD conversion
        usd = self.env.ref('base.USD')

        for rec in records:
            date = rec.invoice_date or fields.Date.context_today(self)

            # Debug print (optional)
            print(f"Converting invoice {rec.name}: {rec.amount_total} {rec.currency_id.name} → USD on {date}")

            # --- Convert invoice totals ---
            try:
                amount_total_usd = rec.currency_id._convert(rec.amount_total, usd, rec.company_id, date)
                amount_tax_usd = rec.currency_id._convert(rec.amount_tax, usd, rec.company_id, date)
                amount_untaxed_usd = rec.currency_id._convert(rec.amount_untaxed, usd, rec.company_id, date)
            except Exception as e:
                print(f"Total conversion failed for {rec.name}: {e}")
                amount_total_usd = rec.amount_total
                amount_tax_usd = rec.amount_tax
                amount_untaxed_usd = rec.amount_untaxed

            # Round and store
            converted_values[rec.id] = {
                'amount_total_usd': round(float(amount_total_usd), 2),
                'amount_tax_usd': round(float(amount_tax_usd), 2),
                'amount_untaxed_usd': round(float(amount_untaxed_usd), 2),
            }

            line_converted_values[rec.id] = {}
            for line in rec.invoice_line_ids:
                try:
                    discounted_price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100)
                    discounted_subtotal = discounted_price_unit * line.quantity

                    price_unit_usd = rec.currency_id._convert(discounted_price_unit, usd, rec.company_id, date, round=False)
                    price_unit_usd = float_round(price_unit_usd, precision_digits=4)
                    price_subtotal_usd = rec.currency_id._convert(discounted_subtotal, usd, rec.company_id, date)

                except Exception as e:
                    print(f"Line conversion failed for invoice {rec.name}, line {line.id}: {e}")
                    discounted_price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100)
                    discounted_subtotal = discounted_price_unit * line.quantity
                    price_unit_usd = discounted_price_unit
                    price_subtotal_usd = discounted_subtotal
                line_converted_values[rec.id][line.id] = {
                    # 'price_unit_usd': round(float(price_unit_usd), 4),
                    'price_unit_usd': price_unit_usd,
                    'price_subtotal_usd': round(float(price_subtotal_usd), 2),
                }


        # --- Related data (credit notes, etc.) ---
        related_data = []
        related_invoice = None
        sale_order = None
        for rec in records:
            if rec.move_type == 'out_refund':
                related_invoice = rec.reversed_entry_id
                if not related_invoice and rec.partner_id:
                    related_invoice = self.env['account.move'].sudo().search(
                        [('partner_id', '=', rec.partner_id.id), ('move_type', '=', 'out_invoice')],
                        limit=1
                    )
                sale_order = related_invoice.invoice_origin and self.env['sale.order'].sudo().search(
                    [('name', '=', related_invoice.invoice_origin)], limit=1) or None

        product_quantities = {}
        if related_invoice:
            for line in related_invoice.invoice_line_ids:
                product_quantities[line.product_id.id] = line.quantity

        related_data.append({
            'credit_note': rec.name,
            'related_invoice': related_invoice.name if related_invoice else '',
            'sale_order': sale_order.name if sale_order else '',
            'order_date': sale_order.date_order if sale_order else '',
            'product_quantities': product_quantities,
        })

        return {
            'doc_ids': docids,
            'docs': records,
            'convert_to_words': self.convert_to_words,
            'sale_orders': sale_orders,
            'delivery_orders': delivery_orders,
            'payment_terms': payment_terms,
            'invoice_date': related_invoice.invoice_date if related_invoice else '',
            'company_id': records.company_id,
            'invoice_line_ids': records.invoice_line_ids,
            'related_data': related_data,
            'converted_values': converted_values,
            'line_converted_values': line_converted_values,  # <-- for QWeb
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