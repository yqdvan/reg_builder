# resolve multiple bits.
# gen xml file

import sys
import os

os.chdir("./")  # 设置项目路径
sys.path.append("./lib/python")
import re
import platform
import getopt
import threading
import time

from openpyxl import load_workbook
from my_Nodes import my_Debug, my_Block, _analysis_sheet, may_need_exit
from verilog_writer import verilog_writer


class my_Thread(threading.Thread):
    def __init__(self, name, parr):
        threading.Thread.__init__(self)
        self.name = name
        # self.block = deepcopy(block_thread)
        self.block = None
        self.verilog_writer = None
        if isinstance(parr, my_Block):
            self.block = parr
        elif isinstance(parr, verilog_writer):
            self.verilog_writer = parr

    def run(self):
        s_time = time.time()
        try:
            if my_Debug.debug_thread == 1:
                print('thread start:' + self.name + "\n")
            if self.block:
                self.block.gen_docx(self.name)
            if self.verilog_writer:
                self.verilog_writer.create_v_file()
        except Exception as e:
            print(e)
            may_need_exit()
        else:
            print(self.name + " success.")
            if my_Debug.debug_thread == 1:
                print('thread ' + self.name, " cost:", str(time.time() - s_time), "\n")


def _reg_build(elxFile: str):
    # 1.1 ==== read config  ====
    excel = load_workbook(elxFile)
    sheetCfg = excel['CONFIG']
    chip_name = 'empty'
    block_list = []
    block_arrive = 0
    gen_doc_cnt = 0
    gen_xml_cnt = 0

    for row in sheetCfg:
        if row[0].value == 'Chip Name:':
            chip_name = row[1].value
        if row[0].value == 'Block Name':
            block_arrive = 1
            continue
        if block_arrive == 1:
            if row[0].value is not None:
                block_list.append(
                    my_Block(row[0].value, row[1].value, row[2].value, row[3].value, [], row[4].value))
            else:
                break
    if my_Debug.debug == 1:
        for block in block_list:
            block.display()

    # 1.2 ===== analysis block sheet ====
    begin_time = time.time()  # (second)
    th_list = []

    for block_cur in block_list:

        try:
            if block_cur.need_gen == 'yes' or block_cur.gen_xml == 'yes':
                print("\n--", block_cur.block_name, "is analysing... \n")
                sheet_cache = excel[block_cur.block_name]
                _analysis_sheet(sheet_cache, block_cur)
                print(block_cur.block_name, "analysing end. \n")

        except Exception as e:
            print(block_cur.block_name, "analysis error!")
            print(e)
            may_need_exit()

        if block_cur.need_gen == 'yes':
            # block_cur.gen_docx(chip_name)
            gen_doc_cnt = gen_doc_cnt + 1
            # th_list.append(my_Thread(block_cur.block_name + "_thread", block_cur))
            # ------------------------------------------------------------------------------------------------------
            th_list.append(my_Thread(block_cur.block_name + "_thread", verilog_writer(block_cur)))

    if my_Debug.debug_otp_show == 1:
        print("\n-->otp reg show:\n")
        for block in block_list:
            for reg in block.reg_list:
                if reg.need_otp == 'yes':
                    print(reg.display())
        print("\n-->otp reg show end\n")

    # 2. ===== gen docx or verilog file ====
    for th in th_list:
        th.start()

    # 2.1 ===== gen RDL file ====
    for block_cur in block_list:
        if block_cur.need_gen == 'yes':
            block_cur.gen_rdl()

    # 3. === gen xml file ===
    my_Debug.debug = 0 if my_Debug.debug == 0 else print("\nXML creating INFO.")

    pageIndex = 0
    xml_is_empty = 1

    xml_line = []
    xml_line_inner = []
    str_cache = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
    xml_line.append(str_cache)
    xml_line_inner.append(str_cache)
    str_cache = "<" + chip_name + "Cfg>\n"
    xml_line.append(str_cache)
    xml_line_inner.append(str_cache)

    for block_cur in block_list:
        if block_cur.gen_xml == 'yes':
            xml_is_empty = 0
            gen_xml_cnt = gen_xml_cnt + 1
            print("-- generate xml for ", block_cur.block_name, " ...\n")
            page_cache = "Page" + str(pageIndex)
            str_cache = r'       <Page Name="' + page_cache + r'" Text="Global1" />' + "\n"
            xml_line.append(str_cache)
            pageIndex += 1

            for reg in block_cur.reg_list:
                # reg.display()
                reg.to_xml(xml_line, str(page_cache))
                reg.to_xml(xml_line_inner, str(page_cache), 'yes')

    str_cache = "</" + chip_name + "Cfg>\n"
    xml_line.append(str_cache)
    xml_line_inner.append(str_cache)

    # 4. xml encoding utf-8
    xml_file_name = chip_name + '_xml_file.cfg'
    xml_inner_file_name = chip_name + '_xml_file_inner.cfg'
    if not xml_is_empty:
        try:
            f = open(xml_file_name, 'w', encoding='utf-8')
            f.writelines(xml_line)
            f.close()
            f = open(xml_inner_file_name, 'w', encoding='utf-8')
            f.writelines(xml_line_inner)
            f.close()
        except Exception as e:
            print("-- xml file operate error!!!")
            print(e)
            may_need_exit()
        else:
            if my_Debug.v2_flag == 1:
                print("-- xml file write success!")

    # 5. calculate cost time
    print("-- waiting for docx gen......")
    for th in th_list:
        th.join()
    end_time = time.time()
    print("\n-- reg_builder.py cost time:", str(end_time - begin_time), "(s)")

    if my_Debug.ok_flag == 1:
        # print("\n ^_^ generate verilog(", gen_doc_cnt, ") and xml file(", gen_xml_cnt, ") success!")
        print("\n ^_^ generate verilog (", gen_doc_cnt, ") file success!")
    else:
        print("\n T_T some error occurs in processing, please check printed info.")


