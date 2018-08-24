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
#            : 2018-08-23 Liu Gefeng   代码重构，将正则匹配和行类型内容转为全局变量
# =========================================================================

import sys
import re
import os
import os.path
import platform

PLATFORM = platform.system()

# =========================================================================
# Comment: 常量定义
# =========================================================================
# 元素类型0: 非元素行, 1: 普通元素行, 2: 数组元素行
PROP_TYPE_NONE = 0
PROP_TYPE_PLAIN = 1
PROP_TYPE_ARRAY_START = 2
PROP_TYPE_ARRAY_END = 3
PROP_TYPE_ARRAY_ITEM = 4
PROP_TYPE_CUSTOM_START = 5
PROP_TYPE_CUSTOM_END = 6
PROP_TYPE_CUSTOM_RESOURCE_START = 7
PROP_TYPE_CUSTOM_RESOURCE_END = 8

# 普通属性匹配
# <string name="status_bar_accessibility_dismiss_recents">Dismiss recent apps</string>
re_plain_property = re.compile(r'\s*\<\s*([\w\-]+)\s+name\s*="([^\"]+)".*</([\w\-]+)>\s*$')

# 数组属性
#<plurals name="status_bar_accessibility_recent_apps">
#    <item quantity="one">1 screen in Overview</item>
#    <item quantity="other">%d screens in Overview</item>
#</plurals>
re_array_begin = re.compile(r'^\s*<([\w\-]+)\s+name="([^"]+)\"[^/]?>\s*$')

# </plurals>
re_array_end = re.compile(r'^\s*</([^>]+)>\s*$')

# <resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">
re_resource_start = re.compile(r'^\s*<resources\s+.*>\s*$')

# </resources>
re_resource_end = re.compile(r'^\s*</resources>\s*$')

# <!-- BSP: add by xxx @{ -->
# <!-- Product: add by xxx @{ -->
# <!-- Vision: add by xxx @{ -->
match_start_pattern = r'^\s*<!\-\-\s*(bsp|product|vision)\s*:\s*.*by\s+(\w+)\s+.*@\{\s*\-\->\s*$'
re_match_start = re.compile(match_start_pattern, flags=re.IGNORECASE)

# <!-- BSP: @} --> or <!-- @} --> 
re_match_end = re.compile(r'^\s*<!\-\-.*@\}\s*\-\->\s*$')

# 获取source xml属性更改内容扫描状态定义
# 1: 当前正在查找匹配起始行 如：<!-- BSP: add by xxx @{ -->
# 2: 当前正在搜集用户修改属性行并查找匹配结束行 如：<!-- BSP: @} -->
# 3: 当前正在搜集用户属性信息，遇到当前为数组的需要进行多行处理情况
SOURCE_SCAN_STATE_NORMAL = 0
SOURCE_SCAN_STATE_MINE   = 1
SOURCE_SCAN_STATE_ARRAY  = 2

# target xml扫描状态
# 0: 起始状态 1: 匹配属性状态 2: 匹配非修改属性状态
TARGET_SCAN_STATE_NORMAL = 0
TARGET_SCAN_STATE_PROPERTY = 1
TARGET_SCAN_STATE_ARRAY_NONE_UPDATE = 2
TARGET_SCAN_STATE_UPDATE = 3
TARGET_SCAN_STATE_END = 4

