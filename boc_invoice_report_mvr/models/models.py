from odoo import models, fields, api
from num2words import num2words
from decimal import Decimal


class BocInvoiceReportMVR(models.AbstractModel):
    _name = 'report.boc_invoice_report_mvr.boc_invoice_report_mvr'
    _description = "Invoice report (show values in MVR)"

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

        # --- Convert to MVR using Odoo's official method ---
        converted_values = {}
        line_converted_values = {}
        mvr_currency = self.env.ref('base.MVR')

        for rec in records:
            date = rec.invoice_date or fields.Date.context_today(self)

            # Debug print
            print(f"Converting invoice {rec.name}: {rec.amount_total} {rec.currency_id.name} → MVR on {date}")

            # --- Convert invoice totals ---
            try:
                amount_total_mvr = rec.currency_id._convert(rec.amount_total, mvr_currency, rec.company_id, date)
                amount_tax_mvr = rec.currency_id._convert(rec.amount_tax, mvr_currency, rec.company_id, date)
                amount_untaxed_mvr = rec.currency_id._convert(rec.amount_untaxed, mvr_currency, rec.company_id, date)
            except Exception as e:
                print(f"Total conversion failed for {rec.name}: {e}")
                amount_total_mvr = rec.amount_total
                amount_tax_mvr = rec.amount_tax
                amount_untaxed_mvr = rec.amount_untaxed

            converted_values[rec.id] = {
                'amount_total_mvr': round(float(amount_total_mvr), 2),
                'amount_tax_mvr': round(float(amount_tax_mvr), 2),
                'amount_untaxed_mvr': round(float(amount_untaxed_mvr), 2),
            }

            line_converted_values[rec.id] = {}
            for line in rec.invoice_line_ids:
                try:
                    discounted_price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100)
                    discounted_subtotal = discounted_price_unit * line.quantity

                    price_unit_mvr = rec.currency_id._convert(discounted_price_unit, mvr_currency, rec.company_id, date)
                    price_subtotal_mvr = rec.currency_id._convert(discounted_subtotal, mvr_currency, rec.company_id, date)

                except Exception as e:
                    print(f"Line conversion failed for invoice {rec.name}, line {line.id}: {e}")
                    discounted_price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100)
                    discounted_subtotal = discounted_price_unit * line.quantity
                    price_unit_mvr = discounted_price_unit
                    price_subtotal_mvr = discounted_subtotal

                line_converted_values[rec.id][line.id] = {
                    'price_unit_mvr': round(float(price_unit_mvr), 2),
                    'price_subtotal_mvr': round(float(price_subtotal_mvr), 2),
                }


        # --- Related data (credit notes) ---
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