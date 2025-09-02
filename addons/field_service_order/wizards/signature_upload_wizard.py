# -*- coding: utf-8 -*-

import os
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class FieldServiceSignatureUploadWizard(models.TransientModel):
    """
    簽名上傳精靈
    
    功能說明：
    - 提供簡化的檔案上傳式簽名功能
    - 支援圖片檔案（JPG, PNG）和掃描文件（PDF）
    - 自動建立附件記錄
    - 記錄到工單的 chatter
    """
    _name = 'field.service.signature.upload.wizard'
    _description = '服務工單簽名上傳精靈'
    
    # 關聯的工單
    order_id = fields.Many2one(
        'field.service.order',
        '工單',
        required=True,
        ondelete='cascade'
    )
    
    # 簽名類型
    signature_type = fields.Selection([
        ('customer', '客戶簽名'),
        ('technician', '技術人員簽名')
    ], '簽名類型', required=True, default='customer',
        help='選擇簽名的類型')
    
    # 簽名檔案
    signature_file = fields.Binary(
        '簽名檔案',
        required=True,
        help='請上傳簽名的圖片檔案（JPG, PNG）或掃描文件（PDF）'
    )
    
    # 檔案名稱
    filename = fields.Char(
        '檔案名稱',
        required=True,
        help='簽名檔案的名稱'
    )
    
    # 簽名人姓名
    signed_by = fields.Char(
        '簽名人姓名',
        required=True,
        help='簽名人的完整姓名'
    )
    
    # 簽名日期時間
    signed_date = fields.Datetime(
        '簽名日期時間',
        default=fields.Datetime.now,
        required=True,
        help='簽名的日期和時間'
    )
    
    # 備註
    notes = fields.Text(
        '備註',
        help='關於簽名的額外說明或備註'
    )
    
    # ===========================================
    # 驗證方法
    # ===========================================
    
    @api.onchange('signature_file', 'filename')
    def _onchange_signature_file(self):
        """
        檔案變更時的驗證
        
        檢查檔案類型是否符合要求
        """
        if self.filename:
            # 檢查副檔名
            valid_extensions = ['.jpg', '.jpeg', '.png', '.pdf', '.gif']
            file_ext = os.path.splitext(self.filename)[1].lower()
            
            if file_ext not in valid_extensions:
                return {
                    'warning': {
                        'title': _('檔案類型警告'),
                        'message': _('建議使用以下格式之一：%s') % ', '.join(valid_extensions)
                    }
                }
    
    @api.constrains('signature_file', 'filename')
    def _check_file_size(self):
        """
        檢查檔案大小
        
        確保上傳的檔案不會太大
        """
        for record in self:
            if record.signature_file:
                # 簡單的檔案大小檢查（假設 base64 編碼）
                # 實際檔案大小約為 base64 長度的 3/4
                estimated_size = len(record.signature_file) * 3 / 4 / (1024 * 1024)  # MB
                
                if estimated_size > 10:  # 10MB 限制
                    raise ValidationError(_('簽名檔案大小不能超過 10MB！'))
    
    # ===========================================
    # 預設值方法
    # ===========================================
    
    @api.model
    def default_get(self, fields_list):
        """
        設定預設值
        
        根據工單狀態和類型設定合適的預設值
        """
        defaults = super().default_get(fields_list)
        
        # 從 context 取得 active_id 作為 order_id
        if 'order_id' in fields_list and self._context.get('active_id'):
            defaults['order_id'] = self._context.get('active_id')
        
        # 如果有 order_id，可以預填一些資訊
        order_id = defaults.get('order_id')
        if order_id:
            order = self.env['field.service.order'].browse(order_id)
            
            if 'signed_by' in fields_list and not defaults.get('signed_by'):
                # 根據簽名類型預設簽名人
                if defaults.get('signature_type') == 'customer' and order.contact_id:
                    defaults['signed_by'] = order.contact_id.name
                elif defaults.get('signature_type') == 'technician' and order.technician_id:
                    defaults['signed_by'] = order.technician_id.name
        
        return defaults
    
    # ===========================================
    # 業務方法
    # ===========================================
    
    def action_upload_signature(self):
        """
        確認上傳簽名
        
        執行簽名上傳的核心邏輯：
        1. 更新工單的簽名資訊
        2. 建立附件記錄
        3. 記錄到 chatter
        4. 可能更新工單狀態
        """
        self.ensure_one()
        
        if not self.order_id:
            raise UserError(_('找不到對應的工單！'))
        
        # 準備更新的資料
        update_vals = {
            'customer_signature_file': self.signature_file,
            'signature_filename': self.filename,
            'signed_by': self.signed_by,
            'signed_date': self.signed_date,
            'signature_upload_date': fields.Datetime.now(),
        }
        
        # 如果工單已完成且是客戶簽名，更新狀態為已簽名
        if (self.signature_type == 'customer' and 
            self.order_id.state == 'done'):
            update_vals['state'] = 'signed'
        
        # 更新工單資料
        self.order_id.write(update_vals)
        
        # 建立附件記錄
        attachment_name = _('簽名_%s_%s') % (
            self.order_id.name, 
            self.filename
        )
        
        attachment = self.env['ir.attachment'].create({
            'name': attachment_name,
            'type': 'binary',
            'datas': self.signature_file,
            'res_model': 'field.service.order',
            'res_id': self.order_id.id,
            'description': _('%s簽名 - %s') % (
                _('客戶') if self.signature_type == 'customer' else _('技術人員'),
                self.signed_by
            ),
            'mimetype': self._get_mimetype_from_filename(self.filename)
        })
        
        # 準備 chatter 訊息
        signature_type_name = _('客戶') if self.signature_type == 'customer' else _('技術人員')
        
        message_body = _("""
        <p><b>%s簽名已上傳</b></p>
        <ul>
            <li>簽名人：%s</li>
            <li>簽名時間：%s</li>
            <li>檔案名稱：%s</li>
            %s
        </ul>
        """) % (
            signature_type_name,
            self.signed_by,
            self.signed_date.strftime('%Y-%m-%d %H:%M:%S') if self.signed_date else '',
            self.filename,
            '<li>備註：%s</li>' % self.notes if self.notes else ''
        )
        
        # 記錄到 chatter
        self.order_id.message_post(
            body=message_body,
            attachment_ids=[attachment.id],
            subject=_('%s簽名已上傳') % signature_type_name
        )
        
        # 傳送成功通知
        notification_message = _('已成功上傳 %s 的簽名！') % self.signed_by
        
        if self.order_id.state == 'signed':
            notification_message += _('\n工單狀態已更新為「已簽名」。')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('簽名上傳成功'),
                'message': notification_message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'}
            }
        }
    
    def action_cancel(self):
        """
        取消上傳
        
        關閉精靈視窗而不執行任何操作
        """
        return {'type': 'ir.actions.act_window_close'}
    
    # ===========================================
    # 輔助方法
    # ===========================================
    
    def _get_mimetype_from_filename(self, filename):
        """
        根據檔案名稱取得 MIME 類型
        
        Args:
            filename (str): 檔案名稱
            
        Returns:
            str: MIME 類型
        """
        if not filename:
            return 'application/octet-stream'
        
        file_ext = os.path.splitext(filename)[1].lower()
        
        mime_mapping = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
        }
        
        return mime_mapping.get(file_ext, 'application/octet-stream')
    
    @api.model
    def create_signature_request(self, order_id, signature_type='customer'):
        """
        建立簽名請求
        
        便利方法，用於從工單直接建立簽名上傳精靈
        
        Args:
            order_id (int): 工單 ID
            signature_type (str): 簽名類型
            
        Returns:
            dict: 開啟精靈的動作
        """
        return {
            'name': _('上傳簽名'),
            'type': 'ir.actions.act_window',
            'res_model': 'field.service.signature.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': order_id,
                'default_signature_type': signature_type,
            }
        }