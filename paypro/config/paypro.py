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
				{
					"type": "doctype",
					"name": "Attendance Request",
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
					"name": "Compensatory Leave Request",
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
					"name": "Leave Encashment",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Leave Block List",
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
				{
					"type": "doctype",
					"name": "Retention Bonus",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Employee Incentive",
					"description": _("paypro"),
					"onboard": 1,
				},          
            ]
        },
		{
			"label": _("Employee Benefit"),
			"items": [                
                {
					"type": "doctype",
					"name": "Employee Benefit Application",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Employee Benefit Claim",
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
			"label": _("Recruitment"),
			"items": [
                {
					"type": "doctype",
					"name": "Job Opening",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "Job Applicant",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Job Offer",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Staffing Plan",
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
			"label": _("Shift Management"),
			"items": [                
                {
					"type": "doctype",
					"name": "Shift Type",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Shift Request",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Shift Assignment",
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
				{
					"type": "doctype",
					"name": "Holiday List",
					"description": _("paypro"),
					"onboard": 1,
				},
            ]
        },
		{
			"label": _("Accounting"),
			"items": [
                {
					"type": "doctype",
					"name": "Account",
					"description": _("paypro"),
					"onboard": 1,
				},
                {
					"type": "doctype",
					"name": "Mode of Payment",
					"description": _("paypro"),
					"onboard": 1,
				},
				{
					"type": "doctype",
					"name": "Fiscal Year",
					"description": _("paypro"),
					"onboard": 1,
				},
            ]
        },
    ]
