from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class ServiceContract(models.Model):
    _name = 'service.contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '服務合約'
    _order = 'name desc'

    # 合約識別
    name = fields.Char('合約編號', required=True, index=True, tracking=True)
    contract_name = fields.Char('合約名稱', tracking=True)
    
    # 合約類型
    contract_type = fields.Selection([
        ('warranty', '保固合約'),
        ('maintenance', '維護合約'),
        ('full_service', '全責保固'),
        ('spare', '備機合約'),
        ('rental', '租賃合約'),
        ('other', '其他')
    ], string='合約類型', required=True, tracking=True)
    
    # 客戶資訊
    partner_id = fields.Many2one('res.partner', '客戶', required=True, tracking=True)
    department_id = fields.Many2one(
        'company.department', 
        '簽約部門',
        domain="[('company_id', '=', partner_id)]"
    )
    contact_id = fields.Many2one(
        'company.contact', 
        '簽約聯絡人',
        domain="[('company_id', '=', partner_id)]"
    )
    
    # 人員相關
    responsible_employee_id = fields.Many2one(
        'hr.employee',
        '負責人',
        help="我方負責此合約的員工",
        tracking=True
    )
    
    # 合約期限
    sign_date = fields.Date('簽約日期', tracking=True)
    start_date = fields.Date('開始日期', required=True, tracking=True)
    end_date = fields.Date('結束日期', required=True, tracking=True)
    
    # 設備關聯
    equipment_ids = fields.Many2many(
        'service.equipment',
        'contract_equipment_rel',
        'contract_id',
        'equipment_id',
        string='涵蓋設備'
    )
    equipment_count = fields.Integer('設備數量', compute='_compute_equipment_count')
    
    # 財務資訊
    total_amount = fields.Monetary('合約總額', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency', 
        '幣別',
        default=lambda self: self.env.company.currency_id
    )
    
    # 驗收和財務相關
    acceptance_date = fields.Date(
        '驗收日期',
        help="客戶驗收合約服務的日期",
        tracking=True
    )
    billing_date = fields.Date(
        '請款時間',
        help="向客戶請款的日期",
        tracking=True
    )
    payment_received_date = fields.Date(
        '入帳日期',
        help="實際收到款項的日期",
        tracking=True
    )
    
    # 金額細分
    billed_amount = fields.Monetary(
        '已請款金額',
        currency_field='currency_id',
        tracking=True
    )
    received_amount = fields.Monetary(
        '已收金額',
        currency_field='currency_id',
        tracking=True
    )
    balance_amount = fields.Monetary(
        '餘額',
        compute='_compute_balance',
        store=True,
        currency_field='currency_id'
    )
    
    # 付款相關
    payment_term = fields.Selection([
        ('monthly', '月付'),
        ('quarterly', '季付'),
        ('yearly', '年付'),
        ('onetime', '一次付清')
    ], string='付款條件')
    
    # 狀態管理
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirmed', '已確認'),
        ('active', '執行中'),
        ('expired', '已到期'),
        ('renewed', '已續約'),
        ('cancelled', '已取消'),
        ('closed', '已結案')
    ], string='狀態', default='draft', required=True, tracking=True)
    
    # 計算欄位
    days_to_expiry = fields.Integer('到期剩餘天數', compute='_compute_expiry_info')
    is_expiring_soon = fields.Boolean('即將到期', compute='_compute_is_expiring_soon', store=True)
    duration_months = fields.Integer('合約期間(月)', compute='_compute_duration')
    
    # 備註
    remarks = fields.Text('備註')
    
    # 顯示名稱
    display_name = fields.Char('顯示名稱', compute='_compute_display_name', store=True)

    @api.depends('name', 'contract_name', 'partner_id.name')
    def _compute_display_name(self):
        """計算顯示名稱"""
        for record in self:
            parts = []
            if record.name:
                parts.append(record.name)
            if record.contract_name:
                parts.append(f"({record.contract_name})")
            if record.partner_id and record.partner_id.name:
                parts.append(f"- {record.partner_id.name}")
            record.display_name = ' '.join(parts) if parts else '/'

    @api.depends('equipment_ids')
    def _compute_equipment_count(self):
        """計算關聯的設備數量"""
        for record in self:
            record.equipment_count = len(record.equipment_ids)

    @api.depends('total_amount', 'received_amount')
    def _compute_balance(self):
        """計算合約餘額"""
        for record in self:
            record.balance_amount = (record.total_amount or 0) - (record.received_amount or 0)

    @api.depends('end_date')
    def _compute_expiry_info(self):
        """計算到期剩餘天數"""
        today = date.today()
        for record in self:
            if record.end_date:
                delta = record.end_date - today
                record.days_to_expiry = delta.days
            else:
                record.days_to_expiry = 0

    @api.depends('end_date', 'state')
    def _compute_is_expiring_soon(self):
        """計算是否即將到期"""
        today = date.today()
        for record in self:
            if record.end_date and record.state == 'active':
                delta = record.end_date - today
                # 30天內到期算即將到期
                record.is_expiring_soon = (0 <= delta.days <= 30)
            else:
                record.is_expiring_soon = False

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        """計算合約期間"""
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.duration_months = round(delta.days / 30)
            else:
                record.duration_months = 0

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """客戶變更時清除部門和聯絡人"""
        if self.partner_id:
            self.department_id = False
            self.contact_id = False

    @api.constrains('start_date', 'end_date')
    def _check_contract_dates(self):
        """檢查合約日期邏輯"""
        for record in self:
            if record.start_date and record.end_date:
                if record.end_date <= record.start_date:
                    raise ValidationError('合約結束日期必須晚於開始日期！')

    @api.constrains('name')
    def _check_contract_number_unique(self):
        """確保合約編號唯一"""
        for record in self:
            if record.name:
                duplicate = self.search([
                    ('name', '=', record.name),
                    ('id', '!=', record.id)
                ])
                if duplicate:
                    raise ValidationError(f'合約編號 {record.name} 已存在！')

    def action_confirm(self):
        """確認合約"""
        for record in self:
            if record.state == 'draft':
                record.state = 'confirmed'
                record.message_post(body="合約已確認")

    def action_activate(self):
        """啟動合約"""
        today = date.today()
        for record in self:
            if record.state == 'confirmed' and record.start_date <= today:
                record.state = 'active'
                record.message_post(body="合約已啟動")

    def action_expire(self):
        """到期合約"""
        for record in self:
            if record.state == 'active':
                record.state = 'expired'
                record.message_post(body="合約已到期")

    def action_renew(self):
        """續約"""
        self.ensure_one()
        # 建立新的合約記錄
        new_contract = self.copy({
            'name': f"{self.name}-R",
            'state': 'draft',
            'start_date': self.end_date + timedelta(days=1),
            'end_date': self.end_date + timedelta(days=365),  # 預設續約一年
            'sign_date': False,
        })
        
        # 原合約標記為已續約
        self.state = 'renewed'
        self.message_post(body=f"合約已續約，新合約編號：{new_contract.name}")
        
        return {
            'name': '續約合約',
            'type': 'ir.actions.act_window',
            'res_model': 'service.contract',
            'res_id': new_contract.id,
            'view_mode': 'form',
        }

    def action_cancel(self):
        """取消合約"""
        for record in self:
            if record.state not in ('closed', 'cancelled'):
                record.state = 'cancelled'
                record.message_post(body="合約已取消")

    def action_close(self):
        """結案合約"""
        for record in self:
            if record.state in ('expired', 'cancelled'):
                record.state = 'closed'
                record.message_post(body="合約已結案")

    def action_view_equipment(self):
        """查看涵蓋設備"""
        self.ensure_one()
        return {
            'name': f'{self.name} - 涵蓋設備',
            'type': 'ir.actions.act_window',
            'res_model': 'service.equipment',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.equipment_ids.ids)],
        }

    def action_add_equipment(self):
        """添加設備"""
        self.ensure_one()
        return {
            'name': '選擇設備',
            'type': 'ir.actions.act_window',
            'res_model': 'service.equipment',
            'view_mode': 'list',
            'domain': [('id', 'not in', self.equipment_ids.ids)],
            'context': {
                'search_default_partner_id': self.partner_id.id,
            }
        }

    # 自動化方法
    @api.model
    def _cron_check_expiring_contracts(self):
        """定期檢查即將到期的合約"""
        expiring_contracts = self.search([
            ('state', '=', 'active'),
            ('is_expiring_soon', '=', True)
        ])
        
        for contract in expiring_contracts:
            # 建立活動提醒
            contract.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'合約即將到期：{contract.name}',
                note=f'合約將於 {contract.end_date} 到期，剩餘 {contract.days_to_expiry} 天',
                date_deadline=contract.end_date - timedelta(days=7)
            )

    @api.model
    def _cron_expire_contracts(self):
        """自動到期合約"""
        today = date.today()
        expired_contracts = self.search([
            ('state', '=', 'active'),
            ('end_date', '<', today)
        ])
        
        for contract in expired_contracts:
            contract.action_expire()

    # API 方法供工單系統使用
    @api.model
    def get_equipment_contracts(self, serial_number):
        """
        獲取設備的合約資訊
        Args:
            serial_number (str): 設備序號
        Returns:
            dict: 合約資訊列表
        """
        equipment = self.env['service.equipment'].search([('name', '=', serial_number)], limit=1)
        if not equipment:
            return {'success': False, 'message': f'找不到序號 {serial_number} 的設備'}
        
        contracts = equipment.contract_ids.filtered(lambda c: c.state == 'active')
        
        contract_list = []
        for contract in contracts:
            contract_list.append({
                'id': contract.id,
                'name': contract.name,
                'contract_type': contract.contract_type,
                'start_date': contract.start_date,
                'end_date': contract.end_date,
                'is_expiring_soon': contract.is_expiring_soon,
                'days_to_expiry': contract.days_to_expiry,
            })
        
        return {
            'success': True,
            'equipment_id': equipment.id,
            'contracts': contract_list
        }