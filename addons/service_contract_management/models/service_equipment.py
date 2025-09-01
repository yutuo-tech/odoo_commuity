from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ServiceEquipment(models.Model):
    _name = 'service.equipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '設備/貨物管理'
    _order = 'name, id desc'

    # 核心識別
    name = fields.Char('設備序號', required=True, index=True, tracking=True)
    asset_number = fields.Char('資產編號', tracking=True)
    
    # 產品關聯
    product_id = fields.Many2one('product.template', '產品', required=True, tracking=True)
    variant_id = fields.Many2one(
        'product.product', 
        '產品型號',
        domain="[('product_tmpl_id', '=', product_id)]"
    )
    
    # 客戶資訊（出貨後填寫）
    partner_id = fields.Many2one('res.partner', '客戶公司', tracking=True)
    department_id = fields.Many2one(
        'company.department', 
        '使用部門',
        domain="[('company_id', '=', partner_id)]"
    )
    contact_id = fields.Many2one(
        'company.contact', 
        '聯絡人',
        domain="[('company_id', '=', partner_id)]"
    )
    
    # 人員相關
    receiver_contact_id = fields.Many2one(
        'company.contact',
        '簽收人員',
        domain="[('company_id', '=', partner_id)]",
        help="客戶方簽收設備的人員",
        tracking=True
    )
    responsible_employee_id = fields.Many2one(
        'hr.employee',
        '負責人員',
        help="我方負責發貨的員工",
        tracking=True
    )
    
    # 財務相關
    partner_tax_id = fields.Char(
        '對方統編',
        help="客戶公司統一編號",
        size=10
    )
    
    # 設備資訊
    production_date = fields.Date('生產日期')  # 更明確的命名
    purchase_date = fields.Date('採購日期', tracking=True)
    manufacture_date = fields.Date('製造日期')  # 保留原欄位相容性
    delivery_date = fields.Date('實際交貨日期', tracking=True)
    installation_date = fields.Date('安裝日期')
    installation_location = fields.Text('安裝位置')
    warranty_start_date = fields.Date('保固開始日')
    warranty_end_date = fields.Date('保固到期日', tracking=True)
    
    # 狀態管理
    status = fields.Selection([
        ('in_production', '生產中'),
        ('in_stock', '庫存中'),
        ('reserved', '已預留'),
        ('shipped', '已出貨'),
        ('installed', '已安裝'),
        ('in_operation', '運行中'),
        ('maintenance', '保養中'),
        ('repair', '維修中'),
        ('returned', '已退回'),
        ('scrapped', '已報廢')
    ], string='狀態', default='in_production', required=True, tracking=True)
    
    # 財務資訊
    price = fields.Float('價格', digits='Product Price')
    currency_id = fields.Many2one(
        'res.currency', 
        '幣別',
        default=lambda self: self.env.company.currency_id
    )
    
    # 合約關聯
    contract_ids = fields.Many2many(
        'service.contract',
        'contract_equipment_rel',
        'equipment_id',
        'contract_id',
        string='相關合約'
    )
    contract_count = fields.Integer('合約數量', compute='_compute_contract_count')
    
    # 追蹤資訊
    last_maintenance_date = fields.Date('上次維護', tracking=True)
    next_maintenance_date = fields.Date('下次保養日期')
    maintenance_frequency = fields.Selection([
        ('weekly', '每週'),
        ('monthly', '每月'),
        ('quarterly', '每季'),
        ('semi_annual', '每半年'),
        ('annual', '每年'),
        ('on_demand', '視需求')
    ], string='維護頻率', default='quarterly', tracking=True)
    maintenance_count = fields.Integer('保養次數', default=0)
    repair_count = fields.Integer('維修次數', default=0)
    
    # 備註
    notes = fields.Text('備註')
    
    # 狀態相關的計算欄位
    is_under_warranty = fields.Boolean('保固期內', compute='_compute_warranty_status', store=True, search='_search_under_warranty')
    warranty_days_remaining = fields.Integer('保固剩餘天數', compute='_compute_warranty_status', store=True)
    
    # 顯示名稱
    display_name = fields.Char('顯示名稱', compute='_compute_display_name', store=True)

    @api.depends('name', 'product_id.name', 'partner_id.name')
    def _compute_display_name(self):
        """計算顯示名稱"""
        for record in self:
            parts = []
            if record.name:
                parts.append(record.name)
            if record.product_id and record.product_id.name:
                parts.append(f"({record.product_id.name})")
            if record.partner_id and record.partner_id.name:
                parts.append(f"- {record.partner_id.name}")
            record.display_name = ' '.join(parts) if parts else '/'

    @api.depends('contract_ids')
    def _compute_contract_count(self):
        """計算關聯的合約數量"""
        for record in self:
            record.contract_count = len(record.contract_ids)

    @api.depends('warranty_end_date')
    def _compute_warranty_status(self):
        """計算保固狀態"""
        today = fields.Date.today()
        for record in self:
            if record.warranty_end_date:
                record.is_under_warranty = record.warranty_end_date >= today
                delta = record.warranty_end_date - today
                record.warranty_days_remaining = delta.days if delta.days > 0 else 0
            else:
                record.is_under_warranty = False
                record.warranty_days_remaining = 0

    def _search_under_warranty(self, operator, value):
        """搜尋保固期內的設備"""
        today = fields.Date.today()
        if (operator == '=' and value) or (operator == '!=' and not value):
            domain = [('warranty_end_date', '>=', today)]
        else:
            domain = ['|', ('warranty_end_date', '<', today), ('warranty_end_date', '=', False)]
        return domain

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """產品變更時清除產品型號"""
        if self.product_id:
            self.variant_id = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """客戶變更時清除部門和聯絡人"""
        if self.partner_id:
            self.department_id = False
            self.contact_id = False

    @api.constrains('name')
    def _check_serial_number_unique(self):
        """確保設備序號唯一"""
        for record in self:
            if record.name:
                duplicate = self.search([
                    ('name', '=', record.name),
                    ('id', '!=', record.id)
                ])
                if duplicate:
                    raise ValidationError(f'設備序號 {record.name} 已存在！')

    @api.constrains('warranty_start_date', 'warranty_end_date')
    def _check_warranty_dates(self):
        """檢查保固日期邏輯"""
        for record in self:
            if record.warranty_start_date and record.warranty_end_date:
                if record.warranty_end_date < record.warranty_start_date:
                    raise ValidationError('保固結束日期不能早於開始日期！')

    def action_view_contracts(self):
        """查看相關合約"""
        self.ensure_one()
        return {
            'name': f'{self.name} - 相關合約',
            'type': 'ir.actions.act_window',
            'res_model': 'service.contract',
            'view_mode': 'list,form',
            'domain': [('equipment_ids', 'in', self.ids)],
            'context': {
                'default_equipment_ids': [(6, 0, self.ids)],
            }
        }

    def action_create_contract(self):
        """建立新合約"""
        self.ensure_one()
        return {
            'name': '建立服務合約',
            'type': 'ir.actions.act_window',
            'res_model': 'service.contract',
            'view_mode': 'form',
            'context': {
                'default_equipment_ids': [(6, 0, self.ids)],
                'default_partner_id': self.partner_id.id,
                'default_department_id': self.department_id.id,
                'default_contact_id': self.contact_id.id,
            }
        }

    # API 方法供工單系統使用
    @api.model
    def get_equipment_by_serial(self, serial_number):
        """
        根據序號獲取設備完整資訊
        Args:
            serial_number (str): 設備序號
        Returns:
            dict: 設備資訊
        """
        equipment = self.search([('name', '=', serial_number)], limit=1)
        if not equipment:
            return {'success': False, 'message': f'找不到序號 {serial_number} 的設備'}
        
        return {
            'success': True,
            'equipment': {
                'id': equipment.id,
                'serial_number': equipment.name,
                'asset_number': equipment.asset_number,
                'product': equipment.product_id.name,
                'variant': equipment.variant_id.name if equipment.variant_id else None,
                'customer': equipment.partner_id.name if equipment.partner_id else None,
                'department': equipment.department_id.name if equipment.department_id else None,
                'contact': equipment.contact_id.name if equipment.contact_id else None,
                'status': equipment.status,
                'installation_location': equipment.installation_location,
                'warranty_end_date': equipment.warranty_end_date,
                'is_under_warranty': equipment.is_under_warranty,
                'last_maintenance_date': equipment.last_maintenance_date,
                'next_maintenance_date': equipment.next_maintenance_date,
            }
        }

    def update_equipment_status(self, new_status, notes=None):
        """
        更新設備狀態（從工單系統調用）
        Args:
            new_status (str): 新狀態
            notes (str): 備註
        """
        self.ensure_one()
        self.write({
            'status': new_status,
        })
        if notes:
            self.message_post(body=notes)
        return True

    def record_maintenance_activity(self, activity_data):
        """
        記錄維護活動
        Args:
            activity_data (dict): 活動資料
        """
        self.ensure_one()
        self.write({
            'last_maintenance_date': activity_data.get('date', fields.Date.today()),
            'maintenance_count': self.maintenance_count + 1,
        })
        
        # 記錄活動
        message = f"保養活動記錄：{activity_data.get('description', '')}"
        self.message_post(body=message)
        return True