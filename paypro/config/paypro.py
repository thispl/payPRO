from frappe import _

def get_data():
    return [
        {
			"label": _("Employee"),
			"items": [
                {
					"type": "doctype",
					"name": "Employee",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Branch",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Department",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Designation",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "Shift Type",
					"description": _("paypro"),
					"onboard": 1,
				},               
            ]
        },
        {
			"label": _("Attendance"),
			"items": [
                {
					"type": "doctype",
					"name": "Attendance",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "Employee Checkin",
					"description": _("paypro"),
					"onboard": 1,
				},
            ]
        },
        {
			"label": _("Leaves"),
			"items": [
                {
					"type": "doctype",
					"name": "Leave Application",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Leave Allocation",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Leave Type",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "Leave Period",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Holiday List",
					"description": _("paypro"),
					"onboard": 1,
				},
               
            ]
        },
        {
			"label": _("Payroll"),
			"items": [
                {
					"type": "doctype",
					"name": "Salary Structure",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Salary Structure Assignment",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Payroll Entry",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Salary Slip",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "Additional Salary",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "Payroll Period",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "Salary Component",
					"description": _("paypro"),
					"onboard": 1,
				},           
            ]
        },
        {
			"label": _("Time Sheets"),
			"items": [
                {
					"type": "doctype",
					"name": "Timesheet",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "Activity Type",
					"description": _("paypro"),
					"onboard": 1,
				},                
            ]
        },
        {
			"label": _("Loans"),
			"items": [
                {
					"type": "doctype",
					"name": "Loan Application",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "Loan Type",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "Loan",
					"description": _("paypro"),
					"onboard": 1,
				},
            ]
        },
        {
			"label": _("Settings"),
			"items": [
                {
					"type": "doctype",
					"name": "Company",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "HR Settings",
					"description": _("paypro"),
					"onboard": 1,
				},
            ]
        },
    ]
