from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestProduct(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_name = 'Product Test Name'
        cls.product_code = 'PTN'
        cls.product = cls.env['product.product'].create({
            'name': cls.product_name,
            'default_code': cls.product_code,
            'dummy_erp_id': False
        })

    def test_product_needs_to_be_updated(self):
        update_to_dummy_erp = self.product.update_to_dummy_erp
        self.assertEqual(update_to_dummy_erp, True,
                         "When product created it should be by default update to dummy ERP if it does "
                         "not have dummy ERP ID")

    # TODO: Finish testing product
