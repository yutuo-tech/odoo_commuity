{
    'name': '企業產品管理',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': '企業產品管理系統 - 繼承版',
    'description': """
企業產品管理模組（基礎版）
==========================

基於 Odoo 核心模組實作，提供產品、維修問題和保養項目管理：

* 產品管理：繼承 product.template
* 物料管理：繼承 product.product，使用 BOM 管理物料關係
* 維修問題庫：以物料為主項，維修問題為次項的結構
* 保養項目管理：為每個產品定義保養清單，支援多種保養類型

架構特色：
* 利用 Odoo 內建 BOM（物料清單）管理產品與物料關係
* 簡化設計，移除重複的物料種類概念
* 維修流程：產品 → BOM → 物料 → 維修問題
* 保養流程：產品 → 保養類型 → 保養項目清單 (checklist)
* 支援內外部工單差異化顯示
* 充分利用 Odoo 核心功能，維護成本低
* 專為工單系統提供基礎數據支援
    """,
    'author': 'Enterprise Solutions Team',
    'website': '',
    'depends': [
        'product',
        'stock',
        'mrp',
        'mail',
        'medical_service_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        'views/material_category_views.xml',
        'views/material_repair_views.xml',
        'views/maintenance_item_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # 在表單控制器樣式之後載入，確保能覆蓋核心的 margin-right: auto
            ('after', 'web/static/src/views/form/form_controller.scss', 
             'enterprise_product_management/static/src/scss/product_responsive.scss'),
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}