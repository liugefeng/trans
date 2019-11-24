# coding: UTF-8

# =========================================================================
# File Name  : trans.py
# Author     : 刘戈峰
# Create Date: 2018-08-19
# Platform   : Linux/Windows
# Comment    :  
# History    : 2019-11-24 work finished
# =========================================================================

import sys
import re
import os.path
import configparser

class XmlFile:
    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.lst_strs = []
        self.map_strs = {}

    def set_data(self, lst_strs):
        self.lst_strs = lst_strs
        for item,value in lst_strs:
            if not item in self.map_strs.keys():
                self.map_strs[item] = 1

    def generate_custom_str(self):
        result = ""
        for str, value in self.lst_strs:
            result = result + '    <string name="' + str +'">' + value + '</string>\n'

        return result

    def scan(self):
        if not os.path.exists(self.xml_file):
            print("file " + self.xml_file + " not exits!")
            sys.exit()

        file_id = open(self.xml_file, 'r', errors = "ignore")
        line_text = file_id.readline()

        # <string name="emptyPhoneNumber">(No phone number)</string>
        re_str = re.compile(r'^\s*<string\s+name\s*="([^"]+)".*</string>.*$')

        # </resources>
        re_resource_end = re.compile(r'^\s*</resources>\s*$');

        result = ""
        while line_text:
            match = re_str.search(line_text)
            if not match:
                # for </resources>
                sub_march = re_resource_end.search(line_text)
                if sub_march:
                    result = result + self.generate_custom_str();

                result = result + line_text

                line_text = file_id.readline()
                continue

            name = match.group(1);
            if name in self.map_strs.keys():
                line_text = self.file_id.readline()
                continue
            else: 
                result = result + line_text
                line_text = file_id.readline()

        file_id.close()

class CfgFileManager:
    def __init__(self, config_file):
        if not os.path.exists(config_file):
            print("config file " + config_file + " not exists!")
            sys.exit()

        self.cg = configparser.ConfigParser()
        self.cg.read(config_file, encoding='utf-8')
        self.lst_xml_files = []

    def scan_cfg_files(self):
        # get xml files
        lst_files = self.cg.sections()
        print(lst_files)

        for item in lst_files:
            xml_file = XmlFile(item)
            lst_strs = self.cg.items(item)
            xml_file.set_data(lst_strs)

            self.lst_xml_files.append(xml_file)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("no xml file found.")
        sys.exit()

    config_file = CfgFileManager(sys.argv[1])
    config_file.scan_cfg_files()

    for item in config_file.lst_xml_files:
        item.scan()

