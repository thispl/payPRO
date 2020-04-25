# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe import _
from frappe.utils import formatdate, format_datetime, getdate, get_datetime, nowdate, flt, cstr, add_days, today
from frappe.model.document import Document
from frappe.desk.form import assign_to
from paypro.paypro.doctype.employee.employee import get_holiday_list_for_employee

class EmployeeBoardingController(Document):
	'''
		Create the project and the task for the boarding process
		Assign to the concerned person and roles as per the onboarding/separation template
	'''
	def validate(self):
		# remove the task if linked before submitting the form
		if self.amended_from:
			for activity in self.activities:
				activity.task = ''

	def on_submit(self):
		# create the project for the given employee onboarding
		project_name = _(self.doctype) + " : "
		if self.doctype == "Employee Onboarding":
			project_name += self.job_applicant
		else:
			project_name += self.employee
		project = frappe.get_doc({
				"doctype": "Project",
				"project_name": project_name,
				"expected_start_date": self.date_of_joining if self.doctype == "Employee Onboarding" else self.resignation_letter_date,
				"department": self.department,
				"company": self.company
			}).insert(ignore_permissions=True)
		self.db_set("project", project.name)
		self.db_set("boarding_status", "Pending")
		self.reload()
		self.create_task_and_notify_user()

	def create_task_and_notify_user(self):
		# create the task for the given project and assign to the concerned person
		for activity in self.activities:
			if activity.task:
				continue

			task = frappe.get_doc({
					"doctype": "Task",
					"project": self.project,
					"subject": activity.activity_name + " : " + self.employee_name,
					"description": activity.description,
					"department": self.department,
					"company": self.company,
					"task_weight": activity.task_weight
				}).insert(ignore_permissions=True)
			activity.db_set("task", task.name)
			users = [activity.user] if activity.user else []
			if activity.role:
				user_list = frappe.db.sql_list('''select distinct(parent) from `tabHas Role`
					where parenttype='User' and role=%s''', activity.role)
				users = users + user_list

				if "Administrator" in users:
					users.remove("Administrator")

			# assign the task the users
			if users:
				self.assign_task_to_users(task, set(users))

	def assign_task_to_users(self, task, users):
		for user in users:
			args = {
				'assign_to' 	:	user,
				'doctype'		:	task.doctype,
				'name'			:	task.name,
				'description'	:	task.description or task.subject,
				'notify':	self.notify_users_by_email
			}
			assign_to.add(args)

	def on_cancel(self):
		# delete task project
		for task in frappe.get_all("Task", filters={"project": self.project}):
			frappe.delete_doc("Task", task.name, force=1)
		frappe.delete_doc("Project", self.project, force=1)
		self.db_set('project', '')
		for activity in self.activities:
			activity.db_set("task", "")


@frappe.whitelist()
def get_onboarding_details(parent, parenttype):
	return frappe.get_all("Employee Boarding Activity",
		fields=["activity_name", "role", "user", "required_for_employee_creation", "description", "task_weight"],
		filters={"parent": parent, "parenttype": parenttype},
		order_by= "idx")

@frappe.whitelist()
def get_boarding_status(project):
	status = 'Pending'
	if project:
		doc = frappe.get_doc('Project', project)
		if flt(doc.percent_complete) > 0.0 and flt(doc.percent_complete) < 100.0:
			status = 'In Process'
		elif flt(doc.percent_complete) == 100.0:
			status = 'Completed'
		return status

def set_employee_name(doc):
	if doc.employee and not doc.employee_name:
		doc.employee_name = frappe.db.get_value("Employee", doc.employee, "employee_name")

def update_employee(employee, details, date=None, cancel=False):
	internal_work_history = {}
	for item in details:
		fieldtype = frappe.get_meta("Employee").get_field(item.fieldname).fieldtype
		new_data = item.new if not cancel else item.current
		if fieldtype == "Date" and new_data:
			new_data = getdate(new_data)
		elif fieldtype =="Datetime" and new_data:
			new_data = get_datetime(new_data)
		setattr(employee, item.fieldname, new_data)
		if item.fieldname in ["department", "designation", "branch"]:
			internal_work_history[item.fieldname] = item.new
	if internal_work_history and not cancel:
		internal_work_history["from_date"] = date
		employee.append("internal_work_history", internal_work_history)
	return employee

@frappe.whitelist()
def get_employee_fields_label():
	fields = []
	for df in frappe.get_meta("Employee").get("fields"):
		if df.fieldname in ["salutation", "user_id", "employee_number", "employment_type",
			"holiday_list", "branch", "department", "designation", "grade",
			"notice_number_of_days", "reports_to", "leave_policy", "company_email"]:
				fields.append({"value": df.fieldname, "label": df.label})
	return fields

@frappe.whitelist()
def get_employee_field_property(employee, fieldname):
	if employee and fieldname:
		field = frappe.get_meta("Employee").get_field(fieldname)
		value = frappe.db.get_value("Employee", employee, fieldname)
		options = field.options
		if field.fieldtype == "Date":
			value = formatdate(value)
		elif field.fieldtype == "Datetime":
			value = format_datetime(value)
		return {
			"value" : value,
			"datatype" : field.fieldtype,
			"label" : field.label,
			"options" : options
		}
	else:
		return False

def validate_dates(doc, from_date, to_date):
	date_of_joining, relieving_date = frappe.db.get_value("Employee", doc.employee, ["date_of_joining", "relieving_date"])
	if getdate(from_date) > getdate(to_date):
		frappe.throw(_("To date can not be less than from date"))
	elif getdate(from_date) > getdate(nowdate()):
		frappe.throw(_("Future dates not allowed"))
	elif date_of_joining and getdate(from_date) < getdate(date_of_joining):
		frappe.throw(_("From date can not be less than employee's joining date"))
	elif relieving_date and getdate(to_date) > getdate(relieving_date):
		frappe.throw(_("To date can not greater than employee's relieving date"))

def validate_overlap(doc, from_date, to_date, company = None):
	query = """
		select name
		from `tab{0}`
		where name != %(name)s
		"""
	query += get_doc_condition(doc.doctype)

	if not doc.name:
		# hack! if name is null, it could cause problems with !=
		doc.name = "New "+doc.doctype

	overlap_doc = frappe.db.sql(query.format(doc.doctype),{
			"employee": doc.get("employee"),
			"from_date": from_date,
			"to_date": to_date,
			"name": doc.name,
			"company": company
		}, as_dict = 1)

	if overlap_doc:
		if doc.get("employee"):
			exists_for = doc.employee
		if company:
			exists_for = company
		throw_overlap_error(doc, exists_for, overlap_doc[0].name, from_date, to_date)

