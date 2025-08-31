# -*- coding: utf-8 -*-
from odoo import models, fields, api


class EPMMaterialRepair(models.Model):
    """
    維修問題庫 - 使用 BOM 管理物料關係
    主項: 物料（product.product）
    次項: 維修問題名稱（允許多個）
    """
    _name = 'epm.material.repair'
    _description = '維修問題庫'
    _order = 'material_id, name'
    
    # 核心欄位
    material_id = fields.Many2one('product.product', '物料（零件）', required=True,
                                  help='選擇物料，物料本身就是產品，可透過 BOM 與主產品關聯')
    name = fields.Char('問題名稱', required=True,
                       help='維修問題描述，如：馬達異音、軸承磨損等')
    
    # 詳細資訊欄位
    repair_type = fields.Char('維修類型',
                              help='維修類型分類，如：預防性維修、緊急維修等')
    price = fields.Float('價格', digits='Product Price',
                         help='該維修問題的預估維修費用')
    currency = fields.Selection([
        ('TWD', '台幣'),
        ('USD', '美元'),
        ('EUR', '歐元')
    ], '幣別', default='TWD')
    description = fields.Text('描述',
                              help='詳細的維修問題描述和解決方案')
    is_public = fields.Boolean('是否顯示給外部工單', default=True,
                               help='控制此維修問題是否在外部工單中顯示')
    
    # 關聯資訊（計算欄位）
    product_tmpl_id = fields.Many2one('product.template', '產品範本',
                                      related='material_id.product_tmpl_id',
                                      store=True, readonly=True)
    
    _sql_constraints = [
        ('material_repair_uniq', 'unique(material_id, name)', 
         '相同物料的問題名稱必須唯一！'),
    ]
    
    @api.model
    def get_repairs_by_product(self, product_id):
        """
        根據產品取得相關的維修問題
        透過 BOM 找到產品的所有物料，再找到這些物料的維修問題
        
        Args:
            product_id (int): 產品 ID
            
        Returns:
            list: 維修問題記錄列表
        """
        # 找到產品的 BOM
        product = self.env['product.template'].browse(product_id)
        boms = self.env['mrp.bom'].search([('product_tmpl_id', '=', product_id)])
        
        if not boms:
            return []
            
        # 從 BOM 中取得所有物料
        material_ids = []
        for bom in boms:
            material_ids.extend(bom.bom_line_ids.product_id.ids)
        
        if not material_ids:
            return []
            
        # 找到這些物料的維修問題
        repairs = self.search([('material_id', 'in', material_ids)])
        return repairs