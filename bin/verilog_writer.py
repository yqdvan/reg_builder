import re
import time
from string import Template

from my_Nodes import my_Block, my_Reg, add_info, may_need_exit

# ------- Template string ------
# ---- declare begin
md_declare_tmp = '''
module ${module_name}
#(
    parameter ADDR_WIDTH   = ${ADDR_WIDTH},
    parameter BUS_WIDTH    = ${BUS_WIDTH},
    parameter BLOCK_OFFSET = 'h${BLOCK_OFFSET}
)
(
'''

sw_port_tmp = '''
    //RAM ports
    input                               clk_i        ,
    input                               rst_n_i      ,
    input                               rd_en_i      ,
    input                               wr_en_i      ,
    input           [ADDR_WIDTH-1:0]    address_i    ,
    input           [ BUS_WIDTH-1:0]    wr_data_i    ,
    output                              err_o        ,
    output                              rd_data_vld_o,
    output          [ BUS_WIDTH-1:0]    rd_data_o    
);'''

wire_declare_tmp = '''
    wire                        ${decode_name};
    wire    [BUS_WIDTH -1:0]    ${reg_rd_data}; 
    wire    [ADDR_WIDTH-1:0]    ${offset_name};
'''

assign_tmp = '''
    assign  ${offset_name}= BLOCK_OFFSET + ${addr_width}'h${offset};
    assign  ${decode_name}= (${offset_name_no_space} == address_i[ADDR_WIDTH-1:0]) ? 1'b1 : 1'b0 ;
'''

rd_decode_tmp = '''
    assign  ${reg_rd_data}= ${decode_name} ? {${field_group}} : {BUS_WIDTH{1'b0}};
'''

always_tmp = '''
    always @(posedge clk_i or negedge rst_n_i)
        begin
        if (!rst_n_i) begin
${initial_lines}
        end
        else begin
${cmt_and_assign_lines}
        end       
    end // always end
'''

hw_w_tmp = '''
            if(${hard_wr_vld})begin // hardware write.
                ${field_name}<=  ${hard_wr_i};
            end '''

sw_w_tmp = '''
            ${els}if(${reg_decode} & wr_en_i)begin // software write.
                ${field_name}<= wr_data_i${wr_bits};
            end  
'''

sw_rc_tmp = '''
            ${els}if(${reg_decode} & rd_en_i)begin // software read clear.
                ${field_name}<= {${bits_width}{1'b0}};
            end  
'''

sw_w1c_tmp = '''
            ${els}if(${reg_decode} & wr_en_i & wr_data_i${wr_bits} == {${bits_width}{1'b1}})begin // software write '1' to clear.
                ${field_name}<= {${bits_width}{1'b0}};
            end 
'''


# ---- declare end

class DEBUG(object):
    def __init__(self, level=1):
        self.level = level

    def info(self, log_txt):
        if self.level < 1:
            if isinstance(log_txt, list):
                for txt in log_txt:
                    print(txt)
            else:
                print(log_txt)
        if not isinstance(log_txt, list):
            add_info(log_txt)

    def warning(self, wn_txt):
        if self.level < 3:
            print(wn_txt)
        if not isinstance(wn_txt, list):
            add_info(wn_txt)

    def error(self, err_txt):
        if self.level < 5:
            print("ERR: " + err_txt)