# =========================================================================
# Function : parseCurLine
# Comment  : 解析当前文本行内容，并返回当前行类型和属性名称(有的话)
# Return   : 属性类型、属性名称
# =========================================================================
def parseCurLine(line_text):
    # 参数合法性检查
    if not line_text:
        return PROP_TYPE_NONE, ""

    # 是否为普通属性
    match = re_plain_property.search(line_text)
    if match:
        prop_name = match.group(2).strip()
        return PROP_TYPE_PLAIN, prop_name

    # 是否为数组类型 
    match = re_array_begin.search(line_text)
    if match:
        prop_name = match.group(2).strip()
        return PROP_TYPE_ARRAY_START, prop_name

    # 书否为数组结束行
    match = re_array_end.search(line_text)
    if match:
        prop_name = match.group(1).strip()
        if prop_name != "resources":
            return PROP_TYPE_ARRAY_END, prop_name

    # 修改注释起始行
    # <!--BSP: add by xxx @{ -->
    match = re_match_start.search(line_text)
    if match:
        return PROP_TYPE_CUSTOM_START, ""

    # 修改注释结束行
    # 如 <!-- BSP: @} -->
    match = re_match_end.search(line_text)
    if match:
        return PROP_TYPE_CUSTOM_END, ""

    # <resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">
    match = re_resource_start.search(line_text)
    if match:
        return PROP_TYPE_CUSTOM_RESOURCE_START, "" 

    # </resources>
    match = re_resource_end.search(line_text)
    if match:
        return PROP_TYPE_CUSTOM_RESOURCE_END, "" 

    # 其他类型(非元素相关行, 不包括数组内容部元素行)
    return PROP_TYPE_NONE, ""

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

    # =========================================================================
    # Function: generateEmptyXmlFile
    # Comment : 如果target xml不存在，则根据source xml生成空文件, 然后将修改信息
    #         : 写入文件中
    # =========================================================================
    def generateEmptyXmlFile(self):
        file_id = open(self.path, 'r')
        if not file_id:
            print("failed to open source file " + self.path + " to generate empty xml file.")
            return ""

        result = ""

        # 一次性读取文件内容到列表中
        lst_lines = file_id.readlines()
        file_id.close()

        # 获取修改信息
        for line_text in lst_lines:
            result = result + line_text
            match = re_resource_start.search(line_text)
            if match:
                break

        del lst_lines[:]
        return result

    # =========================================================================
    # Function: parse
    # Comment: 扫描xml文件，获取个人字符串移植信息
    # =========================================================================
    def parse(self):
        file_id = open(self.path, 'r')
        if not file_id:
            print("failed to open file " + self.path + " to read.")
            return

        lst_lines = file_id.readlines()
        file_id.close()

        scan_state = SOURCE_SCAN_STATE_NORMAL
        last_scan_state = SOURCE_SCAN_STATE_NORMAL
        cur_array_name = ""
        line_no = 0
        for line_text in lst_lines:
            line_no = line_no + 1

            # 当前状态为查找个人翻译字符串起始位置
            # 如：<!-- BSP: add by liugefeng @{ -->
            if scan_state == SOURCE_SCAN_STATE_NORMAL:
                line_type, prop_name = parseCurLine(line_text)
                if line_type == PROP_TYPE_CUSTOM_START: 
                    # 多个修改段落之间用空格隔开
                    if len(self.lst_trans) > 0:
                        self.lst_trans.append("\n")

                    if last_scan_state != scan_state:
                        last_scan_state = scan_state

                    scan_state = SOURCE_SCAN_STATE_MINE
                    continue

                continue

            # 当前状态为已经匹配到翻译字符串起始位置，记录当前翻译串
            # 匹配到<!-- BSP: @} --> 结束
            if scan_state == SOURCE_SCAN_STATE_MINE:
                line_type, prop_name = parseCurLine(line_text)

                # 找到匹配结束，则重新进入NORMAL状态
                if line_type == PROP_TYPE_CUSTOM_END: 
                    if last_scan_state != scan_state:
                        last_scan_state = scan_state

                    scan_state = SOURCE_SCAN_STATE_NORMAL
                    continue

                self.lst_trans.append(line_text) 

                # 当前行为普通元素
                if line_type == PROP_TYPE_PLAIN:
                    if not prop_name:
                        print("prop name null for line " + str(line_no))
                        continue

                    if not prop_name in self.map_trans:
                        self.map_trans[prop_name] = str(len(self.lst_trans) - 1)
                    else:
                        print("repeat property found about " + prop_name)

                    continue

                # 当前行为数组元素
                if line_type == PROP_TYPE_ARRAY_START:
                    if not prop_name:
                        print("prop name null for line " + str(line_no))
                        continue

                    if not prop_name in self.map_trans:
                        cur_array_name = prop_name

                        if last_scan_state != scan_state:
                            last_scan_state = scan_state

                        scan_state = SOURCE_SCAN_STATE_ARRAY
                        self.map_trans[prop_name] = str(len(self.lst_trans) - 1)
                    else:
                        print("repeat property found about array " + prop_name + " on line " + str(line_no))
                    continue

            # 搜集数组元素，并查找数组结束行
            if scan_state == SOURCE_SCAN_STATE_ARRAY:
                line_type, prop_name = parseCurLine(line_text)
                self.lst_trans.append(line_text)

                if line_type != PROP_TYPE_ARRAY_END:
                    continue

                last_scan_state, scan_state = scan_state, last_scan_state 

                if cur_array_name and cur_array_name in self.map_trans:
                    self.map_trans[cur_array_name] = self.map_trans[cur_array_name] + "," + str(len(self.lst_trans) - 1)
                    cur_array_name = ""

                continue

        if scan_state != SOURCE_SCAN_STATE_NORMAL:
            print("scan state error for scanning file " + self.path)
        return

    # =========================================================================
    # Function : clear
    # Comment  : 清空数据
    # =========================================================================
    def clear(self):
        del self.lst_trans[:]
        self.map_trans.clear()

