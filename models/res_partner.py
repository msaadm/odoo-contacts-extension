from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_grant_portal_access = fields.Boolean(
        string='Grant Portal Access',
        default=True,  # Changed default to True
        tracking=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.x_grant_portal_access:
                if record.email and record.name:
                    wizard = self.env['portal.wizard'].create({
                        'user_ids': [(0, 0, {
                            'partner_id': record.id,
                            'email': record.email,
                        })]
                    })
                    wizard.user_ids.action_grant_access()
                    record.x_grant_portal_access = False
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'x_grant_portal_access' in vals and vals.get('x_grant_portal_access'):
            for record in self:
                if record.email and record.name:
                    wizard = self.env['portal.wizard'].create({
                        'user_ids': [(0, 0, {
                            'partner_id': record.id,
                            'email': record.email,
                        })]
                    })
                    wizard.user_ids.action_grant_access()
                    record.x_grant_portal_access = False
        return result