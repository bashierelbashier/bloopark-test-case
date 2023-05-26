{
    "name": "Dummy ERP Connector",
    "version": "16.0.0.1",
    "summary": "Connect dummyjson API with Odoo.",
    "author": "Bashier Elbashier",
    "license": "Other proprietary",
    "installable": True,
    "application": True,
    "depends": ["base", "sale", "website_sale", "stock", "product", "sale_stock"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/dummy_erp_integration_views.xml",
        "views/dummy_erp_integration_log_views.xml",
        "views/product_template_views.xml"
    ],
}
