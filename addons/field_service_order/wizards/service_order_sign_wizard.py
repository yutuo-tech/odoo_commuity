# -*- coding: utf-8 -*-

import base64
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ServiceOrderSignWizard(models.TransientModel):
    """
    服務工單簽名精靈
    
    功能說明：
    - 批量發送簽名請求
    - 配置簽名模板和參數
    - 管理簽名流程
    """
    _name = 'service.order.sign.wizard'
    _description = '服務工單簽名精靈'
    
    # 基本設定
    order_ids = fields.Many2many(
        'field.service.order',
        'service_order_sign_wizard_order_rel',
        'wizard_id',
        'order_id',
        string='服務工單',
        required=True,
        help='需要發送簽名請求的工單'
    )
    
    order_count = fields.Integer(
        '工單數量',
        compute='_compute_order_count',
        help='選擇的工單數量'
    )
    
    # 簽名設定
    template_id = fields.Many2one(
        'sign.oca.template',
        '簽名模板',
        help='使用的簽名模板'
    )
    
    subject = fields.Char(
        '郵件主旨',
        default='請簽名確認服務處理單',
        required=True,
        help='發送給客戶的郵件主旨'
    )
    
    message = fields.Html(
        '郵件內容',
        help='發送給客戶的郵件內容'
    )
    
    # 發送選項
    send_immediately = fields.Boolean(
        '立即發送',
        default=True,
        help='立即發送簽名請求給客戶'
    )
    
    include_pdf = fields.Boolean(
        '包含PDF附件',
        default=True,
        help='在郵件中包含客戶服務處理單PDF'
    )
    
    reminder_days = fields.Integer(
        '提醒天數',
        default=3,
        help='幾天後發送提醒郵件'
    )
    
    # 狀態欄位
    state = fields.Selection([
        ('draft', '草稿'),
        ('processing', '處理中'),
        ('done', '完成')
    ], '狀態', default='draft')
    
    # 處理結果
    success_count = fields.Integer('成功數量', readonly=True)
    failed_count = fields.Integer('失敗數量', readonly=True)
    error_message = fields.Text('錯誤訊息', readonly=True)
    
    @api.depends('order_ids')
    def _compute_order_count(self):
        """計算工單數量"""
        for record in self:
            record.order_count = len(record.order_ids)
    
    @api.model
    def default_get(self, fields_list):
        """設定預設值"""
        res = super().default_get(fields_list)
        
        # 從 context 取得選擇的工單
        if self.env.context.get('active_ids'):
            active_ids = self.env.context['active_ids']
            orders = self.env['field.service.order'].browse(active_ids)
            
            # 篩選可以發送簽名請求的工單
            valid_orders = orders.filtered(lambda o: o.state == 'done')
            res['order_ids'] = [(6, 0, valid_orders.ids)]
            
            # 設定預設郵件內容
            if len(valid_orders) == 1:
                order = valid_orders[0]
                res['subject'] = f'請簽名確認服務處理單 - {order.name}'
                res['message'] = self._get_default_message(order)
            else:
                res['subject'] = f'請簽名確認服務處理單 ({len(valid_orders)} 份)'
        
        return res
    
    def _get_default_message(self, order):
        """取得預設郵件內容"""
        return f"""
        <p>親愛的 <strong>{order.partner_id.name}</strong>，</p>
        <p>您的服務工單已完成，請點選連結進行線上簽名確認。</p>
        <p>工單詳情：</p>
        <ul>
            <li>工單編號：{order.name}</li>
            <li>服務日期：{order.date}</li>
            <li>服務人員：{order.technician_id.name or ''}</li>
            <li>設備序號：{order.serial_number or ''}</li>
        </ul>
        <p>感謝您的配合！</p>
        """
    
    # 驗證方法
    @api.constrains('order_ids')
    def _check_orders_state(self):
        """檢查工單狀態"""
        for record in self:
            invalid_orders = record.order_ids.filtered(lambda o: o.state != 'done')
            if invalid_orders:
                raise ValidationError(
                    _('只有已完成狀態的工單才能發送簽名請求！\n無效工單：%s') % 
                    ', '.join(invalid_orders.mapped('name'))
                )
    
    @api.constrains('reminder_days')
    def _check_reminder_days(self):
        """檢查提醒天數"""
        for record in self:
            if record.reminder_days < 0 or record.reminder_days > 30:
                raise ValidationError(_('提醒天數必須在 0 到 30 之間！'))
    
    # 主要方法
    def action_send_signature_request(self):
        """發送簽名請求"""
        self.ensure_one()
        
        if not self.order_ids:
            raise UserError(_('請選擇要發送簽名請求的工單！'))
        
        self.state = 'processing'
        
        success_count = 0
        failed_count = 0
        error_messages = []
        
        for order in self.order_ids:
            try:
                # 發送簽名請求
                self._send_single_signature_request(order)
                success_count += 1
                
                # 記錄活動
                order.message_post(
                    body=_('已透過精靈發送簽名請求'),
                    message_type='notification'
                )
                
            except Exception as e:
                failed_count += 1
                error_msg = f'{order.name}: {str(e)}'
                error_messages.append(error_msg)
        
        # 更新結果
        self.write({
            'state': 'done',
            'success_count': success_count,
            'failed_count': failed_count,
            'error_message': '\n'.join(error_messages) if error_messages else False
        })
        
        # 顯示結果
        if failed_count == 0:
            message = _('成功發送 %d 份簽名請求！') % success_count
            message_type = 'success'
        else:
            message = _('發送完成：成功 %d 份，失敗 %d 份') % (success_count, failed_count)
            message_type = 'warning'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('簽名請求發送完成'),
                'message': message,
                'type': message_type,
                'sticky': True,
            }
        }
    
    def _send_single_signature_request(self, order):
        """
        發送單一工單的簽名請求
        
        Args:
            order: 服務工單記錄
        """
        # 生成客戶服務處理單 PDF
        report = self.env.ref('field_service_order.action_report_customer_service')
        pdf_content, _ = report._render_qweb_pdf(order.ids)
        
        # 建立簽名請求
        sign_request = self.env['sign.oca.request'].create({
            'name': f'{self.subject} - {order.name}',
            'data': base64.b64encode(pdf_content),
            'filename': f'{order.name}_客戶服務處理單.pdf',
            'record_ref': f'{order._name},{order.id}',
            'user_id': self.env.user.id,
        })
        
        # 建立簽名項目
        self.env['sign.oca.request.item'].create({
            'request_id': sign_request.id,
            'partner_id': order.partner_id.id,
        })
        
        # 更新工單的簽名請求關聯
        order.signature_request_id = sign_request.id
        
        # 發送簽名請求
        if self.send_immediately:
            sign_request.action_send()
        
        # 如果設定了提醒，建立活動
        if self.reminder_days > 0:
            order.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('簽名提醒'),
                note=_('提醒客戶簽名確認服務處理單'),
                date_deadline=fields.Date.today() + timedelta(days=self.reminder_days),
                user_id=order.technician_id.user_id.id if order.technician_id.user_id else self.env.user.id
            )
    
    def action_preview_orders(self):
        """預覽工單清單"""
        self.ensure_one()
        
        return {
            'name': _('選擇的工單'),
            'type': 'ir.actions.act_window',
            'res_model': 'field.service.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.order_ids.ids)],
            'context': {'create': False, 'edit': False}
        }
    
    def action_reset(self):
        """重設精靈"""
        self.write({
            'state': 'draft',
            'success_count': 0,
            'failed_count': 0,
            'error_message': False
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'service.order.sign.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }