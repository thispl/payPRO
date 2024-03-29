// Copyright (c) 2020, Teampro and contributors
// For license information, please see license.txt

cur_frm.add_fetch('employee', 'employee_name', 'employee_name');
cur_frm.add_fetch('employee', 'department', 'department');

frappe.ui.form.on('Compensatory Leave Request', {
	refresh: function(frm) {
		frm.set_query("leave_type", function() {
			return {
				filters: {
					"is_compensatory": true
				}
			};
		});
	},
	half_day: function(frm) {
		if(frm.doc.half_day == 1){
			frm.set_df_property('half_day_date', 'reqd', true);
		}
		else{
			frm.set_df_property('half_day_date', 'reqd', false);
		}
	}
});
