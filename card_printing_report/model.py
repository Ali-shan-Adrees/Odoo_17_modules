import qrcode
import base64
from io import BytesIO
from odoo import models, fields,api


class card_printing_report(models.AbstractModel):
    _name = 'report.card_printing_report.card_printing_report'
    _description = "Card Printing Report"

    def generate_qr_code(self, url):
        """Generate QR code as base64 for the portal URL"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=4,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    @api.model
    def _get_report_values(self, docids, data=None):
        record_wizard = self.env['card.printing.report'].browse(self.env.context.get('active_ids'))
        product_id = record_wizard.product_id

        record = self.env['product.conversion'].search([
            ('product_id', '=', product_id.id),
            ('state', '=', 'validate')
        ])

        main_product_list = []
        for rec in record:
            for line in rec.card_line_ids:
                portal_url = line.product_id.generate_portal_authentication_link()
                qr_code_base64 = self.generate_qr_code(portal_url)
                qr_code_uri = f"data:image/png;base64,{qr_code_base64}"

                main_product_list.append({
                    'product_id': line.product_id.name,
                    'maturity_date': line.maturity_date,
                    'qr_code': qr_code_uri,
                    'tag_number': line.indexed_number,
                })

        return {
            'doc_ids': docids,
            'doc_model': 'product.conversion',
            'product_id': product_id,
            'main_product_list': main_product_list,
        }