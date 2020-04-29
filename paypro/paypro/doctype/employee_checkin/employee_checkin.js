// Copyright (c) 2020, Teampro and contributors
// For license information, please see license.txt

cur_frm.add_fetch('employee','employee_name','employee_name');
cur_frm.add_fetch('employee','department','department');
cur_frm.add_fetch('employee','designation','designation');


frappe.ui.form.on('Employee Checkin', {
	setup: (frm) => {
		if(!frm.doc.time) {
			frm.set_value("time", frappe.datetime.now_datetime());
		}
	}
});