def get_doc_condition(doctype):
	if doctype == "Compensatory Leave Request":
		return "and employee = %(employee)s and docstatus < 2 \
		and (work_from_date between %(from_date)s and %(to_date)s \
		or work_end_date between %(from_date)s and %(to_date)s \
		or (work_from_date < %(from_date)s and work_end_date > %(to_date)s))"
	elif doctype == "Leave Period":
		return "and company = %(company)s and (from_date between %(from_date)s and %(to_date)s \
			or to_date between %(from_date)s and %(to_date)s \
			or (from_date < %(from_date)s and to_date > %(to_date)s))"

def throw_overlap_error(doc, exists_for, overlap_doc, from_date, to_date):
	msg = _("A {0} exists between {1} and {2} (").format(doc.doctype,
		formatdate(from_date), formatdate(to_date)) \
		+ """ <b><a href="#Form/{0}/{1}">{1}</a></b>""".format(doc.doctype, overlap_doc) \
		+ _(") for {0}").format(exists_for)
	frappe.throw(msg)

def get_employee_leave_policy(employee):
	leave_policy = frappe.db.get_value("Employee", employee, "leave_policy")
	if not leave_policy:
		employee_grade = frappe.db.get_value("Employee", employee, "grade")
		if employee_grade:
			leave_policy = frappe.db.get_value("Employee Grade", employee_grade, "default_leave_policy")
			if not leave_policy:
				frappe.throw(_("Employee {0} of grade {1} have no default leave policy").format(employee, employee_grade))
	if leave_policy:
		return frappe.get_doc("Leave Policy", leave_policy)
	else:
		frappe.throw(_("Please set leave policy for employee {0} in Employee / Grade record").format(employee))

def validate_tax_declaration(declarations):
	subcategories = []
	for d in declarations:
		if d.exemption_sub_category in subcategories:
			frappe.throw(_("More than one selection for {0} not allowed").format(d.exemption_sub_category))
		subcategories.append(d.exemption_sub_category)

def get_total_exemption_amount(declarations):
	exemptions = frappe._dict()
	for d in declarations:
		exemptions.setdefault(d.exemption_category, frappe._dict())
		category_max_amount = exemptions.get(d.exemption_category).max_amount
		if not category_max_amount:
			category_max_amount = frappe.db.get_value("Employee Tax Exemption Category", d.exemption_category, "max_amount")
			exemptions.get(d.exemption_category).max_amount = category_max_amount
		sub_category_exemption_amount = d.max_amount \
			if (d.max_amount and flt(d.amount) > flt(d.max_amount)) else d.amount

		exemptions.get(d.exemption_category).setdefault("total_exemption_amount", 0.0)
		exemptions.get(d.exemption_category).total_exemption_amount += flt(sub_category_exemption_amount)

		if category_max_amount and exemptions.get(d.exemption_category).total_exemption_amount > category_max_amount:
			exemptions.get(d.exemption_category).total_exemption_amount = category_max_amount

	total_exemption_amount = sum([flt(d.total_exemption_amount) for d in exemptions.values()])
	return total_exemption_amount

def get_leave_period(from_date, to_date, company):
	leave_period = frappe.db.sql("""
		select name, from_date, to_date
		from `tabLeave Period`
		where company=%(company)s and is_active=1
			and (from_date between %(from_date)s and %(to_date)s
				or to_date between %(from_date)s and %(to_date)s
				or (from_date < %(from_date)s and to_date > %(to_date)s))
	""", {
		"from_date": from_date,
		"to_date": to_date,
		"company": company
	}, as_dict=1)

	if leave_period:
		return leave_period

def generate_leave_encashment():
	''' Generates a draft leave encashment on allocation expiry '''
	from erpnext.hr.doctype.leave_encashment.leave_encashment import create_leave_encashment

	if frappe.db.get_single_value('HR Settings', 'auto_leave_encashment'):
		leave_type = frappe.get_all('Leave Type', filters={'allow_encashment': 1}, fields=['name'])
		leave_type=[l['name'] for l in leave_type]

		leave_allocation = frappe.get_all("Leave Allocation", filters={
			'to_date': add_days(today(), -1),
			'leave_type': ('in', leave_type)
		}, fields=['employee', 'leave_period', 'leave_type', 'to_date', 'total_leaves_allocated', 'new_leaves_allocated'])

		create_leave_encashment(leave_allocation=leave_allocation)

def allocate_earned_leaves():
	'''Allocate earned leaves to Employees'''
	e_leave_types = frappe.get_all("Leave Type",
		fields=["name", "max_leaves_allowed", "earned_leave_frequency", "rounding"],
		filters={'is_earned_leave' : 1})
	today = getdate()
	divide_by_frequency = {"Yearly": 1, "Half-Yearly": 6, "Quarterly": 4, "Monthly": 12}

	for e_leave_type in e_leave_types:
		leave_allocations = frappe.db.sql("""select name, employee, from_date, to_date from `tabLeave Allocation` where %s
			between from_date and to_date and docstatus=1 and leave_type=%s""", (today, e_leave_type.name), as_dict=1)
		for allocation in leave_allocations:
			leave_policy = get_employee_leave_policy(allocation.employee)
			if not leave_policy:
				continue
			if not e_leave_type.earned_leave_frequency == "Monthly":
				if not check_frequency_hit(allocation.from_date, today, e_leave_type.earned_leave_frequency):
					continue
			annual_allocation = frappe.db.get_value("Leave Policy Detail", filters={
				'parent': leave_policy.name,
				'leave_type': e_leave_type.name
			}, fieldname=['annual_allocation'])
			if annual_allocation:
				earned_leaves = flt(annual_allocation) / divide_by_frequency[e_leave_type.earned_leave_frequency]
				if e_leave_type.rounding == "0.5":
					earned_leaves = round(earned_leaves * 2) / 2
				else:
					earned_leaves = round(earned_leaves)

				allocation = frappe.get_doc('Leave Allocation', allocation.name)
				new_allocation = flt(allocation.total_leaves_allocated) + flt(earned_leaves)

				if new_allocation > e_leave_type.max_leaves_allowed and e_leave_type.max_leaves_allowed > 0:
					new_allocation = e_leave_type.max_leaves_allowed

				if new_allocation == allocation.total_leaves_allocated:
					continue
				allocation.db_set("total_leaves_allocated", new_allocation, update_modified=False)
				create_additional_leave_ledger_entry(allocation, earned_leaves, today)

