from . import models

def post_init_hook(cr, registry):
    # Remove old field from ir.model.fields
    cr.execute("""
        DELETE FROM ir_model_fields 
        WHERE model = 'res.partner' 
        AND name = 'x_grant_portal_access'
    """)

    cr.execute("ALTER TABLE res_partner DROP COLUMN x_grant_portal_access")
    
    # Remove old field references from views
    cr.execute("""
        UPDATE ir_ui_view v
        SET arch_db = arch_db::jsonb #- '{field,x_grant_portal_access}'
        WHERE arch_db::text LIKE '%x_grant_portal_access%'
    """)