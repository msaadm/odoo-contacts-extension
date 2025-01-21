from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_signature_template_id = fields.Many2one(
        'sign.template',
        string='Signature Agreement',
        tracking=True
    )

    has_portal_access = fields.Boolean(
        string='Has Portal Access',
        compute='_compute_has_portal_access',
    )
    
    activation_link = fields.Char(
        string='Portal Activation Link',
        compute='_compute_activation_link',
    )

    @api.depends('user_ids', 'user_ids.active')
    def _compute_has_portal_access(self):
        for partner in self:
            # Check if partner has portal user
            portal_user = self.env['res.users'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('active', '=', True)
            ])
            if portal_user > 0:
                partner.has_portal_access = True
            else:
                partner.has_portal_access = False
            _logger.info('Computing portal access for partner %s (ID: %s): %s', 
                        partner.name, partner.id, partner.has_portal_access)

    @api.depends('has_portal_access')
    def _compute_activation_link(self):
        for partner in self:
            if partner.has_portal_access:
                signup_url = partner.with_context(signup_force_type_in_url='signup')._get_signup_url_for_action()[partner.id]
                partner.activation_link = signup_url
            else:
                partner.activation_link = False

    def toggle_portal_access(self):
        self.ensure_one()
        _logger.info('Toggle portal access for partner %s (ID: %s). Current status: %s', 
                    self.name, self.id, self.has_portal_access)
        
        if not self.email:
            raise ValidationError('Please add an email address before granting portal access.')
        
        if not self.name:
            raise ValidationError('Contact must have a name before granting portal access.')

        if self.has_portal_access:
            # Find and remove the portal user
            portal_user = self.env['res.users'].sudo().search([
                ('partner_id', '=', self.id),
                ('active', '=', True)
            ], limit=1)
            
            if portal_user:
                _logger.info('Removing portal user: %s', portal_user.id)
                portal_user.sudo().unlink()
        else:
            # Grant access using portal.wizard
            wizard = self.env['portal.wizard'].sudo().create({
                'user_ids': [(0, 0, {
                    'partner_id': self.id,
                    'email': self.email,
                })]
            })
            wizard.user_ids.action_grant_access()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': {
                'notification': {
                    'type': 'success',
                    'title': 'Success',
                    'message': f'Portal access has been {"granted" if self.has_portal_access else "revoked"} for {self.name}',
                    'sticky': False
                }
            }
        }

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