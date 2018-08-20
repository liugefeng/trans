# coding: UTF-8

# =========================================================================
# File Name  : trans.py
# Author     : 刘戈峰
# Create Date: 2018-08-19
# platform   : Linux/Windows
# Comment    : 该脚本主要用于android平台升级字符串移植
#            : 脚本首先搜索符合用户owner的添加的所有字符串，然后用这些字符串
#            : 去更新新平台的字符串(新平台没有的则添加，已有的则更新)
#            : 新xml文件更新方式：
#            : 1. 针对新xml文件中已有的元素行，删除已有行，使用旧xml文件中的内容
#            : 2. 针对新文件中没有的元素，则直接将旧xml文件中的内容加入到新xml
#            : 3. 更新内容将同意放在文件中的同一个注释标记对中
#            : 4. 针对新文件中已有修改内容，不能进行修改
#            :
# TODO       : 更新新xml文件功能尚未开发
#            :
# Note       : 目前搜集了用户修改属性在列表中的位置信息，目前尚未用到，以后可能
#            : 会使用到，暂时保留该部分代码
#            :
# History    : 2018-08-18 Liu Gefeng   数组多行问题解决
#            : 2018-08-18 Liu Gefeng   旧xml文件扫描功能开发完毕
# =========================================================================

import sys
import re
import os
import os.path
import platform

PLATFORM = platform.system()

# =========================================================================
# Class  : SourceXmlFile
# Comment: 扫描指定文件中指定owner修改信息(用来后续更新到新xml文件中)
# =========================================================================
class SourceXmlFile:
    def __init__(self, xmlFile, transOwner):
        # xml文件位置
        self.path = xmlFile.strip()
        self.trans_owner = transOwner.strip()

        # 存放个人相关字符串信息
        self.lst_trans = []
        self.map_trans = {}

        # 扫描状态定义
        # 1: 当前正在查找匹配起始行 如：<!-- BSP: add by xxx @{ -->
        # 2: 当前正在搜集用户修改属性行并查找匹配结束行 如：<!-- BSP: @} -->
        # 3: 当前正在搜集用户属性信息，遇到当前为数组的需要进行多行处理情况
        self.SCAN_STATE_NORMAL = 0
        self.SCAN_STATE_MINE   = 1
        self.SCAN_STATE_ARRAY  = 2

    # =========================================================================
    # Function: parse
    # Comment: 扫描xml文件，获取个人字符串移植信息
    # =========================================================================
    def generateEmptyXmlFile(self):
        file_id = open(self.path, 'r')
        if not file_id:
            print("failed to open source file " + self.path + " to generate empty xml file.")
            return ""

        # <resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">
        re_resource_start = re.compile(r'^\s*<resources\s+.*>\s*$')
        result = ""

        while True:
            line_text = file_id.readline()
            if not line_text:
                break

            result = result + line_text
            match = re_resource_start.search(line_text)
            if match:
                break

        file_id.close()
        return result

    # =========================================================================
    # Function: parse
    # Comment: 扫描xml文件，获取个人字符串移植信息
    # =========================================================================
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

        # 普通属性匹配
        # <string name="status_bar_accessibility_dismiss_recents">Dismiss recent apps</string>
        re_plain_property = re.compile(r'\s*\<\s*([\w\-]+)\s+name\s*="([^\"]+)".*</([\w\-]+)>\s*$')

        # 数组属性
        #<plurals name="status_bar_accessibility_recent_apps">
        #    <item quantity="one">1 screen in Overview</item>
        #    <item quantity="other">%d screens in Overview</item>
        #</plurals>
        re_match_array_begin = re.compile(r'^\s*<([\w\-]+)\s+name="([^"]+)\"[^/]?>\s*$')

        # </plurals>
        re_match_array_end = re.compile(r'^\s*</[^>]+\s*>\s*$')

        cur_array_name = ""
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
                    # 多个修改段落之间用空格隔开
                    if len(self.lst_trans) > 0:
                        self.lst_trans.append("\n")

                    scan_state = self.SCAN_STATE_MINE
                    continue

                continue

            # 当前状态为已经匹配到翻译字符串起始位置，记录当前翻译串
            # 匹配到<!-- BSP: @} --> 结束
            if scan_state == self.SCAN_STATE_MINE:
                match = re_match_end.search(line_text)
                if not match:
                    self.lst_trans.append(line_text) 

                    # 普通属性匹配
                    sub_match = re_plain_property.search(line_text)

                    if sub_match:
                        prop_type = sub_match.group(1).strip()
                        prop_name = sub_match.group(2).strip()

                        if not prop_name in self.map_trans:
                            self.map_trans[prop_name] = str(len(self.lst_trans) - 1)
                        else:
                            print("repeat property found about " + prop_name)

                        continue

                    # 数组属性匹配
                    sub_match = re_match_array_begin.search(line_text)
                    if sub_match:
                        prop_name = sub_match.group(2)

                        if not prop_name in self.map_trans:
                            cur_array_name = prop_name
                            scan_state = self.SCAN_STATE_ARRAY
                            self.map_trans[prop_name] = str(len(self.lst_trans) - 1)
                        else:
                            print("repeat property found about array " + prop_name)

                        continue

                    continue

                # 找到用户修改字符串结束行
                # <!-- BSP: @} -->
                scan_state = self.SCAN_STATE_NORMAL
                continue

            # 搜集数组元素，并查找数组结束行
            if scan_state == self.SCAN_STATE_ARRAY:
                self.lst_trans.append(line_text)

                match = re_match_array_end.search(line_text)
                if not match:
                    continue

                scan_state = self.SCAN_STATE_NORMAL
                self.map_trans[cur_array_name] = self.map_trans[cur_array_name] + "," + str(len(self.lst_trans) - 1)
                continue

        file_id.close() 
        if scan_state != self.SCAN_STATE_NORMAL:
            print("scan state error for scanning file " + self.path)
        return

class TargetXmlFile:
    def __init__(self, xmlFile, sourceXmlFile):
        self.path = xmlFile.strip()
        self.source_xml_file = sourceXmlFile

    # =========================================================================
    # Function : parse
    # Comment  : 根据source xml文件生成target xml文件
    # Condition: 新xml文件不存在
    # =========================================================================
    def generateTargetFile(self):
        # 创建文件
        file_id = open(self.path, 'w')
        if not file_id:
            print("failed to create file " + self.path + ".")
            return

        # 获取空xml文件模板内容
        result = self.source_xml_file.generateEmptyXmlFile()

        # 加入更新内容
        result = result + "    <!-- BSP: add by " + self.source_xml_file.trans_owner  +  "\n"
        for line_text in self.source_xml_file.lst_trans:
            result = result + line_text

        result = result + "    <!-- BSP: @} -->\n"

        # 加入resources结尾标志
        result = result + "</resources>\n"

        file_id.write(result)
        file_id.close()

    def scanTargetFile(self):
        # 文件不存在，(xxxxx 后续要进行专门处理)
        if not os.path.exists(self.path):
            return

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
    print("owner: " + owner)

    source_path = sys.argv[2].strip()
    if not os.path.exists(source_path):
        print("old source path not found!")
        exit()
    print("source path: " + source_path)

    target_path = sys.argv[3].strip()
    if not os.path.exists(target_path):
        print("new source path not found!")
        exit()
    print("target path: " + target_path)

    source_file = SourceXmlFile(source_path, owner)
    source_file.parse()

    target_file = TargetXmlFile(target_path, source_file)
    target_file.generateTargetFile()

