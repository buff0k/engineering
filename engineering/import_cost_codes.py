import frappe


COST_CODES = [
    ("2400", "Diesel"),
    ("2401", "Oil"),
    ("2402", "Grease"),
    ("3000", "Accounting Fees"),
    ("3025", "Advertising"),
    ("3050", "Audit Fees"),
    ("3070", "Awards"),
    ("3100", "Accomodation"),
    ("3150", "Admin Charges"),
    ("3155", "Assessment Rates"),
    ("3160", "Minor Assets - Various"),
    ("3161", "Minor Assets - Tools"),
    ("3162", "Minor Assets - Furniture"),
    ("3200", "Bank Charges"),
    ("3215", "BEE Costs"),
    ("3220", "Community upliftment"),
    ("3240", "Communication Equipment"),
    ("3250", "Computer, Printing & Accessories"),
    ("3300", "Consultig Fees"),
    ("3310", "Consumables"),
    ("3320", "Commission"),
    ("3340", "Cleaning"),
    ("3350", "Donations"),
    ("3351", "Donations - Sect. 18A"),
    ("3355", "Debt Collection"),
    ("3470", "Drilling, Blasting & Explosives"),
    ("3471", "Drilling - Accessories"),
    ("3500", "Equipment Rental - ROP's"),
    ("3501", "Equipment Rental - Plant Hire"),
    ("3502", "Equipment Rental - Plant Hire Isambane"),
    ("3503", "Equipment Rental - Plant Hire Msobo"),
    ("3504", "Equipment Rental - Toilet Hire"),
    ("3505", "Equipment Rental - Light Plant"),
    ("3506", "Equipment Rental - Pump Hire"),
    ("3507", "Equipment Rental - Other"),
    ("3509", "Equipment Rental - OEM"),
    ("3550", "Embezzlement/Theft"),
    ("3600", "Entertainment"),
    ("3650", "Electricity & Water"),
    ("3700", "Fleet Management"),
    ("3705", "Garden maintenance"),
    ("3710", "Gifts & Flowers"),
    ("3800", "Insurance"),
    ("3810", "Injury on Duty Costs"),
    ("3850", "Environmental Costs"),
    ("3900", "Interest Paid"),
    ("3901", "Labour Hire"),
    ("3902", "Legal Fees"),
    ("3903", "Licenses"),
    ("3905", "Licks & feeds"),
    ("3907", "Learnerships"),
    ("3908", "Medical & Induction Fees"),
    ("3910", "Motorvehicles - Petrol, Oil, Toll"),
    ("3915", "Placement Fees"),
    ("3920", "Printing and Stationary"),
    ("3930", "Professional Fees"),
    ("3940", "Protective Clothing"),
    ("3960", "Postage"),
    ("4300", "Rent Premises"),
    ("4330", "Rent Mailbox"),
    ("4350", "Repairs and Maintenance - W/S & General"),
    ("4351", "R & M Buildings"),
    ("4356", "Crushers & Screens - GET"),
    ("4362", "Crushers & Screens - R & M"),
    ("4364", "Damages - All Equipment"),
    ("4382", "LDV & Busses - Tyres"),
    ("4384", "LDV & Busses - R & M"),
    ("4393", "Sup. Equip. - Tyres"),
    ("4395", "Sup. Equip. - R & M"),
    ("4404", "Trucks - Tyres"),
    ("4405", "Trucks - Suspension"),
    ("4406", "Trucks - R & M"),
    ("4407", "Excavators - GET"),
    ("4408", "Excavators - R & M"),
    ("4409", "Dozers - GET"),
    ("4410", "Dozers - R & M"),
    ("4411", "ADT's - GET"),
    ("4412", "ADT's - Tyres"),
    ("4413", "ADT's - R & M"),
    ("4414", "Loaders - GET"),
    ("4415", "Loaders - Tyres"),
    ("4416", "Loaders - R & M"),
    ("4417", "Graders - GET"),
    ("4418", "Graders - Tyres"),
    ("4419", "Graders - R & M"),
    ("4420", "Trailers - Tyres"),
    ("4421", "Trailers - Suspension"),
    ("4422", "Trailers - R & M"),
    ("4430", "Sample Testing"),
    ("4440", "Security"),
    ("4480", "Site Establishment"),
    ("4500", "Subscription Fees"),
    ("4525", "Staff Welfare"),
    ("4603", "Upset Allowances"),
    ("4610", "Casual Wages"),
    ("4700", "Telephoneand Cell Phone"),
    ("4710", "Subcontractors"),
    ("4725", "Training"),
    ("4730", "Traffic Fines"),
    ("4740", "Transport of Equipment to Sites"),
    ("4760", "Employee Transport Expenses"),
    ("4765", "Travel - Local"),
    ("4770", "Travel - Overseas"),
    ("5310", "Imbalenthe Loan Account"),
    ("5380", "Excavo Loan Account"),
    ("5450", "Umsizi Loan Account"),
    ("5465", "Capstone Loan Account"),

    ("001", "M15"),
    ("002", "BNK"),
    ("003", "OTR"),
    ("004", "UIT"),
    ("005", "RDP"),
    ("008", "MIW/WORKSHOP"),
    ("009", "GRN"),
    ("012", "KRR"),
    ("015", "MID/HEAD OFFICE"),
    ("017", "GWB"),
    ("019", "KLP"),
    ("022", "KOP"),
    ("026", "WON"),
    ("029", "BFT"),
    ("031", "HKP"),
    ("034", "MIM"),
]


def import_cost_codes():
    created = 0
    updated = 0
    skipped = 0

    for code, component in COST_CODES:
        existing_name = frappe.db.exists("Cost Code Sheet", {"cost_code": code})

        if existing_name:
            doc = frappe.get_doc("Cost Code Sheet", existing_name)

            if doc.component != component:
                doc.component = component
                doc.save(ignore_permissions=True)
                updated += 1
            else:
                skipped += 1
        else:
            doc = frappe.get_doc({
                "doctype": "Cost Code Sheet",
                "cost_code": code,
                "component": component
            })
            doc.insert(ignore_permissions=True)
            created += 1

    frappe.db.commit()

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "total": len(COST_CODES)
    }
