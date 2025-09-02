# -*- coding: utf-8 -*-
{
    'name': 'Field Service Order',
    'version': '18.0.1.0.0',
    'category': 'Services/Field Service',
    'sequence': 10,
    'summary': '現場服務工單管理系統（簡化版）',
    'description': """
現場服務工單管理系統（重構簡化版）
====================================

功能包含：
- 保養工單管理
- 維修單管理  
- 工作日誌管理
- 客戶處理單管理（從工單自動生成）
- 電子簽名整合
- PDF 報表匯出

重構特色：
- 選擇設備後自動帶入所有相關資訊（客戶、合約、產品）
- 直接整合 enterprise_product_management 模組，避免重複資料
- 保養項目透過 epm.maintenance.item 動態載入
- 維修問題透過 epm.material.repair 選擇
- 簡化數據結構，降低系統負擔
- 支援行動裝置簽名和完整工作流程
""",
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'web',
        'mail',
        'hr',
        'maintenance',
        'repair',
        'sign_oca',
        'service_contract_management',
        'medical_service_management', 
        'enterprise_product_management',
    ],
    'data': [
        # Security
        'security/field_service_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/ir_sequence_data.xml',
        'data/work_nature_data.xml',
        'data/mail_template_data.xml',
        
        # Views
        'views/field_service_order_views.xml',
        'views/field_service_auxiliary_views.xml',
        'views/customer_service_sheet_views.xml',
        'views/service_order_sign_wizard_views.xml',
        'views/field_service_menu.xml',
        
        # Wizards
        'wizards/signature_upload_wizard_views.xml',
        'wizards/signature_view_wizard_views.xml',
        'wizards/customer_service_sheet_wizard_views.xml',
        
        # Reports
        'reports/customer_service_report.xml',
        'reports/customer_service_sheet_report.xml',
        
        # Templates
        'templates/customer_service_sheet_print.xml',
    ],
    'demo': [
        # 'demo/field_service_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 在表單控制器樣式之後載入，確保能覆蓋核心的 margin-right: auto
            ('after', 'web/static/src/views/form/form_controller.scss', 
             'field_service_order/static/src/scss/field_service_responsive.scss'),
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
}