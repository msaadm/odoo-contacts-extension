from odoo import models, fields, api
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_grant_portal_access = fields.Boolean(
        string='Grant Portal Access',
        default=True,
        tracking=True
    )

    x_signature_template_id = fields.Many2one(
        'sign.template',
        string='Signature Agreement',
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
    
    def action_send_agreement(self):
        if self.x_signature_template_id and self.email:
            template = self.x_signature_template_id

            # Get roles from template's signature items
            roles = template.sign_item_ids.mapped('responsible_id')
            if not roles:
                raise ValidationError('The selected template has no signature roles defined. Please configure the template first.')

            # Create signature request
            sign_request = self.env['sign.request'].create({
                'template_id': template.id,
                'subject': f'Signature Request: {template.name}',
                'reference': template.name,
                'request_item_ids': [(0, 0, {
                    'role_id': role.id,
                    'partner_id': self.id,
                }) for role in roles],
            })

            # Reset the template field after sending
            self.x_signature_template_id = False

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Signature request sent to {self.email}',
                    'type': 'success',
                    'sticky': False,
                }
            }
        elif not self.email:
            raise ValidationError('Please add an email address before requesting signature.')
        elif not self.x_signature_template_id:
            raise ValidationError('Please select a signature template before requesting signature.')