# -*- coding: utf-8 -*-
import os
import binascii
from odoo import models, fields, api,_
from odoo.exceptions import ValidationError, UserError


class HrAppApis(models.Model):
	_name = 'hr.app.apis'
	_description = 'HR App APIs'
	_inherit = ['mail.thread', 'mail.activity.mixin']

	name = fields.Char("Name", tracking=True, required=True)
	token = fields.Char(string='Header Token', readonly=True, copy=False)

	@api.model
	def create(self, vals):
		records = self.env['hr.app.apis'].sudo().search([])
		if len(records) >= 1:
			raise ValidationError("Sorry! You Cannot Create More Than 1 Record!")
		else:
			vals['token'] = binascii.hexlify(os.urandom(20)).decode()
		return super(HrAppApis, self).create(vals)