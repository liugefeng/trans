# coding: UTF-8

# =========================================================================
# File Name  : translate_modifier.py
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

class MyConfigParser(configparser.ConfigParser):
    def __init__(self, defaults=None):
        configparser.ConfigParser.__init__(self, defaults=None)

    def optionxform(self, optionstr):
        return optionstr;

class CfgFile:
    def __init__(self, name):
        if not os.path.exists(name):
            print("config file " + name + " not exits!")
            sys.exit();

        self.file_id = open(name, 'r', errors = "ignore")
        self.lst_symbols = []
        self.map_symbols = {}
        self.lst_xml_files = {}

    def scan(self):
        # SYMBOLS_FILE(symbols.xml);
        re_symbols = re.compile(r'^\s*SYMBOLS_FILE\s*\(([^\)]+)\)\s*;\s*$')

        # STRING_FILE(strings.xml);
        re_string_file = re.compile(r'^\s*STRING_FILE\s*\(([^\)]+)\)\s*;\s*$')

        # ConfigItem(byteShort, transtest1);
        re_config_item = re.compile(r'^\s*ConfigItem\s*\(([^,]+),([^\)]+)\)\s*;\s*$')

        # scan state const
        SCAN_STATE_START = 0
        SCAN_STATE_STRING_FILE = 1
        SCAN_STATE_STRING_ITEM = 2

        scan_state = SCAN_STATE_START
        line_text = self.file_id.readline()
        line_no = 0
        xml_file = None
        while line_text:
            line_no = line_no + 1

            # SYMBOLS_FILE(symbols.xml);
            if scan_state == SCAN_STATE_START:
                result = re_symbols.search(line_text)
                if result:
                    symbol_str = result.group(1).strip()
                    scan_state = SCAN_STATE_STRING_FILE
                    self.lst_xml_files = symbol_str.split(',')
                    #print(self.lst_xml_files)

                line_text = self.file_id.readline()
                continue

            # STRING_FILE(strings.xml);
            if scan_state == SCAN_STATE_STRING_FILE:
                result = re_string_file.search(line_text)
                if result:
                    name = result.group(1).strip()
                    if not os.path.exists(name):
                        print("xml file " + name + " not exits on line " + str(line_no))
                        line_text = self.file_id.readline()
                        continue

                    xml_file = XmlFile(name)
                    self.lst_xml_files.append(xml_file)
                    scan_state = SCAN_STATE_STRING_ITEM

                line_text = self.file_id.readline()
                continue

            # ConfigItem(byteShort, transtest1);
            if scan_state == SCAN_STATE_STRING_ITEM:
                result = re_config_item.search(line_text)
                if result:
                    name = result.group(1).strip()
                    value = result.group(2).strip()
                    self.lst_xml_files[-1].set_data(name, value)
                    print(name + ":" + value)
                    line_text = self.file_id.readline()
                    continue

                result = re_string_file.search(line_text)
                if result:
                    scan_state = SCAN_STATE_STRING_FILE
                    line_no = line_no - 1
                    # line_text = self.file_id.readline()
                    continue

                line_text = self.file_id.readline()
                continue

        print(scan_state)
        self.file_id.close()

class XmlFile:
    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.lst_strs = []
        self.map_strs = {}

    def set_data(self, str, value):
        if not str in self.lst_strs:
            self.lst_strs.append(str)
            self.map_strs[str] = value

    def generate_custom_str(self):
        result = ""
        for str in self.lst_strs:
            result = result + '    <string name="' + str +'">' + self.map_strs[str] + '</string>\n'

        return result

    def update(self):
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
                res_march = re_resource_end.search(line_text)
                if res_march:
                    result = result + self.generate_custom_str();

                result = result + line_text
                line_text = file_id.readline()
                continue

            name = match.group(1).strip();
            if name in self.map_strs.keys():
                line_text = file_id.readline()
                continue

            result = result + line_text
            line_text = file_id.readline()

        file_id.close()

        # generate new config file
        file_id = open(self.xml_file + "_temp", "w")
        file_id.write(result)
        file_id.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("no xml file found.")
        sys.exit()

    cfg_file = CfgFile(sys.argv[1])
    cfg_file.scan()

