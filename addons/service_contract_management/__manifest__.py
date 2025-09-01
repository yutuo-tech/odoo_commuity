{
    'name': '服務合約管理',
    'version': '18.0.1.0.0',
    'summary': '設備管理、服務合約管理、保養檢查項目定義',
    'description': '''
        服務合約管理模組
        ================
        
        核心功能：
        * 設備/貨物全生命週期管理
        * 服務合約管理（保固、維護、租賃等）
        * 保養檢查項目定義
        * 為工單系統提供基礎資料支援
        
        主要特色：
        * 完整的設備狀態追蹤
        * 靈活的合約類型支援
        * 標準化的保養檢查清單
        * 與現有客戶和產品模組整合
    ''',
    'author': 'Development Team',
    'website': '',
    'category': 'Services',
    'license': 'LGPL-3',
    
    'depends': [
        'base',
        'mail',
        'product',
        'stock',
        'account',
        'hr',
        'medical_service_management',
        'enterprise_product_management'
    ],
    
    'data': [
        # 安全性
        'security/security.xml',
        'security/ir.model.access.csv',
        
        # 資料
        'data/sequence_data.xml',
        
        # 視圖
        'views/service_equipment_views.xml',
        'views/service_contract_views.xml',
        'views/maintenance_checklist_views.xml',
        'views/menu.xml',
    ],
    
    'demo': [
        'data/demo/service_equipment_demo.xml',
        'data/demo/service_contract_demo.xml',
    ],
    
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 100,
}