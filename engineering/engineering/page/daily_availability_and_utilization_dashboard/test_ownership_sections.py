import unittest


from engineering.engineering.page.daily_availability_and_utilization_dashboard.ownership_sections import (
    get_ownership_average_sections,
    should_show_spare_average_section,
)


class TestOwnershipAverageSections(unittest.TestCase):
    def test_all_assets_keeps_company_and_supplier_averages_separate(self):
        self.assertEqual(
            get_ownership_average_sections("All Assets"),
            (
                (
                    "Isambane & Excavo Assets",
                    "Isambane & Excavo Assets - Average per Category",
                ),
                (
                    "Suppliers Assets",
                    "Supplier Assets - Average per Category",
                ),
            ),
        )

    def test_company_assets_never_requests_supplier_averages(self):
        self.assertEqual(
            get_ownership_average_sections("Isambane & Excavo Assets"),
            (
                (
                    "Isambane & Excavo Assets",
                    "Isambane & Excavo Assets - Average per Category",
                ),
            ),
        )

    def test_supplier_assets_never_show_a_spare_average_section(self):
        self.assertFalse(
            should_show_spare_average_section("Suppliers Assets")
        )
        self.assertTrue(
            should_show_spare_average_section("Isambane & Excavo Assets")
        )


if __name__ == "__main__":
    unittest.main()
