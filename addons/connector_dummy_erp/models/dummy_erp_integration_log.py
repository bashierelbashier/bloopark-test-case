from odoo import models, fields


class DummyERPIntegrationLog(models.Model):
    _name = 'dummy.erp.integration.log'
    _description = 'Dummy ERP Integration Log'
    _order = "create_date desc"

    """
    This model is used as a log for the operations that occur in the integration object, like importing, exporting
    and display the status of the operation with the payloads used in the operation.
    """

    integration_id = fields.Many2one(
        "dummy.erp.integration", "Dummy ERP Integration", required=1, ondelete="cascade"
    )
    name = fields.Char("Subject", required=1)
    details = fields.Text("Details")
    type = fields.Selection(
        [("info", "Info"), ("warning", "Warning"), ("error", "Error")]
    )
    company_id = fields.Many2one(related="integration_id.company_id", store=1)
