import base64
import requests

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"
    """
    We apply all operations on product template since the other ERP does not have attributes/variants, and whenever
    we need variant-specific attributes we use the product_variant_id field from product.template.
    """

    # Integration technical fields
    dummy_erp_integration_id = fields.Many2one("dummy.erp.integration", ondelete="restrict")
    dummy_erp_id = fields.Integer("ID In Dummy ERP")

    # Integration needed fields
    dummy_erp_brand = fields.Char("Dummy ERP Brand")
    dummy_erp_rating = fields.Float("Dummy ERP Rating")
    discount_percentage = fields.Float("Discount Percentage")
    dummy_erp_stock = fields.Float("Dummy ERP Stock")

    # Indicating whether this product should be updated in the dummy ERP. By default, created products should be synced.
    update_to_dummy_erp = fields.Boolean(default=True)

    # Override write function to mark record as update_to_dummy_erp if a relevant field was updated
    def write(self, vals):
        dummy_erp_fields = ["image_1920", "name", "description_sale", "list_price", "discount_percentage",
                            "dummy_erp_rating", "dummy_erp_brand", "product_categ_id", "dummy_erp_stock"]
        dummy_erp_updated_fields = [vals_field for
                                    vals_field in vals if vals_field in dummy_erp_fields]
        res = super(ProductTemplate, self).write(vals)
        if len(dummy_erp_updated_fields) > 0 and not self.env.context.get('do_not_update_dummy_erp', False):
            self.update_to_dummy_erp = True
        return res

    @api.model
    def get_products_to_update(self):
        """
        Get the products that need to be updated in the remote Dummy ERP
        :return: list of dicts containing product payload compatible with remote Dummy ERP
        """
        products = self.search([("update_to_dummy_erp", "=", True)])
        return self.prepare_dummy_erp_payload(products)

    @api.model
    def get_product_id_by_dummy_erp_id(self, dummy_erp_id):
        """
        Get the product.product id from Odoo using the id of Dummy ERP
        :param dummy_erp_id: integer representing record id in the remote Dummy ERP
        :return: product.product object or False
        """
        return self.search([("dummy_erp_id", "=", dummy_erp_id)], limit=1).product_variant_id

    @api.model
    def get_category_by_name(self, categ_name):
        """
        Get the id of the product.category with the provided name, if it exists return it if not create it then return
        the id.
        :param categ_name: string: the name of the product category to retrieve
        :return: integer: product category id
        """
        categ_object = self.env["product.category"]
        categ_id = categ_object.search([("name", "=", categ_name)], limit=1)
        if categ_id:
            return categ_id.id
        else:
            return categ_object.create({"name": categ_name}).id

    @api.model
    def prepare_dummy_erp_payload(self, recs):
        """
        Prepare the payload for the remote Dummy ERP
        :param recs: record set containing products to prepare payload from
        :return: List of dictionaries containing product payloads
        """
        payload = []
        base_url = self.get_base_url()
        for rec in recs:
            payload.append({
                "product_obj": rec,
                "title": rec.name,
                "description": rec.description_sale or "",
                "price": rec.list_price,
                "discountPercentage": rec.discount_percentage or 0.0,
                "rating": rec.dummy_erp_rating or 0.0,
                "stock": rec.dummy_erp_stock or 0.0,
                "brand": rec.dummy_erp_brand or "",
                "category": rec.categ_id.name,
                "thumbnail": base_url + f'/web/image/product.template/{rec.id}/image_128',
                "images": [
                    base_url + f'/web/image/product.template/{rec.id}/image_128',
                    base_url + f'/web/image/product.template/{rec.id}/image_256',
                    base_url + f'/web/image/product.template/{rec.id}/image_512',
                    base_url + f'/web/image/product.template/{rec.id}/image_1024',
                    base_url + f'/web/image/product.template/{rec.id}/image_1920'
                ]
            })
        return payload

    @api.model
    def create_or_update_from_dummy_erp_payload(self, integration_id, payload):
        """
        Create product if it does not exist and update it if it does exist, this function calls the other function
        prepare_dicts_from_dummy_erp_payload to prepare the odoo-compatible creation dictionaries
        :param integration_id: dummy.erp.integration object
        :param payload: list of dicts imported from the remote Dummy ERP
        :return: None
        """
        products = self.prepare_dicts_from_dummy_erp_payload(integration_id, payload)
        for product_dict in products:
            if product_dict["id"]:
                product_obj = self.search(
                    [("dummy_erp_id", "=", product_dict["id"])], limit=1
                )
                product_dict.pop('id')
                if product_obj:
                    product_obj.with_context(do_not_update_dummy_erp=True).write(product_dict)
                else:
                    self.create(product_dict)

    @api.model
    def prepare_dicts_from_dummy_erp_payload(self, integration_id, payload):
        """
        Prepare the odoo-compatible dictionaries for creating or writing products
        :param integration_id: dummy.erp.integration object
        :param payload: list of dictionaries containing products' data imported from Dummy ERP
        :return:
        """
        product_dicts = []
        for product in payload:
            image_1920 = False
            if len(product["images"]) > 0:
                # Get image data from URL
                image_1920 = base64.b64encode(requests.get(product["images"][0]).content)
            product_dicts.append({
                "id": product["id"],
                "name": product["title"],
                # Since all products have stock attribute then they all should be stored
                "detailed_type": "product",
                "list_price": product["price"],
                "description_sale": product["description"],
                "taxes_id": integration_id.default_tax_ids.ids,
                "categ_id": self.get_category_by_name(product["category"]),
                "dummy_erp_rating": product["rating"],
                "dummy_erp_brand": product["brand"],
                "dummy_erp_stock": product["stock"],
                "dummy_erp_id": product["id"],
                # Synced products don't need to be updated in dummy ERP because when they arrive they are same
                "update_to_dummy_erp": False,
                "dummy_erp_integration_id": integration_id.id,
                "image_1920": image_1920,
                # Enable all products in website for users to create them
                "website_published": True
            })
        return product_dicts
