# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FieldServicePartReplacement(models.Model):
    """
    服務工單零件更換記錄 - 簡化版
    
    功能說明：
    - 記錄維修工單中的零件更換情況
    - 使用物料種類進行二階段選擇
    - 只保留必要的記錄資訊
    """
    _name = 'field.service.part.replacement'
    _description = '零件更換記錄'
    _order = 'sequence, id'
    
    # 關聯欄位
    order_id = fields.Many2one(
        'field.service.order',
        '服務工單',
        required=True,
        ondelete='cascade',
        help='所屬的維修工單'
    )
    
    sequence = fields.Integer('排序', default=10)
    
    # 物料種類選擇
    material_category_id = fields.Many2one(
        'epm.material.category',
        '物料種類',
        help='先選擇物料種類，然後選擇該種類下的具體物料'
    )
    
    # 零件資訊
    product_id = fields.Many2one(
        'product.product',
        '零件產品',
        required=True,
        domain="[('x_material_category_ids', 'in', [material_category_id])]",
        help='選擇要更換的零件產品（根據物料種類過濾）'
    )
    
    # 數量和單位
    quantity = fields.Float(
        '更換數量',
        required=True,
        default=1.0,
        digits='Product Unit of Measure',
        help='更換的零件數量'
    )
    
    # 備註
    notes = fields.Text(
        '備註',
        help='零件更換的特殊備註或說明'
    )
    
    # 簡單的顯示名稱
    display_name = fields.Char(
        '顯示名稱',
        compute='_compute_display_name',
        store=True
    )
    
    @api.onchange('order_id')
    def _onchange_order_id_bom(self):
        """
        工單變更時更新零件選擇範圍
        
        根據工單設備的產品查詢相關的 BOM，限制可選的零件範圍。
        """
        if self.order_id and self.order_id.equipment_id and self.order_id.equipment_id.product_id:
            equipment_product = self.order_id.equipment_id.product_id
            
            # 查詢設備產品的 BOM
            bom = self.env['mrp.bom'].search([
                ('product_tmpl_id', '=', equipment_product.id)
            ], limit=1)
            
            if bom:
                # 取得 BOM 中的所有零件 ID
                bom_lines = self.env['mrp.bom.line'].search([('bom_id', '=', bom.id)])
                product_ids = bom_lines.mapped('product_id').ids
                
                return {
                    'domain': {
                        'product_id': [('id', 'in', product_ids)]
                    }
                }
        
        # 預設顯示所有產品類型的產品
        return {
            'domain': {
                'product_id': [('type', '=', 'product')]
            }
        }
    
    @api.depends('product_id', 'quantity')
    def _compute_display_name(self):
        """計算顯示名稱"""
        for record in self:
            if record.product_id:
                record.display_name = f"{record.product_id.name} x{record.quantity}"
            else:
                record.display_name = f"零件更換 x{record.quantity}"
    
    # onchange 方法
    @api.onchange('material_category_id')
    def _onchange_material_category(self):
        """物料種類變更時清空產品選擇"""
        if self.material_category_id:
            self.product_id = False
            # 過濾該種類下的產品
            return {
                'domain': {
                    'product_id': [('x_material_category_ids', 'in', [self.material_category_id.id])]
                }
            }
        else:
            return {
                'domain': {
                    'product_id': [('type', '=', 'product')]
                }
            }
    
    # 約束條件
    @api.constrains('quantity')
    def _check_quantity_positive(self):
        """檢查數量必須為正數"""
        for record in self:
            if record.quantity <= 0:
                raise ValidationError(_('更換數量必須大於 0！'))