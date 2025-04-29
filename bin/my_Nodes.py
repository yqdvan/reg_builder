import os
import re
import shutil
import threading
import time
import zipfile
from copy import deepcopy
from xml.dom.minidom import Document  # tool auto import.


class my_Debug(object):
    debug = 0
    flag = 0
    v2_flag = 0
    debug_select = 0
    debug_thread = 0
    debug_yes_no = 0
    debug_otp_show = 0
    debug_peakrdl = 0

    ok_flag = 1
    # static parameter for print debug info.
    max_info = 10
    info_index: int = 0
    info_list = [" "] * max_info


def print_info():
    for i in range(0, my_Debug.max_info):
        # my_Debug.info_list[i] = " "
        print(my_Debug.info_list[my_Debug.info_index % my_Debug.max_info])
        my_Debug.info_list[my_Debug.info_index % my_Debug.max_info] = " "
        my_Debug.info_index = my_Debug.info_index + 1
    my_Debug.info_index = 0
    print(" ")


def add_info(info):
    my_Debug.info_list[my_Debug.info_index] = str(info)
    if my_Debug.info_index == my_Debug.max_info - 1:
        my_Debug.info_index = 0
    else:
        my_Debug.info_index = my_Debug.info_index + 1


def may_need_exit():
    my_Debug.ok_flag = 0
    if my_Debug.debug == 1:
        exit()
    else:
        print_info()


def _zip_dir(path, output=None):
    try:
        """压缩指定目录"""
        output = output or os.path.basename(path) + '.zip'  # 压缩文件的名字
        zip_zip = zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED)
        for root, dirs, files in os.walk(path):
            relative_root = '' if root == path else root.replace(path, '') + os.sep  # 计算文件相对路径
            for filename in files:
                zip_zip.write(os.path.join(root, filename), relative_root + filename)  # 文件路径 压缩文件路径（相对路径）
        zip_zip.close()
    except Exception as e:
        print("_zip_dir error!")
        print(e)
        may_need_exit()
    else:
        shutil.rmtree(path)
        if my_Debug.v2_flag == 1:
            print("zip dir:" + path + " success!")


def _unzip(zip_file, output=None, dir_name='un_zip'):
    try:
        """解压zip文件"""
        unzip_zip = zipfile.ZipFile(zip_file)
        output = output or os.path.dirname(zip_file)  # 默认解压到当前目录同名文件夹中
        unzip_zip.extractall(output)  # 会被解压到输入的路径中
        unzip_zip.close()
    except Exception as e:
        print("_unzip error!")
        print(e)
        may_need_exit()
    else:
        os.remove(zip_file)
        if my_Debug.v2_flag == 1:
            print("unzip file:" + zip_file + " success!")


def _replace_str(file, patt, repl_str):
    try:
        f = open(file, 'r')
        all_lines = f.readlines()
        f.close()
        f = open(file, 'w+')
        for each_line in all_lines:
            a = re.sub(patt, repl_str, each_line)
            f.writelines(a)
        f.close()
    except Exception as e:
        print("_replace_str error! ")
        print(e)
        may_need_exit()
    else:
        if my_Debug.debug == 1:
            print("replace str success!")


def _edit_ids_cfg(block_name):
    ids_file_name = block_name + r'.docx'
    unzip_dir = block_name
    ids_out_dir = block_name + '_idsout'

    _unzip(ids_file_name, unzip_dir)
    _replace_str(unzip_dir + r'\docProps\custom.xml', 'idsout', ids_out_dir)
    _zip_dir(unzip_dir, ids_file_name)


