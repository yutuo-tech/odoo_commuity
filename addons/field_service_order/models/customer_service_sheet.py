# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from markupsafe import Markup


class CustomerServiceSheet(models.Model):
    """
    客戶處理單管理
    
    客戶處理單是由保養工單、維修工單或工作日誌生成的客戶服務文件。
    大部分欄位直接從關聯的工單引用，不重複儲存資料。
    
    功能：
    - 從工單自動引入對應欄位資料
    - 客戶建議事項編輯
    - 客戶簽名功能
    - PDF 匯出
    - 一個工單對應一個客戶處理單
    
    設計原則：
    - 使用 related 和 computed 欄位避免資料重複
    - 只儲存差異化資料（建議事項、簽名等）
    - 工單更新時資料自動同步
    """
    _name = 'customer.service.sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '客戶處理單'
    _order = 'create_date desc, id desc'
    _rec_name = 'display_name'
    _check_company_auto = True
    
    # ===========================================
    # 核心關聯欄位
    # ===========================================
    
    service_order_id = fields.Many2one(
        'field.service.order',
        '關聯工單',
        required=True,
        ondelete='cascade',
        index=True,
        help='關聯的服務工單，刪除工單時會自動刪除客戶處理單'
    )
    
    order_type = fields.Selection(
        related='service_order_id.order_type',
        string='工單類型',
        store=True,
        readonly=True,
        help='從工單自動取得：保養工單、維修單或工作日誌'
    )
    
    display_name = fields.Char(
        '客戶處理單編號',
        compute='_compute_display_name',
        store=True,
        help='顯示名稱：工單編號 + 客戶處理單'
    )
    
    company_id = fields.Many2one(
        'res.company',
        '公司',
        related='service_order_id.company_id',
        store=True,
        readonly=True
    )
    
    active = fields.Boolean(
        '啟用',
        default=True,
        help='取消勾選以封存此客戶處理單'
    )
    
    # ===========================================
    # 共通欄位 (從工單引入)
    # ===========================================
    
    service_date = fields.Date(
        '服務日期',
        related='service_order_id.date',
        store=True,
        readonly=True,
        help='從工單引入的服務日期'
    )
    
    service_time = fields.Char(
        '服務時間',
        compute='_compute_service_time',
        store=True,
        help='從工單的開始和結束時間計算得出'
    )
    
    customer_name = fields.Char(
        '客戶名稱',
        compute='_compute_order_info',
        store=True,
        readonly=True,
        help='從工單引入的客戶名稱'
    )
    
    department_name = fields.Char(
        '使用單位',
        compute='_compute_order_info',
        store=True,
        readonly=True,
        help='從工單引入的使用部門'
    )
    
    service_location = fields.Char(
        '服務地點',
        compute='_compute_service_location',
        store=True,
        help='客戶名稱 + 使用單位的組合'
    )
    
    service_type_display = fields.Char(
        '服務類型',
        compute='_compute_service_type_display',
        store=True,
        help='根據工單類型顯示對應的服務類型'
    )
    
    technician_name = fields.Char(
        '處理人員',
        compute='_compute_order_info',
        store=True,
        readonly=True,
        help='從工單引入的技術人員姓名'
    )
    
    # ===========================================
    # 保養工單專用欄位
    # ===========================================
    
    equipment_model = fields.Char(
        'Model (機器版本)',
        compute='_compute_order_info',
        store=True,
        readonly=True,
        help='從工單引入的設備型號'
    )
    
    unit_number = fields.Char(
        '單位編號',
        related='service_order_id.unit_number',
        store=True,
        readonly=True,
        help='從工單引入的單位編號'
    )
    
    serial_number = fields.Char(
        'Serial No (機器序號)',
        related='service_order_id.serial_number',
        store=True,
        readonly=True,
        help='從工單引入的設備序號'
    )
    
    asset_number = fields.Char(
        '儀器財編',
        related='service_order_id.hospital_asset_number',
        store=True,
        readonly=True,
        help='從工單引入的醫院財產編號'
    )
    
    maintenance_checklist = fields.Html(
        'Control Checklist (檢查清單)',
        compute='_compute_maintenance_checklist',
        store=True,
        help='從工單的保養檢查清單生成，經過篩選後呈現'
    )
    
    # ===========================================
    # 維修單/工作日誌專用欄位
    # ===========================================
    
    problem_description = fields.Text(
        '事項描述',
        compute='_compute_problem_description',
        store=True,
        help='從維修單的問題描述或工作日誌的記錄內容引入'
    )
    
    solution_description = fields.Text(
        '處理事項',
        compute='_compute_solution_description',
        store=True,
        help='從工單的處理事項引入'
    )
    
    work_nature = fields.Char(
        '工作性質',
        compute='_compute_work_nature',
        store=True,
        help='從工作日誌的工作性質引入'
    )
    
    # 維修單專用欄位
    part_replacement_html = fields.Html(
        '零件更換記錄',
        compute='_compute_repair_info',
        store=True,
        help='從維修工單引入的零件更換記錄'
    )
    
    repair_problems_html = fields.Html(
        '維修問題',
        compute='_compute_repair_info',
        store=True,
        help='從維修工單引入的維修問題清單'
    )
    
    # ===========================================
    # 客戶處理單專用欄位 (需要儲存的資料)
    # ===========================================
    
    customer_suggestion = fields.Text(
        '客戶建議事項',
        tracking=True,
        help='客戶對設備使用或維護的建議事項，這是客戶處理單獨有的欄位，不與工單同步'
    )
    
    # ===========================================
    # 簽名相關欄位
    # ===========================================
    
    customer_signature = fields.Binary(
        '客戶簽名',
        help='客戶透過手機或平板簽名'
    )
    
    x_customer_signature_file = fields.Binary(
        '客戶簽名檔案',
        help='上傳客戶簽名的圖片檔案或掃描文件',
        attachment=True
    )
    
    signature_filename = fields.Char(
        '簽名檔案名稱',
        help='上傳的簽名檔案名稱'
    )
    
    signature_upload_date = fields.Datetime(
        '簽名上傳時間',
        readonly=True,
        help='簽名檔案上傳的時間'
    )
    
    signed_by = fields.Char(
        '簽名人',
        help='客戶簽名人姓名'
    )
    
    signed_date = fields.Datetime(
        '簽名時間',
        help='客戶簽名的時間'
    )
    
    signature_status = fields.Selection([
        ('pending', '待簽名'),
        ('signed', '已簽名'),
        ('rejected', '已拒絕')
    ], '簽名狀態', default='pending', tracking=True)
    
    # ===========================================
    # PDF 相關欄位
    # ===========================================
    
    pdf_file = fields.Binary(
        'PDF 檔案',
        help='生成的客戶處理單 PDF 檔案'
    )
    
    pdf_filename = fields.Char(
        'PDF 檔案名稱',
        help='PDF 檔案名稱'
    )
    
    pdf_generated_date = fields.Datetime(
        'PDF 生成時間',
        readonly=True,
        help='PDF 檔案生成的時間'
    )
    
    include_photos_in_pdf = fields.Boolean(
        'PDF包含照片',
        default=True,
        help='生成PDF時是否包含工單的附件照片'
    )
    
    # ===========================================
    # 狀態管理欄位
    # ===========================================
    
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirmed', '已確認'),
        ('sent', '已發送'),
        ('signed', '已簽名'),
        ('completed', '已完成')
    ], '狀態', default='draft', required=True, tracking=True)
    
    color = fields.Integer(
        '顏色索引', 
        default=0, 
        help='看板視圖的顏色標籤'
    )
    
    # ===========================================
    # 計算欄位方法
    # ===========================================
    
    @api.depends('service_order_id', 'service_order_id.partner_id', 'service_order_id.department_id', 
                 'service_order_id.technician_id', 'service_order_id.product_variant_id')
    def _compute_order_info(self):
        """計算工單相關資訊，避免使用 related 欄位"""
        for record in self:
            order = record.service_order_id
            if order:
                record.customer_name = order.partner_id.name if order.partner_id else ""
                record.department_name = order.department_id.name if order.department_id else ""
                record.technician_name = order.technician_id.name if order.technician_id else ""
                record.equipment_model = order.product_variant_id.name if order.product_variant_id else ""
            else:
                record.customer_name = ""
                record.department_name = ""
                record.technician_name = ""
                record.equipment_model = ""
    
    @api.depends('service_order_id', 'service_order_id.name')
    def _compute_display_name(self):
        """計算顯示名稱"""
        for record in self:
            if record.service_order_id:
                record.display_name = f"{record.service_order_id.name} - 客戶處理單"
            else:
                record.display_name = "新客戶處理單"
    
    @api.depends('service_order_id.start_date', 'service_order_id.end_date')
    def _compute_service_time(self):
        """計算服務時間範圍"""
        for record in self:
            if record.service_order_id.start_date and record.service_order_id.end_date:
                start_time = record.service_order_id.start_date.strftime('%H:%M')
                end_time = record.service_order_id.end_date.strftime('%H:%M')
                record.service_time = f"{start_time} - {end_time}"
            elif record.service_order_id.start_date:
                start_time = record.service_order_id.start_date.strftime('%H:%M')
                record.service_time = f"{start_time} 開始"
            else:
                record.service_time = ""
    
    @api.depends('customer_name', 'department_name')
    def _compute_service_location(self):
        """計算服務地點（客戶名稱 + 使用單位）"""
        for record in self:
            parts = []
            if record.customer_name:
                parts.append(record.customer_name)
            if record.department_name:
                parts.append(record.department_name)
            record.service_location = ' - '.join(parts) if parts else ""
    
    @api.depends('order_type', 'service_order_id.maintenance_type', 'service_order_id.work_nature_main')
    def _compute_service_type_display(self):
        """計算服務類型顯示名稱"""
        for record in self:
            if record.order_type == 'maintenance':
                maintenance_type_dict = dict(record.service_order_id._fields['maintenance_type'].selection)
                record.service_type_display = maintenance_type_dict.get(record.service_order_id.maintenance_type, '保養')
            elif record.order_type == 'repair':
                record.service_type_display = '維修'
            elif record.order_type == 'work_log':
                work_nature_dict = dict(record.service_order_id._fields['work_nature_main'].selection)
                record.service_type_display = work_nature_dict.get(record.service_order_id.work_nature_main, '工作日誌')
            else:
                record.service_type_display = ""
    
    @api.depends('service_order_id.checklist_line_ids')
    def _compute_maintenance_checklist(self):
        """
        計算保養檢查清單
        
        從工單的檢查清單中篩選要顯示給客戶的項目
        """
        for record in self:
            if record.order_type == 'maintenance' and record.service_order_id.checklist_line_ids:
                checklist_html = """<table style='border-collapse: collapse; width: 100%; border: 1px solid #333;'>
                <thead>
                    <tr style='background-color: #f0f0f0;'>
                        <th style='border: 1px solid #333; padding: 8px; text-align: left; width: 45%;'>項目</th>
                        <th style='border: 1px solid #333; padding: 8px; text-align: center; width: 15%;'>狀態</th>
                        <th style='border: 1px solid #333; padding: 8px; text-align: left; width: 40%;'>備註</th>
                    </tr>
                </thead>
                <tbody>"""
                
                for line in record.service_order_id.checklist_line_ids:
                    # 只顯示要給客戶看的項目（可以在保養項目中設定 show_to_customer 欄位）
                    status = "✓ 完成" if line.is_checked else "✗ 未完成"
                    status_color = "color: green;" if line.is_checked else "color: red;"
                    item_name = line.name or line.maintenance_item_id.name or '未設定項目名稱'
                    checklist_html += f"""
                    <tr>
                        <td style='border: 1px solid #333; padding: 8px;'>{item_name}</td>
                        <td style='border: 1px solid #333; padding: 8px; text-align: center; {status_color}'>{status}</td>
                        <td style='border: 1px solid #333; padding: 8px;'>{line.notes or ''}</td>
                    </tr>
                    """
                
                checklist_html += "</tbody></table>"
                record.maintenance_checklist = Markup(checklist_html)
            else:
                record.maintenance_checklist = ""
    
    @api.depends('order_type', 'service_order_id.problem_description', 'service_order_id.record_content')
    def _compute_problem_description(self):
        """計算問題描述"""
        for record in self:
            if record.order_type == 'repair':
                record.problem_description = record.service_order_id.problem_description or ""
            elif record.order_type == 'work_log':
                # 工作日誌使用記錄內容作為事項描述
                if record.service_order_id.record_content:
                    # 移除 HTML 標籤，只保留純文字
                    import re
                    clean_text = re.sub('<.*?>', '', record.service_order_id.record_content or "")
                    record.problem_description = clean_text
                else:
                    record.problem_description = ""
            else:
                record.problem_description = ""
    
    @api.depends('service_order_id.solution_description')
    def _compute_solution_description(self):
        """計算處理事項"""
        for record in self:
            record.solution_description = record.service_order_id.solution_description or ""
    
    @api.depends('service_order_id.work_nature_main', 'service_order_id.work_nature_sub')
    def _compute_work_nature(self):
        """計算工作性質"""
        for record in self:
            if record.order_type == 'work_log':
                parts = []
                if record.service_order_id.work_nature_main:
                    main_dict = dict(record.service_order_id._fields['work_nature_main'].selection)
                    parts.append(main_dict.get(record.service_order_id.work_nature_main, ''))
                if record.service_order_id.work_nature_sub:
                    sub_dict = dict(record.service_order_id._fields['work_nature_sub'].selection)
                    parts.append(sub_dict.get(record.service_order_id.work_nature_sub, ''))
                record.work_nature = ' - '.join(filter(None, parts))
            else:
                record.work_nature = ""
    
    @api.depends('service_order_id.part_replacement_ids', 'service_order_id.repair_problem_ids')
    def _compute_repair_info(self):
        """計算維修相關資訊（零件更換和維修問題）"""
        for record in self:
            if record.order_type == 'repair':
                # 生成零件更換記錄 HTML
                if record.service_order_id.part_replacement_ids:
                    parts_html = """<table style='border-collapse: collapse; width: 100%; border: 1px solid #333;'>
                    <thead>
                        <tr style='background-color: #f0f0f0;'>
                            <th style='border: 1px solid #333; padding: 8px; text-align: left; width: 35%;'>零件名稱</th>
                            <th style='border: 1px solid #333; padding: 8px; text-align: left; width: 25%;'>零件編號</th>
                            <th style='border: 1px solid #333; padding: 8px; text-align: center; width: 15%;'>更換數量</th>
                            <th style='border: 1px solid #333; padding: 8px; text-align: left; width: 25%;'>備註</th>
                        </tr>
                    </thead>
                    <tbody>"""
                    for part in record.service_order_id.part_replacement_ids:
                        parts_html += f"""
                        <tr>
                            <td style='border: 1px solid #333; padding: 8px;'>{part.product_id.name if part.product_id else ''}</td>
                            <td style='border: 1px solid #333; padding: 8px;'>{part.product_id.default_code if part.product_id and part.product_id.default_code else ''}</td>
                            <td style='border: 1px solid #333; padding: 8px; text-align: center;'>{part.quantity or 0}</td>
                            <td style='border: 1px solid #333; padding: 8px;'>{part.notes or ''}</td>
                        </tr>
                        """
                    parts_html += "</tbody></table>"
                    record.part_replacement_html = Markup(parts_html)
                else:
                    record.part_replacement_html = Markup("<p style='color: #666;'>無零件更換記錄</p>")
                
                # 生成維修問題記錄 HTML
                if record.service_order_id.repair_problem_ids:
                    problems_html = """<table style='border-collapse: collapse; width: 100%; border: 1px solid #333;'>
                    <thead>
                        <tr style='background-color: #f0f0f0;'>
                            <th style='border: 1px solid #333; padding: 8px; text-align: left; width: 30%;'>問題名稱</th>
                            <th style='border: 1px solid #333; padding: 8px; text-align: left; width: 25%;'>物料</th>
                            <th style='border: 1px solid #333; padding: 8px; text-align: left; width: 45%;'>描述</th>
                        </tr>
                    </thead>
                    <tbody>"""
                    for problem in record.service_order_id.repair_problem_ids:
                        problems_html += f"""
                        <tr>
                            <td style='border: 1px solid #333; padding: 8px;'>{problem.name or '未命名'}</td>
                            <td style='border: 1px solid #333; padding: 8px;'>{problem.material_id.name if problem.material_id else ''}</td>
                            <td style='border: 1px solid #333; padding: 8px;'>{problem.description or ''}</td>
                        </tr>
                        """
                    problems_html += "</tbody></table>"
                    record.repair_problems_html = Markup(problems_html)
                else:
                    record.repair_problems_html = Markup("<p style='color: #666;'>無維修問題記錄</p>")
            else:
                record.part_replacement_html = ""
                record.repair_problems_html = ""
    
    # ===========================================
    # 約束條件
    # ===========================================
    
    @api.constrains('service_order_id')
    def _check_unique_service_order(self):
        """確保一個工單只能對應一個客戶處理單"""
        for record in self:
            if record.service_order_id:
                existing = self.search([
                    ('service_order_id', '=', record.service_order_id.id),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(
                        _('工單 %s 已經存在客戶處理單，一個工單只能對應一個客戶處理單！') % record.service_order_id.name
                    )
    
    # ===========================================
    # CRUD 方法
    # ===========================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """建立客戶處理單時的處理邏輯"""
        records = super().create(vals_list)
        return records
    
    def write(self, vals):
        """更新客戶處理單時的處理邏輯"""
        result = super().write(vals)
        
        # 如果上傳了簽名，更新相關時間
        if 'x_customer_signature_file' in vals or 'customer_signature' in vals:
            for record in self:
                record.write({
                    'signature_upload_date': fields.Datetime.now(),
                    'signature_status': 'signed' if vals.get('x_customer_signature_file') or vals.get('customer_signature') else 'pending'
                })
        
        return result
    
    # ===========================================
    # 業務方法
    # ===========================================
    
    def action_confirm(self):
        """確認客戶處理單"""
        for record in self:
            record.state = 'confirmed'
            record.message_post(body=_("客戶處理單已確認"))
    
    def action_send_to_customer(self):
        """發送給客戶"""
        for record in self:
            record.state = 'sent'
            record.message_post(body=_("客戶處理單已發送給客戶"))
    
    def action_complete(self):
        """完成客戶處理單"""
        for record in self:
            if record.signature_status != 'signed':
                raise UserError(_('請先完成客戶簽名才能完成客戶處理單！'))
            record.state = 'completed'
            record.message_post(body=_("客戶處理單已完成"))
    
    def action_generate_pdf(self):
        """開啟 HTML 預覽以供列印"""
        self.ensure_one()
        
        # 使用自定義控制器來顯示 HTML 報表，避免 Odoo 報表系統的編碼問題
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/customer_service_sheet/{self.id}',
            'target': 'new',
        }
    
    def action_download_pdf(self):
        """下載 PDF"""
        self.ensure_one()
        
        if not self.pdf_file:
            # 如果沒有 PDF，先生成
            self.action_generate_pdf()
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/pdf_file/{self.pdf_filename}?download=true',
            'target': 'self',
        }
    
    def action_upload_signature(self):
        """上傳簽名精靈"""
        self.ensure_one()
        
        return {
            'name': _('上傳客戶簽名'),
            'type': 'ir.actions.act_window',
            'res_model': 'customer.service.sheet.signature.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sheet_id': self.id,
            }
        }
    
    def action_view_service_order(self):
        """查看關聯的服務工單"""
        self.ensure_one()
        
        return {
            'name': _('服務工單'),
            'type': 'ir.actions.act_window',
            'res_model': 'field.service.order',
            'res_id': self.service_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    @api.model
    def create_from_service_order(self, service_order_id):
        """
        從服務工單建立客戶處理單
        
        Args:
            service_order_id (int): 服務工單 ID
            
        Returns:
            customer.service.sheet: 新建立的客戶處理單
        """
        service_order = self.env['field.service.order'].browse(service_order_id)
        
        if not service_order.exists():
            raise UserError(_('指定的服務工單不存在！'))
        
        # 檢查是否已經存在客戶處理單
        existing = self.search([('service_order_id', '=', service_order_id)])
        if existing:
            raise UserError(_('此工單已經存在客戶處理單！'))
        
        # 建立客戶處理單
        sheet = self.create({
            'service_order_id': service_order_id,
        })
        
        return sheet