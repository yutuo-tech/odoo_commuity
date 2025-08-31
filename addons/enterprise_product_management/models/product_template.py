# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    """
    繼承產品模板，添加工單系統所需的產品類型
    
    已有欄位：
    - name: 產品名稱
    - description: 描述
    - list_price: 標準售價
    - standard_price: 成本
    """
    _inherit = 'product.template'
    
    # SQL 必需欄位
    x_product_type = fields.Char('產品類型')  # 對應 SQL: product_type