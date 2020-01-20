#! /usr/bin/env python
# coding:utf-8

import re
import sys
import os

def scan_cfg_file(cfg_file):
    if not os.path.exists(cfg_file):
        print("config file " + cfg_file + " not found!")
        sys.exit()

    # scan item string from config file
    re_item = re.compile(r'^\s*(\w+)\s*=\s*(.*)$')
    result = ""
    fp = open(cfg_file, encoding='utf-8', errors='ignore')
    line_text = fp.readline()
    while line_text:
        obj_search = re_item.search(line_text)
        if obj_search:
            # <string name="unknownName">Unknown</string>
            result = result + "<string name=\"" + obj_search.group(1) + "\">" + obj_search.group(2) + "</string>\n"
        line_text = fp.readline()

    fp.close()

    # generate result file
    fp = open("result.txt", "w")
    fp.write(result)
    fp.close()

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("no config file found!")
        sys.exit()

    cfg_file = sys.argv[1].strip()
    scan_cfg_file(cfg_file)