def _add_new_table(file, domain_name, addr):
    # file = Document(doc_name)
    # 原表格模版 在第三个
    doc_table = file.tables[3]

    new_tbl = deepcopy(doc_table._tbl)

    # 定位最后一行
    page = file.paragraphs[len(file.paragraphs) - 1]
    page._p.addnext(new_tbl)
    file.add_paragraph(" ")
    file.add_paragraph(" ")

    tables = file.tables
    table = tables[len(tables) - 1]

    table.cell(0, 10).text = domain_name
    table.cell(1, 3).text = addr

    if my_Debug.v2_flag == 1:
        file.save("add-tab-doc_name.docx")
    my_Debug.debug = 0 if my_Debug.debug == 0 else print('exit add new table ' + domain_name)


def _add_item(regList, descr):
    itm_p1 = 'emp_p1'
    itm_p2 = 'emp_descrption'
    try:
        strs = descr.split(':', 1)
        itm_p1 = strs[0]
        itm_p2 = strs[1]
    except:
        my_Debug.debug = 0 if my_Debug.debug == 0 else print('\n\n\n\n\n items resolved Error!\n\n\n\n\n')
    else:
        my_Debug.debug = 0 if my_Debug.debug == 0 else print(strs)

    regList[-1].bitList[-1].items.append(my_Item(itm_p1, itm_p2))


def _resolve_sw_hw(sw, hw):
    ans = []
    if sw == "R":
        ans.append("ro")
    elif sw == "R/W":
        ans.append("rw")
    elif sw == "W":
        ans.append("wo")
    elif sw == "WRC":
        ans.append("wrc")
    elif sw == "RC":
        ans.append("rc")
    else:
        ans.append(sw)
    if hw == "R":
        ans.append("ro")
    elif hw == "R/W":
        ans.append("rw")
    elif hw == "W":
        ans.append("wo")
    elif hw == "N/A":
        ans.append("na")
    else:
        ans.append(hw)
    return ans


