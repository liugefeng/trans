# coding: UTF-8

# =========================================================================
# File Name  : trans.py
# Author     : 刘戈峰
# Create Date: 2018-08-19
# platform   : Linux/Windows
# Comment    : 该脚本主要用于android平台升级字符串移植
#            : 脚本首先搜索符合用户owner的添加的所有字符串，然后这些字符串
#            : 去更新新平台的字符串(新平台没有的则添加，已有的则更新)
#            :
# History    : 2018-08-12 Liu Gefeng   功能基本完成
#            : 2018-08-12 Liu Gefeng   解决下载完毕未退出ftp问题
#            : 2018-08-12 Liu Gefeng   解决下载最后一次上传文件问题
#            : 2018-08-15 Liu Gefeng   去除download函数
#            : 2018-08-17 Liu Gefeng   修改只能下载当天最新文件问题
#            : 2018-08-17 Liu Gefeng   日期兼容python 2.7
# =========================================================================

import sys
import re
import os
import os.path
import time
import platform
from datetime import date

PLATFORM = platform.system()

class XmlFile:
    def __init__(self, xmlFile, transOwner):
        # xml文件位置
        self.path = xmlFile.strip()
        self.trans_owner = transOwner.strip()

        # 存放个人相关字符串信息
        self.lst_trans = []
        self.map_trans = {}

        # 扫描状态定义
        self.SCAN_STATE_NORMAL = 0
        self.SCAN_STATE_MINE   = 1

    # 扫描xml文件，获取个人字符串移植信息
    def parse(self):
        file_id = open(self.path, 'r')
        scan_state = self.SCAN_STATE_NORMAL

        # <!-- BSP: add by xxx @{ -->
        # <!-- Product: add by xxx @{ -->
        # <!-- Vision: add by xxx @{ -->
        match_start_pattern = r'\s*<!\-\-\s*(bsp|product|vision)\s*:\s*.*by\s+(\w+)\s+.*@\{\s*\-\->\s*$'
        re_match_start = re.compile(match_start_pattern, flags=re.IGNORECASE)

        # <!-- BSP: @} --> or <!-- @} --> 
        re_match_end = re.compile(r'^\s*<!\-\-.*@\}\s*\-\->\s*$')

        while True:
            line_text = file_id.readline()

            # 文件读取完毕
            if not line_text:
                break

            # 当前状态为查找个人翻译字符串起始位置
            # 如：<!-- BSP: add by liugefeng @{ -->
            if scan_state == self.SCAN_STATE_NORMAL:
                match = re_match_start.search(line_text)
                if not match:
                    continue

                owner = match.group(2)
                if owner == self.trans_owner:
                    print("owner: " + owner)
                    scan_state = self.SCAN_STATE_MINE
                    continue

                continue

            # 当前状态为已经匹配到翻译字符串起始位置，记录当前翻译串
            # 匹配到<!-- BSP: @} --> 结束
            if scan_state == self.SCAN_STATE_MINE:
                match = re_match_end.search(line_text)
                if not match:
                    self.lst_trans.append(line_text) 
                    continue

                scan_state = self.SCAN_STATE_NORMAL
                continue

        file_id.close() 

# =============================================================================
# usage : 
# usage1: python trans.py owner source_path target_path
# =============================================================================
if __name__ == "__main__":
    usage = '''
python trans.py owner source_path target_path
    '''

    param_num = len(sys.argv[1:])
    if param_num != 3:
        print("Error: parameter error." + usage)
        exit()

    # parameter check
    owner = sys.argv[1].strip()

    source_path = sys.argv[2].strip()
    if not os.path.exists(source_path):
        print("old source path not found!")
        exit()

    target_path = sys.argv[3].strip()
    if not os.path.exists(target_path):
        print("new source path not found!")
        exit()

    source_file = XmlFile(source_path, owner)
    source_file.parse()

    str = ""
    for item in source_file.lst_trans:
        str += item 

    print(str)