def create_additional_leave_ledger_entry(allocation, leaves, date):
	''' Create leave ledger entry for leave types '''
	allocation.new_leaves_allocated = leaves
	allocation.from_date = date
	allocation.unused_leaves = 0
	allocation.create_leave_ledger_entry()

def check_frequency_hit(from_date, to_date, frequency):
	'''Return True if current date matches frequency'''
	from_dt = get_datetime(from_date)
	to_dt = get_datetime(to_date)
	from dateutil import relativedelta
	rd = relativedelta.relativedelta(to_dt, from_dt)
	months = rd.months
	if frequency == "Quarterly":
		if not months % 3:
			return True
	elif frequency == "Half-Yearly":
		if not months % 6:
			return True
	elif frequency == "Yearly":
		if not months % 12:
			return True
	return False

def get_salary_assignment(employee, date):
	assignment = frappe.db.sql("""
		select * from `tabSalary Structure Assignment`
		where employee=%(employee)s
		and docstatus = 1
		and %(on_date)s >= from_date order by from_date desc limit 1""", {
			'employee': employee,
			'on_date': date,
		}, as_dict=1)
	return assignment[0] if assignment else None

def get_sal_slip_total_benefit_given(employee, payroll_period, component=False):
	total_given_benefit_amount = 0
	query = """
	select sum(sd.amount) as 'total_amount'
	from `tabSalary Slip` ss, `tabSalary Detail` sd
	where ss.employee=%(employee)s
	and ss.docstatus = 1 and ss.name = sd.parent
	and sd.is_flexible_benefit = 1 and sd.parentfield = "earnings"
	and sd.parenttype = "Salary Slip"
	and (ss.start_date between %(start_date)s and %(end_date)s
		or ss.end_date between %(start_date)s and %(end_date)s
		or (ss.start_date < %(start_date)s and ss.end_date > %(end_date)s))
	"""

	if component:
		query += "and sd.salary_component = %(component)s"

	sum_of_given_benefit = frappe.db.sql(query, {
		'employee': employee,
		'start_date': payroll_period.start_date,
		'end_date': payroll_period.end_date,
		'component': component
	}, as_dict=True)

	if sum_of_given_benefit and flt(sum_of_given_benefit[0].total_amount) > 0:
		total_given_benefit_amount = sum_of_given_benefit[0].total_amount
	return total_given_benefit_amount

def get_holidays_for_employee(employee, start_date, end_date):
	holiday_list = get_holiday_list_for_employee(employee)

	holidays = frappe.db.sql_list('''select holiday_date from `tabHoliday`
		where
			parent=%(holiday_list)s
			and holiday_date >= %(start_date)s
			and holiday_date <= %(end_date)s''', {
				"holiday_list": holiday_list,
				"start_date": start_date,
				"end_date": end_date
			})

	holidays = [cstr(i) for i in holidays]

	return holidays

@erpnext.allow_regional
def calculate_annual_eligible_hra_exemption(doc):
	# Don't delete this method, used for localization
	# Indian HRA Exemption Calculation
	return {}

@erpnext.allow_regional
def calculate_hra_exemption_for_period(doc):
	# Don't delete this method, used for localization
	# Indian HRA Exemption Calculation
	return {}

def get_previous_claimed_amount(employee, payroll_period, non_pro_rata=False, component=False):
	total_claimed_amount = 0
	query = """
	select sum(claimed_amount) as 'total_amount'
	from `tabEmployee Benefit Claim`
	where employee=%(employee)s
	and docstatus = 1
	and (claim_date between %(start_date)s and %(end_date)s)
	"""
	if non_pro_rata:
		query += "and pay_against_benefit_claim = 1"
	if component:
		query += "and earning_component = %(component)s"

	sum_of_claimed_amount = frappe.db.sql(query, {
		'employee': employee,
		'start_date': payroll_period.start_date,
		'end_date': payroll_period.end_date,
		'component': component
	}, as_dict=True)
	if sum_of_claimed_amount and flt(sum_of_claimed_amount[0].total_amount) > 0:
		total_claimed_amount = sum_of_claimed_amount[0].total_amount
	return total_claimed_amount

import frappe.defaults
from frappe.utils import nowdate, cstr, flt, cint, now, getdate
from frappe import throw, _
from frappe.utils import formatdate, get_number_format_info
from six import iteritems
# imported to enable erpnext.accounts.utils.get_account_currency
from paypro.paypro.doctype.account.account import get_account_currency

# from erpnext.stock.utils import get_stock_value_on
# from erpnext.stock import get_warehouse_account_map


class FiscalYearError(frappe.ValidationError): pass

@frappe.whitelist()
def get_fiscal_year(date=None, fiscal_year=None, label="Date", verbose=1, company=None, as_dict=False):
	return get_fiscal_years(date, fiscal_year, label, verbose, company, as_dict=as_dict)[0]

def get_fiscal_years(transaction_date=None, fiscal_year=None, label="Date", verbose=1, company=None, as_dict=False):
	fiscal_years = frappe.cache().hget("fiscal_years", company) or []

	if not fiscal_years:
		# if year start date is 2012-04-01, year end date should be 2013-03-31 (hence subdate)
		cond = ""
		if fiscal_year:
			cond += " and fy.name = {0}".format(frappe.db.escape(fiscal_year))
		if company:
			cond += """
				and (not exists (select name
					from `tabFiscal Year Company` fyc
					where fyc.parent = fy.name)
				or exists(select company
					from `tabFiscal Year Company` fyc
					where fyc.parent = fy.name
					and fyc.company=%(company)s)
				)
			"""

		fiscal_years = frappe.db.sql("""
			select
				fy.name, fy.year_start_date, fy.year_end_date
			from
				`tabFiscal Year` fy
			where
				disabled = 0 {0}
			order by
				fy.year_start_date desc""".format(cond), {
				"company": company
			}, as_dict=True)

		frappe.cache().hset("fiscal_years", company, fiscal_years)

	if transaction_date:
		transaction_date = getdate(transaction_date)

	for fy in fiscal_years:
		matched = False
		if fiscal_year and fy.name == fiscal_year:
			matched = True

		if (transaction_date and getdate(fy.year_start_date) <= transaction_date
			and getdate(fy.year_end_date) >= transaction_date):
			matched = True

		if matched:
			if as_dict:
				return (fy,)
			else:
				return ((fy.name, fy.year_start_date, fy.year_end_date),)

	error_msg = _("""{0} {1} not in any active Fiscal Year.""").format(label, formatdate(transaction_date))
	if verbose==1: frappe.msgprint(error_msg)
	raise FiscalYearError(error_msg)