def _analysis_line(row, sheet, st_line, decr_str, regList):
    #### 1. 当前不为空 & 下一个不为空 ： 填    items.len == 0 , my_bit ++
    if (sheet.cell(row=st_line, column=3).value != None and sheet.cell(row=(st_line + 1), column=3).value != None):

        swh = _resolve_sw_hw(row[6].value, row[7].value)
        software = swh[0]
        hardware = swh[1]

        my_Debug.debug = 0 if my_Debug.debug == 0 else print("hardware : " + hardware)

        # my_Debug.debug = 0 if my_Debug.debug == 0 else print("兼容： next col==3: ", st_line, " ", sheet.cell(row=(st_line + 1), column=3).value)
        info_cache = "兼容： next col==3: " + str(st_line) + " " + str(sheet.cell(row=(st_line + 1), column=3).value)
        if my_Debug.debug == 0:
            add_info(info_cache)
        else:
            print(info_cache)

        decr_str = ''

        regList[-1].bitList.append(
            my_Bit(row[2].value, row[3].value, [], row[4].value, row[9].value, software, hardware, row[5].value))

    #### 2. 当前不为空 & 下面是空     ：填一半   items.len == 0 my_bit ++
    elif (sheet.cell(row=st_line, column=3).value != None and sheet.cell(row=(st_line + 1), column=3).value == None):

        swh = _resolve_sw_hw(row[6].value, row[7].value)
        software = swh[0]
        hardware = swh[1]

        my_Debug.debug = 0 if my_Debug.debug == 0 else print("hardware : " + hardware)

        # my_Debug.debug = 0 if my_Debug.debug == 0 else print("当前不为空 & 下面是空     ：填一半")
        # my_Debug.debug = 0 if my_Debug.debug == 0 else print(decr_str + "\n" + row[4].value)
        info_cache = decr_str + "\n" + str(row[4].value)
        if my_Debug.debug == 0:
            add_info(info_cache)
        else:
            print(info_cache)

        decr_str = row[4].value

        regList[-1].bitList.append(
            my_Bit(row[2].value, row[3].value, [], row[4].value, row[9].value, software, hardware, row[5].value))

    #### 3. 当前为空  & 下一个不为空  ：填另一半   itms ++
    elif (sheet.cell(row=st_line, column=3).value == None and sheet.cell(row=(st_line + 1), column=3).value != None):

        # my_Debug.debug = 0 if my_Debug.debug == 0 else print("当前为空  & 下一个不为空  ：填另一半")
        # my_Debug.debug = 0 if my_Debug.debug == 0 else print(decr_str + "\n" + row[4].value)

        info_cache = decr_str + "\n" + str(row[4].value)
        if my_Debug.debug == 0:
            add_info(info_cache)
        else:
            print(info_cache)

        decr_str = ''

        _add_item(regList, row[4].value)

    #### 4. 当前为空  & 下一个为空 & 没到结尾    ： 记录，不填  itms ++
    elif (sheet.cell(row=st_line, column=3).value == None and sheet.cell(row=(st_line + 1),
                                                                         column=3).value == None and sheet.cell(
        row=(st_line + 1), column=5).value != None):

        # my_Debug.debug = 0 if my_Debug.debug == 0 else print("当前为空  & 下一个为空 & 没到结尾    ： 记录，不填")
        # my_Debug.debug = 0 if my_Debug.debug == 0 else print(decr_str + "\n" + row[4].value)
        info_cache = decr_str + "\n" + str(row[4].value)
        if my_Debug.debug == 0:
            add_info(info_cache)
        else:
            print(info_cache)

        decr_str = decr_str + "\n" + row[4].value

        _add_item(regList, row[4].value)

    #### 5. 当前为空  & 下一个为空 & 到结尾了    ： 填另一半 itms ++
    elif (sheet.cell(row=st_line, column=3).value == None and sheet.cell(row=(st_line + 1),
                                                                         column=3).value is None and sheet.cell(
        row=(st_line + 1), column=5).value == None):

        # my_Debug.debug = 0 if my_Debug.debug == 0 else print("当前为空  & 下一个为空 & 到结尾    ： 填另一半")
        # my_Debug.debug = 0 if my_Debug.debug == 0 else print(decr_str + "\n" + row[4].value)

        info_cache = decr_str + "\n" + str(row[4].value)
        if my_Debug.debug == 0:
            add_info(info_cache)
        else:
            print(info_cache)

        decr_str = ''

        _add_item(regList, row[4].value)

    my_Debug.debug = 0 if my_Debug.debug == 0 else print("exit file ab: ", "st line:", st_line, " rtn des: ", decr_str)
    my_Debug.debug = 0 if my_Debug.debug == 0 else print('exit analysis_line')
    return decr_str


def _optimize(opt_file, name_str, block):
    tmp_table = opt_file.tables[3]
    tmp_table._element.getparent().remove(tmp_table._element)

    tmp_table = opt_file.tables[1]
    tmp_table.cell(0, 3).text = name_str  # chip name

    tmp_table = opt_file.tables[2]
    tmp_table.cell(0, 2).text = block.block_name
    tmp_table.cell(1, 1).text = block.block_offset
    if block.block_size != '0':
        tmp_table.cell(1, 5).text = block.block_size

    for opt_table in opt_file.tables:
        rm_cnt = 0
        max_line = len(opt_table.rows)
        for index in range(8, max_line):
            row = opt_table.rows[index - rm_cnt]
            my_Debug.debug = 0 if my_Debug.debug == 0 else print("index : %d , rm_cnt: %d", index, rm_cnt)
            my_Debug.debug = 0 if my_Debug.debug == 0 else print(row.cells[0].text)
            if row.cells[0].text == "" and row.cells[1].text == "":
                my_Debug.debug = 0 if my_Debug.debug == 0 else print("remove line")
                row._element.getparent().remove(row._element)
                rm_cnt += 1
                if index - rm_cnt == len(opt_table.rows):
                    break
    if my_Debug.v2_flag == 1:
        opt_file.save("opt.docx")
    my_Debug.debug = 0 if my_Debug.debug == 0 else print('exit remove empty line.')


