// Copyright (c) 2020, Teampro and contributors
// For license information, please see license.txt

frappe.provide("paypro.job_offer");

frappe.ui.form.on("Job Offer", {
	onload: function (frm) {
		frm.set_query("select_terms", function() {
			return { filters: { hr: 1 } };
		});
	},

	setup: function (frm) {
		frm.email_field = "applicant_email";
	},

	select_terms: function (frm) {
		paypro.utils.get_terms(frm.doc.select_terms, frm.doc, function (r) {
			if (!r.exc) {
				frm.set_value("terms", r.message);
			}
		});
	},

	refresh: function (frm) {
		if ((!frm.doc.__islocal) && (frm.doc.status == 'Accepted')
			&& (frm.doc.docstatus === 1) && (!frm.doc.__onload || !frm.doc.__onload.employee)) {
			frm.add_custom_button(__('Create Employee'),
				function () {
					paypro.job_offer.make_employee(frm);
				}
			);
		}

		if(frm.doc.__onload && frm.doc.__onload.employee) {
			frm.add_custom_button(__('Show Employee'),
				function () {
					frappe.set_route("Form", "Employee", frm.doc.__onload.employee);
				}
			);
		}
	}

});

paypro.job_offer.make_employee = function (frm) {
	frappe.model.open_mapped_doc({
		method: "paypro.paypro.doctype.job_offer.job_offer.make_employee",
		frm: frm
	});
};