def validate_fiscal_year(date, fiscal_year, company, label="Date", doc=None):
	years = [f[0] for f in get_fiscal_years(date, label=_(label), company=company)]
	if fiscal_year not in years:
		if doc:
			doc.fiscal_year = years[0]
		else:
			throw(_("{0} '{1}' not in Fiscal Year {2}").format(label, formatdate(date), fiscal_year))

@frappe.whitelist()
def get_balance_on(account=None, date=None, party_type=None, party=None, company=None,
	in_account_currency=True, cost_center=None, ignore_account_permission=False):
	if not account and frappe.form_dict.get("account"):
		account = frappe.form_dict.get("account")
	if not date and frappe.form_dict.get("date"):
		date = frappe.form_dict.get("date")
	if not party_type and frappe.form_dict.get("party_type"):
		party_type = frappe.form_dict.get("party_type")
	if not party and frappe.form_dict.get("party"):
		party = frappe.form_dict.get("party")
	if not cost_center and frappe.form_dict.get("cost_center"):
		cost_center = frappe.form_dict.get("cost_center")


	cond = []
	if date:
		cond.append("posting_date <= %s" % frappe.db.escape(cstr(date)))
	else:
		# get balance of all entries that exist
		date = nowdate()

	if account:
		acc = frappe.get_doc("Account", account)

	try:
		year_start_date = get_fiscal_year(date, verbose=0)[1]
	except FiscalYearError:
		if getdate(date) > getdate(nowdate()):
			# if fiscal year not found and the date is greater than today
			# get fiscal year for today's date and its corresponding year start date
			year_start_date = get_fiscal_year(nowdate(), verbose=1)[1]
		else:
			# this indicates that it is a date older than any existing fiscal year.
			# hence, assuming balance as 0.0
			return 0.0

	allow_cost_center_in_entry_of_bs_account = get_allow_cost_center_in_entry_of_bs_account()

	if account:
		report_type = acc.report_type
	else:
		report_type = ""

	if cost_center and (allow_cost_center_in_entry_of_bs_account or report_type =='Profit and Loss'):
		cc = frappe.get_doc("Cost Center", cost_center)
		if cc.is_group:
			cond.append(""" exists (
				select 1 from `tabCost Center` cc where cc.name = gle.cost_center
				and cc.lft >= %s and cc.rgt <= %s
			)""" % (cc.lft, cc.rgt))

		else:
			cond.append("""gle.cost_center = %s """ % (frappe.db.escape(cost_center, percent=False), ))


	if account:

		if not (frappe.flags.ignore_account_permission
			or ignore_account_permission):
			acc.check_permission("read")

		if report_type == 'Profit and Loss':
			# for pl accounts, get balance within a fiscal year
			cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" \
				% year_start_date)
		# different filter for group and ledger - improved performance
		if acc.is_group:
			cond.append("""exists (
				select name from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= %s and ac.rgt <= %s
			)""" % (acc.lft, acc.rgt))

			# If group and currency same as company,
			# always return balance based on debit and credit in company currency
			if acc.account_currency == frappe.get_cached_value('Company',  acc.company,  "default_currency"):
				in_account_currency = False
		else:
			cond.append("""gle.account = %s """ % (frappe.db.escape(account, percent=False), ))

	if party_type and party:
		cond.append("""gle.party_type = %s and gle.party = %s """ %
			(frappe.db.escape(party_type), frappe.db.escape(party, percent=False)))

	if company:
		cond.append("""gle.company = %s """ % (frappe.db.escape(company, percent=False)))

	if account or (party_type and party):
		if in_account_currency:
			select_field = "sum(debit_in_account_currency) - sum(credit_in_account_currency)"
		else:
			select_field = "sum(debit) - sum(credit)"
		bal = frappe.db.sql("""
			SELECT {0}
			FROM `tabGL Entry` gle
			WHERE {1}""".format(select_field, " and ".join(cond)))[0][0]

		# if bal is None, return 0
		return flt(bal)

def get_count_on(account, fieldname, date):
	cond = []
	if date:
		cond.append("posting_date <= %s" % frappe.db.escape(cstr(date)))
	else:
		# get balance of all entries that exist
		date = nowdate()

	try:
		year_start_date = get_fiscal_year(date, verbose=0)[1]
	except FiscalYearError:
		if getdate(date) > getdate(nowdate()):
			# if fiscal year not found and the date is greater than today
			# get fiscal year for today's date and its corresponding year start date
			year_start_date = get_fiscal_year(nowdate(), verbose=1)[1]
		else:
			# this indicates that it is a date older than any existing fiscal year.
			# hence, assuming balance as 0.0
			return 0.0

	if account:
		acc = frappe.get_doc("Account", account)

		if not frappe.flags.ignore_account_permission:
			acc.check_permission("read")

		# for pl accounts, get balance within a fiscal year
		if acc.report_type == 'Profit and Loss':
			cond.append("posting_date >= '%s' and voucher_type != 'Period Closing Voucher'" \
				% year_start_date)

		# different filter for group and ledger - improved performance
		if acc.is_group:
			cond.append("""exists (
				select name from `tabAccount` ac where ac.name = gle.account
				and ac.lft >= %s and ac.rgt <= %s
			)""" % (acc.lft, acc.rgt))
		else:
			cond.append("""gle.account = %s """ % (frappe.db.escape(account, percent=False), ))

		entries = frappe.db.sql("""
			SELECT name, posting_date, account, party_type, party,debit,credit,
				voucher_type, voucher_no, against_voucher_type, against_voucher
			FROM `tabGL Entry` gle
			WHERE {0}""".format(" and ".join(cond)), as_dict=True)

		count = 0
		for gle in entries:
			if fieldname not in ('invoiced_amount','payables'):
				count += 1
			else:
				dr_or_cr = "debit" if fieldname == "invoiced_amount" else "credit"
				cr_or_dr = "credit" if fieldname == "invoiced_amount" else "debit"
				select_fields = "ifnull(sum(credit-debit),0)" \
					if fieldname == "invoiced_amount" else "ifnull(sum(debit-credit),0)"

				if ((not gle.against_voucher) or (gle.against_voucher_type in ["Sales Order", "Purchase Order"]) or
				(gle.against_voucher==gle.voucher_no and gle.get(dr_or_cr) > 0)):
					payment_amount = frappe.db.sql("""
						SELECT {0}
						FROM `tabGL Entry` gle
						WHERE docstatus < 2 and posting_date <= %(date)s and against_voucher = %(voucher_no)s
						and party = %(party)s and name != %(name)s"""
						.format(select_fields),
						{"date": date, "voucher_no": gle.voucher_no,
							"party": gle.party, "name": gle.name})[0][0]

					outstanding_amount = flt(gle.get(dr_or_cr)) - flt(gle.get(cr_or_dr)) - payment_amount
					currency_precision = get_currency_precision() or 2
					if abs(flt(outstanding_amount)) > 0.1/10**currency_precision:
						count += 1

		return count

