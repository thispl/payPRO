# -*- coding: utf-8 -*-
# Copyright (c) 2020, Teampro and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt
from paypro.paypro.utils import validate_tax_declaration, get_total_exemption_amount, calculate_hra_exemption_for_period

class EmployeeTaxExemptionProofSubmission(Document):
	def validate(self):
		validate_tax_declaration(self.tax_exemption_proofs)
		self.set_total_actual_amount()
		self.set_total_exemption_amount()
		self.calculate_hra_exemption()

	def set_total_actual_amount(self):
		self.total_actual_amount = flt(self.get("house_rent_payment_amount"))
		for d in self.tax_exemption_proofs:
			self.total_actual_amount += flt(d.amount)

	def set_total_exemption_amount(self):
		self.exemption_amount = get_total_exemption_amount(self.tax_exemption_proofs)

	def calculate_hra_exemption(self):
		self.monthly_hra_exemption, self.monthly_house_rent, self.total_eligible_hra_exemption = 0, 0, 0
		if self.get("house_rent_payment_amount"):
			hra_exemption = calculate_hra_exemption_for_period(self)
			if hra_exemption:
				self.exemption_amount += hra_exemption["total_eligible_hra_exemption"]
				self.monthly_hra_exemption = hra_exemption["monthly_exemption"]
				self.monthly_house_rent = hra_exemption["monthly_house_rent"]
				self.total_eligible_hra_exemption = hra_exemption["total_eligible_hra_exemption"]