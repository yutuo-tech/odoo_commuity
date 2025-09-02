# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FieldServiceExpense(models.Model):
    """
    服務工單費用記錄
    
    功能說明：
    - 記錄工單相關的各項費用
    - 支援多幣別
    - 可記錄多筆費用項目
    
    對應需求文件第 20 項：費用資料
    """
    _name = 'field.service.expense'
    _description = '服務工單費用記錄'
    _order = 'sequence, id'
    
    # 關聯欄位
    order_id = fields.Many2one(
        'field.service.order',
        '服務工單',
        required=True,
        ondelete='cascade',
        help='所屬的服務工單'
    )
    
    # 基本資訊
    sequence = fields.Integer('排序', default=10)
    
    expense_type = fields.Selection([
        ('material', '材料費'),
        ('labor', '工資'),
        ('transport', '交通費'),
        ('accommodation', '住宿費'),
        ('meal', '餐費'),
        ('fuel', '燃料費'),
        ('parts', '零件費'),
        ('consumables', '耗材費'),
        ('service', '服務費'),
        ('other', '其他')
    ], '費用類型', required=True, default='material',
        help='選擇費用項目類型')
    
    description = fields.Char(
        '說明',
        required=True,
        help='費用項目的詳細說明'
    )
    
    # 金額相關
    amount = fields.Monetary(
        '金額',
        required=True,
        currency_field='currency_id',
        help='填寫金額'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        '幣別',
        required=True,
        default=lambda self: self.env.company.currency_id,
        help='選擇幣別'
    )
    
    # 數量和單價 (可選)
    quantity = fields.Float(
        '數量',
        default=1.0,
        digits='Product Unit of Measure',
        help='費用項目的數量'
    )
    
    unit_price = fields.Monetary(
        '單價',
        currency_field='currency_id',
        compute='_compute_unit_price',
        inverse='_inverse_unit_price',
        store=True,
        help='單價 = 金額 / 數量'
    )
    
    # 審核相關
    is_approved = fields.Boolean(
        '已審核',
        default=False,
        help='費用是否已審核確認'
    )
    
    approved_by = fields.Many2one(
        'res.users',
        '審核人',
        help='費用審核人'
    )
    
    approved_date = fields.Datetime(
        '審核時間',
        help='費用審核時間'
    )
    
    # 備註
    notes = fields.Text('備註')
    
    # 計算欄位
    display_name = fields.Char(
        '顯示名稱',
        compute='_compute_display_name',
        store=True
    )
    
    @api.depends('expense_type', 'description', 'amount', 'currency_id')
    def _compute_display_name(self):
        """計算顯示名稱"""
        for record in self:
            expense_type_dict = dict(record._fields['expense_type'].selection)
            type_name = expense_type_dict.get(record.expense_type, record.expense_type)
            
            if record.currency_id:
                amount_str = f"{record.amount:,.2f} {record.currency_id.name}"
            else:
                amount_str = f"{record.amount:,.2f}"
            
            record.display_name = f"{type_name} - {record.description} ({amount_str})"
    
    @api.depends('amount', 'quantity')
    def _compute_unit_price(self):
        """計算單價"""
        for record in self:
            if record.quantity and record.quantity != 0:
                record.unit_price = record.amount / record.quantity
            else:
                record.unit_price = record.amount
    
    def _inverse_unit_price(self):
        """反向計算總金額"""
        for record in self:
            if record.unit_price and record.quantity:
                record.amount = record.unit_price * record.quantity
    
    # 約束條件
    @api.constrains('amount')
    def _check_amount_positive(self):
        """檢查金額必須為正數"""
        for record in self:
            if record.amount < 0:
                raise ValidationError(_('費用金額不能為負數！'))
    
    @api.constrains('quantity')
    def _check_quantity_positive(self):
        """檢查數量必須為正數"""
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_('數量必須大於 0！'))
    
    # 方法
    def action_approve(self):
        """審核費用"""
        self.write({
            'is_approved': True,
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now()
        })
        
        for record in self:
            record.order_id.message_post(
                body=_('費用項目 "%s" 已審核：%s %s') % (
                    record.description,
                    record.amount,
                    record.currency_id.name
                )
            )
    
    def action_reject(self):
        """拒絕費用"""
        self.write({
            'is_approved': False,
            'approved_by': False,
            'approved_date': False
        })
        
        for record in self:
            record.order_id.message_post(
                body=_('費用項目 "%s" 已拒絕：%s %s') % (
                    record.description,
                    record.amount,
                    record.currency_id.name
                )
            )


class FieldServiceExpenseType(models.Model):
    """
    費用類型管理 (可選)
    
    功能說明：
    - 管理常用的費用類型
    - 可預設單價和說明
    """
    _name = 'field.service.expense.type'
    _description = '費用類型'
    _order = 'name'
    
    name = fields.Char('費用類型名稱', required=True)
    code = fields.Char('代碼', required=True, help='費用類型代碼')
    
    default_amount = fields.Monetary(
        '預設金額',
        currency_field='currency_id',
        help='此類型費用的預設金額'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        '幣別',
        default=lambda self: self.env.company.currency_id
    )
    
    description = fields.Text('說明')
    active = fields.Boolean('啟用', default=True)
    
    # 約束條件
    _sql_constraints = [
        ('code_unique', 'unique(code)', '費用類型代碼必須唯一！'),
    ]