# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class FieldServiceTag(models.Model):
    """
    服務工單標籤
    
    功能說明：
    - 管理工作日誌的關聯標籤
    - 支援顏色標記
    - 按建立時間排序
    
    對應需求文件第 12 項：關聯標籤
    """
    _name = 'field.service.tag'
    _description = '服務工單標籤'
    _order = 'name'
    
    name = fields.Char(
        '標籤名稱',
        required=True,
        help='標籤的名稱，可手動新增'
    )
    
    color = fields.Integer(
        '顏色索引',
        default=0,
        help='標籤的顏色，用於視覺區分'
    )
    
    active = fields.Boolean(
        '啟用',
        default=True,
        help='停用的標籤不會出現在選項中'
    )
    
    description = fields.Text(
        '描述',
        help='標籤的詳細說明'
    )
    
    # 使用統計
    usage_count = fields.Integer(
        '使用次數',
        compute='_compute_usage_count',
        help='此標籤被使用的次數'
    )
    
    order_ids = fields.Many2many(
        'field.service.order',
        'field_service_order_tag_rel',
        'tag_id',
        'order_id',
        string='關聯工單',
        help='使用此標籤的工單'
    )
    
    create_date = fields.Datetime(
        '建立時間',
        default=fields.Datetime.now,
        readonly=True,
        help='標籤建立的時間，用於排序'
    )
    
    created_by = fields.Many2one(
        'res.users',
        '建立人',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    # 計算欄位
    display_name = fields.Char(
        '顯示名稱',
        compute='_compute_display_name',
        store=True
    )
    
    @api.depends('name', 'usage_count')
    def _compute_display_name(self):
        """計算顯示名稱，包含使用次數"""
        for record in self:
            record.display_name = f"{record.name} ({record.usage_count})"
    
    @api.depends('order_ids')
    def _compute_usage_count(self):
        """計算使用次數"""
        for record in self:
            record.usage_count = len(record.order_ids)
    
    # 約束條件
    _sql_constraints = [
        ('name_unique', 'unique(name)', '標籤名稱必須唯一！'),
    ]
    
    # 方法
    @api.model
    def get_popular_tags(self, limit=10):
        """
        取得熱門標籤
        
        Args:
            limit (int): 返回的標籤數量限制
            
        Returns:
            recordset: 按使用次數排序的標籤
        """
        return self.search([], order='usage_count desc', limit=limit)
    
    @api.model
    def get_recent_tags(self, limit=10):
        """
        取得最近建立的標籤
        
        Args:
            limit (int): 返回的標籤數量限制
            
        Returns:
            recordset: 按建立時間排序的標籤
        """
        return self.search([], order='create_date desc', limit=limit)
    
    @api.model
    def create_if_not_exists(self, tag_name):
        """
        如果標籤不存在則建立
        
        Args:
            tag_name (str): 標籤名稱
            
        Returns:
            record: 標籤記錄
        """
        existing_tag = self.search([('name', '=', tag_name)], limit=1)
        if existing_tag:
            return existing_tag
        
        return self.create({'name': tag_name})


class FieldServiceTagCategory(models.Model):
    """
    標籤分類 (可選)
    
    功能說明：
    - 將標籤進行分類管理
    - 支援階層式分類
    """
    _name = 'field.service.tag.category'
    _description = '標籤分類'
    _order = 'name'
    _parent_store = True
    
    name = fields.Char('分類名稱', required=True)
    
    parent_id = fields.Many2one(
        'field.service.tag.category',
        '上級分類',
        ondelete='cascade'
    )
    
    child_ids = fields.One2many(
        'field.service.tag.category',
        'parent_id',
        '子分類'
    )
    
    parent_path = fields.Char(index=True)
    
    tag_ids = fields.One2many(
        'field.service.tag',
        'category_id',
        '標籤'
    )
    
    active = fields.Boolean('啟用', default=True)
    color = fields.Integer('顏色索引', default=0)
    description = fields.Text('描述')
    
    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        """檢查父級遞迴"""
        if not self._check_recursion():
            raise ValidationError(_('您不能建立遞迴的分類結構！'))


# 為標籤模型添加分類欄位
class FieldServiceTagWithCategory(models.Model):
    _inherit = 'field.service.tag'
    
    category_id = fields.Many2one(
        'field.service.tag.category',
        '分類',
        help='標籤所屬的分類'
    )
    
    category_path = fields.Char(
        '分類路徑',
        related='category_id.parent_path',
        readonly=True
    )