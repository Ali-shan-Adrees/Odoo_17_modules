# -*- coding: utf-8 -*-
# from odoo import http


# class PerfomaInvoiceReport(http.Controller):
#     @http.route('/perfoma_invoice_report/perfoma_invoice_report/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/perfoma_invoice_report/perfoma_invoice_report/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('perfoma_invoice_report.listing', {
#             'root': '/perfoma_invoice_report/perfoma_invoice_report',
#             'objects': http.request.env['perfoma_invoice_report.perfoma_invoice_report'].search([]),
#         })

#     @http.route('/perfoma_invoice_report/perfoma_invoice_report/objects/<model("perfoma_invoice_report.perfoma_invoice_report"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('perfoma_invoice_report.object', {
#             'object': obj
#         })
