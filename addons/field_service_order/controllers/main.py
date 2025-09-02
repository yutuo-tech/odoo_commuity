# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class CustomerServiceSheetController(http.Controller):
    """
    客戶處理單控制器
    
    提供 HTTP 路由來直接顯示 HTML 報表，避免 Odoo 報表系統的編碼問題
    """
    
    @http.route('/report/customer_service_sheet/<int:sheet_id>', auth='user', type='http')
    def customer_service_sheet_report(self, sheet_id, **kwargs):
        """
        顯示客戶處理單的 HTML 報表
        
        Args:
            sheet_id (int): 客戶處理單 ID
            
        Returns:
            HTTP Response: 包含 HTML 內容的響應
        """
        # 檢查權限
        try:
            sheet = request.env['customer.service.sheet'].browse(sheet_id)
            if not sheet.exists():
                return request.not_found()
            
            # 檢查用戶是否有讀取權限
            sheet.check_access_rights('read')
            sheet.check_access_rule('read')
            
        except Exception:
            return request.not_found()
        
        # 渲染模板
        html = request.env['ir.qweb']._render('field_service_order.customer_service_sheet_print', {
            'doc': sheet,
            'datetime': __import__('datetime'),
        })
        
        # 返回響應，明確設定 UTF-8 編碼
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-cache, no-store, must-revalidate'),
            ('Pragma', 'no-cache'),
            ('Expires', '0'),
        ])