frappe.query_reports["Availability & Utilisation Report"] = {
  tree: true,
  name_field: "category",
  initial_depth: 1,

  filters: [
    {
      fieldname: "site",
      label: "Site",
      fieldtype: "Link",
      options: "Location",
      reqd: 0
    },
    {
      fieldname: "from_date",
      label: "Start Date",
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.add_days(frappe.datetime.get_today(), -7)
    },
    {
      fieldname: "to_date",
      label: "End Date",
      fieldtype: "Date",
      reqd: 1,
      default: frappe.datetime.get_today()
    },

    {
      fieldname: "hourly",
      label: "Hourly",
      fieldtype: "Select",
      options: [
        "",
        "06:00 am",
        "07:00 am",
        "08:00 am",
        "09:00 am",
        "10:00 am",
        "11:00 am",
        "12:00 am",
        "13:00 pm",
        "14:00 pm",
        "15:00 pm",
        "16:00 pm",
        "17:00 pm",
        "18:00 pm",
        "19:00 pm",
        "20:00 pm",
        "21:00 pm",
        "22:00 pm",
        "23:00 pm",
        "00:00 am",
        "01:00 am",
        "02:00 am",
        "03:00 am",
        "04:00 am",
        "05:00 am",
        "06:00 am (next day)"
      ],
      default: "",
      reqd: 0
    },

    {
      fieldname: "two_hourly",
      label: "Two hourly",
      fieldtype: "Select",
      options: [
        "",
        "06:00 am To 07:00 am",
        "07:00 am To 08:00 am",
        "08:00 am To 09:00 am",
        "09:00 am To 10:00 am",
        "10:00 am To 11:00 am",
        "11:00 am To 12:00 am",
        "12:00 am To 13:00 pm",
        "13:00 pm To 14:00 pm",
        "14:00 pm To 15:00 pm",
        "15:00 pm To 16:00 pm",
        "16:00 pm To 17:00 pm",
        "17:00 pm To 18:00 pm",
        "18:00 pm To 19:00 pm",
        "19:00 pm To 20:00 pm",
        "20:00 pm To 21:00 pm",
        "21:00 pm To 22:00 pm",
        "22:00 pm To 23:00 pm",
        "23:00 pm To 00:00 am",
        "00:00 am To 01:00 am",
        "01:00 am To 02:00 am",
        "02:00 am To 03:00 am",
        "03:00 am To 04:00 am",
        "04:00 am To 05:00 am",
        "05:00 am To 06:00 am",
        "06:00 am To 07:00 am (next day)"
      ],
      default: "",
      reqd: 0
    },

    {
      fieldname: "all_sites",
      label: "All Sites",
      fieldtype: "Check",
      default: 0
    }
  ]
};