@frappe.whitelist()
def add_ac(args=None):
	from frappe.desk.treeview import make_tree_args

	if not args:
		args = frappe.local.form_dict

	args.doctype = "Account"
	args = make_tree_args(**args)

	ac = frappe.new_doc("Account")

	if args.get("ignore_permissions"):
		ac.flags.ignore_permissions = True
		args.pop("ignore_permissions")

	ac.update(args)

	if not ac.parent_account:
		ac.parent_account = args.get("parent")

	ac.old_parent = ""
	ac.freeze_account = "No"
	if cint(ac.get("is_root")):
		ac.parent_account = None
		ac.flags.ignore_mandatory = True

	ac.insert()

	return ac.name

@frappe.whitelist()
def add_cc(args=None):
	from frappe.desk.treeview import make_tree_args

	if not args:
		args = frappe.local.form_dict

	args.doctype = "Cost Center"
	args = make_tree_args(**args)

	if args.parent_cost_center == args.company:
		args.parent_cost_center = "{0} - {1}".format(args.parent_cost_center,
			frappe.get_cached_value('Company',  args.company,  'abbr'))

	cc = frappe.new_doc("Cost Center")
	cc.update(args)

	if not cc.parent_cost_center:
		cc.parent_cost_center = args.get("parent")

	cc.old_parent = ""
	cc.insert()
	return cc.name

def reconcile_against_document(args):
	"""
		Cancel JV, Update aginst document, split if required and resubmit jv
	"""
	for d in args:

		check_if_advance_entry_modified(d)
		validate_allocated_amount(d)

		# cancel advance entry
		doc = frappe.get_doc(d.voucher_type, d.voucher_no)

		doc.make_gl_entries(cancel=1, adv_adj=1)

		# update ref in advance entry
		if d.voucher_type == "Journal Entry":
			update_reference_in_journal_entry(d, doc)
		else:
			update_reference_in_payment_entry(d, doc)

		# re-submit advance entry
		doc = frappe.get_doc(d.voucher_type, d.voucher_no)
		doc.make_gl_entries(cancel = 0, adv_adj =1)

		if d.voucher_type in ('Payment Entry', 'Journal Entry'):
			doc.update_expense_claim()

def check_if_advance_entry_modified(args):
	"""
		check if there is already a voucher reference
		check if amount is same
		check if jv is submitted
	"""
	ret = None
	if args.voucher_type == "Journal Entry":
		ret = frappe.db.sql("""
			select t2.{dr_or_cr} from `tabJournal Entry` t1, `tabJournal Entry Account` t2
			where t1.name = t2.parent and t2.account = %(account)s
			and t2.party_type = %(party_type)s and t2.party = %(party)s
			and (t2.reference_type is null or t2.reference_type in ("", "Sales Order", "Purchase Order"))
			and t1.name = %(voucher_no)s and t2.name = %(voucher_detail_no)s
			and t1.docstatus=1 """.format(dr_or_cr = args.get("dr_or_cr")), args)
	else:
		party_account_field = ("paid_from"
			if erpnext.get_party_account_type(args.party_type) == 'Receivable' else "paid_to")

		if args.voucher_detail_no:
			ret = frappe.db.sql("""select t1.name
				from `tabPayment Entry` t1, `tabPayment Entry Reference` t2
				where
					t1.name = t2.parent and t1.docstatus = 1
					and t1.name = %(voucher_no)s and t2.name = %(voucher_detail_no)s
					and t1.party_type = %(party_type)s and t1.party = %(party)s and t1.{0} = %(account)s
					and t2.reference_doctype in ("", "Sales Order", "Purchase Order")
					and t2.allocated_amount = %(unadjusted_amount)s
			""".format(party_account_field), args)
		else:
			ret = frappe.db.sql("""select name from `tabPayment Entry`
				where
					name = %(voucher_no)s and docstatus = 1
					and party_type = %(party_type)s and party = %(party)s and {0} = %(account)s
					and unallocated_amount = %(unadjusted_amount)s
			""".format(party_account_field), args)

	if not ret:
		throw(_("""Payment Entry has been modified after you pulled it. Please pull it again."""))

def validate_allocated_amount(args):
	if args.get("allocated_amount") < 0:
		throw(_("Allocated amount cannot be negative"))
	elif args.get("allocated_amount") > args.get("unadjusted_amount"):
		throw(_("Allocated amount cannot be greater than unadjusted amount"))

