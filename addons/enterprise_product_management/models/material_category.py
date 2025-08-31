# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MaterialCategory(models.Model):
    """
    物料種類 - 簡化版本
    用於歸類和管理物料（產品）
    """
    _name = 'epm.material.category'
    _description = '物料種類'
    _order = 'sequence, name'

    # 基本資訊
    name = fields.Char('種類名稱', required=True,
                       help='物料種類的名稱，例如：電子零件、機械零件等')
    code = fields.Char('種類代碼',
                       help='種類的簡短代碼，用於快速識別')
    sequence = fields.Integer('順序', default=10,
                              help='排序用，數字越小越靠前')
    active = fields.Boolean('啟用', default=True)
    
    # 詳細資訊
    description = fields.Text('說明',
                              help='物料種類的詳細說明')
    color = fields.Integer('顏色', default=0,
                           help='在看板視圖中的顯示顏色')
    
    # 關聯欄位
    product_ids = fields.Many2many(
        'product.product', 
        'epm_material_category_product_rel',
        'category_id', 'product_id',
        string='物料清單',
        help='屬於此種類的所有物料'
    )
    
    # 統計欄位
    product_count = fields.Integer(
        '物料數量', 
        compute='_compute_product_count',
        store=True,
        help='該種類下的物料總數'
    )
    
    repair_problem_count = fields.Integer(
        '維修問題數量',
        compute='_compute_repair_problem_count',
        store=True,
        help='該種類下所有物料的維修問題總數'
    )

    @api.depends('product_ids')
    def _compute_product_count(self):
        """計算物料數量"""
        for category in self:
            category.product_count = len(category.product_ids)

    @api.depends('product_ids')
    def _compute_repair_problem_count(self):
        """計算維修問題數量"""
        for category in self:
            if category.product_ids:
                repair_count = self.env['epm.material.repair'].search_count([
                    ('material_id', 'in', category.product_ids.ids)
                ])
                category.repair_problem_count = repair_count
            else:
                category.repair_problem_count = 0

    # 約束
    _sql_constraints = [
        ('code_unique', 'unique(code)', '種類代碼必須唯一！'),
        ('name_unique', 'unique(name)', '種類名稱必須唯一！'),
    ]

    # 動作方法
    def action_view_products(self):
        """查看該種類的所有物料"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - 物料清單',
            'res_model': 'product.product',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.product_ids.ids)],
            'context': {
                'search_default_material_category_id': self.id
            },
            'target': 'current',
        }

    def action_view_repair_problems(self):
        """查看該種類的所有維修問題"""
        self.ensure_one()
        material_ids = self.product_ids.ids
        return {
            'type': 'ir.actions.act_window',
            'name': f'{self.name} - 維修問題',
            'res_model': 'epm.material.repair',
            'view_mode': 'list,form',
            'domain': [('material_id', 'in', material_ids)],
            'context': {
                'search_default_material_id': material_ids
            },
            'target': 'current',
        }

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """增強搜尋：支援按代碼和名稱搜尋"""
        if name:
            # 同時搜尋名稱和代碼
            categories = self.search(['|', ('name', operator, name), ('code', operator, name)] + (args or []), limit=limit)
            return categories.name_get()
        return super().name_search(name, args, operator, limit)

    def name_get(self):
        """自訂顯示名稱"""
        result = []
        for category in self:
            if category.code:
                name = f'[{category.code}] {category.name}'
            else:
                name = category.name
            result.append((category.id, name))
        return result