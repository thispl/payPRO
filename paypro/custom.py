
from __future__ import unicode_literals
import frappe
from frappe import throw, _
from frappe.model.document import Document
import time
from datetime import timedelta
from frappe.utils import nowdate, get_last_day, getdate, add_days, add_years

@frappe.whitelist()
def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)+1):
        yield start_date + timedelta(n)

@frappe.whitelist()
def create_repayment_entry(loan, applicant, company, posting_date, loan_type,
	payment_type, interest_payable, payable_principal_amount, amount_paid, penalty_amount=None):

	lr = frappe.get_doc({
		"doctype": "Loan Repayment",
		"against_loan": loan,
		"payment_type": payment_type,
		"company": company,
		"posting_date": posting_date,
		"applicant": applicant,
		"penalty_amount": penalty_amount,
		"interets_payable": interest_payable,
		"payable_principal_amount": payable_principal_amount,
		"amount_paid": amount_paid,
		"loan_type": loan_type
	}).insert()

	return lr

@frappe.whitelist()
def calculate_amounts(against_loan, posting_date, payment_type):

	amounts = {
		'penalty_amount': 0.0,
		'interest_amount': 0.0,
		'pending_principal_amount': 0.0,
		'payable_principal_amount': 0.0,
		'payable_amount': 0.0,
		'due_date': ''
	}

	amounts = get_amounts(amounts, against_loan, posting_date, payment_type)

	return amounts