def update_reference_in_journal_entry(d, jv_obj):
	"""
		Updates against document, if partial amount splits into rows
	"""
	jv_detail = jv_obj.get("accounts", {"name": d["voucher_detail_no"]})[0]
	jv_detail.set(d["dr_or_cr"], d["allocated_amount"])
	jv_detail.set('debit' if d['dr_or_cr']=='debit_in_account_currency' else 'credit',
		d["allocated_amount"]*flt(jv_detail.exchange_rate))

	original_reference_type = jv_detail.reference_type
	original_reference_name = jv_detail.reference_name

	jv_detail.set("reference_type", d["against_voucher_type"])
	jv_detail.set("reference_name", d["against_voucher"])

	if d['allocated_amount'] < d['unadjusted_amount']:
		jvd = frappe.db.sql("""
			select cost_center, balance, against_account, is_advance,
				account_type, exchange_rate, account_currency
			from `tabJournal Entry Account` where name = %s
		""", d['voucher_detail_no'], as_dict=True)

		amount_in_account_currency = flt(d['unadjusted_amount']) - flt(d['allocated_amount'])
		amount_in_company_currency = amount_in_account_currency * flt(jvd[0]['exchange_rate'])

		# new entry with balance amount
		ch = jv_obj.append("accounts")
		ch.account = d['account']
		ch.account_type = jvd[0]['account_type']
		ch.account_currency = jvd[0]['account_currency']
		ch.exchange_rate = jvd[0]['exchange_rate']
		ch.party_type = d["party_type"]
		ch.party = d["party"]
		ch.cost_center = cstr(jvd[0]["cost_center"])
		ch.balance = flt(jvd[0]["balance"])

		ch.set(d['dr_or_cr'], amount_in_account_currency)
		ch.set('debit' if d['dr_or_cr']=='debit_in_account_currency' else 'credit', amount_in_company_currency)

		ch.set('credit_in_account_currency' if d['dr_or_cr']== 'debit_in_account_currency'
			else 'debit_in_account_currency', 0)
		ch.set('credit' if d['dr_or_cr']== 'debit_in_account_currency' else 'debit', 0)

		ch.against_account = cstr(jvd[0]["against_account"])
		ch.reference_type = original_reference_type
		ch.reference_name = original_reference_name
		ch.is_advance = cstr(jvd[0]["is_advance"])
		ch.docstatus = 1

	# will work as update after submit
	jv_obj.flags.ignore_validate_update_after_submit = True
	jv_obj.save(ignore_permissions=True)

def update_reference_in_payment_entry(d, payment_entry, do_not_save=False):
	reference_details = {
		"reference_doctype": d.against_voucher_type,
		"reference_name": d.against_voucher,
		"total_amount": d.grand_total,
		"outstanding_amount": d.outstanding_amount,
		"allocated_amount": d.allocated_amount,
		"exchange_rate": d.exchange_rate
	}

	if d.voucher_detail_no:
		existing_row = payment_entry.get("references", {"name": d["voucher_detail_no"]})[0]
		original_row = existing_row.as_dict().copy()
		existing_row.update(reference_details)

		if d.allocated_amount < original_row.allocated_amount:
			new_row = payment_entry.append("references")
			new_row.docstatus = 1
			for field in list(reference_details):
				new_row.set(field, original_row[field])

			new_row.allocated_amount = original_row.allocated_amount - d.allocated_amount
	else:
		new_row = payment_entry.append("references")
		new_row.docstatus = 1
		new_row.update(reference_details)

	payment_entry.flags.ignore_validate_update_after_submit = True
	payment_entry.setup_party_account_field()
	payment_entry.set_missing_values()
	payment_entry.set_amounts()

	if d.difference_amount and d.difference_account:
		payment_entry.set_gain_or_loss(account_details={
			'account': d.difference_account,
			'cost_center': payment_entry.cost_center or frappe.get_cached_value('Company',
				payment_entry.company, "cost_center"),
			'amount': d.difference_amount
		})

	if not do_not_save:
		payment_entry.save(ignore_permissions=True)

def unlink_ref_doc_from_payment_entries(ref_doc):
	remove_ref_doc_link_from_jv(ref_doc.doctype, ref_doc.name)
	remove_ref_doc_link_from_pe(ref_doc.doctype, ref_doc.name)

	frappe.db.sql("""update `tabGL Entry`
		set against_voucher_type=null, against_voucher=null,
		modified=%s, modified_by=%s
		where against_voucher_type=%s and against_voucher=%s
		and voucher_no != ifnull(against_voucher, '')""",
		(now(), frappe.session.user, ref_doc.doctype, ref_doc.name))

	if ref_doc.doctype in ("Sales Invoice", "Purchase Invoice"):
		ref_doc.set("advances", [])

		frappe.db.sql("""delete from `tab{0} Advance` where parent = %s"""
			.format(ref_doc.doctype), ref_doc.name)

def remove_ref_doc_link_from_jv(ref_type, ref_no):
	linked_jv = frappe.db.sql_list("""select parent from `tabJournal Entry Account`
		where reference_type=%s and reference_name=%s and docstatus < 2""", (ref_type, ref_no))

	if linked_jv:
		frappe.db.sql("""update `tabJournal Entry Account`
			set reference_type=null, reference_name = null,
			modified=%s, modified_by=%s
			where reference_type=%s and reference_name=%s
			and docstatus < 2""", (now(), frappe.session.user, ref_type, ref_no))

		frappe.msgprint(_("Journal Entries {0} are un-linked").format("\n".join(linked_jv)))

def remove_ref_doc_link_from_pe(ref_type, ref_no):
	linked_pe = frappe.db.sql_list("""select parent from `tabPayment Entry Reference`
		where reference_doctype=%s and reference_name=%s and docstatus < 2""", (ref_type, ref_no))

	if linked_pe:
		frappe.db.sql("""update `tabPayment Entry Reference`
			set allocated_amount=0, modified=%s, modified_by=%s
			where reference_doctype=%s and reference_name=%s
			and docstatus < 2""", (now(), frappe.session.user, ref_type, ref_no))

		for pe in linked_pe:
			pe_doc = frappe.get_doc("Payment Entry", pe)
			pe_doc.set_total_allocated_amount()
			pe_doc.set_unallocated_amount()
			pe_doc.clear_unallocated_reference_document_rows()

			frappe.db.sql("""update `tabPayment Entry` set total_allocated_amount=%s,
				base_total_allocated_amount=%s, unallocated_amount=%s, modified=%s, modified_by=%s
				where name=%s""", (pe_doc.total_allocated_amount, pe_doc.base_total_allocated_amount,
					pe_doc.unallocated_amount, now(), frappe.session.user, pe))

		frappe.msgprint(_("Payment Entries {0} are un-linked").format("\n".join(linked_pe)))

@frappe.whitelist()
def get_company_default(company, fieldname):
	value = frappe.get_cached_value('Company',  company,  fieldname)

	if not value:
		throw(_("Please set default {0} in Company {1}")
			.format(frappe.get_meta("Company").get_label(fieldname), company))

	return value

def fix_total_debit_credit():
	vouchers = frappe.db.sql("""select voucher_type, voucher_no,
		sum(debit) - sum(credit) as diff
		from `tabGL Entry`
		group by voucher_type, voucher_no
		having sum(debit) != sum(credit)""", as_dict=1)

	for d in vouchers:
		if abs(d.diff) > 0:
			dr_or_cr = d.voucher_type == "Sales Invoice" and "credit" or "debit"

			frappe.db.sql("""update `tabGL Entry` set %s = %s + %s
				where voucher_type = %s and voucher_no = %s and %s > 0 limit 1""" %
				(dr_or_cr, dr_or_cr, '%s', '%s', '%s', dr_or_cr),
				(d.diff, d.voucher_type, d.voucher_no))