def _analysis_sheet(sheet, block):
    index = 8  # 模板表格从8开始填
    is_arrive = 0
    my_Debug.debugCount = 0
    lineNum = 2  # No.1 is head of table.
    desc_cache = ''

    for row in sheet:
        if is_arrive == 0 and re.match("0x*", str(row[0].value)):
            is_arrive = 1

        if is_arrive:
            xx = ['current:', index, row[0].value, row[1].value, row[2].value, row[3].value, row[5].value,
                  row[6].value, row[4].value]
            add_info(xx) if my_Debug.debug == 0 else print(xx)

            if row[0].value is not None:
                my_Debug.debug = 0 if my_Debug.debug == 0 else print('--- should one time')

                # addr_cache = int(row[0].value, 16) + int(block.block_offset, 16)
                if my_Debug.debug_yes_no == 1:
                    print("regValid[9]:", row[9].value, " external[10]:", row[10].value, row[0].value, row[1].value,
                          row[2].value, row[3].value, row[4].value, row[5].value, row[6].value, row[7].value,
                          row[8].value)
                block.reg_list.append(my_Reg(row[0].value, row[1].value, [], row[10].value, row[9].value, row[8].value))
                if my_Debug.debug_otp_show == 1:
                    print("otp :", row[8].value)

                # 分析第一行
                desc_cache = _analysis_line(row, sheet, lineNum, desc_cache, block.reg_list)

            else:
                # 剩余行
                desc_cache = _analysis_line(row, sheet, lineNum, desc_cache, block.reg_list)

            lineNum = lineNum + 1

        else:
            my_Debug.debug = 0 if my_Debug.debug == 0 else print('next line.')

    my_Debug.debug = 0 if my_Debug.debug == 0 else print('\n\n\n\nexit docxEdit')


