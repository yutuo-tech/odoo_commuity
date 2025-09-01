# 服務合約管理模組

## 模組概述
服務合約管理模組提供完整的設備生命週期管理、服務合約管理和保養檢查項目定義功能。

## 主要功能

### 1. 設備/貨物管理
- 完整生命週期追蹤（生產→庫存→出貨→運行→維護→報廢）
- 唯一序號管理
- 客戶資訊關聯
- 保固期限追蹤
- 維護歷史記錄

### 2. 服務合約管理
- 多種合約類型（保固、維護、全責保固、備機、租賃）
- 合約與設備的多對多關聯
- 合約期限管理和到期提醒
- 合約狀態流程管理

### 3. 保養檢查項目
- 按產品型號定義檢查項目
- 支援多種保養類型
- 結構化檢查清單
- 為工單系統提供 API 支援

## 安裝說明

1. 確保已安裝依賴模組：
   - medical_service_management
   - enterprise_product_management

2. 將模組目錄放置在 Odoo addons 路徑下

3. 重新啟動 Odoo 服務器

4. 在應用程式選單中搜尋「服務合約管理」並安裝

## 使用者群組

- **服務使用者**: 基本查看權限
- **設備管理員**: 設備管理權限
- **合約管理員**: 合約管理權限
- **系統管理員**: 完整管理權限

## API 介面

模組提供以下 API 供工單系統使用：

### 設備查詢
```python
# 根據序號查詢設備資訊
equipment_info = self.env['service.equipment'].get_equipment_by_serial('EQ123456')

# 更新設備狀態
equipment.update_equipment_status('maintenance', '進入保養狀態')
```

### 合約查詢
```python
# 查詢設備合約
contracts = self.env['service.contract'].get_equipment_contracts('EQ123456')
```

### 保養清單
```python
# 獲取保養檢查清單
checklist = self.env['maintenance.checklist'].get_maintenance_checklist('EQ123456', 'routine')

# 獲取支援的保養類型
types = self.env['maintenance.checklist'].get_maintenance_types(product_id=1)
```

## 開發者指南

### 模型關係
- service.equipment ←→ service.contract (多對多)
- maintenance.checklist → product.template/product.product
- service.equipment → res.partner (客戶)

### 狀態管理
設備狀態流轉：
```
生產中 → 庫存中 → 已預留 → 已出貨 → 已安裝 → 運行中
                                              ↓
已報廢 ← 已退回 ← 維修中 ← 保養中 ← 運行中
```

合約狀態流轉：
```
草稿 → 已確認 → 執行中 → 已到期/已續約/已取消 → 已結案
```

## 版本歷史

- v18.0.1.0.0: 初始版本，包含基本功能

## 技術支援

如有問題或建議，請聯繫開發團隊。