def get_stock_and_account_balance(account=None, posting_date=None, company=None):
	if not posting_date: posting_date = nowdate()

	warehouse_account = get_warehouse_account_map(company)

	account_balance = get_balance_on(account, posting_date, in_account_currency=False, ignore_account_permission=True)

	related_warehouses = [wh for wh, wh_details in warehouse_account.items()
		if wh_details.account == account and not wh_details.is_group]

	total_stock_value = 0.0
	for warehouse in related_warehouses:
		value = get_stock_value_on(warehouse, posting_date)
		total_stock_value += value

	precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")
	return flt(account_balance, precision), flt(total_stock_value, precision), related_warehouses

def get_currency_precision():
	precision = cint(frappe.db.get_default("currency_precision"))
	if not precision:
		number_format = frappe.db.get_default("number_format") or "#,###.##"
		precision = get_number_format_info(number_format)[2]

	return precision

def get_stock_rbnb_difference(posting_date, company):
	stock_items = frappe.db.sql_list("""select distinct item_code
		from `tabStock Ledger Entry` where company=%s""", company)

	pr_valuation_amount = frappe.db.sql("""
		select sum(pr_item.valuation_rate * pr_item.qty * pr_item.conversion_factor)
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
		where pr.name = pr_item.parent and pr.docstatus=1 and pr.company=%s
		and pr.posting_date <= %s and pr_item.item_code in (%s)""" %
		('%s', '%s', ', '.join(['%s']*len(stock_items))), tuple([company, posting_date] + stock_items))[0][0]

	pi_valuation_amount = frappe.db.sql("""
		select sum(pi_item.valuation_rate * pi_item.qty * pi_item.conversion_factor)
		from `tabPurchase Invoice Item` pi_item, `tabPurchase Invoice` pi
		where pi.name = pi_item.parent and pi.docstatus=1 and pi.company=%s
		and pi.posting_date <= %s and pi_item.item_code in (%s)""" %
		('%s', '%s', ', '.join(['%s']*len(stock_items))), tuple([company, posting_date] + stock_items))[0][0]

	# Balance should be
	stock_rbnb = flt(pr_valuation_amount, 2) - flt(pi_valuation_amount, 2)

	# Balance as per system
	stock_rbnb_account = "Stock Received But Not Billed - " + frappe.get_cached_value('Company',  company,  "abbr")
	sys_bal = get_balance_on(stock_rbnb_account, posting_date, in_account_currency=False)

	# Amount should be credited
	return flt(stock_rbnb) + flt(sys_bal)


def get_held_invoices(party_type, party):
	"""
	Returns a list of names Purchase Invoices for the given party that are on hold
	"""
	held_invoices = None

	if party_type == 'Supplier':
		held_invoices = frappe.db.sql(
			'select name from `tabPurchase Invoice` where release_date IS NOT NULL and release_date > CURDATE()',
			as_dict=1
		)
		held_invoices = set([d['name'] for d in held_invoices])

	return held_invoices


def get_outstanding_invoices(party_type, party, account, condition=None, filters=None):
	outstanding_invoices = []
	precision = frappe.get_precision("Sales Invoice", "outstanding_amount") or 2

	if account:
		root_type, account_type = frappe.get_cached_value("Account", account, ["root_type", "account_type"])
		party_account_type = "Receivable" if root_type == "Asset" else "Payable"
		party_account_type = account_type or party_account_type
	else:
		party_account_type = erpnext.get_party_account_type(party_type)

	if party_account_type == 'Receivable':
		dr_or_cr = "debit_in_account_currency - credit_in_account_currency"
		payment_dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
	else:
		dr_or_cr = "credit_in_account_currency - debit_in_account_currency"
		payment_dr_or_cr = "debit_in_account_currency - credit_in_account_currency"

	held_invoices = get_held_invoices(party_type, party)

	invoice_list = frappe.db.sql("""
		select
			voucher_no, voucher_type, posting_date, due_date,
			ifnull(sum({dr_or_cr}), 0) as invoice_amount
		from
			`tabGL Entry`
		where
			party_type = %(party_type)s and party = %(party)s
			and account = %(account)s and {dr_or_cr} > 0
			{condition}
			and ((voucher_type = 'Journal Entry'
					and (against_voucher = '' or against_voucher is null))
				or (voucher_type not in ('Journal Entry', 'Payment Entry')))
		group by voucher_type, voucher_no
		order by posting_date, name""".format(
			dr_or_cr=dr_or_cr,
			condition=condition or ""
		), {
			"party_type": party_type,
			"party": party,
			"account": account,
		}, as_dict=True)

	payment_entries = frappe.db.sql("""
		select against_voucher_type, against_voucher,
			ifnull(sum({payment_dr_or_cr}), 0) as payment_amount
		from `tabGL Entry`
		where party_type = %(party_type)s and party = %(party)s
			and account = %(account)s
			and {payment_dr_or_cr} > 0
			and against_voucher is not null and against_voucher != ''
		group by against_voucher_type, against_voucher
	""".format(payment_dr_or_cr=payment_dr_or_cr), {
		"party_type": party_type,
		"party": party,
		"account": account
	}, as_dict=True)

	pe_map = frappe._dict()
	for d in payment_entries:
		pe_map.setdefault((d.against_voucher_type, d.against_voucher), d.payment_amount)

	for d in invoice_list:
		payment_amount = pe_map.get((d.voucher_type, d.voucher_no), 0)
		outstanding_amount = flt(d.invoice_amount - payment_amount, precision)
		if outstanding_amount > 0.5 / (10**precision):
			if (filters and filters.get("outstanding_amt_greater_than") and
				not (outstanding_amount >= filters.get("outstanding_amt_greater_than") and
				outstanding_amount <= filters.get("outstanding_amt_less_than"))):
				continue

			if not d.voucher_type == "Purchase Invoice" or d.voucher_no not in held_invoices:
				outstanding_invoices.append(
					frappe._dict({
						'voucher_no': d.voucher_no,
						'voucher_type': d.voucher_type,
						'posting_date': d.posting_date,
						'invoice_amount': flt(d.invoice_amount),
						'payment_amount': payment_amount,
						'outstanding_amount': outstanding_amount,
						'due_date': d.due_date
					})
				)

	outstanding_invoices = sorted(outstanding_invoices, key=lambda k: k['due_date'] or getdate(nowdate()))
	return outstanding_invoices


