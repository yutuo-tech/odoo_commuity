# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class FieldServiceSignatureViewWizard(models.TransientModel):
    """
    簽名檢視精靈
    
    功能說明：
    - 專用於顯示已上傳的簽名檔案
    - 避免與主要工單表單產生衝突
    """
    _name = 'field.service.signature.view.wizard'
    _description = '服務工單簽名檢視精靈'
    
    # 關聯的工單
    order_id = fields.Many2one(
        'field.service.order',
        '工單',
        required=True,
        ondelete='cascade'
    )
    
    # 工單基本資訊（相關欄位，便於顯示）
    order_name = fields.Char(
        '工單編號',
        related='order_id.name',
        readonly=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        '客戶公司',
        related='order_id.partner_id',
        readonly=True
    )
    
    contact_id = fields.Many2one(
        'company.contact',
        '聯絡人',
        related='order_id.contact_id',
        readonly=True
    )
    
    equipment_id = fields.Many2one(
        'service.equipment',
        '設備',
        related='order_id.equipment_id',
        readonly=True
    )
    
    technician_id = fields.Many2one(
        'hr.employee',
        '技術人員',
        related='order_id.technician_id',
        readonly=True
    )
    
    # 簽名相關欄位
    customer_signature_file = fields.Binary(
        '客戶簽名檔案',
        related='order_id.customer_signature_file',
        readonly=True
    )
    
    signature_filename = fields.Char(
        '檔案名稱',
        related='order_id.signature_filename',
        readonly=True
    )
    
    signed_by = fields.Char(
        '簽名人姓名',
        related='order_id.signed_by',
        readonly=True
    )
    
    signed_date = fields.Datetime(
        '簽名日期時間',
        related='order_id.signed_date',
        readonly=True
    )
    
    signature_upload_date = fields.Datetime(
        '上傳日期時間',
        related='order_id.signature_upload_date',
        readonly=True
    )
    
    def action_close(self):
        """關閉簽名檢視"""
        return {'type': 'ir.actions.act_window_close'}
    
    def action_view_order(self):
        """返回工單檢視"""
        self.ensure_one()
        return {
            'name': _('服務工單'),
            'type': 'ir.actions.act_window',
            'res_model': 'field.service.order',
            'view_mode': 'form',
            'res_id': self.order_id.id,
            'target': 'current',
        }