# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class FieldServiceChecklistLine(models.Model):
    """
    服務工單檢查清單行
    
    功能說明：
    - 關聯企業產品模組的保養項目 (epm.maintenance.item)
    - 支援勾選完成狀態
    - 控制是否顯示在客戶報表上
    
    使用場景：
    - 保養工單的 Check List
    - 根據設備類型和保養類型動態載入
    """
    _name = 'field.service.checklist.line'
    _description = '服務工單檢查清單行'
    _order = 'sequence, id'
    
    # 關聯欄位
    order_id = fields.Many2one(
        'field.service.order',
        '服務工單',
        required=True,
        ondelete='cascade',
        help='所屬的服務工單'
    )
    
    maintenance_item_id = fields.Many2one(
        'epm.maintenance.item',
        '保養項目',
        required=False,
        help='關聯到企業產品模組的保養項目'
    )
    
    # 基本資訊欄位 (從保養項目關聯取得，但允許直接設置)
    name = fields.Char(
        '項目名稱',
        help='保養項目的名稱'
    )
    
    key_points = fields.Text(
        '保養要點',
        related='maintenance_item_id.key_points',
        readonly=True,
        help='保養的關鍵要點和注意事項'
    )
    
    description = fields.Text(
        '詳細描述',
        related='maintenance_item_id.description',
        readonly=True,
        help='保養項目的詳細說明、步驟和要求'
    )
    
    sequence = fields.Integer(
        '排序',
        related='maintenance_item_id.sequence',
        store=True,
        readonly=True,
        help='保養項目的執行順序'
    )
    
    maintenance_type = fields.Selection(
        related='maintenance_item_id.maintenance_type',
        readonly=True,
        help='保養類型'
    )
    
    # 執行狀態欄位
    is_checked = fields.Boolean(
        '已完成',
        default=False,
        help='勾選表示此項目已完成'
    )
    
    checked_date = fields.Datetime(
        '完成時間',
        help='項目完成的時間'
    )
    
    checked_by = fields.Many2one(
        'hr.employee',
        '完成人員',
        help='執行此項目的人員'
    )
    
    # 報表控制欄位
    show_on_report = fields.Boolean(
        '顯示在報表上',
        related='maintenance_item_id.is_public',
        readonly=True,
        help='控制此項目是否在客戶服務處理單中顯示'
    )
    
    # 備註欄位
    notes = fields.Text(
        '備註',
        help='針對此項目的特殊備註'
    )
    
    # 計算欄位
    display_name = fields.Char(
        '顯示名稱',
        compute='_compute_display_name',
        store=True
    )
    
    @api.depends('name', 'is_checked')
    def _compute_display_name(self):
        """計算顯示名稱，包含完成狀態"""
        for record in self:
            status = "✓" if record.is_checked else "○"
            record.display_name = f"{status} {record.name or ''}"
    
    # onchange 方法
    @api.onchange('maintenance_item_id')
    def _onchange_maintenance_item_id(self):
        """當選擇保養項目時，自動帶入名稱"""
        if self.maintenance_item_id:
            self.name = self.maintenance_item_id.name
    
    @api.onchange('is_checked')
    def _onchange_is_checked(self):
        """勾選狀態改變時更新完成時間和人員"""
        if self.is_checked:
            self.checked_date = fields.Datetime.now()
            # 從工單取得技術人員
            if self.order_id.technician_id:
                self.checked_by = self.order_id.technician_id
        else:
            self.checked_date = False
            self.checked_by = False
    
    # 方法
    def toggle_check(self):
        """切換勾選狀態"""
        self.is_checked = not self.is_checked
    
    def mark_as_done(self):
        """標記為完成"""
        self.write({
            'is_checked': True,
            'checked_date': fields.Datetime.now(),
            'checked_by': self.order_id.technician_id.id if self.order_id.technician_id else False
        })
    
    def mark_as_undone(self):
        """標記為未完成"""
        self.write({
            'is_checked': False,
            'checked_date': False,
            'checked_by': False
        })


# 刪除了 FieldServiceChecklistTemplate 類別，
# 因為直接使用 epm.maintenance.item 的 API 更加簡潔且不產生重複資料