def get_account_name(account_type=None, root_type=None, is_group=None, account_currency=None, company=None):
	"""return account based on matching conditions"""
	return frappe.db.get_value("Account", {
		"account_type": account_type or '',
		"root_type": root_type or '',
		"is_group": is_group or 0,
		"account_currency": account_currency or frappe.defaults.get_defaults().currency,
		"company": company or frappe.defaults.get_defaults().company
	}, "name")

@frappe.whitelist()
def get_companies():
	"""get a list of companies based on permission"""
	return [d.name for d in frappe.get_list("Company", fields=["name"],
		order_by="name")]

@frappe.whitelist()
def get_children(doctype, parent, company, is_root=False):
	from erpnext.accounts.report.financial_statements import sort_accounts

	parent_fieldname = 'parent_' + doctype.lower().replace(' ', '_')
	fields = [
		'name as value',
		'is_group as expandable'
	]
	filters = [['docstatus', '<', 2]]

	filters.append(['ifnull(`{0}`,"")'.format(parent_fieldname), '=', '' if is_root else parent])

	if is_root:
		fields += ['root_type', 'report_type', 'account_currency'] if doctype == 'Account' else []
		filters.append(['company', '=', company])

	else:
		fields += ['root_type', 'account_currency'] if doctype == 'Account' else []
		fields += [parent_fieldname + ' as parent']

	acc = frappe.get_list(doctype, fields=fields, filters=filters)

	if doctype == 'Account':
		sort_accounts(acc, is_root, key="value")
		company_currency = frappe.get_cached_value('Company',  company,  "default_currency")
		for each in acc:
			each["company_currency"] = company_currency
			each["balance"] = flt(get_balance_on(each.get("value"), in_account_currency=False))

			if each.account_currency != company_currency:
				each["balance_in_account_currency"] = flt(get_balance_on(each.get("value")))

	return acc

def create_payment_gateway_account(gateway):
	from erpnext.setup.setup_wizard.operations.company_setup import create_bank_account

	company = frappe.db.get_value("Global Defaults", None, "default_company")
	if not company:
		return

	# NOTE: we translate Payment Gateway account name because that is going to be used by the end user
	bank_account = frappe.db.get_value("Account", {"account_name": _(gateway), "company": company},
		["name", 'account_currency'], as_dict=1)

	if not bank_account:
		# check for untranslated one
		bank_account = frappe.db.get_value("Account", {"account_name": gateway, "company": company},
			["name", 'account_currency'], as_dict=1)

	if not bank_account:
		# try creating one
		bank_account = create_bank_account({"company_name": company, "bank_account": _(gateway)})

	if not bank_account:
		frappe.msgprint(_("Payment Gateway Account not created, please create one manually."))
		return

	# if payment gateway account exists, return
	if frappe.db.exists("Payment Gateway Account",
		{"payment_gateway": gateway, "currency": bank_account.account_currency}):
		return

	try:
		frappe.get_doc({
			"doctype": "Payment Gateway Account",
			"is_default": 1,
			"payment_gateway": gateway,
			"payment_account": bank_account.name,
			"currency": bank_account.account_currency
		}).insert(ignore_permissions=True)

	except frappe.DuplicateEntryError:
		# already exists, due to a reinstall?
		pass

@frappe.whitelist()
def update_number_field(doctype_name, name, field_name, number_value, company):
	'''
		doctype_name = Name of the DocType
		name = Docname being referred
		field_name = Name of the field thats holding the 'number' attribute
		number_value = Numeric value entered in field_name

		Stores the number entered in the dialog to the DocType's field.

		Renames the document by adding the number as a prefix to the current name and updates
		all transaction where it was present.
	'''
	doc_title = frappe.db.get_value(doctype_name, name, frappe.scrub(doctype_name)+"_name")

	validate_field_number(doctype_name, name, number_value, company, field_name)

	frappe.db.set_value(doctype_name, name, field_name, number_value)

	if doc_title[0].isdigit():
		separator = " - " if " - " in doc_title else " "
		doc_title = doc_title.split(separator, 1)[1]

	frappe.db.set_value(doctype_name, name, frappe.scrub(doctype_name)+"_name", doc_title)

	new_name = get_autoname_with_number(number_value, doc_title, name, company)

	if name != new_name:
		frappe.rename_doc(doctype_name, name, new_name)
		return new_name

def validate_field_number(doctype_name, name, number_value, company, field_name):
	''' Validate if the number entered isn't already assigned to some other document. '''
	if number_value:
		if company:
			doctype_with_same_number = frappe.db.get_value(doctype_name,
				{field_name: number_value, "company": company, "name": ["!=", name]})
		else:
			doctype_with_same_number = frappe.db.get_value(doctype_name,
				{field_name: number_value, "name": ["!=", name]})
		if doctype_with_same_number:
			frappe.throw(_("{0} Number {1} already used in account {2}")
				.format(doctype_name, number_value, doctype_with_same_number))

def get_autoname_with_number(number_value, doc_title, name, company):
	''' append title with prefix as number and suffix as company's abbreviation separated by '-' '''
	if name:
		name_split=name.split("-")
		parts = [doc_title.strip(), name_split[len(name_split)-1].strip()]
	else:
		abbr = frappe.get_cached_value('Company',  company,  ["abbr"], as_dict=True)
		parts = [doc_title.strip(), abbr.abbr]
	if cstr(number_value).strip():
		parts.insert(0, cstr(number_value).strip())
	return ' - '.join(parts)

@frappe.whitelist()
def get_coa(doctype, parent, is_root, chart=None):
	from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import build_tree_from_json

	# add chart to flags to retrieve when called from expand all function
	chart = chart if chart else frappe.flags.chart
	frappe.flags.chart = chart

	parent = None if parent==_('All Accounts') else parent
	accounts = build_tree_from_json(chart) # returns alist of dict in a tree render-able form

	# filter out to show data for the selected node only
	accounts = [d for d in accounts if d['parent_account']==parent]

	return accounts

def get_allow_cost_center_in_entry_of_bs_account():
	def generator():
		return cint(frappe.db.get_value('Accounts Settings', None, 'allow_cost_center_in_entry_of_bs_account'))
	return frappe.local_cache("get_allow_cost_center_in_entry_of_bs_account", (), generator, regenerate_if_none=True)

def get_stock_accounts(company):
	return frappe.get_all("Account", filters = {
		"account_type": "Stock",
		"company": company
	})