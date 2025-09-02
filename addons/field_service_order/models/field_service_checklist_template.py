# -*- coding: utf-8 -*-

# 此檔案中的模型已被移除，因為：
# 
# 1. FieldServiceChecklistTemplate 被移除：
#    - 原因：與 epm.maintenance.item 功能重複
#    - 替代方案：直接使用 epm.maintenance.item.get_public_maintenance_items()
#              API 根據產品和保養類型動態載入保養項目
#
# 2. FieldServiceChecklistTemplateItem 被移除：
#    - 原因：不再需要模板項目，直接使用 epm.maintenance.item
#    - 替代方案：工單的 checklist_line_ids 直接關聯 epm.maintenance.item
#
# 重構優勢：
# - 避免資料重複：不再需要維護兩套相似的保養項目系統
# - 簡化維護：所有保養項目統一在 enterprise_product_management 模組管理
# - 提高一致性：確保保養項目的定義在整個系統中保持一致
# - 減少錯誤：降低因資料不同步而產生的問題
#
# 使用方式：
# - 設備選擇後，系統會自動根據設備的產品類型載入對應的保養項目
# - 保養類型選擇後，會篩選出該類型的保養項目
# - 工單的 checklist_line_ids 直接關聯到 epm.maintenance.item

from odoo import models

# 保留空白檔案結構，避免模組載入錯誤