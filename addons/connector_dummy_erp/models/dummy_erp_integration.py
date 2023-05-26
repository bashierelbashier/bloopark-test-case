from odoo import models, fields, api, _

from odoo.exceptions import ValidationError

from .api_client import perform_request

# Define path for each operation, we set limit=0 to get all
# records since they are not too much in this case; implementing
# pagination and resource limiting will be useless.
DUMMY_JSON_PATHS = {
    "test": "/test",
    "get_products": "/products?limit=0",
    "get_user_carts": "/users/%s/carts?limit=0",
    "get_users": "/users?limit=0",
    "update_cart": "/carts",
    "add_cart": "/carts/add",
    "update_product": "/products",
    "add_product": "/products/add"
}


class DummyERPIntegration(models.Model):
    _name = 'dummy.erp.integration'
    _description = 'Dummy ERP Integration'
    _inherit = ['mail.thread']

    """
    Dummy ERP Integration
    """
    # Default values computation methods
    def _default_pricelist(self):
        return self.env['product.pricelist'].search([('company_id', 'in', (False, self.env.company.id)),
                                                     ('currency_id', '=', self.env.company.currency_id.id)],
                                                    limit=1)

    # Basic integration fields
    name = fields.Char("Name", required=1)
    active = fields.Boolean("Active", default=False, tracking=True)
    base_url = fields.Char("Base Integration URL", default="https://dummyjson.com")

    # Automation fields
    auto_import_product = fields.Boolean("Auto Import Products", default=False, tracking=True)
    auto_import_user = fields.Boolean("Auto Import Users", default=False, tracking=True)
    auto_export_cart = fields.Boolean("Auto Export Carts", default=False, tracking=True)
    auto_export_product = fields.Boolean("Auto Export Products", default=False, tracking=True)

    # Cron IDS
    import_product_cron_id = fields.Many2one("ir.cron")
    import_user_cron_id = fields.Many2one("ir.cron")
    export_cart_cron_id = fields.Many2one("ir.cron")
    export_product_cron_id = fields.Many2one("ir.cron")

    # Smart buttons
    cron_ids = fields.One2many(
        "ir.cron", "dummy_erp_integration_id", context={"active_test": False}
    )
    cron_count = fields.Integer("Jobs", compute="_compute_cron_count")
    integration_log_ids = fields.One2many("dummy.erp.integration.log", "integration_id")

    # Business logic fields
    pricelist_id = fields.Many2one("product.pricelist", "Pricelist", default=_default_pricelist, tracking=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company.id)
    default_tax_ids = fields.Many2many("account.tax", string="Default Taxes", domain=[('type_tax_use', '=', 'sale')],
                                       tracking=True)

    ##################
    # Helper methods
    ##################
    def _get_base_url(self):
        """
        Helper method to return URL after removing the trailing '/' if it exists because paths already have it.
        :return:
        """
        self.ensure_one()
        if self.base_url[-1] == "/":
            return self.base_url[0:-1]
        else:
            return self.base_url

    def log_operation(self, subject, details, type):
        """
        Helper method used to create log entries for the integration object with passed parameters
        :param subject: Main operation title
        :param details: Long description for the log entry
        :param type: Entry type either error, warning, or info.
        :return: None
        """
        self.env["dummy.erp.integration.log"].sudo().create(
            {
                "integration_id": self.id,
                "name": subject,
                "details": details,
                "type": type,
            }
        )

    ######################
    # View records methods
    ######################
    def action_view_crons(self):
        action = self.env["ir.actions.actions"]._for_xml_id("base.ir_cron_act")
        action.update({"domain": [("dummy_erp_integration_id", "=", self.id)]})
        return action

    def _compute_cron_count(self):
        for rec in self:
            rec.cron_count = len(rec.cron_ids)

    def action_view_log(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "connector_dummy_erp.act_window_dummy_erp_log"
        )
        action.update({"domain": [("integration_id", "=", self.id)]})
        return action

    ################################################################
    # Technical methods
    ################################################################

    # TODO: Override method for batch creation
    # Override create to create cron jobs once integration created
    @api.model
    def create(self, vals):
        res = super(DummyERPIntegration, self).create(vals)
        res._create_dummy_erp_product_importer()
        res._create_dummy_erp_user_importer()
        res._create_dummy_erp_cart_exporter()
        res._create_dummy_erp_product_exporter()
        return res

    # Override write to change cron active status based on integration automation fields
    def write(self, vals):
        res = super(DummyERPIntegration, self).write(vals)
        if 'auto_import_product' in vals:
            self.import_product_cron_id.active = vals['auto_import_product']
        if 'auto_import_user' in vals:
            self.import_user_cron_id.active = vals['auto_import_user']
        if 'auto_export_cart' in vals:
            self.export_cart_cron_id.active = vals['auto_export_cart']
        if 'auto_export_product' in vals:
            self.export_product_cron_id.active = vals['auto_export_product']
        return res

    # Override toggle active to deactivate/activate all automation fields based on integration status
    def toggle_active(self):
        res = super(DummyERPIntegration, self).toggle_active()
        self.write({
            "auto_import_product": self.active,
            "auto_import_user": self.active,
            "auto_export_cart": self.active,
            "auto_export_product": self.active
        })
        return res

    def test_connection(self):
        """
        Test the connection of the given integration values by sending an HTTP request to the test path defined in the
        remote API.
        It raises and error if it cannot connect.
        :return: None
        """
        try:
            response = perform_request(self, "GET", {}, DUMMY_JSON_PATHS["test"])
            if 200 <= response.status_code < 300 and response.json()["status"]:
                message = _("Connection Test Successful!")
                self.log_operation(
                    _("Test Connection"),
                    message,
                    "info",
                )
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "message": message,
                        "type": "success",
                        "sticky": False,
                    },
                }
            elif response.json()["status"] == "error":
                message = response.json()["message"]["description"]
                self.log_operation(
                    _("Test Connection"),
                    message,
                    "error",
                )
                raise ValidationError(
                    _("The server refused the test connection with error: ") + message
                )
        except Exception as e:
            self.log_operation(
                _("Test Connection"),
                str(e),
                "error",
            )
            raise ValidationError(
                _("An error occurred testing connection: ") + str(e)
            )

    def _create_dummy_erp_product_importer(self):
        """
        Creates a new cron job which runs import products with the id of this object.
        """
        model_id = self.env["ir.model"].search([("model", "=", self._name)])
        cron_id = self.env["ir.cron"].create(
            dict(
                name=f"Dummy ERP Integration {self.name}: Import Products",
                model_id=model_id.id,
                interval_number=20,
                interval_type="minutes",
                active=False,
                numbercall=-1,
                state="code",
                code=f"model.import_dummy_products({self.id})",
            )
        )
        self.import_product_cron_id = cron_id.id
        cron_id.dummy_erp_integration_id = self

    def _create_dummy_erp_user_importer(self):
        """
        Creates a new cron job which runs import users with the id of this object.
        """
        model_id = self.env["ir.model"].search([("model", "=", self._name)])
        cron_id = self.env["ir.cron"].create(
            dict(
                name=f"Dummy ERP Integration {self.name}: Import Users",
                model_id=model_id.id,
                interval_number=20,
                interval_type="minutes",
                active=False,
                numbercall=-1,
                state="code",
                code=f"model.import_dummy_users({self.id})",
            )
        )
        self.import_user_cron_id = cron_id.id
        cron_id.dummy_erp_integration_id = self

    def _create_dummy_erp_cart_exporter(self):
        """
        Creates a new cron job which runs export carts with the id of this object.
        """
        model_id = self.env["ir.model"].search([("model", "=", self._name)])
        cron_id = self.env["ir.cron"].create(
            dict(
                name=f"Dummy ERP Integration {self.name}: Export Carts",
                model_id=model_id.id,
                interval_number=2,
                interval_type="minutes",
                active=False,
                numbercall=-1,
                state="code",
                code=f"model.export_dummy_carts({self.id})",
            )
        )
        self.export_cart_cron_id = cron_id.id
        cron_id.dummy_erp_integration_id = self

    def _create_dummy_erp_product_exporter(self):
        """
        Creates a new cron job which runs export products with the id of this object.
        """
        model_id = self.env["ir.model"].search([("model", "=", self._name)])
        cron_id = self.env["ir.cron"].create(
            dict(
                name=f"Dummy ERP Integration {self.name}: Export Products",
                model_id=model_id.id,
                interval_number=2,
                interval_type="minutes",
                active=False,
                numbercall=-1,
                state="code",
                code=f"model.export_dummy_products({self.id})",
            )
        )
        self.export_product_cron_id = cron_id.id
        cron_id.dummy_erp_integration_id = self

    ##########################
    # Business Logic methods: Importers
    ##########################
    @api.model
    def import_dummy_products(self, integration_id):
        """
        Import the products from the external ERP API, raise an error if something goes wrong.
        :param integration_id: dummy.erp.integration object
        :return: None
        """
        integration = self.with_context(active_test=False).search([("id", "=", integration_id)])
        try:
            response = perform_request(integration, "GET", {}, DUMMY_JSON_PATHS["get_products"])
            if (
                    200 <= response.status_code < 300
                    and "products" in response.json()
                    and len(response.json()["products"]) > 0
            ):
                payload = response.json()["products"]
                self.env["product.template"].create_or_update_from_dummy_erp_payload(
                    integration, payload
                )
                integration.log_operation(
                    _("Import Products"),
                    (
                        f"Products batch imported successfully {response.json()['products']}"
                    ),
                    "info",
                )

        except Exception as exc:
            integration.log_operation(
                _("Import Products"),
                (f"Exception: {str(exc)}"),
                "error",
            )

    @api.model
    def import_dummy_users(self, integration_id):
        """
        Import the user from the external ERP API, raise an error if something goes wrong.
        :param integration_id: dummy.erp.integration object
        :return: None
        """
        integration = self.with_context(active_test=False).search([("id", "=", integration_id)])
        try:
            response = perform_request(integration, "GET", {}, DUMMY_JSON_PATHS["get_users"])
            if (
                    200 <= response.status_code < 300
                    and "users" in response.json()
                    and len(response.json()["users"]) > 0
            ):
                payload = response.json()["users"]
                self.env["res.users"].create_or_update_from_dummy_erp_payload(
                    integration, payload
                )
                integration.log_operation(
                    _("Import Users"),
                    (
                        f"Users batch imported successfully {response.json()['users']}"
                    ),
                    "info",
                )

        except Exception as exc:
            integration.log_operation(
                _("Import Users"),
                (f"Exception: {str(exc)}"),
                "error",
            )

    ##########################
    # Business Logic methods: Exporters
    ##########################
    @api.model
    def export_dummy_products(self, integration_id):
        """
        Export only the updated products to the external ERP API, raise an error if something goes wrong.
        :param integration_id: dummy.erp.integration object
        :return: None
        """
        integration = self.with_context(active_test=False).search([("id", "=", integration_id)])
        products = self.env["product.template"].get_products_to_update()
        try:
            for product in products:
                payload = product
                product_obj = payload.pop("product_obj")
                if product_obj.dummy_erp_id:
                    path = f"{DUMMY_JSON_PATHS['update_product']}/{product_obj.dummy_erp_id}"
                    method = "PUT"
                else:
                    path = DUMMY_JSON_PATHS["add_product"]
                    method = "POST"
                response = perform_request(integration, method, payload, path)
                if 200 <= response.status_code < 300 and "id" in response.json():
                    product_obj.with_context(do_not_update_dummy_erp=True).write({
                        "dummy_erp_id": response.json()['id'],
                        "update_to_dummy_erp": False
                    })
                else:
                    raise ValidationError(
                        f"Cannot update product {product_obj.name} in dummy ERP"
                    )
            integration.log_operation(
                _("Update products in dummy ERP"),
                f"Products successfully updated in dummy ERP with payload: {str(products)}",
                "info",
            )
        except Exception as exc:
            integration.log_operation(
                _("Update products in dummy ERP"),
                (f"Exception: {str(exc)}"),
                "error",
            )

    @api.model
    def export_dummy_carts(self, integration_id):
        """
        Import only the updated carts to the external ERP API, raise an error if something goes wrong.
        :param integration_id: dummy.erp.integration object
        :return: None
        """
        integration = self.with_context(active_test=False).search([("id", "=", integration_id)])
        carts = self.env["sale.order"].get_carts_to_update()
        try:
            for cart in carts:
                payload = cart
                cart_obj = payload.pop("cart_obj")
                if cart_obj.dummy_erp_id:
                    path = f"{DUMMY_JSON_PATHS['update_cart']}/{cart_obj.dummy_erp_id}"
                    method = "PUT"
                    payload.pop("userId")
                else:
                    path = DUMMY_JSON_PATHS["add_cart"]
                    method = "POST"
                payload.pop("id")
                response = perform_request(integration, method, payload, path)
                if 200 <= response.status_code < 300 and "id" in response.json():
                    cart_obj.with_context(do_not_update_dummy_erp=True).write({
                        "dummy_erp_id": response.json()['id'],
                        "update_to_dummy_erp": False
                    })
                else:
                    raise ValidationError(
                        f"Cannot update cart {cart_obj.name} in dummy ERP: {response.content}"
                    )
            integration.log_operation(
                _("Update carts in dummy ERP"),
                f"Carts successfully updated in dummy ERP with payload: {str(carts)}",
                "info",
            )
        except Exception as exc:
            integration.log_operation(
                _("Update carts in dummy ERP"),
                (f"Exception: {str(exc)}"),
                "error",
            )