def _banner():
    banner = '''              

    _____              ____        _ _     _           
   |  __ \            |  _ \      (_) |   | |          
   | |__) |___  __ _  | |_) |_   _ _| | __| | ___ _ __ 
   |  _  // _ \/ _` | |  _ <| | | | | |/ _` |/ _ \ '__|
   | | \ \  __/ (_| | | |_) | |_| | | | (_| |  __/ |   
   |_|  \_\___|\__, | |____/ \__,_|_|_|\__,_|\___|_|   
                __/ |                                  
               |___/                                   

                             
'''
    print(banner)


def _help_info():
    help_str = '''
*************************************************************
                            help
#------------------------------------------------------------
#-- Name        : reg_build
#-- Version     : v0.1
#-- Description : Use to generate verilog from sheet file.
#-- Modified by : duanyq
#------------------------------------------------------------
Usage: reg_build [-template] [-help] [-file <sheet_file_name>]

Options:
    -h, --help
        help page.

    -t, --template
        Create a template sheet file at current directory.

    -f, --file
        Determine sheet_file_name name. will read this sheet,
        and generate verilog according CONFIG page of sheet.

Example:
    step 1. execute \033[33mreg_build -t\033[0m will get standard sheet file.
    step 2. edit file and save. \033[33m"soffice ./registers.xlsm &"\033[0m
    step 3. execute \033[33mreg_build -f ./registers.xlsm\033[0m to generate.

#------------------------------------------------------------
'''
    print(help_str)


##--------------------------------------- Main() ----------------------------------------##
if __name__ == '__main__':
    _banner()
    if len(sys.argv) == 1:
        print("reg_build: Please Execute \"\033[33mreg_build -h\033[0m\" To Get Help Information.")
        exit()
    try:
        opts, args = getopt.getopt(sys.argv[1:], "htdf:", ["help", "template", "debug", "file="])
    except getopt.GetoptError:
        print("Error: Please execute \"reg_build -h\" to get help information.")
        sys.exit(2)

    sys_plt = platform.system()
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            # print("help info.")
            _help_info()
        elif opt in ("-t", "--template"):
            if sys_plt == "Windows":
                res_dir = os.getcwd() + "\\template\\registers.xlsm"
                os.system("copy " + res_dir + " " + os.getcwd())
            else:
                #res_dir = re.match("(.*reg_build\/)", sys.argv[0]).group(1) + "template/registers.xlsm"
                res_dir = re.match("(.*)reg_builder.py", sys.argv[0]).group(1) + "../template/registers.xlsm"
                os.system("cp " + res_dir + " " + os.getcwd())
            print("reg_build: " + "copy template sheet file 'registers.xlsm' to current dir success!")
        elif opt in ("-f", "--file"):
            print("reg_build: " + "start analysis sheet file \'" + arg + "\' ......")
            _reg_build(arg)
        elif opt in ("-d", "--debug"):
            print(sys.argv)
            print(sys.argv[0])
            print("reg_build: " + os.getcwd())
            # res_dir = re.match("(.*arsoc\/)", sys.argv[0]).group(1) + "project/flowsetup/reg_builder/registers.xlsm"
            if sys_plt == "Windows":
                res_dir = os.getcwd() + "\\template\\registers.xlsm"
                print("cmd: " + "res_dir:" + res_dir)
            else:
                res_dir = re.match("(.*reg_build\/)", sys.argv[0]).group(1) + "template/registers.xlsm"
                print("cmd: " + "res_dir:" + res_dir)
        else:
            print("please execute \"reg_build -h\" to get help information.")
            exit()

# --- useless code ---
# == get excle name ==
# sys_plt = platform.system()
# if sys_plt == "Windows":
#     elxFile = r'.\registers.xlsm'
# elif sys_plt == "Linux":
#     elxFile = r'./registers.xlsm'
# else:
#     elxFile = ""
#     raise SystemError
# args = sys.argv[1:]
# args_length = len(args) if args else 0
# if args_length != 0:
#     elxFile = sys.argv[1]
# my_Debug.debug = 0 if my_Debug.debug == 0 else print(elxFile)
