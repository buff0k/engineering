IN_HOUSE_ASSETS = "Isambane & Excavo Assets"
SUPPLIER_ASSETS = "Suppliers Assets"
ALL_ASSETS = "All Assets"


def get_ownership_average_sections(asset_ownership):
    """Return the independently calculated ownership bands to display."""
    selected = asset_ownership or IN_HOUSE_ASSETS

    labels = {
        IN_HOUSE_ASSETS: "Isambane & Excavo Assets - Average per Category",
        SUPPLIER_ASSETS: "Supplier Assets - Average per Category",
    }

    scopes = (
        (IN_HOUSE_ASSETS, SUPPLIER_ASSETS)
        if selected == ALL_ASSETS
        else (selected,)
    )

    return tuple(
        (scope, labels.get(scope, f"{scope} - Average per Category"))
        for scope in scopes
    )
