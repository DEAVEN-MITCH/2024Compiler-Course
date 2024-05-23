
#!/usr/bin/env python3

import re

from . import common_parser

# 递归打印节点信息的方法，在调试时可以使用
# print_node_recursive(node)
# 递归打印节点信息

def print_node_recursive(node, depth=0):
    # 打印当前节点信息
    print("  " * depth + f"Node: {node.type}")
    # 遍历当前节点的子节点并递归打印
    for child in node.children:
        print_node_recursive(child, depth + 1)

class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type == "comment"

    # 仿照java_parser对应函数，两种语言是一样的（大概）
    def is_identifier(self, node):
        return node.type == "identifier"
    
    def string_literal(self, node, statements, replacement):
        replacement = []
        for child in node.named_children:
            self.parse(child, statements, replacement)

        ret = self.read_node_text(node)
        if replacement:
            for r in replacement:
                (expr, value) = r
                ret = ret.replace(self.read_node_text(expr), value)
                
        parts = re.split(r'(\\x[0-9A-Fa-f]+)', ret)

        ret = ''.join(chr(int(hex_value[2:], 16)) if hex_value.startswith("\\x") else hex_value for hex_value in parts)
        return self.escape_string(ret)

    def concatenated_string(self, node, statements, replacement):
        replacement = []
        ret = ""

        for child in node.named_children:
            parsed = self.parse(child, statements, replacement)
            ret += parsed[1:-1]

        if replacement:
            for r in replacement:
                (expr, value) = r
                ret = ret.replace(self.read_node_text(expr), value)

        ret = self.handle_hex_string(ret)

        return self.escape_string(ret)

    # 数字常量
    def regular_number_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        value = self.common_eval(value)
        return str(value)
    
    def regular_literal(self, node, statements, replacement):
        return self.read_node_text(node)
    
    def char_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        return "'%s'" % value
    
    def is_constant_literal(self, node):
        return node.type in [
            "number_literal",
            "true",
            "false",
            "char_literal",
            "null_literal",
            "string_literal",
            "storage_class_specifier",
            "type_qualifier",
            "ms_call_modifier",
        ]

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "number_literal" : self.regular_number_literal,
            "true": self.regular_literal,
            "false": self.regular_literal,
            "char_literal": self.char_literal,
            "null_literal": self.regular_literal,
            "identifier": self.regular_literal,
            "field_identifier": self.regular_literal,
            "string_literal": self.string_literal,
            "concatenated_string": self.concatenated_string,
            "storage_class_specifier": self.regular_literal,
            "type_qualifier": self.regular_literal,
            "ms_call_modifier": self.regular_literal,
            "ms_pointer_modifier": self.regular_literal,
        }

        return LITERAL_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)


    # 辅助解析成员引用
    def parse_field(self, node, statements):
        # argument为 _expression，递归解析
        myobject = self.find_child_by_field(node, "argument")
        shadow_object = self.parse(myobject, statements)
        # field为 identifier，直接读取
        field = self.find_child_by_field(node, "field")
        shadow_field = self.read_node_text(field)

        return (shadow_object, shadow_field)
    
    def field(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        shadow_object, shadow_field = self.parse_field(node, statements)
        statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": shadow_field}})
        return tmp_var
    
    # 辅助解析数组取值
    def parse_subscript(self, node, statements):
        # 对象与索引均为 _expression
        array = self.find_child_by_field(node, "argument")
        shadow_array = self.parse(array, statements)
        index = self.find_child_by_field(node, "index")
        shadow_index = self.parse(index, statements)

        return (shadow_array, shadow_index)    

    def subscript(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        shadow_array, shadow_index = self.parse_subscript(node, statements)
        statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index}})
        return tmp_var
    
    # 指针操作，包括取值和取址
    def parse_pointer(self, node, statements):
        operator = self.find_child_by_field(node, "operator")
        argument = self.find_child_by_field(node, "argument")
        shadow_object = self.parse(argument, statements)
        return (operator, shadow_object)
    
    def pointer(self, node, statements):
        tmp_var = self.tmp_variable(statements)      
        operator, shadow_object = self.parse_pointer(node, statements)

        # 取址与取值需分开处理
        if(self.read_node_text(operator) == "&"):
            statements.append({"addr_of": {"target": tmp_var, "source": shadow_object}})
        else:
            statements.append({"mem_read": {"target": tmp_var, "address": shadow_object}})
        return tmp_var
        
    # call_expresssion也可以作左值
    def call_expression(self, node, statements):
        # C 函数调用的 function 字段不止可以是标识符
        func = self.find_child_by_field(node, "function")
        shadow_name = self.parse(func, statements)

        # 参数列表
        args = self.find_child_by_field(node, "arguments")
        args_list = []

        if args.named_child_count > 0:
            for child in args.named_children:
                if self.is_comment(child):
                    continue

                shadow_variable = self.parse(child, statements)
                if shadow_variable:
                    args_list.append(shadow_variable)

        # 返回值暂存
        tmp_return = self.tmp_variable(statements)
        statements.append({"call_stmt": {"target": tmp_return, "name": shadow_name, "args": args_list}})

        # "@return" 标识符
        return self.global_return()
    
    # 赋值语句的转换, 基于java_parser对应内容，用c_grammar对应定义扩展
    # 总是return 最后一步的target
    def assignment_expression(self, node, statements:list):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        operator = self.find_child_by_field(node, "operator")
        # 将等号符号去掉，这样复合赋值就会将复合的操作暴露出来
        shadow_operator = self.read_node_text(operator).replace("=", "")

        # 后序遍历，先parse右孩子
        shadow_right = self.parse(right, statements)

        # 0. 先拆括号
        while left.type == "parenthesized_expression":
            assert left.named_child_count == 1
            left = left.named_children[0]
            
        # 1. 如果左边是成员引用且为复合赋值，那A.b+=c就额外加一层
        # field_read %v1, A, b
        # assignment %v2, %v1, c
        # field_write A, b, %v2
          
        if left.type == "field_expression":
            shadow_object, field = self.parse_field(left, statements)

            # 如果只是单纯的赋值，不必将A.b读到临时变量
            # field_write A, b, c; 即可
            if not shadow_operator:
                statements.append(
                    {"field_write": {"receiver_object": shadow_object, "field": field, "source": shadow_right}})
                return shadow_right

            # 复合赋值
            tmp_var = self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": field, }})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"field_write": {"receiver_object": shadow_object, "field": field, "source": tmp_var2}})

            return tmp_var2

        # 2. 如果左边是数组引用，那就不是赋值语句，而是数组写入
        if left.type == "subscript_expression":
            shadow_array, shadow_index = self.parse_subscript(left, statements)

            if not shadow_operator:
                statements.append(
                    {"array_write": {"array": shadow_array, "index": shadow_index, "source": shadow_right}})
                return shadow_right

            tmp_var = self.tmp_variable(statements)
            statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index, }})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": tmp_var2}})

            return tmp_var2

        # 3. 指针取值
        if left.type == "pointer_expression":
            # 理应确保这里的左值只可能是取值而不是取址
            operator, shadow_object = self.parse_pointer(left, statements)
            # assert self.read_node_text(operator) == "*"

            if not shadow_operator:
                statements.append({"mem_write": {"address": shadow_object, "source": shadow_right}})
                return shadow_right
            
            tmp_var = self.tmp_variable(statements)
            statements.append({"mem_read": {"target": tmp_var, "address": shadow_object}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"mem_write": {"address": shadow_object, "source": tmp_var2}})

            return tmp_var2
        
        # 4. 函数调用
        if left.type == "call_expression":
            return_obj = self.call_expression(left, statements)
            if not shadow_operator:
                statements.append({"assign_stmt": {"target": return_obj, "operand": shadow_right}})
            else:
                statements.append({"assign_stmt": {"target": return_obj, "operator": shadow_operator,
                                               "operand": return_obj, "operand2": shadow_right}})
            return return_obj
        

        # 5. 最后一种, identifier，返回左值，比如a=b=3，那么b=3就应该返回b
        shadow_left = self.read_node_text(left)
        # print(shadow_right)
        if not shadow_operator:
            statements.append({"assign_stmt": {"target": shadow_left, "operand": shadow_right}})
        else:
            statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                               "operand": shadow_left, "operand2": shadow_right}})
        return shadow_left
    

    # ~a 翻译成 assign_stmt %v0, ~, a
    def unary_expression(self, node, statements):
        operand = self.find_child_by_field(node, "argument")
        shadow_operand = self.parse(operand, statements)
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)

        tmp_var = self.tmp_variable(statements)

        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_operand}})
        return tmp_var
    
    # 与普通的unary不一样，自增自减会改变原值，应当向assignment一样分情况讨论!
    def update_expression(self, node, statements):
        operand = self.find_child_by_field(node, "argument")
        # shadow_operand = self.parse(operand, statements)
        operator = self.find_child_by_field(node, "operator")
        # ++就是+1,--就是-1，取出隐藏的运算符
        # TODO：这里有一个bug，样例为(a+b)*c;可是tree-sitter却将其识别为update表达式，很奇怪
        if self.read_node_text(operator) == "":
            return self.parse(operand, statements)
        shadow_operator = self.read_node_text(operator)[0]
        suffix_update =  operand.start_point[1] < operator.start_point[1]

        # 0. 先拆括号，例子就是b=(a[0])++
        while operand.type == "parenthesized_expression":
            # assert operand.named_child_count == 1
            operand = operand.named_children[0]
        
        # 不管哪种情况，都要整个临时变量来先读出数据
        tmp_var = self.tmp_variable(statements)

        # 1. 拆完后发现是域引用
        if operand.type == "field_expression":
            shadow_object, field = self.parse_field(operand, statements)

            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": field}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append(
                {"assign_stmt": {"target": tmp_var2, "operator": shadow_operator, "operand": tmp_var, "operand2": "1"}})
            statements.append({"field_write": {"receiver_object": shadow_object, "field": field, "source": tmp_var2}})

            # 后缀则返回自增前的值
            if suffix_update:
                return tmp_var
            return tmp_var2
        
        # 2. 拆完后发现是数组引用
        if operand.type == "subscript_expression":
            shadow_array, shadow_index = self.parse_subscript(operand, statements)

            statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append(
                {"assign_stmt": {"target": tmp_var2, "operator": shadow_operator, "operand": tmp_var, "operand2": "1"}})
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": tmp_var2}})

            if suffix_update:
                return tmp_var
            return tmp_var2
        
        # 3. 拆完发现是指针引用，注意语法规定只能是取值而不是取址
        if operand.type == "pointer_expression":
            operator, shadow_object = self.parse_pointer(operand, statements)
            # assert self.read_node_text(operator) == "*"
            
            statements.append({"mem_read": {"target": tmp_var, "address": shadow_object}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append(
                {"assign_stmt": {"target": tmp_var2, "operator": shadow_operator, "operand": tmp_var, "operand2": "1"}})
            statements.append({"mem_write": {"address": shadow_object, "source": tmp_var2}})

            if suffix_update:
                return tmp_var
            return tmp_var2


        # 其他情况：将operand取出到%v1，存到临时变量%v0，%v1自增，据情况返回
        shadow_operand = self.parse(operand, statements)
        statements.append({"assign_stmt":
                            {"target": tmp_var, "operand": shadow_operand}})
        statements.append({"assign_stmt":
                                   {"target": shadow_operand, "operator": shadow_operator,
                                    "operand": shadow_operand, "operand2": "1"}})
        # 前后缀自增返回的不同！
        if suffix_update:
            return tmp_var
        return shadow_operand

    # 将强制类型转换认为是赋值语句，操作数为目标类型，操作符为cast操作
    def cast_expression(self, node, statements):
        value = self.find_child_by_field(node, "value")
        shadow_value = self.parse(value, statements)

        types = self.find_children_by_field(node, "type")
        for t in types:
            statements.append(
                {"assign_stmt": {"target": shadow_value, "operator": "cast", "operand": self.read_node_text(t)}})

        return shadow_value


    # offset_height = offsetof(struct Person, height);
    def offsetof_expression(self, node, statements):
        type_discriptor = self.find_child_by_field(node, "type")
        type_discriptor_name = self.read_node_text(type_discriptor)
        # 两个域，一个是type，一个是field
        field = self.find_child_by_field(node, "member")
        field_discriptor_name = self.read_node_text(field)
        
        tmp_return = self.tmp_variable(statements)

        statements.append({"offsetof": {"target": tmp_return, "struct_name": type_discriptor_name, "field": field_discriptor_name}})
        return self.global_return()

    def compound_literal_expression(self, node, statements):
        # 和offsetof表达式类似，也是两个域，一个是type，一个是value
        type_discriptor = self.find_child_by_field(node, "type")
        type_discriptor_name = self.read_node_text(type_discriptor)

        field = self.find_child_by_field(node, "value")
        field_discriptor_name = self.read_node_text(field)

        tmp_return = self.tmp_variable(statements)
        
        statements.append({"compound_literal": {"target": tmp_return, "struct_name": type_discriptor_name, "field": field_discriptor_name}})
        return self.global_return()

    def generic_expression(self, node, statements):
        type_list = []
        expr_list = []

        args_identifier = self.find_children_by_type(node,"_expression")

        children = node.named_children
        variable_descriptor = self.parse(children[0], statements)

        type_list = [self.read_node_text(children[i]) for i in range(len(children)) if i % 2 != 0]
        expr_list = [self.parse(children[i], statements) for i in range(len(children)) if i % 2 == 0 and i != 0]

        # 创建一个空字典来存储所有的type和expr
        generic_expr_dict = {"variable": variable_descriptor, "expressions": []}

        # 将type_list和expr_list中的元素一一对应地添加到generic_expr_dict中
        for type_, expr in zip(type_list, expr_list):
            generic_expr_dict["expressions"].append({"type": type_, "expr": expr})

        # 将整个generic_expr_dict添加到statements中
        statements.append({"generic_expression": generic_expr_dict})
        return self.global_return()

    def sizeof_expression(self, node, statements):
        #和offsetof表达式类似，也是两个域，一个是type，一个是value
        type_descriptor = self.find_child_by_field(node, "type")
        value_descriptor = self.find_child_by_field(node, "value")

        if type_descriptor:
            shadow_name = self.read_node_text(type_descriptor)
            tmp_return = self.tmp_variable(statements)

            statements.append({"sizeof": {"target": tmp_return, "type": shadow_name}})
            return tmp_return
        elif value_descriptor:
            shadow_name = self.parse(value_descriptor, statements)
            tmp_return = self.tmp_variable(statements)

            statements.append({"sizeof": {"target": tmp_return, "value": shadow_name}})
            return tmp_return

        return self.global_return()

    def alignof_expression(self, node, statements):
        type_descriptor = self.find_child_by_field(node, "type")
        type_descriptor_name = self.read_node_text(type_descriptor)

        tmp_return = self.tmp_variable(statements)

        statements.append({"alignof": {"target": tmp_return, "type_name": type_descriptor_name}})
        return self.global_return()

    def conditional_expression(self, node, statements):
        # 条件表达式（三元运算），本来打算用if语句实现，但是感觉if语句无法突出condition consequence alternative的关系
        condition_discriptor = self.find_child_by_field(node, "condition")
        true_discriptor = self.find_child_by_field(node, "consequence")
        false_discriptor = self.find_child_by_field(node, "alternative")

        shadow_condition = self.parse(condition_discriptor, statements)
        shadow_true = self.parse(true_discriptor, statements)
        shadow_false = self.parse(false_discriptor, statements)

        tmp_return = self.tmp_variable(statements)
        
        statements.append({"conditional": {"target": tmp_return, "condition": shadow_condition, "consequence": shadow_true, "alternative": shadow_false}})
        return self.global_return()
    
    def binary_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        operator = self.find_child_by_field(node, "operator")

        shadow_operator = self.read_node_text(operator)

        shadow_left = self.parse(left, statements)
        shadow_right = self.parse(right, statements)

        tmp_var = self.tmp_variable(statements)
        statements.append({
            "assign_stmt": {
                "target": tmp_var, 
                "operator": shadow_operator, 
                "operand": shadow_left,
                "operand2": shadow_right
            }})

        return tmp_var
    
    def gnu_asm_expression(self, node, statements):
        
        def get_list(target):
            ret = []
            if target:
                if target.named_child_count > 0:
                    for child in target.children:
                        shadow_variable = self.parse(child, statements)
                        if shadow_variable:
                            ret.append(self.read_node_text(child))
            return ret
        
        assembly_code = self.find_child_by_field(node, "assembly_code")
        shadow_assembly_code = self.parse(assembly_code)

        output_operands = self.find_child_by_field(node, "output_operands")
        output_operands_list = get_list(output_operands)
        
        input_operands = self.find_child_by_field(node, "input_operands")
        input_operands_list = get_list(input_operands)
        
        clobbers = self.find_child_by_field(node, "clobbers")
        registers_list = get_list(clobbers)
                    
        goto_labels = self.find_child_by_field(node, "goto_labels")
        labels_list = get_list(goto_labels)
        
        statements.append({
            "gnu_asm": {
                "assembly_code": shadow_assembly_code, 
                "output_operands": output_operands_list, 
                "input_operands": input_operands_list, 
                "registers": registers_list,
                "labels": labels_list
            }})
        
        return 0 
    
    def parenthesized_expression(self, node, statements):
        return self.parse(node.children[1], statements)


    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "assignment_expression": self.assignment_expression,
            "subscript_expression": self.subscript,
            "field_expression": self.field,
            "call_expression": self.call_expression,
            "unary_expression": self.unary_expression,
            "update_expression": self.update_expression,
            "cast_expression": self.cast_expression,
            "pointer_expression": self.pointer,

            "offsetof_expression": self.offsetof_expression,
            "generic_expression": self.generic_expression,
            "conditional_expression": self.conditional_expression,
            "compound_literal_expression": self.compound_literal_expression,
            "sizeof_expression": self.sizeof_expression,
            "alignof_expression": self.alignof_expression,

            "gnu_asm_expression": self.gnu_asm_expression,
            "binary_expression": self.binary_expression,
            "parenthesized_expression": self.parenthesized_expression,
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    # 第四次实验：statements
    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            "labeled_statement": self.label_statement,
            "attributed_statement": self.attributed_statement,
            # "compound_statement",
            # "expression_statement",

            "do_statement": self.do_statement,
            "while_statement": self.while_statement,
            "for_statement": self.for_statement,
            "return_statement": self.return_statement,
            "break_statement": self.break_statement,
            "continue_statement": self.continue_statement,
            "goto_statement": self.goto_statement,
            "if_statement": self.if_statement,

            "switch_statement": self.switch_statement,
            "case_statement": self.case_statement,
            "seh_try_statement": self.seh_try_statement,
            "seh_leave_statement": self.seh_leave_statement,
        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)


    # label statement
    def label_statement(self, node, statements):
        # label_statement = "label" * statement
        name = self.find_child_by_field(node, "label")

        shadow_name = self.parse(name, statements)
        statements.append({"label_stmt": {"name": shadow_name}})

        if node.named_child_count > 1:
            stmt = node.named_children[1]
            self.parse(stmt, statements)

    # attribute_statement，C11之后引入的新属性，用于向编译器提供某些额外信息，
    # 这些信息可以帮助编译器优化代码或改变代码的行为。
    # 由declaration和_statement组成
    def attributed_statement(self, node, statements):
        # attributed_statement = "attribute_declaration"* statement
        attr_decls = []
        for child in node.named_children:
            if child.type == "attribute_declaration":
                self.parse(child, attr_decls)
            else: # attr_decl到头之后是statememt，先把attr_decl放进去
                statements.append({"attributed_stmt": attr_decls})
                self.parse(child, statements)

        
    # 一个attribute_decl还可以有多个attribute
    def parse_attribute(self, node, statements):
        prefix = self.parse(self.find_child_by_field(node, "prefix"))
        name = self.parse(self.find_child_by_field(node, "name"))
        argument_list = node.named_children[-1]
        # args是可选项
        if argument_list.type == "identifier":
            return prefix, name, []
        
        args = []
        if argument_list.named_child_count > 0:
            for arg in argument_list.named_children:
                if self.is_comment(arg):
                    continue

                shadow_arg = self.parse(arg, statements)
                if shadow_arg:
                    args.append(shadow_arg)
        return prefix, name, args
        

    
    def do_statement(self, node, statements):
        # do while 语句
        # do_statement -> "do" statement "while" "(" expression ")" ";"
        do_body = self.find_child_by_field(node, "body")
        do_condition = self.find_child_by_field(node, "condition")
        shadow_condition = self.parse(do_condition, statements)

        body = []
        for child in do_body.named_children:
            self.parse(child, body)

        statements.append({"do_stmt": {"body": body, "condition": shadow_condition}})
        return 0

    def while_statement(self, node, statements):
        # while 语句
        # while_statement -> "while" "(" expression ")" statement
        while_condition = self.find_child_by_field(node, "condition")
        while_body = self.find_child_by_field(node, "body")
        shadow_condition = self.parse(while_condition, statements)

        body = []
        for child in while_body.named_children:
            self.parse(child, body)


        statements.append({"while_stmt": {"condition": shadow_condition, "body": body}})
        return 0

    def for_statement(self, node, statements):
        # for 语句
        # for_statement -> "for" "(" expression? ";" expression? ";" expression? ")" statement
        for_init = self.find_child_by_field(node, "initializer")
        for_condition = self.find_child_by_field(node, "condition")
        for_update = self.find_child_by_field(node, "update")
        for_body = self.find_child_by_field(node, "body")
        shadow_init = self.parse(for_init, statements)
        shadow_condition = self.parse(for_condition, statements)
        shadow_update = self.parse(for_update, statements)

        body = []
        for child in for_body.named_children:
            self.parse(child, body)

        statements.append({"for_stmt": {"init_body": shadow_init, "condition": shadow_condition, "update_body": shadow_update, "body": body}})
        return 0


    def return_statement(self, node, statements):
        # print_node_recursive(node)
        # return 语句
        # return_statement -> "return" expression? ";"
        return_value = node.named_children[0]
        shadow_value = self.parse(return_value, statements)
        print("statements:", statements)
        statements.append({"return_stmt": {"value": shadow_value}})
        return 0

    def break_statement(self, node, statements):
        # break 语句
        statements.append({"break_stmt": {}})
        return 0
    
    def continue_statement(self, node, statements):
        # continue 语句
        statements.append({"continue_stmt": {}})
        return 0
    
    def goto_statement(self, node, statements):
        # goto 语句
        # goto_statement -> "goto" identifier ";"
        label = self.find_child_by_field(node, "label")
        shadow_label = self.read_node_text(label)

        statements.append({"goto_stmt": {"target": shadow_label}})
        return 0
    
    def if_statement(self, node, statements):
        # print_node_recursive(node)
        # if 语句
        # if_statement -> "if" "(" expression ")" statement ("else" statement)?
        if_condition = self.find_child_by_field(node, "condition")
        if_consequence = self.find_child_by_field(node, "consequence")
        if_alternative = self.find_child_by_field(node, "alternative")
        shadow_condition = self.parse(if_condition, statements)

        consequence = []
        for child in if_consequence.named_children:
            self.parse(child, consequence)

        else_body = []
        for child in if_alternative.named_children:
            self.parse(child, else_body)

        statements.append({"if_stmt": {"condition": shadow_condition, "then_body": consequence, "else_body": else_body}})
        return 0    


    def switch_statement(self, node, statements):
        # switch_statement -> "switch" "(" expression ")" "{" ( "case" value ":" statement )* ( "default" ":" statement )? "}"
        condition = self.find_child_by_field(node, "condition")
        shadow_condition = self.parse(condition, statements)
        
        switch_block = self.find_child_by_field(node, "body")
        body = []
        for child in switch_block.named_children:
            self.parse(child, body)
        
        statements.append({"switch_stmt": {"condition": shadow_condition, "body": body}})
        
        return 0
    
    def case_statement(self, node, statements):
        # case_statement = "case" "(" expression ")" statement ("default" statement)?
        
        body = []
        if self.read_node_text(node.children[0]) == "default":
            for child in node.named_children:
                self.parse(child, body)
            statements.append({"default_stmt": {"body": body}})
        else:
            value = self.find_child_by_field(node, "value")
            shadow_value = self.parse(value, statements)
            for child in node.named_children[1:]:
                self.parse(child, body)
            statements.append({"case_stmt": {"condition": shadow_value, "body": body}})
        
        return 0
    
    def seh_try_statement(self, node, statements):
        try_op = {}
        
        body = self.find_child_by_field(node, "body")
        try_body = []
        self.parse(body, try_body)
        try_op["body"] = try_body
        
        except_clause = self.find_child_by_type(node, "seh_except_clause")
        if except_clause:
            filter = self.find_child_by_field(except_clause, "filter")
            shadow_filter = self.parse(filter, statements)
            body = self.find_child_by_field(except_clause, "body")
            shadow_body = []
            self.parse(body, shadow_body)
            try_op["except_clause"] = [{"filter": shadow_filter, "body": shadow_body}]
        else:
            finally_clause = self.find_child_by_type(node, "seh_finally_clause")
            body = self.find_child_by_field(finally_clause, "body")
            shadow_body = []
            self.parse(body, shadow_body)
            try_op["finally_clause"] = [{"body": shadow_body}]
            
        statements.append({"try_stmt": try_op})
        
        return 0
    
    def seh_leave_statement(self, node, statements):
        statements.append({"leave_stmt": {}})
        return 0
    

    # TODO: 第五次实验：declaration
    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
            "declaration": self.handle_declaration,
            "field_declaration": self.handle_declaration,
            "attribute_declaration" : self.attribute_declaration,
            "attribute_specifier": self.attribute_specifier,
            "ms_declspec_modifier": self.ms_declspec_modifier,
            "function_definition": self.function_definition,
            "parameter_declaration": self.parameter_declaration,

            "struct_specifier": self.struct_specifier,
            "union_specifier": self.union_specifier,
            "enum_specifier": self.enum_specifier,
            "enumerator_list": self.enumerator_list,
            "enumerator": self.enumerator,
            "macro_type_specifier": self.macro_type_specifier,
            "sized_type_specifier": self.sized_type_specifier,
            "primitive_type": self.primitive_type,
            "type_identifier": self.primitive_type,
            
            "init_declarator": self.init_declarator,
            "attributed_declarator": self.attributed_declarator,
            "pointer_declarator": self.pointer_declarator,
            "function_declarator": self.function_declarator,
            "array_declarator": self.array_declarator,
            "parenthesized_declarator": self.parenthesized_declarator,
            "ms_based_modifier": self.ms_based_modifier,
            "initializer_list": self.initializer_list,
            "initializer_pair": self.initializer_pair,
        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def init_declarator(self, node, statements):
        ret = {}
        
        declarator = self.find_child_by_field(node, "declarator")
        if declarator.type == "identifier":
            ret["declarator"] = {"name": self.parse(declarator)}
        else:
            ret[declarator.type] = self.parse(declarator, statements)
        
        value = self.find_child_by_field(node, "value")
        ret["value"] = self.parse(value, statements)
        
        return [ret]
        
    def attributed_declarator(self, node, statements):
        ret = {}
        
        declarator = node.children[0]
        if declarator.type == "identifier":
            ret["name"] = self.parse(declarator, statements)
        else:
            ret[declarator.type] = self.parse(declarator, statements)
                
        ret["attribute_declarations"] = []
        for child in node.children[1:]:
            self.parse(child, ret["attribute_declarations"])
                
        return [ret]

    def pointer_declarator(self, node, statements):
        ret = {}
        for child in node.children:
            if child.type == "ms_based_modifier":
                ret["ms_based_modifier"] = self.parse(child, statements)
            elif (child.type == "ms_pointer_modifier") | (child.type == "type_qualifier"):
                if child.type not in ret.keys():
                    ret[child.type] = []
                ret[child.type].append(self.parse(child, statements))
        
        declarator = self.find_child_by_field(node, "declarator")     
        if declarator.type == "identifier":
            ret["name"] = self.parse(declarator, statements)
        else:
            ret[declarator.type] = self.parse(declarator, statements)
           
        return [ret]

    def function_declarator(self, node, statements):
        ret = {}
        declarator = self.find_child_by_field(node, "declarator")     
        if declarator.type == "identifier":
            ret["name"] = self.parse(declarator, statements)
        else:
            ret[declarator.type] = self.parse(declarator, statements)
        
        parameter_list = self.find_child_by_field(node, "parameters")     
        ret["parameters"] = self.parse_parameters(parameter_list, statements)
        
        if len(node.named_children) <= 2:
            return [ret]
        
        begin = 2
        gnu_asm_expression = node.named_children[begin]
        if gnu_asm_expression:
            begin = 3
            ret["gnu_asm_expression"] = []
            self.parse(gnu_asm_expression, ret["gnu_asm_expression"])
        
        ret["attribute"] = []
        for child in node.named_children[begin:]:
            tmp = []
            r = self.parse(child, tmp)
            if tmp:
                ret["attribute"].append(tmp)
            else:
                ret["attribute"].append(r)
        # print(ret)
        return [ret]
    
    def parse_parameters(self, parameter_list, statements):
        parameters = []
        for child in parameter_list.named_children:
            if child.type == "parameter_declaration":
                tmp = []
                self.parse(child, parameters)
                # parameters.append(tmp)
            elif child.type == "variadic_parameter":
                parameters.append({"variadic_parameter": "..."})
        return parameters
    
    def array_declarator(self, node, statements):
        ret = {}

        declarator = self.find_child_by_field(node, "declarator")
        ret["name"] = self.parse(declarator, statements)
        
        for child in node.named_children:
            if child.type == "type_qualifier":
                if "type_qualifier" not in ret.keys():
                    ret["type_qualifier"] = []
                ret["type_qualifier"].append(self.parse(child, statements))

        size = self.find_child_by_field(node, "size")
        if size:
            ret["size"] = self.parse(size, statements)

        return [ret]
    
    def parenthesized_declarator(self, node, statements):
        ret = {}
        if node.named_children[0].type == "ms_call_modifier":
            ret["ms_call_modifier"] = self.parse(node.named_children[0], statements)
            declarator = node.named_children[1]
        else:
            declarator = node.named_children[0]
        
        if declarator.type == "identifier":
            ret["name"] = self.parse(declarator, statements)
        else:
            ret[declarator.type] = self.parse(declarator, statements)
        
        return [ret]
    
    def initializer_list(self, node, statements):
        initializers = []
        for child in node.named_children:
            initializers.append(self.parse(child, statements))
        
        return initializers
    
    def initializer_pair(self, node, statements):
        ret = {}
        
        designator = self.find_child_by_field(node, "designator")
        if designator.type == "subscript_designator":
            ret["index"] = self.parse(designator.named_children[0], statements)
        elif designator.type == "subscript_range_designator":
            start = self.find_child_by_field(designator, "start")
            end = self.find_child_by_field(designator, "end")
            ret["index_start"] = self.parse(start, statements)
            ret["index_end"] = self.parse(end, statements)
        elif designator.type == "field_designator":
            ret["field"] = self.parse(designator.named_children[0], statements)
        elif designator.type == "field_identifier":
            ret["field"] = self.parse(designator, statements)
    
        value = self.find_child_by_field(node, "value")
        ret["value"] = self.parse(value, statements)
        
        return ret
        
    def ms_based_modifier(self, node, statements):
        args = self.parse_args(node.named_children[0], statements)
        return {"args": args}
    
    # 取出单个specifier中的类型名，好在一个declaration只有一个元素
    # 原本格式为[{'primitive_type': {'name': 'int'}}]，提取int
    def peel_type(self, specifier):
        type_value = ""
        for value in specifier.values():
            type_value = value['name']
        return type_value

    def peel_declarator(self, declarator_):
        if self.is_literal(declarator_):
            return self.read_node_text(declarator_)
        else:
            return self.parse(declarator_)[0]["name"]

    # 这里的declaration对标variable_and_constand_declaration
    def handle_declaration(self, node, statements):
        specifiers = []
        
        self.parse(node.named_children[0], specifiers)
        
        shadow_type = None
        # print("specifiers:", specifiers)
        if len(specifiers) != 0 and ('primitive_type' in specifiers[0] or 'sized_type_specifier' in specifiers[0]):
            shadow_type = self.peel_type(specifiers[0])
        else:
            shadow_type = specifiers

        has_init = False
        # declarators = []
        declarator_ = None
        # 这里需要init_decl的协助，在init部分完成后，需要改写为decl+assign
        for child in node.named_children[1:]:
            if self.is_literal(child):
                has_init = False
                declarator_ = self.read_node_text(child)
                # declarators.append(self.read_node_text(child))
            elif child.type == "init_declarator":
                has_init = True
                declarator_ = self.find_child_by_field(child, "declarator")

                declarator_ = self.peel_declarator(declarator_)
                # declarators.append(declarator_)
                value = self.find_child_by_field(child, "value")
                # 对于数组，先构建，再赋值
                if value.type == "initializer_list":
                    tmp_var = self.tmp_variable(statements)
                    statements.append({"new_array": {"type": declarator_, "target": tmp_var}})

                    if value.named_child_count > 0:
                        index = 0
                        for item in value.named_children:
                            if self.is_comment(item):
                                continue

                            source = self.parse(item, statements)
                            statements.append({"array_write": {"array": tmp_var, "index": str(index), "source": source}})
                            index += 1
                    shadow_value = tmp_var
                else:
                    shadow_value = self.parse(value, statements)                    
            else:
                has_init = False
                declarator_ = self.parse(child, statements)
                # declarators.append(self.parse(child, statements))

            statements.append({"variable_decl": {"attr": [], "data_type": shadow_type, "name": declarator_}})
            if has_init:
                statements.append({"assign_stmt": {"target": declarator_, "operand": shadow_value}})


        

    def attribute_declaration(self, node, statements):
        attributes = []
        for attribute in node.named_children:
            prefix, name, args = self.parse_attribute(attribute, statements)
            attributes.append({"attribute":{"prefix": prefix, "name": name, "args": args}})
        statements.append({"attribute_declaration": attributes})

    def parse_args(self, argument_list, statements):
        args = []
        if argument_list.named_child_count > 0:
            for arg in argument_list.named_children:
                if self.is_comment(arg):
                    continue

                shadow_arg = self.parse(arg, statements)
                if shadow_arg:
                    args.append(shadow_arg)
        return args

    def attribute_specifier(self, node, statements):
        if node.named_child_count > 0:
            args = self.parse_args(node.named_children[0], statements)
            statements.append({"attribute_specifier":{"args": args}})
 
    # 有且只有一个子节点identifier
    def ms_declspec_modifier(self, node, statements):
        statements.append({"ms_declspec_modifier": self.parse(node.named_children[0])})

    def parameter_declaration(self, node, statements):
        # 有可能只有类型而没有名字，如函数声明
        specifiers = []
        self.parse(node.named_children[0], specifiers)
        # 取出specifiers中的类型名，助教要求，好在一个declaration只有一个元素
        # 原本格式为[{'primitive_type': {'name': 'int'}}]，提取int
        type_value = self.peel_type(specifiers[0])

        if node.named_child_count > 1:
            name = self.read_node_text(node.named_children[1])
            statements.append({"parameter_decl": {
                "attr": [],
                "data_type": type_value,
                "name": name
            }})
        else:
            statements.append({"parameter_decl": {
                "attr": [],
                "data_type": type_value,
                "name": ""
            }})


    def function_definition(self, node, statements):
        declarator = self.find_child_by_field(node, "declarator")
        shadow_declarator = []
        return_type = ""
        shadow_body = []
        shadow_modifier_1 = []
        shadow_modifier_2 = []
        modifier_1or2 = True
        specifier = []
        shadow_name = None
        if node.named_child_count > 0:
            for child in node.named_children:
                if child.type == "ms_call_modifier":
                    if modifier_1or2:
                        self.parse(child, shadow_modifier_1)
                        modifier_1or2 = False
                    else:
                        self.parse(child, shadow_modifier_2)
                # 函数名与参数列表
                elif child == declarator:   
                    declarator = self.parse(child, statements=statements)
                    shadow_declarator = declarator[0]["parameters"]
                    shadow_name = declarator[0]["name"]

                elif child.type == "body":
                    shadow_body = []
                    self.parse(child, statements=shadow_body)
                else:
                    # 这里specifier就是返回值类型，取出
                    self.parse(child, specifier)
                    # print("返回值：", specifier)
                    for value in specifier[0].values():
                        return_type = value["name"]
                

        statements.append({"function_definition": {
            "modifier1": shadow_modifier_1, 
            "data_type": return_type,
            "modifier2": shadow_modifier_2, 
            "name": shadow_name,
            "parameters": shadow_declarator,
            "body": shadow_body
        }})
        


    def struct_specifier(self, node, statements):
        # 初始化结构体声明的字典
        struct_declaration = {
            "attribute_start": [],
            "attribute_end": [],
            "ms_declspec": [],
            "name": None,
            "body": []
        }
        
        # 处理开头的 attribute_specifier
        attribute_start_node = self.find_child_by_type(node, "attribute_specifier")
        if attribute_start_node:
            self.parse(attribute_start_node, struct_declaration["attribute_start"])
        
        # 处理 ms_declspec_modifier，如果存在则解析并添加到结构体声明中
        ms_declspec_modifier_node = self.find_child_by_type(node, "ms_declspec_modifier")
        if ms_declspec_modifier_node:
            self.parse(ms_declspec_modifier_node, struct_declaration["ms_declspec"])
        
        # 处理结构体名称
        name_node = self.find_child_by_field(node, "name")
        if name_node:
            struct_declaration["name"] = self.read_node_text(name_node)
        
        # 处理结构体（body）
        body_node = self.find_child_by_field(node, "body")
        if body_node:
            for child in body_node.named_children:
                self.parse(child, struct_declaration["body"])
        
        # 处理结尾的 attribute_specifier
        attribute_end_nodes = [child for child in node.named_children if child.type == "attribute_specifier"]
        if len(attribute_end_nodes) > 1:
            self.parse(attribute_end_nodes[-1], struct_declaration["attribute_end"])
        
        # 将结构体声明添加到 statements 中
        statements.append({"struct_declaration": struct_declaration})
        
        return 0


    def union_specifier(self, node, statements):
        # 初始化 union 声明的字典
        # print_node_recursive(node)
        union_declaration = {
            "ms_declspec": [],
            "name": None,
            "body": [],
            "attribute_end": []
        }
        
        # 处理开头的 ms_declspec_modifier
        ms_declspec_modifier_node = self.find_child_by_type(node, "ms_declspec_modifier")
        if ms_declspec_modifier_node:
            self.parse(ms_declspec_modifier_node, union_declaration["ms_declspec"])
        
        # 处理 union 名称
        name_node = self.find_child_by_field(node, "name")
        if name_node:
            union_declaration["name"] = self.read_node_text(name_node)
        
        # 处理 union 体（body）
        body_node = self.find_child_by_field(node, "body")
        if body_node:
            for child in body_node.named_children:
                self.parse(child, union_declaration["body"])
        
        # 处理结尾的 attribute_specifier
        attribute_end_nodes = self.find_child_by_type(node, "attribute_specifier")
        if attribute_end_nodes:
            self.parse(attribute_end_nodes, union_declaration["attribute_end"])
        
        # 将 union 声明添加到 statements 中
        statements.append({"union_declaration": union_declaration})
        
        return 0

    def enum_specifier(self, node, statements):
        # 初始化 enum 声明的字典
        enum_declaration = {
            "name": None,
            "underlying_type": None,
            "body": [],
            "attribute_end": []
        }

        # 查找并处理 enum 名称
        name_node = self.find_child_by_field(node, "name")
        if name_node:
            enum_declaration["name"] = self.read_node_text(name_node)

        # 查找并处理 underlying_type
        underlying_type_node = self.find_child_by_field(node, "underlying_type")
        if underlying_type_node:
            enum_declaration["underlying_type"] = self.read_node_text(underlying_type_node)

        # 查找并处理 enum 体（body）
        body_node = self.find_child_by_field(node, "body")
        if body_node:
            for child in body_node.named_children:
                self.parse(child, enum_declaration["body"])

        # 查找并处理结尾的 attribute_specifier
        attribute_end_nodes = [child for child in node.named_children if child.type == "attribute_specifier"]
        if attribute_end_nodes:
            self.parse(attribute_end_nodes[-1], enum_declaration["attribute_end"])

        # 将 enum 声明添加到 statements 中
        statements.append({"enum_declaration": enum_declaration})

        return 0


    def enumerator_list(self, node, statements):
        for child in node.named_children:
            self.parse(child, statements)
        return 0

    def enumerator(self, node, statements):
        # enumerator -> identifier ("=" constant_expression)?
        name = self.find_child_by_field(node, "name")
        value = self.find_child_by_field(node, "value")
        shadow_name = self.read_node_text(name)
        if value:
            shadow_value = self.parse(value, statements)
            statements.append({"enumerator": {"name": shadow_name, "value": shadow_value}})
        else:
            statements.append({"enumerator": {"name": shadow_name}})
        return 0

    def macro_type_specifier(self, node, statements):
        # macro_type_specifier -> "typedef" type_specifier
        name = self.find_child_by_field(node, "name")
        type_ = self.find_child_by_field(node, "type")
        shadow_name = self.read_node_text(name)
        shadow_type = self.read_node_text(type_)
        statements.append({"macro_type_specifier": {"name": shadow_name, "type": shadow_type}})
        return 0

    # #TODO to modify
    def sized_type_specifier(self, node, statements):
        # sized_type_specifier -> "typedef" type_specifier
        # print_node_recursive(node)
        
        # type_ = self.find_child_by_field(node, "type")
        # shadow_type = self.read_node_text(type_)
        # declarator_ = node.named_children[-1]
        # declarator = self.read_node_text(declarator_)
        statements.append({"sized_type_specifier": {"name": self.read_node_text(node)}})
        

        # type_ = self.find_child_by_field(node, "type")
        # shadow_type = self.read_node_text(type_)
        # statements.append({"sized_type_specifier": {"name": name, "type": shadow_type}})
        return 0
    
    def primitive_type(self, node, statements):
        # primitive_type -> "typedef" type_specifier
        # print_node_recursive(node)
        name = self.read_node_text(node)
        statements.append({"primitive_type": {"name": name}})
        return 0


    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)