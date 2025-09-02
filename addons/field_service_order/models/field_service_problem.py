# -*- coding: utf-8 -*-

# 此檔案中的模型已被移除，因為：
# 
# 1. FieldServiceProblemCategory 被移除：
#    - 原因：與 epm.material.repair 功能重複
#    - 替代方案：直接使用 epm.material.repair 的 material_id (物料) 作為主項，
#              name (問題名稱) 作為次項
#
# 2. FieldServiceProblemSolution 被移除：
#    - 原因：功能過於複雜，增加系統負擔
#    - 替代方案：技術人員直接在工單的 solution_description 欄位記錄處理方法
#
# 重構目標：
# - 減少模型數量，降低系統複雜度
# - 直接利用既有的企業產品管理模組，避免重複建立資料結構
# - 保持功能完整性的同時提高維護效率
#
# 相關變更：
# - 主工單模型使用 repair_problem_line_ids (One2many to field.service.repair.problem.line) 
#   作為維修問題行，支持多個物料的多個問題記錄
# - 保持 problem_description 和 solution_description 文字欄位供手動輸入

from odoo import models

# 保留空白檔案結構，避免模組載入錯誤