# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    """
    繼承產品模板，添加工單系統所需的產品類型和保養項目管理
    
    已有欄位：
    - name: 產品名稱
    - description: 描述
    - list_price: 標準售價
    - standard_price: 成本
    """
    _inherit = 'product.template'
    
    # SQL 必需欄位
    x_product_type = fields.Char('產品類型')  # 對應 SQL: product_type
    
    # 保養項目關聯
    maintenance_item_ids = fields.One2many(
        'epm.maintenance.item', 'product_tmpl_id', 
        string='保養項目',
        help='此產品的所有保養項目清單'
    )
    maintenance_item_count = fields.Integer(
        '保養項目數量', compute='_compute_maintenance_item_count',
        help='此產品的保養項目總數'
    )
    
    @api.depends('maintenance_item_ids')
    def _compute_maintenance_item_count(self):
        """
        計算保養項目數量
        """
        for record in self:
            record.maintenance_item_count = len(record.maintenance_item_ids)
    
    def action_view_maintenance_items(self):
        """
        開啟保養項目視圖
        
        Returns:
            dict: 視窗動作設定
        """
        action = self.env.ref('enterprise_product_management.action_maintenance_item').read()[0]
        
        if self.maintenance_item_count == 1:
            action['views'] = [(self.env.ref('enterprise_product_management.view_maintenance_item_form').id, 'form')]
            action['res_id'] = self.maintenance_item_ids.id
        else:
            action['domain'] = [('product_tmpl_id', '=', self.id)]
            action['context'] = {
                'default_product_tmpl_id': self.id,
                'search_default_filter_active': 1
            }
        
        return action