class my_Block:
    def __init__(self, name, offset, size, gen, regList, gen_xml='no'):
        self.block_name = name if name != None else 'empty_name'
        self.block_offset = offset if offset != None else '0'
        self.block_size = size if size != None else '0'
        self.need_gen = gen if gen != None else 'no'
        # self.is_abso = abso if abso != None else 'no'
        self.gen_xml = gen_xml if gen_xml != None else 'no'
        self.reg_list: list[my_Reg] = regList  # is list

    def display(self):
        print("block name: ", self.block_name, ", offset: ", self.block_offset, "need gen: ", self.need_gen,
              " gen_xml:", self.gen_xml)
        return "block name: " + self.block_name + " offset: " + str(
            self.block_offset) + " need gen: " + self.need_gen + " gen_xml:" + self.gen_xml

    def gen_docx(self, ic_name='AS_xxx'):
        print("--generate docx :" + self.block_name + ".docx ongoing...\n")

        # 1. copy template
        doc_name = '.\\' + self.block_name + '.docx'
        shutil.copy('.\\template\\template.docx', doc_name)
        doc_file = Document(doc_name)

        # 2. iterate add sheets
        for cur_reg in self.reg_list:
            if cur_reg.reg_valid == 'yes':
                if my_Debug.v2_flag == 1:
                    print(cur_reg.display())
                else:
                    add_info(cur_reg.display())
                # if self.is_abso == 'yes':
                #     addr_offset = int(cur_reg.addr, 16) - int(self.block_offset, 16)
                #     _add_new_table(doc_file, cur_reg.regName, hex(addr_offset))
                # else:
                _add_new_table(doc_file, cur_reg.regName, cur_reg.addr)
                tables = doc_file.tables
                table = tables[-1]  # len(tables)
                line_num = 8
                for cur_bit in cur_reg.bitList:
                    if my_Debug.v2_flag == 1:
                        cur_bit.display()
                    table.cell(line_num, 0).text = cur_bit.bits
                    table.cell(line_num, 1).text = cur_bit.bitName
                    table.cell(line_num, 4).text = cur_bit.soft
                    table.cell(line_num, 6).text = cur_bit.hard
                    table.cell(line_num, 7).text = cur_bit.def_value
                    if re.match("reserve", cur_bit.bitName, re.I) is not None:
                        str_is_rsv = "{is_rsv=true}\n" + cur_bit.descr_n
                        table.cell(line_num, 11).text = str_is_rsv
                    else:
                        table.cell(line_num, 11).text = cur_bit.descr_n
                    line_num += 1
        if my_Debug.v2_flag == 1:
            doc_file.save("doc_name.docx")

        # 3. edit chip info & rm empty line of sheets
        _optimize(doc_file, ic_name, self)
        doc_file.save(doc_name)

        # 4. ids config edit
        _edit_ids_cfg(self.block_name)

        if my_Debug.debug_thread == 1:
            print("end of editing " + self.block_name + ".docx ", str(time.time()))
        else:
            print("end of editing " + self.block_name + ".docx")

    def gen_rdl(self):
        rdl_line = []
        rdl_str = 'addrmap ' + self.block_name
        rdl_line.append(rdl_str)
        rdl_str = '{\n        name = "' + self.block_name + '  SPI controller";\n'
        rdl_line.append(rdl_str)
        rdl_str = '''        desc = "Register description of xxxx ";

        default regwidth = 8;
        default sw = rw;
        default hw = r;

'''
        rdl_line.append(rdl_str)
        for reg_cache in self.reg_list:
            rdl_str = '    reg {\n        desc = "' + reg_cache.regName + '";\n'
            rdl_line.append(rdl_str)
            reg_cache.to_rdl(rdl_line)
            rdl_str = '    } ' + reg_cache.regName + ' @ ' + str(reg_cache.addr) + ';\n\n'
            rdl_line.append(rdl_str)
        rdl_line.append('};\n\n')
        # . rdl encoding utf-8
        rdl_file_name = self.block_name + '.rdl'
        try:
            f = open(rdl_file_name, 'w', encoding='utf-8')
            f.writelines(rdl_line)
            f.close()
        except Exception as e:
            print("-- rdl file operate error!!!")
            print(e)
            may_need_exit()
        else:
            if my_Debug.debug_peakrdl == 1:
                print("-- rdl file write success!")


