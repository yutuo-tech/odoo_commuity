# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class EPMMaintenanceItem(models.Model):
    """
    產品保養項目管理
    
    功能說明：
    - 為每個產品定義多個保養項目作為工單系統的 checklist
    - 支援不同保養類型（例行保養、大保養等）
    - 可控制是否顯示給外部工單
    
    業務流程：
    使用者選擇機器 → 選擇保養類型 → 系統產生對應的保養 checklist
    """
    _name = 'epm.maintenance.item'
    _description = '產品保養項目'
    _order = 'product_tmpl_id, maintenance_type, sequence, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # 基本資訊欄位
    product_tmpl_id = fields.Many2one(
        'product.template', '產品', required=True,
        help='選擇要設定保養項目的產品'
    )
    name = fields.Char(
        '保養項目名稱', required=True,
        help='保養項目的具體名稱，如：更換機油、檢查皮帶等'
    )
    
    # 保養類型
    maintenance_type = fields.Selection([
        ('routine', '例行保養'),
        ('major', '大保養'), 
        ('quarterly', '季度保養'),
        ('annual', '年度保養'),
        ('emergency', '緊急保養'),
        ('preventive', '預防性保養'),
    ], '保養類型', required=True, default='routine',
        help='保養的類型分類，用於工單系統篩選對應的 checklist')
    
    # 價格資訊
    price = fields.Float(
        '定價', digits='Product Price', default=0.0,
        help='此保養項目的預估費用'
    )
    currency = fields.Selection([
        ('TWD', '台幣 (TWD)'),
        ('USD', '美元 (USD)'),
        ('EUR', '歐元 (EUR)'),
        ('CNY', '人民幣 (CNY)'),
        ('JPY', '日圓 (JPY)')
    ], '幣值', default='TWD',
        help='價格的幣別')
    
    # 詳細內容欄位
    key_points = fields.Text(
        '保養要點',
        help='保養的關鍵要點和注意事項，提供給技術人員參考'
    )
    description = fields.Text(
        '詳細描述',
        help='保養項目的詳細說明、步驟和要求'
    )
    
    # 顯示控制
    is_public = fields.Boolean(
        '顯示給外部工單', default=True,
        help='控制此保養項目是否在外部工單中顯示，\n'
             '若取消勾選則僅供內部使用'
    )
    
    # 排序和狀態
    sequence = fields.Integer(
        '排序', default=10,
        help='保養項目的執行順序，數字越小越優先'
    )
    active = fields.Boolean(
        '啟用', default=True,
        help='停用的保養項目不會出現在工單選項中'
    )
    
    # 計算欄位
    full_name = fields.Char(
        '完整名稱', compute='_compute_full_name', store=True,
        help='產品名稱 + 保養項目名稱的組合'
    )
    
    # 統計資訊（預留給未來擴展）
    usage_count = fields.Integer(
        '使用次數', default=0, readonly=True,
        help='此保養項目被工單使用的次數統計'
    )
    
    # 約束條件
    _sql_constraints = [
        ('positive_price', 'CHECK(price >= 0)', '價格不能為負數！'),
        ('positive_sequence', 'CHECK(sequence >= 0)', '排序序號不能為負數！'),
        ('product_item_uniq', 
         'unique(product_tmpl_id, name, maintenance_type)', 
         '相同產品的相同保養類型下，保養項目名稱必須唯一！'),
    ]
    
    @api.depends('product_tmpl_id', 'name')
    def _compute_full_name(self):
        """
        計算完整名稱
        格式：[產品名稱] - 保養項目名稱
        """
        for record in self:
            if record.product_tmpl_id and record.name:
                record.full_name = f"[{record.product_tmpl_id.name}] - {record.name}"
            else:
                record.full_name = record.name or ''
    
    @api.model
    def get_maintenance_checklist(self, product_id, maintenance_type=None):
        """
        根據產品和保養類型取得保養項目清單
        
        此方法為工單系統提供 API，用於產生保養 checklist
        
        Args:
            product_id (int): 產品模板 ID
            maintenance_type (str, optional): 保養類型篩選條件
            
        Returns:
            list: 保養項目記錄列表，包含完整的項目資訊
            
        SECURITY: 僅返回啟用且符合條件的保養項目
        """
        domain = [
            ('product_tmpl_id', '=', product_id),
            ('active', '=', True)
        ]
        
        if maintenance_type:
            domain.append(('maintenance_type', '=', maintenance_type))
        
        return self.search(domain, order='sequence, name')
    
    @api.model
    def get_public_maintenance_items(self, product_id, maintenance_type=None):
        """
        取得可顯示給外部工單的保養項目
        
        Args:
            product_id (int): 產品模板 ID
            maintenance_type (str, optional): 保養類型篩選條件
            
        Returns:
            recordset: 符合條件的保養項目記錄集
            
        NOTE: 此方法專為外部工單系統設計
        """
        domain = [
            ('product_tmpl_id', '=', product_id),
            ('active', '=', True),
            ('is_public', '=', True)
        ]
        
        if maintenance_type:
            domain.append(('maintenance_type', '=', maintenance_type))
        
        return self.search(domain, order='sequence, name')
    
    @api.model
    def get_maintenance_types_by_product(self, product_id):
        """
        取得指定產品的所有保養類型選項
        
        Args:
            product_id (int): 產品模板 ID
            
        Returns:
            list: 包含保養類型代碼和名稱的 tuple 列表
        """
        items = self.search([
            ('product_tmpl_id', '=', product_id),
            ('active', '=', True)
        ])
        
        types = set(items.mapped('maintenance_type'))
        type_selection = dict(self._fields['maintenance_type'].selection)
        
        return [(t, type_selection.get(t, t)) for t in types]
    
    @api.constrains('price')
    def _check_price_currency_consistency(self):
        """
        檢查價格與幣值的一致性
        
        當價格大於 0 時，必須指定幣值
        """
        for record in self:
            if record.price > 0 and not record.currency:
                raise UserError('當設定價格時，必須指定幣值！')
    
    def name_get(self):
        """
        自定義顯示名稱
        格式：保養類型 - 保養項目名稱
        """
        result = []
        type_dict = dict(self._fields['maintenance_type'].selection)
        
        for record in self:
            type_name = type_dict.get(record.maintenance_type, record.maintenance_type)
            name = f"{type_name} - {record.name}"
            result.append((record.id, name))
        
        return result
    
    def increment_usage_count(self):
        """
        增加使用次數統計
        
        當保養項目被工單使用時調用此方法
        
        WARNING: 此方法不檢查權限，調用前請確保有適當授權
        """
        for record in self:
            record.sudo().write({'usage_count': record.usage_count + 1})