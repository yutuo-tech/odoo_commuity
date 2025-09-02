# -*- coding: utf-8 -*-

import base64
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class FieldServiceOrder(models.Model):
    """
    現場服務工單管理 (簡化版)
    
    功能說明：
    - 管理保養工單、維修單和工作日誌
    - 透過設備關聯自動取得客戶、合約、產品資訊
    - 直接整合 enterprise_product_management 模組的保養項目和問題庫
    - 支援電子簽名和 PDF 匯出
    
    設計原則：
    - 選擇設備後自動帶入所有相關資訊，避免重複建立資料結構
    - 保養項目透過 epm.maintenance.item 動態載入
    - 維修問題透過 epm.material.repair 選擇
    """
    _name = 'field.service.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '現場服務工單'
    _order = 'date desc, name desc'
    _check_company_auto = True
    
    # ===========================================
    # 基本識別資訊欄位
    # ===========================================
    
    name = fields.Char(
        '工單編號', 
        required=True, 
        copy=False, 
        readonly=True, 
        index=True,
        default='New',
        help='系統自動生成的工單編號'
    )
    
    order_type = fields.Selection([
        ('maintenance', '保養工單'),
        ('repair', '維修單'),
        ('work_log', '工作日誌')
    ], '工單類型', required=True, default='maintenance', tracking=True,
        help='選擇工單類型：保養工單、維修單或工作日誌')
    
    date = fields.Date(
        '單據日期', 
        required=True, 
        default=fields.Date.context_today,
        tracking=True,
        help='工單建立日期，可手動修改'
    )
    
    scheduled_date = fields.Datetime(
        '排程日期時間',
        help='預定執行的日期時間'
    )
    
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirmed', '已確認'),
        ('scheduled', '已排程'),
        ('assigned', '已指派'),
        ('in_progress', '進行中'),
        ('done', '已完成'),
        ('signed', '已簽名'),
        ('closed', '已歸檔'),
        ('cancelled', '已取消')
    ], '狀態', default='draft', required=True, tracking=True,
        help='工單處理狀態')
    
    priority = fields.Selection([
        ('0', '低'),
        ('1', '正常'), 
        ('2', '高'),
        ('3', '緊急')
    ], '優先順序', default='1', tracking=True)
    
    kanban_state = fields.Selection([
        ('normal', '進行中'),
        ('done', '就緒'),
        ('blocked', '阻塞')
    ], '看板狀態', default='normal', help='看板視圖的狀態指示器')
    
    color = fields.Integer('顏色索引', default=0, help='看板視圖的顏色標籤')
    
    active = fields.Boolean(
        '啟用',
        default=True,
        help='取消勾選以封存此工單'
    )
    
    company_id = fields.Many2one(
        'res.company', 
        '公司',
        default=lambda self: self.env.company,
        required=True
    )
    
    # ===========================================
    # 設備選擇後自動帶入的客戶資訊
    # ===========================================
    
    equipment_id = fields.Many2one(
        'service.equipment',
        '設備',
        required=True,
        tracking=True,
        help='選擇設備後會自動帶入所有相關資訊，可掃描 QR code 選擇'
    )
    
    # 以下欄位從 equipment_id 自動帶入，但允許使用者修改
    partner_id = fields.Many2one(
        'res.partner', 
        '客戶名稱',
        tracking=True,
        help='選擇設備後自動帶入，可手動修改'
    )
    
    partner_code = fields.Char(
        '客戶代號',
        compute='_compute_partner_code',
        store=True,
        readonly=True,
        help='根據客戶自動計算'
    )
    
    department_id = fields.Many2one(
        'company.department',
        '使用單位',
        tracking=True,
        help='選擇設備後自動帶入使用科室，可手動修改'
    )
    
    contact_id = fields.Many2one(
        'company.contact',
        '聯絡人',
        tracking=True,
        help='選擇設備後自動帶入聯絡人，可手動修改'
    )
    
    hospital_asset_number = fields.Char(
        '醫院財編',
        tracking=True,
        help='選擇設備後自動帶入財編，可手動修改'
    )
    
    unit_number = fields.Char(
        '單位編號',
        help='手動輸入或掃描 QR code 自動帶入'
    )
    
    # ===========================================
    # 合約資訊（從設備關聯取得）
    # ===========================================
    
    contract_id = fields.Many2one(
        'service.contract',
        '主要合約',
        compute='_compute_primary_contract',
        store=True,
        readonly=True,
        help='從設備的活躍合約中選擇主要合約'
    )
    
    contract_type = fields.Selection(
        related='contract_id.contract_type',
        string='合約類型',
        store=True,
        readonly=True,
        help='全責保固、維護合約、備機合約等'
    )
    
    contract_code = fields.Char(
        '合約代號',
        related='contract_id.name',
        store=True,
        readonly=True,
        help='主要合約的代號'
    )
    
    # ===========================================
    # 設備詳細資訊（從 equipment_id 自動取得）
    # ===========================================
    
    serial_number = fields.Char(
        '機器序號',
        tracking=True,
        help='設備序號，選擇設備後自動帶入，可手動修改'
    )
    
    product_id = fields.Many2one(
        'product.template',
        '產品',
        tracking=True,
        help='設備對應的產品型號，選擇設備後自動帶入，可手動修改'
    )
    
    product_variant_id = fields.Many2one(
        'product.product',
        '產品型號',
        tracking=True,
        help='具體的產品型號，如 HF440-CRRT、HF440-ECMO'
    )
    
    software_version = fields.Char(
        '軟體版本',
        tracking=True,
        help='設備軟體版本，如 V8、NV3，可手動修改'
    )
    
    installation_location = fields.Text(
        '安裝位置',
        tracking=True,
        help='設備的安裝位置，可手動修改'
    )
    
    # ===========================================
    # 人員與時間欄位 (對應需求文件 13-16 項)
    # ===========================================
    
    technician_id = fields.Many2one(
        'hr.employee',
        '維修/保養人員',
        default=lambda self: self._get_default_technician(),
        required=True,
        tracking=True,
        help='由帳號登入可由系統自動帶入'
    )
    
    team_id = fields.Many2one(
        'maintenance.team',
        '維護團隊',
        help='負責此工單的維護團隊'
    )
    
    estimated_duration = fields.Float(
        '預估工時',
        help='預估完成此工單需要的時間（小時）'
    )
    
    actual_duration = fields.Float(
        '實際時長',
        compute='_compute_actual_duration',
        store=True,
        help='實際完成此工單花費的時間（小時）'
    )
    
    start_date = fields.Datetime(
        '開始時間',
        help='實際開始作業的時間'
    )
    
    end_date = fields.Datetime(
        '結束時間',
        help='實際完成作業的時間'
    )
    
    actual_hours = fields.Float(
        '實際工時',
        compute='_compute_actual_hours',
        store=True,
        help='根據開始和結束時間自動計算'
    )
    
    # ===========================================
    # 保養工單專用欄位 (對應需求文件 17-18 項)
    # ===========================================
    
    maintenance_type = fields.Selection([
        ('routine', '例行保養'),
        ('major', '大保養'), 
        ('quarterly', '季度保養'),
        ('annual', '年度保養'),
        ('emergency', '緊急保養'),
        ('preventive', '預防性保養'),
    ], '保養類型', help='點選類型後可對應出不同的Check List')
    
    last_maintenance_date = fields.Date(
        '上次保養日期',
        help='設備最近一次保養的日期'
    )
    
    next_maintenance_date = fields.Date(
        '下次保養日期',
        help='預計下次保養的日期'
    )
    
    # 保養項目關聯（從 enterprise_product_management 動態載入）
    maintenance_item_ids = fields.Many2many(
        'epm.maintenance.item',
        'field_service_order_maintenance_item_rel',
        'order_id',
        'maintenance_item_id',
        string='保養項目',
        domain="[('product_tmpl_id', '=', product_id), ('maintenance_type', '=', maintenance_type)]",
        help='根據設備產品和保養類型自動載入對應的保養項目'
    )
    
    checklist_line_ids = fields.One2many(
        'field.service.checklist.line',
        'order_id',
        '檢查清單',
        help='由掃描QR code知道機器類型，選擇保養類型後自動載入對應的Check List'
    )
    
    # ===========================================
    # 維修單專用欄位 (對應需求文件 15-21 項)
    # ===========================================
    
    # 問題分類改用 enterprise_product_management 的維修問題庫
    
    repair_problem_ids = fields.Many2many(
        'epm.material.repair',
        'field_service_order_repair_problem_rel',
        'order_id',
        'repair_problem_id',
        '維修問題',
        help='選擇此工單相關的維修問題，直接從企業產品管理模組載入'
    )
    
    failure_symptom = fields.Text(
        '故障症狀',
        help='詳細描述故障的症狀和現象'
    )
    
    repair_urgency = fields.Selection([
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '緊急')
    ], '維修緊急程度', default='medium', help='維修工單的緊急程度')
    
    
    
    problem_description = fields.Text(
        '問題描述',
        help='手寫輸入問題詳情'
    )
    
    solution_description = fields.Text(
        '處理事項',
        help='手寫輸入處理方式'
    )
    
    part_category_main = fields.Char(
        '零件更換-主項',
        help='由掃描QR code知道機器類型，對應出不同的零件選項'
    )
    
    part_category_sub = fields.Char(
        '零件更換-次項',
        help='主項選擇馬達後，次項出現馬達光遮'
    )
    
    part_replacement_ids = fields.One2many(
        'field.service.part.replacement',
        'order_id',
        '零件更換記錄'
    )
    
    # ===========================================
    # 工作日誌專用欄位 (對應需求文件 10-16 項)  
    # ===========================================
    
    work_nature_main = fields.Selection([
        ('visit', '拜訪'),
        ('training', '教育訓練'),
        ('inspection', '檢查'),
        ('consultation', '諮詢'),
        ('maintenance', '維護'),
        ('installation', '安裝')
    ], '工作性質-主項', help='下拉式選擇主項')
    
    work_nature_sub = fields.Selection([
        # 拜訪相關
        ('visit_doctor', '醫師拜訪'),
        ('visit_purchase', '採購拜訪'),
        ('visit_admin', '行政拜訪'),
        # 教育訓練相關
        ('training_operation', '操作訓練'),
        ('training_maintenance', '維護訓練'),
        ('training_safety', '安全訓練'),
        # 其他可擴展
    ], '工作性質-次項', help='主項選擇拜訪後，次項出現醫師拜訪、採購拜訪')
    
    customer_contact_ids = fields.Many2many(
        'company.contact',
        'field_service_order_contact_rel',
        'order_id',
        'contact_id',
        string='客戶人員',
        domain="[('company_id', '=', partner_id), ('department_id', '=', department_id)]",
        help='可以多選，限定為選定公司和部門下的人員選項'
    )
    
    tag_ids = fields.Many2many(
        'field.service.tag',
        'field_service_order_tag_rel',
        'order_id',
        'tag_id',
        string='關聯標籤',
        help='類似Tag功能，可手動新增。下拉式選項，依照創立時間排序，用點選方式標記'
    )
    
    record_content = fields.Html(
        '紀錄內容',
        help='手寫輸入，字數希望可達1000字'
    )
    
    # 客戶建議事項（維修單的客戶服務處理單需要）
    customer_suggestion = fields.Text(
        '客戶建議事項',
        help='客戶對設備使用或維護的建議事項',
        tracking=True
    )
    
    # ===========================================
    # 工作日誌專用欄位
    # ===========================================
    
    work_category = fields.Selection([
        ('installation', '安裝'),
        ('maintenance', '維護'),
        ('repair', '修理'),
        ('inspection', '檢查'),
        ('consultation', '諮詢'),
        ('training', '訓練'),
        ('other', '其他')
    ], '工作類別', help='工作日誌的工作類別')
    
    work_hours = fields.Float(
        '工作時數',
        help='此次工作花費的時間（小時）'
    )
    
    work_location = fields.Char(
        '工作地點',
        help='具體的工作執行地點'
    )
    
    weather_condition = fields.Selection([
        ('sunny', '晴天'),
        ('cloudy', '多雲'),
        ('rainy', '雨天'),
        ('stormy', '暴風雨'),
        ('snowy', '雪天'),
        ('foggy', '霧天')
    ], '天氣狀況', help='工作當天的天氣狀況')
    
    daily_work_summary = fields.Text(
        '每日工作總結',
        help='詳細記錄今日完成的工作內容'
    )
    
    is_todo = fields.Boolean(
        '待辦事項',
        compute='_compute_is_todo',
        store=True,
        help='若新增日期超過今天日期，就標記為代辦事項'
    )
    
    # ===========================================
    # 通用欄位 (對應需求文件 19-21 項)
    # ===========================================
    
    description = fields.Text(
        '工作描述',
        help='詳細描述此工單的工作內容'
    )
    
    work_summary = fields.Text(
        '工作總結',
        help='工單完成後的工作總結'
    )
    
    notes = fields.Text(
        '備註',
        help='手寫輸入備註資訊'
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'field_service_attachment_rel',
        'order_id', 'attachment_id',
        '附件照片',
        help='可以使用手機相機，照相後作為附件上傳'
    )
    
    attachment_count = fields.Integer(
        '附件數量',
        compute='_compute_attachment_count'
    )
    
    expense_count = fields.Integer(
        '費用數量',
        compute='_compute_expense_count'
    )
    
    part_replacement_count = fields.Integer(
        '零件更換數量',
        compute='_compute_part_replacement_count'
    )
    
    expense_ids = fields.One2many(
        'field.service.expense',
        'order_id',
        '費用資料',
        help='選擇費用項目，然後填寫金額。此欄位可能填寫多筆費用'
    )
    
    # 費用總計
    total_expense = fields.Float(
        '費用總計',
        compute='_compute_total_expense',
        store=True,
        help='所有費用項目的總計金額'
    )
    
    # ===========================================
    # 簽名相關欄位
    # ===========================================
    
    signature = fields.Binary(
        '客戶簽名',
        help='讓客戶透過手機或平板簽名'
    )
    
    # 簡化的檔案上傳式簽名
    customer_signature_file = fields.Binary(
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
    
    signature_request_id = fields.Many2one(
        'sign.oca.request',
        '簽名請求',
        help='關聯的電子簽名請求'
    )
    
    customer_signature_date = fields.Datetime(
        '客戶簽名日期',
        help='客戶完成簽名的日期時間'
    )
    
    technician_signature_date = fields.Datetime(
        '技術人員簽名日期',
        help='技術人員完成簽名的日期時間'
    )
    
    report_template_id = fields.Many2one(
        'ir.ui.view',
        '報表模板',
        help='用於生成客戶報表的模板'
    )
    
    include_photos_in_report = fields.Boolean(
        '報表包含照片',
        default=True,
        help='生成報表時是否包含附件中的照片'
    )
    
    # ===========================================
    # 計算和關聯欄位
    # ===========================================
    
    @api.depends('start_date', 'end_date')
    def _compute_actual_hours(self):
        """
        計算實際工時
        
        根據開始和結束時間自動計算實際工時
        """
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date >= record.start_date:
                    delta = record.end_date - record.start_date
                    record.actual_hours = delta.total_seconds() / 3600.0
                else:
                    record.actual_hours = 0.0
            else:
                record.actual_hours = 0.0
    
    @api.depends('date', 'order_type')
    def _compute_is_todo(self):
        """
        計算是否為待辦事項
        
        若工作日誌的新增日期超過今天日期，就標記為待辦事項
        """
        today = fields.Date.today()
        for record in self:
            if record.order_type == 'work_log' and record.date:
                record.is_todo = record.date > today
            else:
                record.is_todo = False
    
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        """計算附件數量"""
        for record in self:
            record.attachment_count = len(record.attachment_ids)
    
    @api.depends('expense_ids')
    def _compute_expense_count(self):
        """計算費用數量"""
        for record in self:
            record.expense_count = len(record.expense_ids)
    
    @api.depends('expense_ids.amount')
    def _compute_total_expense(self):
        """
        計算費用總計
        
        根據所有費用項目計算總金額
        """
        for record in self:
            record.total_expense = sum(record.expense_ids.mapped('amount'))
    
    @api.depends('partner_id')
    def _compute_partner_code(self):
        """
        計算客戶代號
        
        根據選擇的客戶自動取得客戶代號
        """
        for record in self:
            record.partner_code = record.partner_id.ref if record.partner_id else False
    
    @api.depends('part_replacement_ids')
    def _compute_part_replacement_count(self):
        """計算零件更換數量"""
        for record in self:
            record.part_replacement_count = len(record.part_replacement_ids)
    
    @api.depends('equipment_id', 'equipment_id.contract_ids', 'equipment_id.contract_ids.state')
    def _compute_primary_contract(self):
        """
        計算主要合約
        
        從設備的活躍合約中選擇第一個作為主要合約
        """
        for record in self:
            if record.equipment_id and record.equipment_id.contract_ids:
                # 找出設備的所有活躍合約
                active_contracts = record.equipment_id.contract_ids.filtered(
                    lambda c: c.state == 'active'
                )
                # 選擇第一個活躍合約作為主要合約，按建立時間排序
                if active_contracts:
                    record.contract_id = active_contracts.sorted('create_date', reverse=True)[0]
                else:
                    record.contract_id = False
            else:
                record.contract_id = False
    
    @api.depends('start_date', 'end_date')
    def _compute_actual_duration(self):
        """
        計算實際工時
        
        與 actual_hours 類似，但用於 actual_duration 欄位
        """
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date >= record.start_date:
                    delta = record.end_date - record.start_date
                    record.actual_duration = delta.total_seconds() / 3600.0
                else:
                    record.actual_duration = 0.0
            else:
                record.actual_duration = 0.0
    
    # ===========================================
    # 預設值方法
    # ===========================================
    
    def _get_repairable_materials(self, product_tmpl_id):
        """
        根據產品取得可維修的物料清單
        
        透過 BOM 找到產品的所有物料，並篩選有維修問題記錄的物料
        
        Args:
            product_tmpl_id (int): 產品範本 ID
            
        Returns:
            list: 可維修物料的 ID 清單
        """
        # 找到產品的 BOM
        boms = self.env['mrp.bom'].search([('product_tmpl_id', '=', product_tmpl_id)])
        
        if not boms:
            return []
            
        # 從 BOM 中取得所有物料
        material_ids = []
        for bom in boms:
            material_ids.extend(bom.bom_line_ids.product_id.ids)
        
        if not material_ids:
            return []
            
        # 只返回有維修問題記錄的物料
        repair_records = self.env['epm.material.repair'].search([('material_id', 'in', material_ids)])
        return list(set(repair_records.mapped('material_id.id')))
    
    def _get_default_technician(self):
        """
        取得預設技術人員
        
        從當前登入使用者關聯的員工記錄取得
        """
        employee = self.env['hr.employee'].search([
            ('user_id', '=', self.env.uid)
        ], limit=1)
        return employee.id if employee else False
    
    # ===========================================
    # onchange 方法 (動態載入邏輯)
    # ===========================================
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
        客戶變更時的處理
        
        清除部門和聯絡人選擇，更新合約和設備的 domain
        """
        if self.partner_id:
            self.department_id = False
            self.contract_id = False
            self.equipment_id = False
            # 客戶變更時可以更新機器版本等資訊
            return {
                'domain': {
                    'department_id': [('company_id', '=', self.partner_id.id)],
                    'contract_id': [
                        ('partner_id', '=', self.partner_id.id),
                        ('state', '=', 'active')
                    ],
                    'equipment_id': [('partner_id', '=', self.partner_id.id)],
                    'customer_contact_ids': [('company_id', '=', self.partner_id.id)]
                }
            }
    
    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):
        """
        設備變更時自動帶入所有相關資訊
        
        自動帶入但允許修改：
        - 客戶資訊（客戶、部門、聯絡人）
        - 設備資訊（序號、財編、安裝位置）
        - 產品資訊（產品、型號、軟體版本）
        - 根據工單類型載入對應的檢查項目或維修選項
        """
        if not self.equipment_id:
            return
        
        # 自動帶入資訊（但允許使用者修改）
        if self.equipment_id.partner_id:
            self.partner_id = self.equipment_id.partner_id
        if self.equipment_id.department_id:
            self.department_id = self.equipment_id.department_id
        if self.equipment_id.contact_id:
            self.contact_id = self.equipment_id.contact_id
        if self.equipment_id.asset_number:
            self.hospital_asset_number = self.equipment_id.asset_number
        if self.equipment_id.name:
            self.serial_number = self.equipment_id.name
        if self.equipment_id.installation_location:
            self.installation_location = self.equipment_id.installation_location
        if self.equipment_id.product_id:
            self.product_id = self.equipment_id.product_id
        if self.equipment_id.variant_id:
            self.product_variant_id = self.equipment_id.variant_id
        if self.equipment_id.software_version:
            self.software_version = self.equipment_id.software_version
        
        # 為維修工單提供可維修的物料選項
        if self.order_type == 'repair' and self.equipment_id.product_id:
            repair_materials = self._get_repairable_materials(self.equipment_id.product_id.id)
            return {
                'domain': {
                    'repair_material_id': [('id', 'in', repair_materials)]
                }
            }
        
        # 如果有合約資訊也一併更新（透過 _compute_primary_contract 自動計算）
        # 手動觸發合約計算
        self._compute_primary_contract()
    
    @api.onchange('equipment_id', 'maintenance_type')
    def _onchange_equipment_maintenance(self):
        """
        設備或保養類型變更時載入保養項目
        
        根據設備類型和保養類型，從企業產品模組載入對應的保養項目作為 Check List
        """
        if self.order_type != 'maintenance':
            return
        
        # 清空現有的檢查清單
        self.checklist_line_ids = [(5, 0, 0)]
        
        if self.equipment_id and self.maintenance_type:
            # 取得設備的產品模板 ID
            equipment_product = self.equipment_id.product_id
            if equipment_product:
                # 使用企業產品模組的 API 取得保養項目
                items = self.env['epm.maintenance.item'].get_public_maintenance_items(
                    equipment_product.id, 
                    self.maintenance_type
                )
                
                # 建立檢查清單行
                lines = []
                for item in items:
                    lines.append((0, 0, {
                        'maintenance_item_id': item.id,
                        'name': item.name,  # 直接設定名稱
                        'is_checked': False,
                    }))
                self.checklist_line_ids = lines
    
    @api.onchange('product_id', 'maintenance_type')
    def _onchange_maintenance_items(self):
        """
        產品或保養類型變更時自動載入保養項目
        
        根據設備產品和保養類型，自動載入對應的保養項目
        """
        if self.product_id and self.maintenance_type:
            # 從企業產品管理模組載入保養項目
            maintenance_items = self.env['epm.maintenance.item'].search([
                ('product_tmpl_id', '=', self.product_id.id),
                ('maintenance_type', '=', self.maintenance_type),
                ('is_public', '=', True),
                ('active', '=', True)
            ])
            self.maintenance_item_ids = maintenance_items
        else:
            self.maintenance_item_ids = False
    
    @api.onchange('equipment_id')
    def _onchange_equipment_repair_problems(self):
        """
        設備變更時更新可選的維修問題
        
        根據設備產品的 BOM 取得相關物料的維修問題
        """
        if self.order_type != 'repair':
            return
        
        if self.equipment_id and self.equipment_id.product_id:
            # 使用企業產品管理模組的 API 取得維修問題
            repair_problems = self.env['epm.material.repair'].get_repairs_by_product(
                self.equipment_id.product_id.id
            )
            
            return {
                'domain': {
                    'repair_problem_ids': [('id', 'in', repair_problems.ids)]
                }
            }
        else:
            return {
                'domain': {
                    'repair_problem_ids': [('id', '=', False)]
                }
            }
    
    # ===========================================
    # 約束條件
    # ===========================================
    
    @api.constrains('start_date', 'end_date')
    def _check_time_logic(self):
        """檢查時間邏輯的合理性"""
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date < record.start_date:
                    raise ValidationError(_('結束時間不能早於開始時間！'))
    
    @api.constrains('date')
    def _check_date_not_future(self):
        """檢查單據日期不能太久遠的未來"""
        today = fields.Date.today()
        max_future_date = today + timedelta(days=365)  # 最多一年後
        
        for record in self:
            if record.date and record.date > max_future_date:
                raise ValidationError(_('單據日期不能超過一年後！'))
    
    # ===========================================
    # CRUD 和狀態管理方法
    # ===========================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        建立工單記錄
        
        自動生成工單編號
        """
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                order_type = vals.get('order_type', 'maintenance')
                if order_type == 'maintenance':
                    vals['name'] = self.env['ir.sequence'].next_by_code('field.service.order.maintenance') or 'New'
                elif order_type == 'repair':
                    vals['name'] = self.env['ir.sequence'].next_by_code('field.service.order.repair') or 'New'
                elif order_type == 'work_log':
                    vals['name'] = self.env['ir.sequence'].next_by_code('field.service.order.work_log') or 'New'
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('field.service.order') or 'New'
        return super().create(vals_list)
    
    def action_schedule(self):
        """
        排程工單
        
        將工單狀態從草稿變更為已排程
        """
        for record in self:
            if record.state == 'draft':
                record.state = 'scheduled'
                record.message_post(body=_("工單已排程"))

    def action_assign(self):
        """
        指派工單
        
        將工單狀態從已排程變更為已指派
        """
        for record in self:
            if record.state == 'scheduled':
                if not record.technician_id:
                    raise UserError(_('請先指定技術人員！'))
                record.state = 'assigned'
                record.message_post(body=_("工單已指派給 %s") % record.technician_id.name)

    def action_confirm(self):
        """
        確認工單
        
        將工單狀態從草稿變更為已確認
        """
        for record in self:
            if record.state == 'draft':
                record.state = 'confirmed'
                record.message_post(body=_("工單已確認"))
    
    def action_start(self):
        """
        開始作業
        
        將工單狀態變更為進行中
        """
        for record in self:
            if record.state in ['draft', 'confirmed', 'scheduled', 'assigned']:
                record.write({
                    'state': 'in_progress'
                })
                record.message_post(body=_("工單作業已開始"))
    
    def action_done(self):
        """
        完成工單
        
        將工單狀態變更為已完成
        """
        for record in self:
            if record.state == 'in_progress':
                record.write({
                    'state': 'done'
                })
                record.message_post(body=_("工單作業已完成"))
    
    def action_request_signature(self):
        """
        請求電子簽名
        
        生成客戶服務處理單並發送簽名請求
        """
        self.ensure_one()
        
        if self.state != 'done':
            raise UserError(_('只有已完成的工單才能請求簽名！'))
        
        # 生成客戶服務處理單 PDF
        report = self.env.ref('field_service_order.action_report_customer_service')
        pdf_content, _ = report._render_qweb_pdf(self.ids)
        
        # 建立簽名請求
        sign_request = self.env['sign.oca.request'].create({
            'name': _('服務單簽名 - %s') % self.name,
            'data': base64.b64encode(pdf_content),
            'filename': f'{self.name}_客戶服務處理單.pdf',
            'record_ref': f'{self._name},{self.id}',
            'user_id': self.env.user.id,
        })
        
        # 建立簽名項目 (客戶簽名)
        self.env['sign.oca.request.item'].create({
            'request_id': sign_request.id,
            'partner_id': self.partner_id.id,
        })
        
        # 更新工單的簽名請求關聯
        self.signature_request_id = sign_request.id
        
        # 發送簽名請求
        sign_request.action_send()
        
        self.message_post(body=_("已向客戶 %s 發送電子簽名請求") % self.partner_id.name)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('簽名請求已發送'),
                'message': _('已向 %s 發送簽名請求') % self.partner_id.name,
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_cancel(self):
        """取消工單"""
        for record in self:
            if record.state not in ('signed', 'closed'):
                record.state = 'cancelled'
                record.message_post(body=_("工單已取消"))
    
    def action_reopen(self):
        """重新開啟工單"""
        for record in self:
            if record.state == 'cancelled':
                record.state = 'draft'
                record.message_post(body=_("工單已重新開啟"))

    def action_reset_draft(self):
        """重設為草稿狀態"""
        for record in self:
            if record.state == 'cancelled':
                record.state = 'draft'
                record.message_post(body=_("工單已重設為草稿"))
    
    # ===========================================
    # 檢視相關方法
    # ===========================================
    
    def action_view_attachments(self):
        """檢視附件"""
        self.ensure_one()
        return {
            'name': _('附件'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', self.attachment_ids.ids)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            }
        }
    
    def action_view_expenses(self):
        """檢視費用記錄"""
        self.ensure_one()
        return {
            'name': _('費用記錄'),
            'type': 'ir.actions.act_window',
            'res_model': 'field.service.expense',
            'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)],
            'context': {
                'default_order_id': self.id,
            }
        }
    
    def action_view_part_replacements(self):
        """檢視零件更換記錄"""
        self.ensure_one()
        return {
            'name': _('零件更換記錄'),
            'type': 'ir.actions.act_window',
            'res_model': 'field.service.part.replacement',
            'view_mode': 'tree,form',
            'domain': [('order_id', '=', self.id)],
            'context': {
                'default_order_id': self.id,
            }
        }
    
    def action_view_signature(self):
        """檢視簽名記錄"""
        self.ensure_one()
        
        # 優先檢查檔案上傳式簽名
        if self.customer_signature_file:
            # 建立一個暫時的簽名檢視精靈
            wizard = self.env['field.service.signature.view.wizard'].create({
                'order_id': self.id,
            })
            return {
                'name': _('客戶簽名'),
                'type': 'ir.actions.act_window',
                'res_model': 'field.service.signature.view.wizard',
                'view_mode': 'form',
                'res_id': wizard.id,
                'target': 'new',
            }
        # 回退到舊的簽名系統
        elif self.signature_request_id:
            return {
                'name': _('簽名記錄'),
                'type': 'ir.actions.act_window',
                'res_model': 'sign.oca.request',
                'view_mode': 'form',
                'res_id': self.signature_request_id.id,
                'target': 'current',
            }
        else:
            # 沒有簽名記錄時，提供上傳選項
            return {
                'name': _('上傳客戶簽名'),
                'type': 'ir.actions.act_window',
                'res_model': 'field.service.signature.upload.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'active_id': self.id,
                    'default_order_id': self.id,
                    'default_signature_type': 'customer'
                }
            }
    
    def action_close(self):
        """關閉當前視窗"""
        return {'type': 'ir.actions.act_window_close'}
    
    def action_create_todo(self):
        """
        建立待辦事項
        
        從工作日誌複製基本資訊建立新的待辦事項
        """
        self.ensure_one()
        
        if self.order_type != 'work_log':
            raise UserError(_('只有工作日誌可以建立待辦事項！'))
        
        # 複製基本資訊建立新工單
        new_order = self.copy({
            'name': 'New',
            'date': fields.Date.today() + timedelta(days=7),  # 預設一週後
            'state': 'draft',
            'record_content': '',
            'notes': _('從工單 %s 建立的待辦事項') % self.name,
        })
        
        return {
            'name': _('待辦事項'),
            'type': 'ir.actions.act_window',
            'res_model': 'field.service.order',
            'res_id': new_order.id,
            'view_mode': 'form',
            'context': {'default_order_type': 'work_log'}
        }
    
    def action_load_maintenance_checklist(self):
        """
        載入保養檢查清單
        
        根據設備類型和保養類型從企業產品管理模組載入對應的保養項目
        """
        self.ensure_one()
        
        if self.order_type != 'maintenance':
            raise UserError(_('只有保養工單可以載入保養檢查清單！'))
        
        if not self.equipment_id:
            raise UserError(_('請先選擇設備！'))
        
        if not self.maintenance_type:
            raise UserError(_('請先選擇保養類型！'))
        
        # 清空現有的檢查清單
        self.checklist_line_ids.unlink()
        
        # 取得設備的產品
        equipment_product = self.equipment_id.product_id
        if not equipment_product:
            raise UserError(_('設備缺少產品資訊！'))
        
        # 使用企業產品模組的 API 取得保養項目
        items = self.env['epm.maintenance.item'].get_public_maintenance_items(
            equipment_product.id, 
            self.maintenance_type
        )
        
        if not items:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('無可用項目'),
                    'message': _('該設備和保養類型沒有定義保養項目'),
                    'type': 'warning',
                }
            }
        
        # 建立檢查清單行
        lines = []
        for item in items:
            lines.append((0, 0, {
                'maintenance_item_id': item.id,
                'name': item.name,
                'is_checked': False,
            }))
        
        self.checklist_line_ids = lines
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('檢查清單已載入'),
                'message': _('已從企業產品管理模組載入 %d 個保養項目') % len(items),
                'type': 'success',
            }
        }
    
    def action_load_repair_checklist(self):
        """
        載入維修檢查清單
        
        根據問題分類載入對應的維修檢查項目
        """
        self.ensure_one()
        
        if self.order_type != 'repair':
            raise UserError(_('只有維修工單可以載入維修檢查清單！'))
        
        if not self.repair_problem_line_ids:
            raise UserError(_('請先選擇維修問題！'))
        
        # 清空現有的檢查清單
        self.checklist_line_ids.unlink()
        
        # 這裡可以整合問題庫的維修程序
        # 暫時使用簡單的範例實作
        repair_steps = [
            '確認問題現象',
            '檢查相關連接',
            '測試功能',
            '更換故障零件',
            '功能測試'
        ]
        
        lines = []
        for step_name in repair_steps:
            lines.append((0, 0, {
                'name': step_name,
                'is_completed': False,
            }))
        
        self.checklist_line_ids = lines
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('維修檢查清單已載入'),
                'message': _('已載入 %d 個維修步驟') % len(repair_steps),
                'type': 'success',
            }
        }
    
    def action_generate_customer_report(self):
        """
        生成客戶報表
        
        根據工單內容生成客戶服務報表
        """
        self.ensure_one()
        
        if self.state not in ['done', 'confirmed']:
            raise UserError(_('只有已完成或已確認的工單才能生成客戶報表！'))
        
        # 生成客戶報表
        report = self.env.ref('field_service_order.action_report_customer_service')
        return report.report_action(self)
    
    def action_upload_signature(self):
        """
        開啟簽名上傳精靈
        
        提供簡化的檔案上傳式簽名功能
        """
        self.ensure_one()
        
        return {
            'name': _('上傳客戶簽名'),
            'type': 'ir.actions.act_window',
            'res_model': 'field.service.signature.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_signature_type': 'customer',
            }
        }
    
    def action_send_signature_request(self):
        """
        發送簽名請求
        
        向客戶發送電子簽名請求
        """
        self.ensure_one()
        
        if self.state != 'done':
            raise UserError(_('只有已完成的工單才能發送簽名請求！'))
        
        if self.signature_request_id:
            raise UserError(_('此工單已經發送過簽名請求！'))
        
        # 這個方法實際上就是 action_request_signature
        # 為了避免重複，這裡直接調用已存在的方法
        return self.action_request_signature()
    
    # ===========================================
    # API 方法 (供外部調用)
    # ===========================================
    
    @api.model
    def get_service_history(self, serial_number):
        """
        根據機器序號查詢服務歷史
        
        Args:
            serial_number (str): 機器序號
            
        Returns:
            dict: 服務歷史記錄
        """
        orders = self.search([
            ('serial_number', '=', serial_number),
            ('state', 'in', ['done', 'signed', 'closed'])
        ], order='date desc')
        
        history = []
        for order in orders:
            history.append({
                'name': order.name,
                'date': order.date,
                'order_type': order.order_type,
                'technician': order.technician_id.name,
                'state': order.state,
                'notes': order.notes,
            })
        
        return {
            'success': True,
            'serial_number': serial_number,
            'history': history,
            'total_count': len(history)
        }