class my_Reg:
    def __init__(self, addr, regName, bitList, xml_show, reg_valid, need_otp='no'):
        self.addr = addr
        self.regName = regName
        self.bitList: list[my_Bit] = bitList  # is list
        self.is_private = 'no' if xml_show == 'yes' else 'yes'  # affect display in xml yes or not.
        self.reg_valid = reg_valid if reg_valid is not None else 'no'  # affect generate code and display in word yes or not.
        self.need_otp = need_otp

    def display(self):
        # print("->my_REG:", self.regName, "addr:", self.addr, "Private:", self.is_private, "reg_Valid:", self.reg_valid)
        dis_str = "//->my_REG:" + self.regName + " addr:" + str(
            self.addr) + " Private:" + self.is_private + " reg_Valid:" + self.reg_valid
        dis_str = "//-----------------------------------------------------\n//    " + "REGISTER".ljust(
            14) + ": " + self.regName + "\n//    " + "ADDRESS".ljust(14) + ": " + self.addr + "\n//"
        for bit in self.bitList:
            # bit.display()
            dis_str = dis_str + "\n" + bit.display()
        return dis_str

    def to_xml(self, xml_line, pageName, beta='no'):
        if beta == 'no' and self.is_private == 'yes':
            return

        line_str = "       <Pnl Name=\"Reg" + self.addr + "\" PageOwnerName=\"" + pageName + "\" Text= \"" + self.regName + "\" RegAddr=\"" + self.addr + "\" />\n"
        xml_line.append(line_str)
        line_str = r'       <Ctrl Name="ReadBtn" PageOwnerName="' + pageName + r'" PanelOwnerName="Reg' + self.addr + r'" Text="Read" CtrlType="Btn" RegAddr="" LSBBit="" MSBBit="" Description="" />'
        line_str = line_str + "\n"
        xml_line.append(line_str)

        line_str = r'       <Ctrl Name="WriteBtn" PageOwnerName="' + pageName + r'" PanelOwnerName="Reg' + self.addr + r'" Text="Write" CtrlType="Btn" RegAddr="" LSBBit="" MSBBit="" Description="" />'
        line_str = line_str + "\n"
        xml_line.append(line_str)
        for bit in self.bitList:
            # bit.display()
            reg_cache = "Reg" + self.addr
            bit.to_xml(xml_line, pageName, reg_cache, beta)

    def to_rdl(self, rdl_line):
        for field in self.bitList:
            rdl_str = '        field { \n'
            rdl_line.append(rdl_str)
            rdl_str = '            desc = "' + str(field.descr) + '";\n'
            rdl_line.append(rdl_str)
            rdl_str = '            sw=' + str(field.soft).replace('o', '') + ';hw=' + str(field.hard).replace('o',
                                                                                                              '') + ';\n'
            rdl_line.append(rdl_str)
            if my_Debug.debug_peakrdl == 1:
                print(field.bits)
                if re.match("\d:\d", field.bits):
                    print("have : ")
                else:
                    print("donot have : ")
            if re.match("\d:\d", field.bits):
                rdl_str = '        } ' + str(field.bitName) + '[' + str(field.bits) + '] = ' + str(
                    field.def_value) + ';\n\n'
            else:
                rdl_str = '        } ' + str(field.bitName) + '[' + str(field.bits) + ':' + str(
                    field.bits) + '] = ' + str(
                    field.def_value) + ';\n\n'
            rdl_line.append(rdl_str)


