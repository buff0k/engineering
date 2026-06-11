frappe.query_reports["Leave Export Report"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1
		}
	],

	onload: function(report) {
		const button = report.page.add_inner_button(__("Export Sage VIP TXT"), function() {
			const filters = report.get_values();

			if (!filters.from_date || !filters.to_date) {
				frappe.msgprint(__("Please select From Date and To Date first."));
				return;
			}

			frappe.call({
				method: "engineering.engineering.report.leave_export_report.leave_export_report.export_sage_vip_txt",
				args: {
					from_date: filters.from_date,
					to_date: filters.to_date
				},
				callback: function(r) {
					if (r.message && r.message.file_url) {
						frappe.msgprint(__("Exported {0} rows.", [r.message.rows]));

						const link = document.createElement("a");
						link.href = r.message.file_url;
						link.download = r.message.file_name || "LVEXP.txt";
						document.body.appendChild(link);
						link.click();
						document.body.removeChild(link);
					}
				}
			});
		});

		button.removeClass("btn-default").addClass("btn-success");
	}
};