class TargetXmlFile:
    def __init__(self, xmlFile, sourceXmlFile):
        self.path = xmlFile.strip()
        self.source_xml_file = sourceXmlFile
        self.lst_lines = []
        if os.path.exists(self.path):
            file_id = open(self.path, 'r')
            if file_id:
                self.lst_lines = file_id.readlines()
                file_id.close()

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
        result = result + "    <!-- BSP: add by " + self.source_xml_file.trans_owner  +  " @{ -->\n"
        for line_text in self.source_xml_file.lst_trans:
            result = result + line_text

        result = result + "    <!-- BSP: @} -->\n"

        # 加入resources结尾标志
        result = result + "</resources>\n"

        file_id.write(result)
        file_id.close()

    # =========================================================================
    # Function : mergeCustomContent
    # Comment  : 合并owner不同位置的注释到最后一处owner位置
    # =========================================================================
    def mergeCustomContent(self):
        # 文件内容为空, 不进行处理
        if not self.lst_lines:
            return

        #owner = self.source_xml_file.trans_owner
        #scan_state = TARGET_SCAN_STATE_NORMAL

        #for lint_text in self.lst_lines:



    # =========================================================================
    # Function : updateTargetFile
    # Comment  : 根据source xml文件中获取的属于owner的更新信息，更新target xml文件
    # Condition: 新xml文件已经存在
    # Note     : 更新规则：
    #          : 1. 针对新文件中的已有元素: 
    #          :    a) 元素为原生信息，则使用source文件的信息
    #          :    b) 元素为修改过的信息，则不更新该元素信息
    #          : 2. 针对新文件中不存在的元素，则直接增加source文件中的信息
    #          : 
    # =========================================================================
    def updateTargetFile(self):
        # 文件内容为空
        if not self.lst_lines:
            return

        result = ""
        line_no = 0
        scan_state = TARGET_SCAN_STATE_NORMAL

        for line_text in self.lst_lines:
            line_no = line_no + 1

            # 开始扫描，查找resource起始标记
            if scan_state == TARGET_SCAN_STATE_NORMAL: 
                result = result + line_text
                line_type, prop_name = parseCurLine(line_text)

                if line_type == PROP_TYPE_CUSTOM_RESOURCE_START: 
                    scan_state = TARGET_SCAN_STATE_PROPERTY 
                    continue 

                continue

            # 扫描元素部分内容
            if scan_state == TARGET_SCAN_STATE_PROPERTY:
                line_type, prop_name = parseCurLine(line_text)

                # 普通元素匹配
                if line_type == PROP_TYPE_PLAIN:
                    if prop_name and prop_name in self.source_xml_file.map_trans:
                        self.source_xml_file.map_trans[prop_name] = "-1"
                        continue
                    else:
                        result = result + line_text

                    continue

                # 数组元素匹配
                if line_type == PROP_TYPE_ARRAY_START:
                    scan_state = TARGET_SCAN_STATE_ARRAY_NONE_UPDATE
                    if prop_name in self.source_xml_file.map_trans:
                        self.source_xml_file.map_trans[prop_name] = "-1"
                    else:
                        result = result + line_text
                    continue

                # 更新部分起始位置匹配
                if line_type == PROP_TYPE_CUSTOM_START:
                    scan_state = TARGET_SCAN_STATE_UPDATE
                    result = result + line_text
                    continue

                # </resources>匹配
                if line_type == PROP_TYPE_CUSTOM_RESOURCE_END:
                    scan_state = TARGET_SCAN_STATE_END
                    result = result + line_text
                    continue

                # 其他情况
                result = result + line_text

            # 扫描未修改数组内容
            if scan_state == TARGET_SCAN_STATE_ARRAY_NONE_UPDATE:
                result = result + line_text
                line_type, prop_name = parseCurLine(line_text)

                if line_type == PROP_TYPE_ARRAY_END:
                    scan_state = TARGET_SCAN_STATE_PROPERTY
                    continue

                continue

            # 更新部分内部扫描
            if scan_state == TARGET_SCAN_STATE_UPDATE:
                line_type, prop_name = parseCurLine(line_text)

                if line_type == PROP_TYPE_CUSTOM_END:
                    scan_state = TARGET_SCAN_STATE_PROPERTY
                    continue

                continue

            # </resources>后面部分内容扫描
            if scan_state == TARGET_SCAN_STATE_END:
                result = result + line_text
                continue
        print(result)

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
    #if not os.path.exists(target_path):
    #    print("new source path not found!")
    #    exit()
    print("target path: " + target_path)

    source_file = SourceXmlFile(source_path, owner)
    source_file.parse()

    # =====================================================================
    #result = ""
    #for item in source_file.lst_trans:
    #    result = result + item

    #print(result)

    #print("MMMMMMMMMMMMMM " + str(len(source_file.map_trans)))
    #for prop_name in source_file.map_trans:
    #    print("MMMMMM" + prop_name + " v: " + source_file.map_trans[prop_name])
    # =====================================================================

    target_file = TargetXmlFile(target_path, source_file)
    #target_file.generateTargetFile()
    target_file.updateTargetFile()