class my_Bit:
    def __init__(self, bits, bitName, items, descr, xml_show='yes', soft='wo', hard='ro', def_value='0x0'):
        self.bits: str = str(bits)
        self.bitName: str = bitName
        self.descr = descr.replace('\n', '').replace('\r', '')  # use for xml line, do not need \n or \r.
        self.descr_n = descr  # use for docx file, need \n and \r.
        self.items: list[my_Item] = items  # is list
        self.is_private = 'no' if xml_show == 'yes' else 'yes'
        self.soft = soft
        self.hard = hard
        self.def_value = def_value
        self.is_rsv: bool = False
        if re.match("reserve", bitName, re.I):
            self.is_rsv = True

    def display(self):
        # print("    my_Bit:", self.bitName, " bits:", self.bits, " Private:", self.is_private, "  soft:", self.soft,
        #       " hard:", self.hard, " Descr:", self.descr)
        dis_str = "//    Field:" + self.bitName.ljust(20) + " Bits " + str(
            self.bits).ljust(
            5) + " Private:" + self.is_private + "  soft:" + self.soft + " hard:" + self.hard + " Descr:" + self.descr
        if len(self.items) == 0:
            pass
        for item in self.items:
            # item.display()
            dis_str = dis_str + "\n" + item.display()
        return dis_str

    def to_xml(self, xml_line, pageName, pnlName, beta='no'):
        if beta == 'no' and self.is_private == 'yes':
            return

        line_str = "empty line"
        if len(self.items) == 0:

            if re.search(":", str(self.bits)) is None:  ## 单bit
                line_str = r'       <Ctrl Name="' + self.bitName + r'" PageOwnerName="' + pageName + r'" PanelOwnerName="' + pnlName + r'" Text="' + self.bitName + r'" CtrlType="ChkBx" RegAddr="0" LSBBit="' + self.bits + r'" MSBBit="' + self.bits + r'" Description="' + self.descr + r'" />' + "\n"
                if my_Debug.flag == 1:
                    print("single bit", self.bits)
            else:  ## 多bit
                # 拆分msb lsb
                if my_Debug.flag == 1:
                    print("multi bit", self.bits)
                msb = re.search('(\d+):(\d+)', self.bits).group(1)
                lsb = re.search('(\d+):(\d+)', self.bits).group(2)
                line_str = r'       <Ctrl Name="' + self.bitName + r'" PageOwnerName="' + pageName + r'" PanelOwnerName="' + pnlName + r'" Text="' + self.bitName + r'" CtrlType="LBx" RegAddr="0" LSBBit="' + lsb + r'" MSBBit="' + msb + r'" Description="' + self.descr + r'" />' + "\n"

            xml_line.append(line_str)

        else:
            if my_Debug.debug_select == 1:
                print("cmbBx size: ", len(self.items), " ", self.bits)  ## cmbBx
            if re.search(":", str(self.bits)) == None:  ## 单bit
                line_str = r'       <Ctrl Name="' + self.bitName + r'" PageOwnerName="' + pageName + r'" PanelOwnerName="' + pnlName + r'" Text="' + self.bitName + r'" CtrlType="CmbBx" RegAddr="0" LSBBit="' + self.bits + r'" MSBBit="' + self.bits + r'" Description="' + self.descr + r'" />' + "\n"
                if my_Debug.debug_select == 1:
                    print("cmbBox single bit", self.bits)
            else:  ## 多bit
                # 拆分msb lsb
                if my_Debug.debug_select == 1:
                    print("cmbBox multip bit", self.bits)
                msb = re.search('(\d+):(\d+)', self.bits).group(1)
                lsb = re.search('(\d+):(\d+)', self.bits).group(2)
                line_str = r'       <Ctrl Name="' + self.bitName + r'" PageOwnerName="' + pageName + r'" PanelOwnerName="' + pnlName + r'" Text="' + self.bitName + r'" CtrlType="CmbBx" RegAddr="0" LSBBit="' + lsb + r'" MSBBit="' + msb + r'" Description="' + self.descr + r'" />' + "\n"

            xml_line.append(line_str)

            key_list = []
            value_list = []
            for item in self.items:
                key_list.append(item.combValue)
                value_list.append(item.combStr)

            line_str_key = r'       <CtrlExtKey PageOwnerName="' + pageName + r'" PanelOwnerName="' + pnlName + r'" CtrlOwnerName="' + self.bitName + r'"   '
            line_str_val = r'       <CtrlExtVal PageOwnerName="' + pageName + r'" PanelOwnerName="' + pnlName + r'" CtrlOwnerName="' + self.bitName + r'"   '

            for i in range(0, len(self.items)):
                line_str_key = line_str_key + " FxParam" + str(i) + "=\"" + key_list[i] + "\""
                line_str_val = line_str_val + " FxParam" + str(i) + "=\"" + value_list[i] + "\""

            line_str_key = line_str_key + r'/>' + "\n"
            line_str_val = line_str_val + r'/>' + "\n"
            xml_line.append(line_str_key)
            xml_line.append(line_str_val)

    def field_cut(self, width=8) -> str:
        field_bits: str = self.bits
        match = re.match("(\d):(\d)", field_bits)
        field_bits = ""
        if match:
            high = int(match.group(1))
            low = int(match.group(2))
            hh = high - low
            field_bits = "[" + str(hh) + ":0]"
        field_bits = field_bits.ljust(width)
        return field_bits

    def cul_field_width(self) -> str:
        field_bits: str = self.bits
        match = re.match("(\d):(\d)", field_bits)
        width = None
        if match:
            high = int(match.group(1))
            low = int(match.group(2))
            width = high - low + 1
        else:
            width = 1
        return str(width)


class my_Item:
    def __init__(self, combValue, combStr):
        self.combValue = combValue
        self.combStr = combStr.replace('\n', '').replace('\r', '')

    def display(self):
        # print("      selection-> Value:", self.combValue, " Str:",
        # self.combStr)
        return "//      selection-> Value:" + str(self.combValue) + " Str:" + self.combStr
