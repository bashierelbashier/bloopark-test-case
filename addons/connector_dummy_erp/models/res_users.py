import requests
import base64

from odoo import api, fields, models, SUPERUSER_ID, _

from .api_client import perform_request
from .dummy_erp_integration import DUMMY_JSON_PATHS


class ResUsers(models.Model):
    _inherit = "res.users"

    # Integration technical fields
    dummy_erp_integration_id = fields.Many2one("dummy.erp.integration", ondelete="restrict")
    dummy_erp_id = fields.Integer("ID In Dummy ERP")

    # Integration needed fields
    first_name = fields.Char("First Name")
    last_name = fields.Char("Last Name")
    maiden_name = fields.Char("Maiden Name")
    age = fields.Integer("Age")
    gender = fields.Char("Gender")
    birth_date = fields.Date("Birth Date")
    blood_group = fields.Char("Blood Group")
    height = fields.Float("Height")
    weight = fields.Float("Weight")
    eye_color = fields.Char("Eye Color")
    university = fields.Char("University")

    @api.model
    def create_or_update_from_dummy_erp_payload(self, integration_id, payload):
        """
        Create or update the users from the payload of Dummy ERP, if user exists update record if not then create it.
        :param integration_id: dummy.erp.integration object
        :param payload: list of dicts imported from Dummy ERP containing users values
        :return: None
        """
        users = self.prepare_dicts_from_dummy_erp_payload(integration_id, payload)
        for user_dict in users:
            if user_dict["id"]:
                user_obj = self.search(
                    [("dummy_erp_id", "=", user_dict["id"])], limit=1
                )
                user_dict.pop('id')
                password = user_dict.pop("password")
                if user_obj:
                    user_obj.write(user_dict)
                else:
                    user_obj = self.create(user_dict)
                user_obj._change_password(password)

    @api.model
    def prepare_dicts_from_dummy_erp_payload(self, integration_id, payload):
        """
        Prepare the creation dictionary from the payload imported from Dummy ERP
        :param integration_id: dummy.erp.integration object
        :param payload: dict with values imported from Dummy ERP
        :return: dict containing the values to create a user in Odoo
        """
        group_portal = self.env.ref("base.group_portal")
        user_dicts = []
        for user in payload:
            image_1920 = False
            name = user["firstName"] or "" + user["maidenName"] or "" + user["lastName"] or ""
            if "image" in user:
                # Get image data from URL
                image_1920 = base64.b64encode(requests.get(user["image"]).content)
            user_dicts.append({
                "id": user["id"],
                "groups_id": [(4, group_portal.id)],
                "image_1920": image_1920,
                "name": name,
                "first_name": user["firstName"],
                "last_name": user["lastName"],
                "maiden_name": user["maidenName"],
                "email": user["email"],
                "login": user["username"],
                "password": user["password"],
                "age": user["age"],
                "gender": user["gender"],
                "birth_date": user["birthDate"],
                "blood_group": user["bloodGroup"],
                "height": user["height"],
                "weight": user["weight"],
                "eye_color": user["eyeColor"],
                "university": user["university"],
                "dummy_erp_integration_id": integration_id.id,
                "dummy_erp_id": user["id"]
            })
        return user_dicts

    # Override log in function to import carts when user with dummy_erp_id successfully logs in
    @classmethod
    def _login(cls, db, login, password, user_agent_env):
        res = super(ResUsers, cls)._login(db, login, password, user_agent_env=user_agent_env)
        if res:
            with cls.pool.cursor() as cr:
                self = api.Environment(cr, SUPERUSER_ID, {})[cls._name]
                self.env["res.users"].search([("id", "=", res)], limit=1).get_dummy_erp_user_carts()
        return res

    def get_dummy_erp_user_carts(self):
        """
        Get user carts if he has any pending carts in the dummy ERP
        :return: None
        """
        if self.dummy_erp_integration_id and self.dummy_erp_id:
            integration = self.dummy_erp_integration_id
            try:
                response = perform_request(integration, "GET", {},
                                           DUMMY_JSON_PATHS["get_user_carts"] % self.dummy_erp_id)
                if (
                        200 <= response.status_code < 300
                        and "carts" in response.json()
                ):
                    payload = response.json()["carts"]
                    if len(payload) > 0:
                        self.env["sale.order"].sudo().create_from_dummy_erp_payload(
                            self, integration, payload
                        )
                    integration.log_operation(
                        _("Get User Carts"),
                        (
                            f"User {self.name} carts imported successfully {response.json()['carts']}"
                        ),
                        "info",
                    )
                else:
                    integration.log_operation(
                        _("Import User Carts"),
                        (f"Exception: {str(response.content)}"),
                        "error",
                    )

            except Exception as exc:
                integration.log_operation(
                    _("Import User Carts"),
                    (f"Exception: {str(exc)}"),
                    "error",
                )