class verilog_writer(object):

    def __init__(self, block: my_Block):
        self.block = block
        self.BUG = DEBUG(4)
        self.port_in_suffix: str = "_i"
        self.port_out_suffix: str = "_o"
        self.indent_1       = 4
        self.indent_name    = 36
        self.addr_width     = 16    # FIXME_ may need calculate from my_block.
        self.bus_width      = 8     # FIXME_ parameterization or auto_calculate ?
        self.block_offset   = re.match("0x(\w+)", self.block.block_offset).group(1)

    def create_v_file(self):
        # verilog encoding utf-8
        verilog_file_name = self.block.block_name + '_regs.v'

        verilog_line = self.file_header()
        verilog_line = verilog_line + self.module_ports()
        verilog_line = verilog_line + self.decode_assign()

        try:
            f = open(verilog_file_name, 'w', encoding='utf-8')
            f.writelines(verilog_line)
            f.close()
        except Exception as e:
            print("-- verilog file operate error!!!")
            print(e)
        else:
            self.BUG.warning("-- verilog file write success!")

    def check_block(self) -> bool:
        for reg in self.block.reg_list:
            # do something
            # 1.addr in increase
            # 2.width in field is correct
            print("yes or no.")
        return True

    def file_header(self) -> list:
        verilog_line = []
        str_cache = '// Copyright(@)2021, Xi\'an Aerosemi Technology Co., Ltd.\n// All rights reserved\n//\n'
        verilog_line.append(str_cache)
        t = time.localtime()
        verilog_line.append('// Create by reg_builder.\n')
        str_cache = "// Create on " + str(t.tm_year) + "/" + str(t.tm_mon) + "/" + str(t.tm_mday) + " " + str(
            t.tm_hour) + ":" + str(t.tm_min) + "\n\n\n"
        verilog_line.append(str_cache)
        self.BUG.info(verilog_line)
        return verilog_line

    def module_ports(self, verilog_line=None):
        if verilog_line is None:
            verilog_line = []
        verilog_line.append('`timescale 1ns/1ps' + "\n" + "\n")
        md_name = self.block.block_name + "_regs"
        str_tmp = Template(md_declare_tmp).substitute(
            {'ADDR_WIDTH': self.addr_width, 'BUS_WIDTH': self.bus_width, 'module_name': md_name, 'BLOCK_OFFSET': self.block_offset})
        verilog_line.append(str_tmp + "\n")

        verilog_line.append("    //HardWare interface\n\n")
        for reg in self.block.reg_list:
            port_prefix = reg.regName + "_"
            for field in reg.bitList:
                self.BUG.warning("module_port->" + field.display())
                field_bits = field.field_cut()
                if field.hard == "ro" or field.hard == "rw":
                    verilog_line.append("    output".ljust(16) + field_bits + (
                            port_prefix + field.bitName + self.port_out_suffix).ljust(44) + "," + "\n")
                if field.hard == "wo" or field.hard == "rw":
                    verilog_line.append(
                        "    input".ljust(16) + field_bits + (port_prefix + field.bitName + self.port_in_suffix).ljust(
                            44) + "," + "\n")
                    verilog_line.append("    input".ljust(16) + "".ljust(8) + (
                            port_prefix + field.bitName + "_vld" + self.port_in_suffix).ljust(44) + "," + "\n")

        verilog_line.append(sw_port_tmp + "\n" + "\n" + "\n" + "\n")
        self.BUG.info(verilog_line)
        return verilog_line

    def decode_assign(self, verilog_line=None):
        if verilog_line is None:
            verilog_line = []

        rd_data_group = []
        for reg in self.block.reg_list:
            self.BUG.warning("decode_assign reg->" + reg.regName + " addr:" + reg.addr)
            verilog_line.append(reg.display())
            verilog_line.append("\n")
            reg_prefix: str = reg.regName + "_"

            reg_rd_data = reg_prefix + "rd_data"
            rd_data_group.append(reg_rd_data)

            decode_name = reg.regName + "_decode_s"
            offset_name = reg.regName + "_offset_s"
            str_tmp = Template(wire_declare_tmp).substitute(
                {'decode_name': decode_name, 'offset_name': offset_name, 'reg_rd_data': reg_rd_data})
            verilog_line.append(str_tmp + "\n")

            field_group = []
            for field in reg.bitList:
                self.BUG.warning("decode_assign->" + field.display())
                field_bits = field.field_cut(20)
                field_name = reg_prefix + field.bitName + "_r"
                str_tmp = '''    reg     ${field_bits}${field_name};'''
                str_tmp = Template(str_tmp).substitute({'field_bits': field_bits, 'field_name': field_name})
                verilog_line.append(str_tmp + "\n")
                if field.is_rsv:
                    field_group.append("{" + field.cul_field_width() + "{1'b0}}")
                else:
                    field_group.append(field_name)

            str_tmp = Template(assign_tmp).substitute(
                {'decode_name': decode_name.ljust(self.indent_name), 'offset_name': offset_name.ljust(self.indent_name),
                 'offset': re.match("0x(\w+)", reg.addr).group(1), 'offset_name_no_space': offset_name, 'addr_width':self.addr_width})
            verilog_line.append(str_tmp)

            for field in reg.bitList:
                if field.hard == "ro" or field.hard == "rw":
                    str_tmp = "    assign  " + (reg_prefix + field.bitName + self.port_out_suffix).ljust(
                        self.indent_name) + "= " + reg_prefix + field.bitName + "_r ;"
                    verilog_line.append(str_tmp + "\n")

            if len(field_group) == 0:
                self.BUG.error("field groups size 0.")
                may_need_exit()
            elif len(field_group) == 1:
                field_group = field_group[0]
            else:
                f_g = ""
                for ff in field_group:
                    f_g = f_g + ff + " ,"
                f_g = f_g.strip(',')
                field_group = f_g

            str_tmp = Template(rd_decode_tmp).substitute(
                {'reg_rd_data': reg_rd_data.ljust(self.indent_name), 'decode_name': decode_name,
                 'field_group': field_group})
            verilog_line.append(str_tmp)

            self.reg_operation(reg, reg_prefix, verilog_line)

        # add rd_data_o 'or'
        str_tmp = "assign rd_data_o       = "
        for item in rd_data_group:
            str_tmp = str_tmp + item.ljust(40) + " |\n        "
        str_tmp = str_tmp.strip()
        str_tmp = str_tmp.strip('|')
        str_tmp = " ".ljust(self.indent_1) + str_tmp + ";\n"
        verilog_line.append("    assign err_o           = rd_en_i & wr_en_i ;" + "\n")
        verilog_line.append("    assign rd_data_vld_o   = rd_en_i           ;" + "\n")
        verilog_line.append(str_tmp + "\n")
        verilog_line.append("endmodule" + "\n")
        self.BUG.info(verilog_line)
        return verilog_line

    def reg_operation(self, reg: my_Reg, reg_prefix: str, verilog_line=None):
        if verilog_line is None:
            verilog_line = []
        # --- reg operation --------
        ini_ln = ""
        for field in reg.bitList:
            self.BUG.warning("reg_operation for1->" + field.display())
            if field.is_rsv:
                continue
            ini_vlue = re.match("0x(\w+)", field.def_value).group(1)
            ini_ln = ini_ln + " ".ljust(3 * self.indent_1) + (reg_prefix + field.bitName + "_r").ljust(
                self.indent_name) + "<= " + field.cul_field_width() + "'h" + ini_vlue + ";\n"
        ass_ln = ""
        for field in reg.bitList:
            self.BUG.warning("reg_operation for2->" + field.display())
            if field.is_rsv:
                continue
            hard_wr_vld = reg_prefix + field.bitName + "_vld" + self.port_in_suffix
            field_name = (reg_prefix + field.bitName + "_r").ljust(self.indent_name)
            hard_wr_i = (reg_prefix + field.bitName + self.port_in_suffix) # .ljust(self.indent_name)
            wr_bits = ("[" + field.bits + "]")   # .ljust(2 * self.indent_1)
            reg_decode = reg_prefix + "decode_s"
            hw_have_w = False
            if field.hard == "wo" or field.hard == "rw":
                hw_have_w = True
                str_tmp = Template(hw_w_tmp).substitute(
                    {'hard_wr_vld': hard_wr_vld, 'field_name': field_name, 'hard_wr_i': hard_wr_i})
                ass_ln = ass_ln + str_tmp
            els_str = "else " if hw_have_w else ""
            if field.soft == "rw" or field.soft == "wo":
                str_tmp = Template(sw_w_tmp).substitute(
                    {'els': els_str, 'field_name': field_name, 'wr_bits': wr_bits, 'reg_decode': reg_decode})
                ass_ln = ass_ln + str_tmp
            elif field.soft == "rc":
                str_tmp = Template(sw_rc_tmp).substitute(
                    {'els': els_str, 'field_name': field_name, 'bits_width': field.cul_field_width(),
                     'reg_decode': reg_decode})
                ass_ln = ass_ln + str_tmp
            elif field.soft == "r/w1c":
                str_tmp = Template(sw_w1c_tmp).substitute(
                    {'els': els_str, 'field_name': field_name, 'bits_width': field.cul_field_width(),
                     'reg_decode': reg_decode, 'wr_bits': wr_bits})
                ass_ln = ass_ln + str_tmp
            else:  # sw: ro, na
                ass_ln = ass_ln
        if ass_ln.strip() == "":
            self.BUG.error("Latch generated!  in reg " + reg.regName + " at " + reg.addr + "\n")
        str_tmp = Template(always_tmp).substitute({'initial_lines': ini_ln.rstrip(), 'cmt_and_assign_lines': ass_ln})
        verilog_line.append(str_tmp + "\n" + "\n" + "\n")
        return verilog_line


if __name__ == '__main__':
    print("hello world")
    v = verilog_writer(my_Block('test_chip_top', '0x100', '0x1000', 'yes', [], 'yes'))
    v.module_ports()
