from odoo import models, api


class SaleOrderLine(models.Model):
    _inherit = ["sale.order.line"]

    # Override write function to mark record as update_to_dummy_erp if a relevant field was updated
    def write(self, vals):
        dummy_erp_fields = ["product_uom_qty", "price_unit", "product_id", "discount"]
        dummy_erp_updated_fields = [vals_field for
                                    vals_field in vals if vals_field in dummy_erp_fields]
        res = super(SaleOrderLine, self).write(vals)

        order_id = self.order_id

        # Check if the partner of this order is a dummy ERP user to mark it as a "to update" order
        user_id = order_id.partner_id.user_ids[0] if len(order_id.partner_id.user_ids) > 0 else False
        if len(dummy_erp_updated_fields) > 0 and not self.env.context.get('do_not_update_dummy_erp',
                                                                          False) and user_id and user_id.dummy_erp_id:
            order_id.update_to_dummy_erp = True
        return res

    # TODO: Override method for batch creation
    # Override create function to mark record as update_to_dummy_erp in the relevant order_id
    @api.model
    def create(self, vals):
        res = super(SaleOrderLine, self).create(vals)
        res.order_id.update_to_dummy_erp = True
        return res
