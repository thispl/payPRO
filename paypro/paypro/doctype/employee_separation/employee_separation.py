# -*- coding: utf-8 -*-
# Copyright (c) 2020, Teampro and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from paypro.paypro.utils import EmployeeBoardingController

class EmployeeSeparation(EmployeeBoardingController):
	def validate(self):
		super(EmployeeSeparation, self).validate()

	def on_submit(self):
		super(EmployeeSeparation, self).on_submit()

	def on_update_after_submit(self):
		self.create_task_and_notify_user()

	def on_cancel(self):
		super(EmployeeSeparation, self).on_cancel()
