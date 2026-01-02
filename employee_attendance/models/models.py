from odoo import models, fields, api
from datetime import timedelta
import pytz
from datetime import datetime, time as datetime_time
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class HrAttendance(models.Model):
	_inherit = 'hr.attendance'
	over_time = fields.Float(string="Overtime", tracking=True, compute="_compute_overtime")
	early_left = fields.Float(string="Early Left", tracking=True)
	late_arrival = fields.Float(string="Late Arrival", tracking=True)
	badge_id = fields.Char(related='employee_id.barcode', string='Badge ID', readonly=True)
	total_late_arrival = fields.Float(
		compute="_compute_total_late_arrival",
		store=True
	)
	employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True, copy=False)
	unauthorized_leave = fields.Integer(
		string='Unauthorized Leave Days',
		compute='_compute_unauthorized_leave',
		store=True
	)
	late_days = fields.Integer(
		string='Late Arrival Days',
		compute='_compute_late_days',
		store=True
	)

	@api.model
	def search(self, domain, offset=0, limit=None, order=None):
		current_user = self.env.user
		new_domain = []
		if not current_user.has_group('employee_attendance.show_all_attendance'):
			new_domain = ['|',
				('employee_id.user_id', '=', current_user.id),
				('employee_id.parent_id.user_id', '=', current_user.id)
			]
		if new_domain:
		   # domain = domain + ['&'] + new_domain
		   domain = domain + new_domain
		return super(HrAttendance, self).search(domain = domain, offset=offset, limit=limit, order=order)


	@api.depends('late_arrival')
	def _compute_late_days(self):
		for record in self:
			# Count this day as a late day if late_arrival is greater than 0
			record.late_days = 1 if record.late_arrival > 0 else 0

	@api.depends('check_in', 'check_out', 'employee_id.resource_calendar_id')
	def _compute_unauthorized_leave(self):
		for attendance in self:
			attendance.unauthorized_leave = 0  # Default value
			# Skip if employee has no work schedule
			if not attendance.employee_id.resource_calendar_id:
				continue
			# Extract date from check_in (if exists)
			date = attendance.check_in and fields.Date.to_date(attendance.check_in)
			if not date:
				continue
			# Get the weekday (0=Monday to 6=Sunday) as a string
			weekday = str(date.weekday())
			calendar = attendance.employee_id.resource_calendar_id
			# FIXED: Use search_count instead of filtered to avoid cache miss error
			try:
				is_working_day = self.env['resource.calendar.attendance'].search_count([
					('calendar_id', '=', calendar.id),
					('dayofweek', '=', weekday)
				]) > 0
			except Exception as e:
				_logger.error(f"Error checking working day: {e}")
				is_working_day = False
			# FIXED LOGIC: Check if this is an absence record
			# We'll consider it unauthorized leave if:
			# 1. It's a working day
			# 2. No check_out time exists
			# 3. Check_in is at start of day (within 5 minutes)
			if is_working_day and not attendance.check_out:
				# Get the start of the day in UTC
				start_of_day = fields.Datetime.to_datetime(date)
				# Calculate the time difference
				time_diff = attendance.check_in - start_of_day
				# If check_in is within the first 5 minutes of the day, consider it an absence record
				if time_diff <= timedelta(minutes=5):
					attendance.unauthorized_leave = 1

	@api.constrains('check_in', 'check_out', 'employee_id')
	def _check_validity(self):
		if not self.env.context.get('synch_ignore_constraints', False):
			super(HrAttendance, self)._check_validity()

	def convert_datetime_to_float(self, dt):
		"""Convert datetime to float (e.g., 09:30 → 9.5)"""
		return dt.hour + dt.minute / 60.0

	@api.depends("check_in", "check_out", "employee_id")
	def _compute_overtime(self):
		user_tz = self.env.user.tz or "UTC"
		tz = pytz.timezone(user_tz)
		for rec in self:
			portal_overtime_requests = self.env['hr.overtime.requests'].sudo().search([
				('employee_id', '=', rec.employee_id.id),
				('requested_date', '=', (rec.check_in + timedelta(hours=5)).date()),
				('state', 'in', ['approve', 'attendance_updated'])
			], limit=1)
			if portal_overtime_requests:
				portal_overtime_requests.state = 'attendance_updated'
				overtime = 0.0
				early_left = 0.0
				late_arrival = 0.0
				rec.over_time = 0.0
				rec.early_left = 0.0
				rec.late_arrival = 0.0
				if rec.check_in and rec.check_out and rec.employee_id:
					check_in_dt = rec.check_in.replace(tzinfo=pytz.UTC).astimezone(
						tz) if rec.check_in.tzinfo is None else rec.check_in.astimezone(tz)
					check_out_dt = rec.check_out.replace(tzinfo=pytz.UTC).astimezone(
						tz) if rec.check_out.tzinfo is None else rec.check_out.astimezone(tz)
					check_in_time = self.convert_datetime_to_float(check_in_dt)
					check_out_time = self.convert_datetime_to_float(check_out_dt)
					check_in_day = str(check_in_dt.weekday())
					if rec.employee_id.resource_calendar_id:
						calendar = rec.employee_id.resource_calendar_id
						# FIXED: Use search instead of filtered to avoid cache miss
						calendar_attendances = self.env['resource.calendar.attendance'].search([
							('calendar_id', '=', calendar.id),
							('dayofweek', '=', check_in_day)
						])
						for attendance in calendar_attendances:
							if check_in_time > attendance.hour_from:
								late_arrival = check_in_time - attendance.hour_from
							if check_out_time < attendance.hour_to:
								early_left = attendance.hour_to - check_out_time
							if check_out_time > attendance.hour_to:
								overtime = check_out_time - attendance.hour_to
					rec.over_time = round(overtime, 2)
					rec.early_left = round(early_left, 2)
					rec.late_arrival = round(late_arrival, 2)
			else:
				early_left = 0.0
				late_arrival = 0.0
				rec.over_time = 0.0
				rec.early_left = 0.0
				rec.late_arrival = 0.0
				if rec.check_in and rec.check_out and rec.employee_id:
					check_in_dt = rec.check_in.replace(tzinfo=pytz.UTC).astimezone(
						tz) if rec.check_in.tzinfo is None else rec.check_in.astimezone(tz)
					check_out_dt = rec.check_out.replace(tzinfo=pytz.UTC).astimezone(
						tz) if rec.check_out.tzinfo is None else rec.check_out.astimezone(tz)
					check_in_time = self.convert_datetime_to_float(check_in_dt)
					check_out_time = self.convert_datetime_to_float(check_out_dt)
					check_in_day = str(check_in_dt.weekday())
					if rec.employee_id.resource_calendar_id:
						calendar = rec.employee_id.resource_calendar_id
						# FIXED: Use search instead of filtered to avoid cache miss
						calendar_attendances = self.env['resource.calendar.attendance'].search([
							('calendar_id', '=', calendar.id),
							('dayofweek', '=', check_in_day)
						])
						for attendance in calendar_attendances:
							if check_in_time > attendance.hour_from:
								late_arrival = check_in_time - attendance.hour_from
							if check_out_time < attendance.hour_to:
								early_left = attendance.hour_to - check_out_time
					rec.early_left = round(early_left, 2)
					rec.late_arrival = round(late_arrival, 2)

	@api.depends("late_arrival")
	def _compute_total_late_arrival(self):
		for employee in self:
			total_late_hours = sum(employee.mapped("late_arrival"))  # Get total hours
			employee.total_late_arrival = total_late_hours * 60  # Convert to minutes


