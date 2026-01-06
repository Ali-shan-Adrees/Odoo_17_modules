## -*- coding: utf-8 -*-
from odoo import http
import ast
from odoo.http import request
import requests
import json
import base64
import re
from datetime import datetime
import pytz
import difflib
from odoo import api, models
from odoo import _, api, fields, models
from requests.exceptions import ConnectionError, HTTPError
import logging
_logger = logging.getLogger(__name__)
from odoo.tools.image import image_data_uri
import passlib.context

DEFAULT_CRYPT_CONTEXT = passlib.context.CryptContext(
	['pbkdf2_sha512', 'plaintext'],
	deprecated=['plaintext'],
)

class MobileAppIntegration(http.Controller):
	def _crypt_context(self):
		return DEFAULT_CRYPT_CONTEXT

	def _get_portal_access(self, user, employee):
		"""Determine which portal features the user has access to"""
		portal_access = []
		
		# Check if user has basic portal access
		has_portal_access = user.sudo().has_group('employee_hr_portal.access_to_employee_portal_custom_user')
		is_quote_manager = user.sudo().has_group('employee_hr_portal.access_to_quot_manager_custom')
		
		if has_portal_access or is_quote_manager:
			employee = employee
			
			if is_quote_manager:
				portal_access = [
					'payslips',
					'attendances',
					'absents',
					'contracts',
					'leaves',
					'advance_requests',
					'overtime_requests',
					'loan_requests',
					'missing_punchs',
					'appraisals',
					'expenses',
					'docs_communications'
				]

			else:
				portal_access.append('payslips')
				portal_access.append('attendances')
				portal_access.append('absents')
				portal_access.append('contracts')
				portal_access.append('leaves')
				portal_access.append('advance_requests')
				portal_access.append('overtime_requests')
				if hasattr(employee, 'allow_loan_request') and employee.allow_loan_request:
					portal_access.append('loan_requests')
				portal_access.append('missing_punchs')
				portal_access.append('appraisals')
				portal_access.append('expenses')
				portal_access.append('docs_communications')
		
		return portal_access

	@http.route('/odoo/api/hr/login', type='json', auth='none', csrf=False, methods=['POST'])
	def hr_user_odoo_login(self, **kwargs):
		headers = request.httprequest.headers
		provided_authorization = headers.get('Authorization')
		hr_api_configurations = request.env['hr.app.apis'].sudo().search([], limit=1)

		response = {
			'success': False,
			'message': '',
			'data': []
		}

		if not provided_authorization:
			response['message'] = 'Unauthorized Access!'
			return response
			
		if not hr_api_configurations or hr_api_configurations.token != provided_authorization.replace('Bearer','').replace(' ',''):
			response['message'] = 'Unauthorized Access!'
			return response

		request_data = json.loads(request.httprequest.data.decode('utf-8'))
		username = request_data.get('username')
		password = request_data.get('password')

		if not username or not password:
			response['message'] = 'Username and password are required!'
			return response

		try:
			request.env.cr.execute(
				"SELECT COALESCE(password, '') FROM res_users WHERE login=%s",
				[username]
			)
			[hashed] = request.env.cr.fetchone()

			request.env.cr.execute(
				"SELECT id FROM res_users WHERE login=%s",
				[username]
			)
			[user_id] = request.env.cr.fetchone()

			valid, replacement = self._crypt_context().verify_and_update(password, hashed)

			if valid:

				user = request.env['res.users'].sudo().browse(int(user_id))
				employee = False
				if user:
					employee = user.employee_id.sudo()
					if not employee:
						employee = request.env['hr.employee'].sudo().search([('user_id','=',user.id)],limit=1)

				if user and employee:
					company = user.company_id.sudo()
					response['data'] = {
						'employee_data': {},
						'company_data': {},
						'portal_access': []
					}

					user_type = 'user'
					is_quote_manager = user.sudo().has_group('employee_hr_portal.access_to_quot_manager_custom')
					if is_quote_manager:
						user_type = 'manager'

					response['data']['employee_data'] = {
						'id': employee.id,
						'user_type':user_type,
						'name': employee.name,
						'department': {
							'id': employee.department_id.id,
							'name': employee.department_id.name
						} if employee.department_id else None,
						'job_position': {
							'id': employee.job_id.id,
							'name': employee.job_id.name
						} if employee.job_id else None,
						'manager': {
							'id': employee.parent_id.id,
							'name': employee.parent_id.name
						} if employee.parent_id else None,
						'work_schedule': employee.resource_calendar_id.name if employee.resource_calendar_id else None,
						'work_email': employee.work_email,
						'mobile_phone': employee.mobile_phone,
						'work_phone': employee.work_phone,
						'employee_id': employee.registration_number,
						'image': image_data_uri(employee.image_1920) if employee.image_1920 else None,
						'gender': employee.gender,
						'marital_status': employee.marital,
						'birthday': employee.birthday if employee.birthday else None,
						'identification_id': employee.identification_id,
						'passport_id': employee.passport_id,
						'bank_accounts': [{
							'bank_name': acc.bank_id.name,
							'acc_number': acc.acc_number
						} for acc in employee.bank_account_id] if employee.bank_account_id else [],
						'address': {
							'street': employee.address_home_id.street,
							'street2': employee.address_home_id.street2,
							'city': employee.address_home_id.city,
							'state': employee.address_home_id.state_id.name,
							'country': employee.address_home_id.country_id.name,
							'zip': employee.address_home_id.zip
						} if employee.address_home_id else None
					}
					
					# Get company data
					response['data']['company_data'] = {
						'id': company.id,
						'name': company.name,
						'email': company.email,
						'phone': company.phone,
						'website': company.website,
						'vat': company.vat,
						'street': company.street,
						'street2': company.street2,
						'city': company.city,
						'state': company.state_id.name if company.state_id else None,
						'country': company.country_id.name if company.country_id else None,
						'zip': company.zip,
						'logo': image_data_uri(company.logo) if company.logo else None,
						'currency': {
							'id': company.currency_id.id,
							'name': company.currency_id.name,
							'symbol': company.currency_id.symbol
						} if company.currency_id else None
					}
					response['data']['portal_access'] = self._get_portal_access(user, employee)
					response['success'] = True
					response['message'] = 'Login Successful!'
				else:
					response['message'] = 'Employee Not Found In Related User!'
			else:
				response['message'] = 'Invalid username or password!'
		except Exception as e:
			_logger.error("Error in HR login API: %s", str(e))
			response['message'] = 'An error occurred during login. Please try again.'
		return response