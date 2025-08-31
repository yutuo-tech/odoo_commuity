{
    'name': '企業產品管理',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': '企業產品管理系統 - 繼承版',
    'description': """
企業產品管理模組（基礎版）
==========================

基於 Odoo 核心模組實作，提供產品和維修問題管理：

* 產品管理：繼承 product.template
* 物料管理：繼承 product.product，使用 BOM 管理物料關係
* 維修問題庫：以物料為主項，維修問題為次項的結構

架構特色：
* 利用 Odoo 內建 BOM（物料清單）管理產品與物料關係
* 簡化設計，移除重複的物料種類概念
* 維修流程：產品 → BOM → 物料 → 維修問題
* 充分利用 Odoo 核心功能，維護成本低
* 專為工單系統提供基礎數據支援
    """,
    'author': 'Enterprise Solutions Team',
    'website': '',
    'depends': [
        'product',
        'stock',
        'mrp',
        'medical_service_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/product_product_views.xml',
        'views/material_category_views.xml',
        'views/material_repair_views.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}