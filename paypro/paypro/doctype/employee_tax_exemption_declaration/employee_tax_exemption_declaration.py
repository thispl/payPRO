# -*- coding: utf-8 -*-
# Copyright (c) 2020, Teampro and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt
from frappe.model.mapper import get_mapped_doc
from paypro.paypro.utils import validate_tax_declaration, get_total_exemption_amount, calculate_annual_eligible_hra_exemption

class DuplicateDeclarationError(frappe.ValidationError): pass

class EmployeeTaxExemptionDeclaration(Document):
	def validate(self):
		validate_tax_declaration(self.declarations)
		self.validate_duplicate()
		self.set_total_declared_amount()
		self.set_total_exemption_amount()
		self.calculate_hra_exemption()

	def validate_duplicate(self):
		duplicate = frappe.db.get_value("Employee Tax Exemption Declaration",
			filters = {
				"employee": self.employee,
				"payroll_period": self.payroll_period,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2]
			}
		)
		if duplicate:
			frappe.throw(_("Duplicate Tax Declaration of {0} for period {1}")
				.format(self.employee, self.payroll_period), DuplicateDeclarationError)

	def set_total_declared_amount(self):
		self.total_declared_amount = 0.0
		for d in self.declarations:
			self.total_declared_amount += flt(d.amount)

	def set_total_exemption_amount(self):
		self.total_exemption_amount = get_total_exemption_amount(self.declarations)

	def calculate_hra_exemption(self):
		self.salary_structure_hra, self.annual_hra_exemption, self.monthly_hra_exemption = 0, 0, 0
		if self.get("monthly_house_rent"):
			hra_exemption = calculate_annual_eligible_hra_exemption(self)
			if hra_exemption:
				self.total_exemption_amount += hra_exemption["annual_exemption"]
				self.salary_structure_hra = hra_exemption["hra_amount"]
				self.annual_hra_exemption = hra_exemption["annual_exemption"]
				self.monthly_hra_exemption = hra_exemption["monthly_exemption"]

@frappe.whitelist()
def make_proof_submission(source_name, target_doc=None):
	doclist = get_mapped_doc("Employee Tax Exemption Declaration", source_name, {
		"Employee Tax Exemption Declaration": {
			"doctype": "Employee Tax Exemption Proof Submission",
			"field_no_map": ["monthly_house_rent", "monthly_hra_exemption"]
		},
		"Employee Tax Exemption Declaration Category": {
			"doctype": "Employee Tax Exemption Proof Submission Detail",
			"add_if_empty": True
		}
	}, target_doc)

	return doclist
