from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MaintenanceChecklist(models.Model):
    _name = 'maintenance.checklist'
    _description = '保養檢查項目定義'
    _order = 'product_id, maintenance_type, sequence, name'

    # 適用範圍
    product_id = fields.Many2one('product.template', '適用產品', required=True)
    variant_id = fields.Many2one(
        'product.product', 
        '適用型號',
        domain="[('product_tmpl_id', '=', product_id)]"
    )
    
    # 保養類型
    maintenance_type = fields.Selection([
        ('routine', '例行保養'),
        ('quarterly', '季度保養'),
        ('semi_annual', '半年保養'),
        ('annual', '年度保養'),
        ('major', '大保養')
    ], string='保養類型', required=True)
    
    # 檢查項目詳情
    name = fields.Char('項目名稱', required=True)
    item_code = fields.Char('項目代碼')
    maintenance_points = fields.Text('保養要點')
    description = fields.Text('詳細說明')
    
    # 顯示和排序
    sequence = fields.Integer('順序', default=10)
    is_display = fields.Boolean('顯示在工單', default=True)
    is_required = fields.Boolean('必要項目', default=False)
    
    # 分類
    category = fields.Selection([
        ('visual', '外觀檢查'),
        ('functional', '功能測試'),
        ('cleaning', '清潔保養'),
        ('replacement', '零件更換'),
        ('calibration', '校正調整'),
        ('other', '其他')
    ], string='項目分類')
    
    # 預估時間（分鐘）
    estimated_time = fields.Integer('預估時間(分鐘)', default=5)
    
    # 啟用狀態
    active = fields.Boolean('啟用', default=True)
    
    # 備註
    notes = fields.Text('備註')
    
    # 顯示名稱
    display_name = fields.Char('顯示名稱', compute='_compute_display_name', store=True)

    @api.depends('name', 'product_id.name', 'maintenance_type')
    def _compute_display_name(self):
        """計算顯示名稱"""
        for record in self:
            type_dict = dict(record._fields['maintenance_type'].selection)
            type_name = type_dict.get(record.maintenance_type, '')
            parts = [record.name]
            if record.product_id:
                parts.append(f"[{record.product_id.name}]")
            if type_name:
                parts.append(f"({type_name})")
            record.display_name = ' '.join(parts)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """產品變更時清除產品型號"""
        if self.product_id:
            self.variant_id = False

    @api.constrains('item_code')
    def _check_item_code_unique(self):
        """確保項目代碼在同一產品和保養類型下唯一"""
        for record in self:
            if record.item_code:
                duplicate = self.search([
                    ('item_code', '=', record.item_code),
                    ('product_id', '=', record.product_id.id),
                    ('maintenance_type', '=', record.maintenance_type),
                    ('id', '!=', record.id)
                ])
                if duplicate:
                    raise ValidationError(
                        f'項目代碼 {record.item_code} 在產品 {record.product_id.name} '
                        f'的 {dict(record._fields["maintenance_type"].selection)[record.maintenance_type]} 中已存在！'
                    )

    # API 方法供工單系統使用
    @api.model
    def get_maintenance_checklist(self, serial_number, maintenance_type):
        """
        獲取特定設備和保養類型的檢查清單
        Args:
            serial_number (str): 設備序號
            maintenance_type (str): 保養類型
        Returns:
            dict: 檢查清單
        """
        # 查找設備
        equipment = self.env['service.equipment'].search([('name', '=', serial_number)], limit=1)
        if not equipment:
            return {'success': False, 'message': f'找不到序號 {serial_number} 的設備'}
        
        # 查找檢查項目
        domain = [
            ('maintenance_type', '=', maintenance_type),
            ('is_display', '=', True),
            ('active', '=', True)
        ]
        
        # 優先使用特定型號的項目，否則使用產品通用項目
        if equipment.variant_id:
            variant_items = self.search(domain + [('variant_id', '=', equipment.variant_id.id)])
            if variant_items:
                checklist_items = variant_items
            else:
                checklist_items = self.search(domain + [
                    ('product_id', '=', equipment.product_id.id),
                    ('variant_id', '=', False)
                ])
        else:
            checklist_items = self.search(domain + [
                ('product_id', '=', equipment.product_id.id),
                ('variant_id', '=', False)
            ])
        
        # 組織檢查清單資料
        checklist = []
        for item in checklist_items:
            category_dict = dict(item._fields['category'].selection) if item.category else {}
            checklist.append({
                'id': item.id,
                'name': item.name,
                'item_code': item.item_code,
                'maintenance_points': item.maintenance_points,
                'description': item.description,
                'category': item.category,
                'category_name': category_dict.get(item.category, ''),
                'is_required': item.is_required,
                'estimated_time': item.estimated_time,
                'sequence': item.sequence,
            })
        
        # 按順序排序
        checklist.sort(key=lambda x: x['sequence'])
        
        return {
            'success': True,
            'equipment_id': equipment.id,
            'equipment_name': equipment.name,
            'product_name': equipment.product_id.name,
            'variant_name': equipment.variant_id.name if equipment.variant_id else None,
            'maintenance_type': maintenance_type,
            'checklist': checklist,
            'total_items': len(checklist),
            'required_items': len([item for item in checklist if item['is_required']]),
            'estimated_total_time': sum(item['estimated_time'] for item in checklist)
        }

    @api.model
    def get_maintenance_types(self, product_id=None, serial_number=None):
        """
        獲取產品支援的保養類型
        Args:
            product_id (int): 產品ID
            serial_number (str): 設備序號（可選）
        Returns:
            dict: 支援的保養類型列表
        """
        if serial_number:
            equipment = self.env['service.equipment'].search([('name', '=', serial_number)], limit=1)
            if not equipment:
                return {'success': False, 'message': f'找不到序號 {serial_number} 的設備'}
            product_id = equipment.product_id.id
        
        if not product_id:
            return {'success': False, 'message': '必須提供產品ID或設備序號'}
        
        # 查找該產品的所有保養類型
        maintenance_types = self.search([
            ('product_id', '=', product_id),
            ('active', '=', True)
        ]).mapped('maintenance_type')
        
        # 去重並組織資料
        unique_types = list(set(maintenance_types))
        type_dict = dict(self._fields['maintenance_type'].selection)
        
        type_list = []
        for mtype in unique_types:
            type_list.append({
                'value': mtype,
                'name': type_dict.get(mtype, mtype)
            })
        
        return {
            'success': True,
            'product_id': product_id,
            'maintenance_types': type_list
        }

    @api.model
    def create_default_checklist(self, product_id, maintenance_type):
        """
        為產品建立預設的檢查清單
        Args:
            product_id (int): 產品ID
            maintenance_type (str): 保養類型
        """
        product = self.env['product.template'].browse(product_id)
        if not product.exists():
            return False
        
        default_items = {
            'routine': [
                {'name': '外觀檢查', 'category': 'visual', 'maintenance_points': '檢查設備外觀是否有損壞', 'sequence': 10},
                {'name': '清潔保養', 'category': 'cleaning', 'maintenance_points': '清潔設備表面', 'sequence': 20},
                {'name': '功能測試', 'category': 'functional', 'maintenance_points': '測試基本功能是否正常', 'sequence': 30},
            ],
            'quarterly': [
                {'name': '深度清潔', 'category': 'cleaning', 'maintenance_points': '深度清潔設備內部', 'sequence': 10},
                {'name': '功能全檢', 'category': 'functional', 'maintenance_points': '全面檢測所有功能', 'sequence': 20},
                {'name': '校正檢查', 'category': 'calibration', 'maintenance_points': '檢查校正狀態', 'sequence': 30},
            ],
            'semi_annual': [
                {'name': '零件檢查', 'category': 'visual', 'maintenance_points': '檢查關鍵零件磨損情況', 'sequence': 10},
                {'name': '潤滑保養', 'category': 'cleaning', 'maintenance_points': '更換潤滑油脂', 'sequence': 20},
                {'name': '精密校正', 'category': 'calibration', 'maintenance_points': '精密校正設備', 'sequence': 30},
            ],
            'annual': [
                {'name': '全面檢修', 'category': 'functional', 'maintenance_points': '全面檢修設備', 'sequence': 10},
                {'name': '零件更換', 'category': 'replacement', 'maintenance_points': '更換易損零件', 'sequence': 20},
                {'name': '性能測試', 'category': 'functional', 'maintenance_points': '全面性能測試', 'sequence': 30},
            ],
            'major': [
                {'name': '大修檢查', 'category': 'functional', 'maintenance_points': '大修前全面檢查', 'sequence': 10},
                {'name': '核心零件更換', 'category': 'replacement', 'maintenance_points': '更換核心零件', 'sequence': 20},
                {'name': '系統重新校正', 'category': 'calibration', 'maintenance_points': '系統全面重新校正', 'sequence': 30},
            ]
        }
        
        items_data = default_items.get(maintenance_type, [])
        for item_data in items_data:
            item_data.update({
                'product_id': product_id,
                'maintenance_type': maintenance_type,
                'estimated_time': 15,  # 預設15分鐘
            })
            self.create(item_data)
        
        return True