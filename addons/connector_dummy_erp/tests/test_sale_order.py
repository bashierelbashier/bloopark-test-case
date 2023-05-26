from odoo.tests import tagged, TransactionCase
from odoo.fields import Command


@tagged('post_install', '-at_install')
class TestSaleOrder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_name = 'Product Test Name'
        cls.product_code = 'PTN'
        cls.product = cls.env['product.product'].create({
            'name': cls.product_name,
            'default_code': cls.product_code,
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner',
        })
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'dummy_erp_id': False,
            'order_line': [
                Command.create({
                    'product_id': cls.product.id,
                })
            ]
        })

    def test_sale_order_needs_to_be_dummy_erp_updated(self):
        update_to_dummy_erp = self.order.update_to_dummy_erp
        self.assertEqual(update_to_dummy_erp, True,
                         "When order created it should be by default update to dummy ERP if it does "
                         "not have dummy ERP ID")
    # TODO: Finish testing sale order