# Define the HrEmployee model to add the isExecutive field
class HrEmployee(models.Model):
	_inherit = 'hr.employee'
	isExecutive = fields.Boolean('Is Executive', default=False)
	give_pension = fields.Boolean(string="Give Pension", default=False)


class HrPayslip(models.Model):
	_inherit = 'hr.payslip'
	total_absences = fields.Integer('Unauthorized Absences', readonly=True)
	total_late_arrival = fields.Float('Late Arrival (Minutes)', readonly=True)
	late_days = fields.Integer('Late Arrival Days', readonly=True)
	total_overall_absences = fields.Float('Total Absences', readonly=True)
	emergency_leave_days = fields.Integer('Emergency Leave Days', readonly=True)

	date_from = fields.Date(
		string='From',
		readonly=False,
		required=True,
		default=lambda self: fields.Date.to_string(
			fields.Date.today().replace(day=1)
		),
		states={'done': [('readonly', True)], 'paid': [('readonly', True)], 'cancel': [('readonly', True)]}
	)
	date_to = fields.Date(
		string='To',
		readonly=False,
		required=True,
		precompute=True,
		# compute="_compute_date_to",
		store=True,
		states={'done': [('readonly', True)], 'paid': [('readonly', True)], 'cancel': [('readonly', True)]}
	)
	employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True, copy=False)

	@api.model
	def search(self, domain, offset=0, limit=None, order=None):
		current_user = self.env.user
		new_domain = []
		if not current_user.has_group('employee_attendance.show_all_attendance'):
				new_domain = [
			('state', '=', 'paid'),
			('employee_id.user_id', '=', current_user.id),
		]
		if new_domain:
		   domain = ['&'] + domain + new_domain
		return super().search(domain = domain, offset=offset, limit=limit, order=order)

	# @api.model
	# def search(self, args=None, offset=0, limit=None, order=None, count=False):
	#     current_user = self.env.user
	#     domain = []
	#     if not current_user.has_group('employee_attendance.show_all_payslip'):
	#         domain = [('employee_id.parent_id.user_id', '=', current_user.id)]

	#     if args:
	#         domain = ['&'] + domain + args if domain else args

	#     return super(HrPayslip, self).search(domain, offset=offset, limit=limit, order=order, count=count)

	# @api.depends('date_from')
	# def _compute_date_to(self):
	# 	for payslip in self:
	# 		if payslip.date_from:
	# 			# Always set date_to to the 19th of the next month
	# 			payslip.date_to = payslip.date_from + relativedelta(months=+1, day=1)
	# 		else:
	# 			payslip.date_to = False

	def _get_or_create_unauth_leave_type(self):
		"""Get or create unauthorized leave work entry type"""
		unauth_type = self.env['hr.work.entry.type'].search([
			('code', '=', 'UNAUTHLEAV')
		], limit=1)
		if not unauth_type:
			unauth_type = self.env['hr.work.entry.type'].create({
				'name': 'Unauthorized Leave',
				'code': 'UNAUTHLEAV',
				'is_leave': True
			})
		return unauth_type

	def _get_or_create_emergency_leave_type(self):
		"""Get or create emergency leave work entry type"""
		emergency_type = self.env['hr.work.entry.type'].search([
			('code', '=', 'EMERGENCY')
		], limit=1)
		if not emergency_type:
			emergency_type = self.env['hr.work.entry.type'].create({
				'name': 'Emergency Leave',
				'code': 'EMERGENCY',
				'is_leave': True
			})
		return emergency_type

	def compute_sheet(self):
		"""
		Override the standard compute_sheet method to include custom calculations.
		This method ensures unauthorized absences are not counted for executives.
		Also handles emergency leaves by deducting them from total absences.
		"""
		for payslip in self:
			employee = payslip.employee_id
			contract = payslip.contract_id
			if not contract:
				continue

			calculated_total_absences = 0
			calculated_total_late_minutes = 0.0
			calculated_late_days = 0
			calculated_emergency_leaves = 0  # Track emergency leaves

			employee_tz_str = employee.tz or 'UTC'
			try:
				tz = pytz.timezone(employee_tz_str)
			except pytz.exceptions.UnknownTimeZoneError:
				tz = pytz.utc

			calendar = contract.resource_calendar_id
			if not calendar:
				continue

			current_date = payslip.date_from
			while current_date <= payslip.date_to:
				day_start_utc = pytz.utc.localize(datetime.combine(current_date, datetime.min.time()))
				day_end_utc = pytz.utc.localize(datetime.combine(current_date, datetime.max.time()))

				work_hours = calendar.get_work_hours_count(
					day_start_utc,
					day_end_utc,
					compute_leaves=False
				)

				if work_hours > 0:
					search_day_start_utc_naive = day_start_utc.replace(tzinfo=None)
					search_day_end_utc_naive = day_end_utc.replace(tzinfo=None)

					attendance = self.env['hr.attendance'].search([
						('employee_id', '=', employee.id),
						('check_in', '>=', search_day_start_utc_naive),
						('check_in', '<=', search_day_end_utc_naive)
					], order='check_in asc', limit=1)

					# Check for any validated leave
					valid_leave = self.env['hr.leave'].search([
						('employee_id', '=', employee.id),
						('date_from', '<=', search_day_end_utc_naive),
						('date_to', '>=', search_day_start_utc_naive),
						('state', '=', 'validate')
					], limit=1)

					# Check specifically for emergency leave
					emergency_leave = False
					if valid_leave:
						# Check if this is an emergency leave by work entry type
						emergency_leave = self.env['hr.leave'].search([
							('employee_id', '=', employee.id),
							('date_from', '<=', search_day_end_utc_naive),
							('date_to', '>=', search_day_start_utc_naive),
							('state', '=', 'validate'),
							('holiday_status_id.work_entry_type_id.code', '=', 'EMERGENCY')
						], limit=1)

					# Only count unauthorized absences for non-executives
					# Don't count if there's emergency leave
					if not attendance and not valid_leave and not employee.isExecutive:
						calculated_total_absences += 1
					elif emergency_leave:
						# Count this as an emergency leave day
						calculated_emergency_leaves += 1
					elif attendance:
						employee_late_arrival_hours = getattr(attendance, 'late_arrival', 0.0)
						if employee_late_arrival_hours > 0:
							calculated_late_days += 1
							calculated_total_late_minutes += employee_late_arrival_hours * 60

				current_date += timedelta(days=1)

			# Update unauthorized leave days (subtract emergency leaves)
			net_unauthorized_absences = max(0, calculated_total_absences - calculated_emergency_leaves)
			self._update_unauth_leave_days(payslip, net_unauthorized_absences)

			# Create/update emergency leave worked days line
			self._update_emergency_leave_days(payslip, calculated_emergency_leaves)

			# Calculate total overall absences including emergency leaves
			current_total_overall_absences = sum(
				line.number_of_days for line in payslip.worked_days_line_ids
				if line.work_entry_type_id and getattr(line.work_entry_type_id, 'is_leave', False)
			)

			write_vals = {
				'total_absences': net_unauthorized_absences,
				'total_late_arrival': calculated_total_late_minutes,
				'late_days': calculated_late_days,
				'emergency_leave_days': calculated_emergency_leaves,
				'total_overall_absences': current_total_overall_absences
			}
			payslip.write(write_vals)

		res = super(HrPayslip, self).compute_sheet()
		return res

	def _update_unauth_leave_days(self, payslip, days):
		"""Create/update unauthorized leave worked days line"""
		unauth_type = self._get_or_create_unauth_leave_type()
		line = payslip.worked_days_line_ids.filtered(
			lambda l: l.work_entry_type_id == unauth_type
		)
		if line:
			line.write({'number_of_days': days})
		else:
			self.env['hr.payslip.worked_days'].create({
				'payslip_id': payslip.id,
				'name': 'Unauthorized Absences',
				'code': 'UNAUTHLEAV',
				'work_entry_type_id': unauth_type.id,
				'number_of_days': days,
			})

	def _update_emergency_leave_days(self, payslip, days):
		"""Create/update emergency leave worked days line"""
		if days <= 0:
			return

		emergency_type = self._get_or_create_emergency_leave_type()
		line = payslip.worked_days_line_ids.filtered(
			lambda l: l.work_entry_type_id == emergency_type
		)

		if line:
			line.write({'number_of_days': days})
		else:
			self.env['hr.payslip.worked_days'].create({
				'payslip_id': payslip.id,
				'name': 'Emergency Leaves',
				'code': 'EMERGENCY',
				'work_entry_type_id': emergency_type.id,
				'number_of_days': days,
			})

	def _get_payslip_lines(self):
		"""Inject late arrival into salary rules"""
		lines = super()._get_payslip_lines()
		late_code = 'LATE'
		for line in lines:
			if line.get('code') == late_code:
				line['amount'] = self.total_late_arrival
		return lines

# class HrLeaveAllocatoin(models.Model):
# 	_inherit = 'hr.leave.allocation'

# 	@api.model
# 	def search(self, args=None, offset=0, limit=None, order=None, count=False):
# 		current_user = self.env.user
# 		domain = []
# 		if not current_user.has_group('employee_attendance.show_all_leave_allocation'):
# 			domain = ['|',
# 				('employee_ids.user_id', '=', current_user.id),
# 				('employee_ids.parent_id.user_id', '=', current_user.id)
# 			]
# 		if args:
# 			domain = ['&'] + domain + args if domain else args
# 		return super(HrLeaveAllocatoin, self).search(domain, offset=offset, limit=limit, order=order, count=count)

class HrContract(models.Model):
	_inherit = 'hr.contract'
	break_hours = fields.Float(string="Break Hours per Day", default=1.5)