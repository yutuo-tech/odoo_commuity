# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductProduct(models.Model):
    """
    繼承產品變體作為物料管理
    
    已有欄位：
    - name: 產品名稱
    - default_code: 內部參考（可作為物料編號）
    - qty_available: 在手數量
    """
    _inherit = 'product.product'
    
    # 物料管理欄位
    x_material_category_ids = fields.Many2many(
        'epm.material.category', 
        'epm_material_category_product_rel',
        'product_id', 'category_id',
        string='物料種類',
        help='選擇物料種類進行分類管理'
    )
    x_stock_quantity = fields.Integer('庫存數量', default=0,
                                      help='額外的庫存管理欄位')
    
    # 保養項目相關欄位（關聯到產品模板）
    maintenance_item_count = fields.Integer(
        '保養項目數量', 
        related='product_tmpl_id.maintenance_item_count',
        readonly=True,
        help='此產品的保養項目總數（來自產品模板）'
    )
    
    def action_view_maintenance_items(self):
        """
        開啟保養項目視圖
        
        此方法調用產品模板的保養項目管理功能，
        因為保養項目定義在產品模板層級。
        
        Returns:
            dict: 視窗動作設定
        """
        self.ensure_one()
        return self.product_tmpl_id.action_view_maintenance_items()