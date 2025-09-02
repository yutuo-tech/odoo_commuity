# -*- coding: utf-8 -*-

from . import models
from . import wizards
from . import controllers

def post_init_hook(env):
    """
    Post installation hook
    
    執行模組安裝後的初始化工作：
    - 建立預設的工作性質選項
    - 建立預設的問題分類
    - 設定預設的序列號
    """
    # 可以在這裡添加初始化邏輯
    pass