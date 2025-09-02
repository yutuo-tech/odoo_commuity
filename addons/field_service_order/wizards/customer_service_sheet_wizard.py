# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CustomerServiceSheetWizard(models.TransientModel):
    """
    客戶處理單生成精靈
    
    功能：
    - 從工單預覽即將生成的客戶處理單內容
    - 根據工單類型顯示不同的欄位
    - 確認後生成客戶處理單
    """
    _name = 'customer.service.sheet.wizard'
    _description = '客戶處理單生成精靈'
    
    # ===========================================
    # 基本欄位
    # ===========================================
    
    service_order_id = fields.Many2one(
        'field.service.order',
        '服務工單',
        required=True,
        readonly=True,
        help='要生成客戶處理單的服務工單'
    )
    
    order_type = fields.Selection([
        ('maintenance', '保養工單'),
        ('repair', '維修單'),
        ('work_log', '工作日誌')
    ], '工單類型', compute='_compute_order_fields', readonly=True)
    
    # ===========================================
    # 預覽欄位（只讀，從工單取得）
    # ===========================================
    
    service_date = fields.Date(
        '服務日期',
        compute='_compute_order_fields',
        readonly=True
    )
    
    customer_name = fields.Char(
        '客戶名稱',
        compute='_compute_order_fields',
        readonly=True
    )
    
    department_name = fields.Char(
        '使用單位',
        compute='_compute_order_fields',
        readonly=True
    )
    
    technician_name = fields.Char(
        '處理人員',
        compute='_compute_order_fields',
        readonly=True
    )
    
    # 保養工單預覽欄位
    equipment_model = fields.Char(
        'Model (機器版本)',
        compute='_compute_order_fields',
        readonly=True
    )
    
    serial_number = fields.Char(
        'Serial No (機器序號)',
        compute='_compute_order_fields',
        readonly=True
    )
    
    unit_number = fields.Char(
        '單位編號',
        compute='_compute_order_fields',
        readonly=True
    )
    
    asset_number = fields.Char(
        '儀器財編',
        compute='_compute_order_fields',
        readonly=True
    )
    
    checklist_preview = fields.Html(
        '檢查清單預覽',
        compute='_compute_checklist_preview',
        help='保養工單的檢查清單預覽'
    )
    
    # 維修單/工作日誌預覽欄位
    problem_description = fields.Text(
        '問題描述',
        compute='_compute_problem_description',
        readonly=True
    )
    
    solution_description = fields.Text(
        '處理事項',
        compute='_compute_order_fields',
        readonly=True
    )
    
    work_nature = fields.Char(
        '工作性質',
        compute='_compute_work_nature',
        readonly=True
    )
    
    # 維修單預覽欄位
    part_replacement_preview = fields.Html(
        '零件更換預覽',
        compute='_compute_repair_preview',
        help='維修工單的零件更換記錄預覽'
    )
    
    repair_problems_preview = fields.Html(
        '維修問題預覽',
        compute='_compute_repair_preview',
        help='維修工單的問題記錄預覽'
    )
    
    # ===========================================
    # 可編輯欄位
    # ===========================================
    
    customer_suggestion = fields.Text(
        '客戶建議事項',
        help='初始的客戶建議事項，可在生成後繼續編輯'
    )
    
    include_photos_in_pdf = fields.Boolean(
        'PDF包含照片',
        default=True,
        help='生成PDF時是否包含工單的附件照片'
    )
    
    # ===========================================
    # 計算欄位
    # ===========================================
    
    @api.depends('service_order_id')
    def _compute_order_fields(self):
        """計算工單相關欄位，避免使用 related 欄位"""
        for wizard in self:
            order = wizard.service_order_id
            if order:
                wizard.order_type = order.order_type or False
                wizard.service_date = order.date or False
                wizard.customer_name = order.partner_id.name if order.partner_id else ""
                wizard.department_name = order.department_id.name if order.department_id else ""
                wizard.technician_name = order.technician_id.name if order.technician_id else ""
                wizard.equipment_model = order.product_variant_id.name if order.product_variant_id else ""
                wizard.serial_number = order.serial_number or ""
                wizard.unit_number = order.unit_number or ""
                wizard.asset_number = order.hospital_asset_number or ""
                wizard.solution_description = order.solution_description or ""
            else:
                wizard.order_type = False
                wizard.service_date = False
                wizard.customer_name = ""
                wizard.department_name = ""
                wizard.technician_name = ""
                wizard.equipment_model = ""
                wizard.serial_number = ""
                wizard.unit_number = ""
                wizard.asset_number = ""
                wizard.solution_description = ""
    
    @api.depends('service_order_id.checklist_line_ids')
    def _compute_checklist_preview(self):
        """計算檢查清單預覽"""
        for wizard in self:
            if wizard.order_type == 'maintenance' and wizard.service_order_id.checklist_line_ids:
                html = "<table class='table table-sm table-striped'>"
                html += "<thead><tr><th>檢查項目</th><th>狀態</th><th>備註</th></tr></thead><tbody>"
                
                for line in wizard.service_order_id.checklist_line_ids:
                    status = "✓ 完成" if line.is_checked else "✗ 未完成"
                    status_class = "text-success" if line.is_checked else "text-danger"
                    html += f"<tr><td>{line.name}</td><td class='{status_class}'>{status}</td><td>{line.notes or ''}</td></tr>"
                
                html += "</tbody></table>"
                wizard.checklist_preview = html
            else:
                wizard.checklist_preview = "<p class='text-muted'>此工單類型沒有檢查清單</p>"
    
    @api.depends('order_type', 'service_order_id.problem_description', 'service_order_id.record_content')
    def _compute_problem_description(self):
        """計算問題描述"""
        for wizard in self:
            if wizard.order_type == 'repair':
                wizard.problem_description = wizard.service_order_id.problem_description or ""
            elif wizard.order_type == 'work_log':
                # 工作日誌使用記錄內容
                if wizard.service_order_id.record_content:
                    import re
                    clean_text = re.sub('<.*?>', '', wizard.service_order_id.record_content or "")
                    wizard.problem_description = clean_text
                else:
                    wizard.problem_description = ""
            else:
                wizard.problem_description = ""
    
    @api.depends('service_order_id.work_nature_main', 'service_order_id.work_nature_sub')
    def _compute_work_nature(self):
        """計算工作性質"""
        for wizard in self:
            if wizard.order_type == 'work_log':
                parts = []
                if wizard.service_order_id.work_nature_main:
                    main_dict = dict(wizard.service_order_id._fields['work_nature_main'].selection)
                    parts.append(main_dict.get(wizard.service_order_id.work_nature_main, ''))
                if wizard.service_order_id.work_nature_sub:
                    sub_dict = dict(wizard.service_order_id._fields['work_nature_sub'].selection)
                    parts.append(sub_dict.get(wizard.service_order_id.work_nature_sub, ''))
                wizard.work_nature = ' - '.join(filter(None, parts))
            else:
                wizard.work_nature = ""
    
    @api.depends('service_order_id.part_replacement_ids', 'service_order_id.repair_problem_ids')
    def _compute_repair_preview(self):
        """計算維修相關預覽資訊"""
        for wizard in self:
            if wizard.order_type == 'repair':
                # 生成零件更換預覽
                if wizard.service_order_id.part_replacement_ids:
                    parts_html = "<table class='table table-sm table-striped'>"
                    parts_html += "<thead><tr><th>零件名稱</th><th>零件編號</th><th>更換數量</th><th>備註</th></tr></thead><tbody>"
                    for part in wizard.service_order_id.part_replacement_ids:
                        parts_html += f"""
                        <tr>
                            <td>{part.product_id.name if part.product_id else ''}</td>
                            <td>{part.product_id.default_code if part.product_id and part.product_id.default_code else ''}</td>
                            <td>{part.quantity or 0}</td>
                            <td>{part.notes or ''}</td>
                        </tr>
                        """
                    parts_html += "</tbody></table>"
                    wizard.part_replacement_preview = parts_html
                else:
                    wizard.part_replacement_preview = "<p class='text-muted'>此維修工單沒有零件更換記錄</p>"
                
                # 生成維修問題預覽
                if wizard.service_order_id.repair_problem_ids:
                    problems_html = "<table class='table table-sm table-striped'>"
                    problems_html += "<thead><tr><th>問題名稱</th><th>物料</th><th>描述</th></tr></thead><tbody>"
                    for problem in wizard.service_order_id.repair_problem_ids:
                        problems_html += f"""
                        <tr>
                            <td>{problem.name or '未命名'}</td>
                            <td>{problem.material_id.name if problem.material_id else ''}</td>
                            <td>{problem.description or ''}</td>
                        </tr>
                        """
                    problems_html += "</tbody></table>"
                    wizard.repair_problems_preview = problems_html
                else:
                    wizard.repair_problems_preview = "<p class='text-muted'>此維修工單沒有維修問題記錄</p>"
            else:
                wizard.part_replacement_preview = ""
                wizard.repair_problems_preview = ""
    
    # ===========================================
    # 預設值設定
    # ===========================================
    
    @api.model
    def default_get(self, fields):
        """設定預設值"""
        res = super().default_get(fields)
        
        # 從上下文取得服務工單 ID
        service_order_id = self.env.context.get('active_id')
        if service_order_id:
            res['service_order_id'] = service_order_id
        
        return res
    
    # ===========================================
    # 業務方法
    # ===========================================
    
    def action_generate_customer_service_sheet(self):
        """生成客戶處理單"""
        self.ensure_one()
        
        # 移除狀態檢查，讓所有狀態的工單都能生成客戶處理單
        
        # 檢查是否已存在客戶處理單
        existing_sheet = self.env['customer.service.sheet'].search([
            ('service_order_id', '=', self.service_order_id.id)
        ])
        
        if existing_sheet:
            # 如果已存在，開啟現有的客戶處理單
            return {
                'type': 'ir.actions.act_window',
                'name': _('客戶處理單'),
                'res_model': 'customer.service.sheet',
                'res_id': existing_sheet.id,
                'view_mode': 'form',
                'target': 'current',
            }
        
        # 建立新的客戶處理單
        sheet_vals = {
            'service_order_id': self.service_order_id.id,
            'customer_suggestion': self.customer_suggestion,
            'include_photos_in_pdf': self.include_photos_in_pdf,
        }
        
        new_sheet = self.env['customer.service.sheet'].create(sheet_vals)
        
        # 直接開啟新建立的客戶處理單
        return {
            'type': 'ir.actions.act_window',
            'name': _('客戶處理單'),
            'res_model': 'customer.service.sheet',
            'res_id': new_sheet.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_cancel(self):
        """取消生成"""
        return {'type': 'ir.actions.act_window_close'}


class CustomerServiceSheetSignatureWizard(models.TransientModel):
    """
    客戶處理單簽名上傳精靈
    
    功能：
    - 上傳客戶簽名檔案
    - 填寫簽名相關資訊
    """
    _name = 'customer.service.sheet.signature.wizard'
    _description = '客戶處理單簽名精靈'
    
    sheet_id = fields.Many2one(
        'customer.service.sheet',
        '客戶處理單',
        required=True
    )
    
    signature_file = fields.Binary(
        '簽名檔案',
        required=True,
        help='上傳客戶簽名的圖片檔案'
    )
    
    signature_filename = fields.Char(
        '檔案名稱',
        help='簽名檔案名稱'
    )
    
    signed_by = fields.Char(
        '簽名人',
        required=True,
        help='客戶簽名人姓名'
    )
    
    signed_date = fields.Datetime(
        '簽名時間',
        default=fields.Datetime.now,
        required=True,
        help='客戶簽名的時間'
    )
    
    def action_upload_signature(self):
        """上傳簽名"""
        self.ensure_one()
        
        # 更新客戶處理單的簽名資訊
        self.sheet_id.write({
            'x_customer_signature_file': self.signature_file,
            'signature_filename': self.signature_filename,
            'signed_by': self.signed_by,
            'signed_date': self.signed_date,
            'signature_status': 'signed',
            'signature_upload_date': fields.Datetime.now(),
        })
        
        # 如果狀態是已發送，自動變更為已簽名
        if self.sheet_id.state == 'sent':
            self.sheet_id.state = 'signed'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('簽名上傳成功'),
                'message': _('客戶簽名已成功上傳'),
                'type': 'success',
            }
        }
    
    def action_cancel(self):
        """取消上傳"""
        return {'type': 'ir.actions.act_window_close'}