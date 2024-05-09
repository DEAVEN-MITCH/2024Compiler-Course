#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type == "comment"

    def is_identifier(self, node):
        return node.type == "identifier"

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "composite_literal": self.composite_literal,
            "func_literal": self.func_literal,
            "raw_string_literal": self.string_literal,
            "interpreted_string_literal":self.string_literal,
            "int_literal": self.regular_number_literal,
            "float_literal": self.regular_number_literal,
            # "imaginary_literal": self.regular_imaginary_literal,
            # "rune_literal": self.regular_rune_literal,
            "nil": self.regular_literal,
            "true": self.regular_literal,
            "false": self.regular_literal,
            "itoa": self.regular_literal,
        }
        # print(node.type,self.read_node_text(node))
        return LITERAL_MAP.get(node.type, None)

    def composite_literal(self,node,statements,replacement):
        type_node=node.child_by_field_name('type')
        shadow_type=self.read_node_text(type_node)
        nt=type_node.type
        body_node=node.child_by_field_name('body')#literal_value
        literal_elements=self.find_children_by_type(body_node,'literal_element')
        keyed_elments=self.find_children_by_type(body_node,'keyed_element')
        tmp_var=self.tmp_variable(statements)
        type_parameters=[]
        args=[]
        init=[]
        fields=[]
        methods=[]
        nested=[]
        if nt=='generic_type':
            bt=type_node.child_by_field_name('type')
            nt=bt.type
            shadow_type=self.read_node_text(bt)
            tp=type_node.child_by_field_name('type_arguments').named_children
            for child in tp:
                if child.type==',':
                    continue
                type_parameters.append(self.read_node_text(child))
        for child in literal_elements:
            n=child.named_children[0]#ex or literal
            v=self.parse(n,statements)
            args.append(v)
        for child in keyed_elments:
            key=child.named_children[0]#literal_element
            value=child.named_children[1]
            keyv=key.named_children[0]#ex or lit
            valuev=value.named_children[0]
            t_key=self.parse(keyv,init)
            t_value=self.parse(valuev,init)
            if nt=='struct_type':#init use field_write
                init.append({"field_write": {"receiver_object": self.global_this(), "field": t_key, "source": t_value}})
            elif nt=='map_type':#init use map_write
                init.append({"map_write": {"target": self.global_this(),"key": t_key, "value": t_value}})
            elif nt=='slice_type' or nt == 'array_type':#init use array_write
                init.append({"array_write": {"array": self.global_this(), "index": t_key, "source": t_value}})
            else:#default use field_write for the moment
                init.append({"field_write": {"receiver_object": self.global_this(), "field": t_key, "source": t_value}})
            
        statements.append({"new_instance":{"target":tmp_var,       "type_parameters":type_parameters,"data_type":shadow_type,"args":args,"init":init,"fields":fields,"methods":methods,"nested":nested}})
        return tmp_var
    



    def regular_imaginary_literal(self, node):
        """处理虚数字面量"""
        imaginary_value = self.read_node_text(node)  # 获取虚数字面量
        return f"Imaginary literal: {imaginary_value}"

    def regular_rune_literal(self, node):
        """处理 rune 字面量"""
        character = chr(node.value)  # 转换为字符
        return f"Rune literal: '{character}' (Unicode: {node.value})"

    def regular_literal(self, node, statements, replacement):
        return self.read_node_text(node)

    def func_literal(self, node, statements,replacement):
        #parameters_list是泛型参数列表，parameters是参数列表，匿名函数没有泛型？
        #parameters processing
        child = self.find_child_by_field(node, "parameters")
        parameters =[]
        init = []
        # tn=child
        # print(child.type)
        # while child and child.named_child_count > 0:
        #     child=child.named_children[0]
        #     print(child.type)

        #outcome
        #parameter_list
        # parameter_declaration
        # identifier
        if child and child.named_child_count > 0:
            # need to deal with parameters
            for p in child.named_children:#parameter_declaration或variadic_parameter_declaration
                self.parse_parameters(p,init)
                while len(init) > 0:
                    parameters.append(init.pop())
        #return type processing
        child = self.find_child_by_field(node, "result")
        mytype = self.read_node_text(child)
        #new variable for ret
        tmp=self.tmp_method()

        type_parameters = []
        attr=[]
        #body stmt processing
        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                self.parse(stmt, new_body)
        statements.append(
            {"method_decl": { "attr":attr,"data_type": mytype, "name": tmp, "parameters": parameters,"body": new_body,"init": init,"type_parameters": type_parameters,}})
    
        return tmp

    def parse_parameters(self,node,statements):
        modifiers = []
        mytype = self.find_child_by_field(node, "type")
        shadow_type = self.read_node_text(mytype)
        name = self.find_child_by_field(node, "name")
        shadow_name=self.read_node_text(name)   
        if node.type=='variadic_parameter_declaration':
            modifiers.append('variadic')
            statements.append({"parameter_decl": {"name": shadow_name, "data_type": shadow_type, "modifiers": modifiers}})
        else :
            children=node.children_by_field_name('name')
            for child in children:#all the parameter decl of the same type processing
                    shadow_name=self.read_node_text(child)
                    statements.append({"parameter_decl": {"name": shadow_name, "data_type": shadow_type, "modifiers": modifiers}})
           

        
    def regular_number_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        if node.type=='float_literal' and  "x" in value.lower():
            try:
                value = float.fromhex(value)
            except:
                value = self.common_eval(value)
        else:
            value = self.common_eval(value)
        # tn=node
        # print(node.type)
        # while len(tn.named_children)>0:
        #     tn=tn.named_children[0]
        #     print(tn.type)
            
        return str(value)

    def string_literal(self, node, statements, replacement):
        ret=''
        if node.type == "raw_string_literal":
            ret ='"'+self.read_node_text(node)[1:-1]+'"'#remove the surrounding ``
            return ret#no need for escape processing for it's raw
        # else type==interpreted_string_literal
        else:
            ret = self.read_node_text(node)#[1:-1]#remove the surrounding ""
        ret = self.handle_hex_string(ret)
        # return ret
        return self.escape_string(ret)

    def handle_hex_string(self, input_string):
        if self.is_hex_string(input_string):
            try:
                tmp_str = input_string.replace('\\x', "")
                tmp_str = bytes.fromhex(tmp_str).decode('utf8')
                return tmp_str
            except:
                pass

        return input_string

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
            'const_declaration':self.const_declaration,
            # 'type_declaration':self.type_declaration,
            'var_declaration':self.var_declaration,
            'short_var_declaration':self.short_var_declaration,

        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

    def const_declaration(self,node,statements):
        const_specs=self.find_children_by_type(node,'const_spec')
        attr=['const']
        for child in const_specs:
            identifiers=child.children_by_field_name('name')
            type_node=child.child_by_field_name('type')
            value_nodes=child.child_by_field_name('value')
            if value_nodes:
                value_nodes=value_nodes.named_children
            shadow_type=None
            if type_node:
                shadow_type=self.read_node_text(type_node)
            shadow_names=[]
            for identifier in identifiers:
                if identifier.type !='identifier':
                    continue
                shadow_name=self.read_node_text(identifier)
                shadow_names.append(shadow_name)
                statements.append({"variable_decl": {"name": shadow_name, "data_type": shadow_type, "attr": attr}})
            if value_nodes and len(value_nodes)==1 and value_nodes[0].type=='call_expression':#expand call return
                ret_arr=self.parse(value_nodes[0],statements)
                i=0
                for shadow_left in shadow_names:
                    statements.append({"array_read": {"target": shadow_left, "array": ret_arr, "index": str(i)}})
                    i+=1 
                continue
            if value_nodes and len(shadow_names)==len(value_nodes):
                for i in range(len(shadow_names)):
                    shadow_value=self.parse(value_nodes[i],statements)
                    statements.append({"assign_stmt": {"target": shadow_names[i], "operand": shadow_value}})

    
    def type_declaration(self,node,statements):
        return
        for child in node.named_children:
            if child.type=='type_spec':
                type_name=child.child_by_field_name('name')
                type_parameters=child.child_by_field_name('type_parameters')
                type_def=child.child_by_field_name('type')
                shadow_name=self.read_node_text(type_name)
                shadow_value=self.read_node_text(type_value)
                statements.append({"class_decl": {"name": shadow_name, "attr": None,"supers":None,"type_parameters":None,"static_init":None,"init":None,"fields":None,"methods":None,"nested":None}})
            elif child.type=='type_alias':
                pass


    def var_declaration(self,node,statements):
        var_specs=self.find_children_by_type(node,'var_spec')
        attr=['var']
        for child in var_specs:
            identifiers=child.children_by_field_name('name')
            type_node=child.child_by_field_name('type')
            value_nodes=child.child_by_field_name('value')
            if value_nodes:
                value_nodes=value_nodes.named_children
            shadow_type=None
            if type_node:
                shadow_type=self.read_node_text(type_node)
            shadow_names=[]
            for identifier in identifiers:
                if identifier.type !='identifier':
                    continue
                shadow_name=self.read_node_text(identifier)
                shadow_names.append(shadow_name)
                statements.append({"variable_decl": {"name": shadow_name, "data_type": shadow_type, "attr": attr}})
            if value_nodes and len(value_nodes)==1 and value_nodes[0].type=='call_expression':#expand call return
                ret_arr=self.parse(value_nodes[0],statements)
                i=0
                for shadow_left in shadow_names:
                    statements.append({"array_read": {"target": shadow_left, "array": ret_arr, "index": str(i)}})
                    i+=1 
                continue
            if value_nodes and len(shadow_names)==len(value_nodes):
                for i in range(len(shadow_names)):
                    shadow_value=self.parse(value_nodes[i],statements)
                    statements.append({"assign_stmt": {"target": shadow_names[i], "operand": shadow_value}})

    def short_var_declaration(self,node,statements):
        left_ex=node.child_by_field_name('left').named_children
        right_ex=node.child_by_field_name('right').named_children
        attr=['var']
        if len(right_ex)==1 and right_ex[0].type=='call_expression':#expand call return
                ret_arr=self.parse(right_ex[0],statements)
                i=0
                for leftexpr in left_ex:
                    if leftexpr.type !='identifier':
                        continue
                    shadow_name=self.parse(leftexpr,statements)
                    statements.append({"variable_decl": {"name": shadow_name, "data_type": None, "attr": attr}})
                    statements.append({"array_read": {"target": shadow_name, "array": ret_arr, "index": str(i)}})
                    i+=1 
        elif len(left_ex)==len(right_ex):
            for i in range(len(left_ex)):
                shadow_name=self.parse(left_ex[i],statements)
                statements.append({"variable_decl": {"name": shadow_name, "data_type": None, "attr": attr}})
                shadow_value=self.parse(right_ex[i],statements)
                statements.append({"assign_stmt": {"target": shadow_name, "operand": shadow_value}})

    def unary_expression(self, node, statements):
        operand = self.find_child_by_field(node, "operand")
        shadow_operand = self.parse(operand, statements)
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)

        tmp_var = self.tmp_variable(statements)

        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_operand}})
        return tmp_var

    def binary_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        operator = self.find_child_by_field(node, "operator")

        shadow_operator = self.read_node_text(operator)

        shadow_left = self.parse(left, statements)
        shadow_right = self.parse(right, statements)

        tmp_var = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_left,
                                           "operand2": shadow_right}})

        return tmp_var

    def field(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        shadow_object, shadow_field = self.parse_field(node, statements)
        statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": shadow_field}})
        return tmp_var

    def parse_field(self, node, statements):
        myobject = self.find_child_by_field(node, "operand")
        shadow_object = self.parse(myobject, statements)

        # to deal with super
        remaining_content = self.read_node_text(node).replace(self.read_node_text(myobject) + ".", "").split(".")[:-1]
        if remaining_content:
            for child in remaining_content:
                tmp_var = self.tmp_variable(statements)
                statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": child}})
                shadow_object = tmp_var

        field = self.find_child_by_field(node, "field")
        shadow_field = self.read_node_text(field)
        return (shadow_object, shadow_field)
    def parse_array(self, node, statements):
        array = self.find_child_by_field(node, "operand")
        shadow_array = self.parse(array, statements)
        index = self.find_child_by_field(node, "index")
        shadow_index = self.parse(index, statements)

        return (shadow_array, shadow_index)

    def array(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        shadow_array, shadow_index = self.parse_array(node, statements)
        statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index}})
        return tmp_var

    def slice_expression(self, node, statements):
        operand = self.find_child_by_field(node, "operand")
        start = self.find_child_by_field(node, "start")
        end = self.find_child_by_field(node, "end")
        capacity = self.find_child_by_field(node, "capacity")
        shadow_operand = self.parse(operand, statements)
        shadow_start = self.parse(start, statements) if start else None
        shadow_end = self.parse(end, statements) if end else None
        shadow_capacity = self.parse(capacity, statements) if capacity else None
        tmp_var = self.tmp_variable(statements)
        statements.append({"slice_stmt": {"target":tmp_var,"array": shadow_operand, "start": shadow_start, "end": shadow_end, "step": shadow_capacity}})
        return tmp_var
    
    def call_expression(self, node, statements):
        name = self.find_child_by_field(node, "function")
        shadow_name = self.parse(name, statements)
        # print(f"node: {self.read_node_text(node)}")
        # print(f"node: {node.sexp()}")

    
        type_arguments = self.find_child_by_field(node, "type_arguments")
        type_text = ""
        if type_arguments:
            type_text = self.read_node_text(type_arguments)[1:-1]
        args = self.find_child_by_field(node, "arguments")
        args_list = []

        if args.named_child_count > 0:
            for child in args.named_children:
                if self.is_comment(child):
                    continue

                shadow_variable = self.parse(child, statements)
                if shadow_variable:
                    args_list.append(shadow_variable)

        tmp_return = self.tmp_variable(statements)
        statements.append({"call_stmt": {"target": tmp_return, "name": shadow_name, "type_parameters": type_text, "args": args_list}})

        return tmp_return
    
    def type_conversion_expression(self, node, statements):
        operand = self.find_child_by_field(node, "operand")#the expression to be converted
        type = self.find_child_by_field(node, "type")
        shadow_operand = self.parse(operand, statements)
        statements.append({"assign_stmt": {"target": shadow_operand, "operand": self.read_node_text(type), "operator": 'cast'}})
        return shadow_operand
    
    def cast_expression(self, node, statements):
        value = self.find_child_by_field(node, "operand")
        shadow_value = self.parse(value, statements)

        types = self.find_children_by_field(node, "type")
        for t in types:
            statements.append(
                {"assign_stmt": {"target": shadow_value, "operator": "cast", "operand": self.read_node_text(t)}})

        return shadow_value
    
    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "unary_expression"          : self.unary_expression,
            "binary_expression"         : self.binary_expression,
            "selector_expression"       : self.field,
            "index_expression"          : self.array,
            "slice_expression"          : self.slice_expression,
            "call_expression"           : self.call_expression,
            "type_assertion_expression"        : self.cast_expression,
            "type_conversion_expression"         : self.type_conversion_expression,
            # "parenthesized_expression"             : self.parenthesized_expression,
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def parenthesized_expression(self, node):
        """处理圆括号表达式"""
        # 假设 'node.expression' 是括号内的表达式
        inner_expression = node.expression
        # 递归解析内部表达式
        return self.parse_expression(inner_expression)  # 根据内部表达式类型进行处理

    def is_expression(self, node):
        # print(node.type)
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def go_statement(self, node, statements):
        #print(f"node: {self.read_node_text(node)}")
        #print(f"node: {node.sexp()}")
        expr = self.find_child_by_type(node, "call_expression")
        tmp_return=""
        shadow_name=""
        type_text=""
        args_list=[]
        if expr:
            #print(f"node: {self.read_node_text(expr)}")
            #print(f"node: {expr.sexp()}")
            name = self.find_child_by_field(expr, "function")
            shadow_name = self.parse(name, statements)  
            type_arguments = self.find_child_by_field(expr, "type_arguments")
            if type_arguments:
                type_text = self.read_node_text(type_arguments)[1:-1]
            args = self.find_child_by_field(expr, "arguments")

            if args.named_child_count > 0:
                for child in args.named_children:
                    if self.is_comment(child):
                        continue

                    shadow_variable = self.parse(child, statements)
                    if shadow_variable:
                        args_list.append(shadow_variable)

            tmp_return = self.tmp_variable(statements)
        statements.append({"call_stmt": {"attr":"go", "target": tmp_return, "name": shadow_name, "type_parameters": type_text, "args": args_list}})

    def defer_statement(self, node, statements):
        expr = self.find_child_by_type(node, "call_expression")
        tmp_return=""
        shadow_name=""
        type_text=""
        args_list=[]
        if expr:
            name = self.find_child_by_field(expr, "function")
            shadow_name = self.parse(name, statements)  
            type_arguments = self.find_child_by_field(expr, "type_arguments")
            if type_arguments:
                type_text = self.read_node_text(type_arguments)[1:-1]
            args = self.find_child_by_field(expr, "arguments")

            if args.named_child_count > 0:
                for child in args.named_children:
                    if self.is_comment(child):
                        continue

                    shadow_variable = self.parse(child, statements)
                    if shadow_variable:
                        args_list.append(shadow_variable)

            tmp_return = self.tmp_variable(statements)
        statements.append({"call_stmt": {"attr":"defer", "target": tmp_return, "name": shadow_name, "type_parameters": type_text, "args": args_list}})


    def if_statement(self, node, statements):
        init_part = self.find_child_by_field(node, "condition")
        if init_part:
            pass #包含decl，下次再写
        condition_part = self.find_child_by_field(node, "condition")
        true_part = self.find_child_by_field(node, "consequence")
        false_part = self.find_child_by_field(node, "alternative")

        true_body = []

        shadow_condition = self.parse(condition_part, statements)
        self.parse(true_part, true_body)
        if false_part:
            false_body = []
            self.parse(false_part, false_body)
            statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body, "else_body": false_body}})
        else:
            statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body}})

    def for_statement(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
        exp = self.find_child_by_type(node, "binary_expression")
        for_clause = self.find_child_by_type(node, "for_clause")
        range_clause = self.find_child_by_type(node, "range_clause")
        body = self.find_child_by_field(node, "body")
        for_body = []
        block = self.find_child_by_field(node, "body")
        self.parse(block, for_body)
        if for_clause:
            init = self.find_child_by_field(for_clause, "initializer")
            condition = self.find_child_by_field(for_clause, "condition")
            step = self.find_child_by_field(for_clause, "update")
            init_body = []
            condition_init = []
            step_body = []

            shadow_condition = self.parse(condition, condition_init)
            self.parse(init, init_body)
            self.parse(step, step_body)

            statements.append({"for_stmt":
                                {"init_body": init_body,
                                "condition": shadow_condition,
                                "condition_prebody": condition_init,
                                "update_body": step_body,
                                "body": for_body}})
        elif range_clause:
            left = self.find_child_by_field(range_clause, "left")
            if left:
                for child in left.named_children:
                    child_val=self.parse(child,statements)
            value = self.find_child_by_field(range_clause, "right")
            shadow_value = self.parse(value, statements)

            statements.append({"forin_stmt":
                                {"attr": None,
                                    "data_type": None,
                                    "name": child_val,
                                    "target": shadow_value,
                                    "body": for_body}})
        elif exp:
            condition_init = []
            shadow_condition = self.parse(exp, condition_init)
            statements.append({"for_stmt":
                                {
                                "condition": shadow_condition,
                                "condition_prebody": condition_init,
                                "body": for_body}})
    

    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            'expression_statement':self.expression_statement,
            'send_statement':self.send_statement,
            'inc_statement':self.inc_statement,
            'dec_statement':self.dec_statement,
            'assignment_statement':self.assignment_statement,
            'return_statement':self.return_statement,

            "go_statement"          : self.go_statement,
            "defer_statement"         : self.defer_statement,
            "if_statement"          : self.if_statement,
            "for_statement"          : self.for_statement,
            #"index_expression"          : self.array,
            #"index_expression"          : self.array,
            #"index_expression"          : self.array,
        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        # print(node.type)
        # print(dir(node))
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)

    def expression_statement(self, node, statements):
        expression = node.named_children[0]
        self.parse(expression, statements)
        return
    
    def send_statement(self, node, statements):
        channel = self.find_child_by_field(node, "channel")
        value = self.find_child_by_field(node, "value")
        shadow_channel = self.parse(channel, statements)
        shadow_value = self.parse(value, statements)
        tmp_variable = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_variable, "operator": '<-', "operand": shadow_channel,
                                           "operand2": shadow_value}})
        return 
    
    def inc_statement(self, node, statements):
        expression = node.named_children[0]
        et=expression.type
        if et=='index_expression':
            array,index=self.parse_array(expression, statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"array_read": {"target": tmp_var, "array": array, "index": index}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '+', "operand": tmp_var,
                                           "operand2": '1'}})
            statements.append({"array_write": {"array": array, "index": index, "source": tmp_var}})
            return
        elif et=='selector_expression':
            target,field=self.parse_field(expression, statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": target, "field": field}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '+', "operand": tmp_var,
                                           "operand2": '1'}})
            statements.append({"field_write": {"receiver_object": target, "field": field, "source": tmp_var}})
            return
        elif self.is_star_expression(expression):
            addr=self.parse(expression.child_by_field_name('operand'),statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"mem_read": {"address": addr,"target":tmp_var}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '+', "operand": tmp_var,
                                           "operand2": '1'}})
            statements.append({"mem_write": {"address": addr,"source":tmp_var}})
            return
        target=self.parse(expression, statements)
        statements.append({"assign_stmt": {"target": target, "operator": '+', "operand": target,
                                           "operand2": '1'}})
        return
    def is_star_expression(self,node):
        return node.type=='unary_expression'  and self.read_node_text(node.child_by_field_name('operator'))=='*'
    def dec_statement(self, node, statements):
        expression = node.named_children[0]
        et=expression.type
        if et=='index_expression':
            array,index=self.parse_array(expression, statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"array_read": {"target": tmp_var, "array": array, "index": index}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '-', "operand": tmp_var,
                                           "operand2": '1'}})
            statements.append({"array_write": {"array": array, "index": index, "source": tmp_var}})
            return
        elif et=='selector_expression':
            target,field=self.parse_field(expression, statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": target, "field": field}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '-', "operand": tmp_var,
                                           "operand2": '1'}})
            statements.append({"field_write": {"receiver_object": target, "field": field, "source": tmp_var}})
            return
        elif self.is_star_expression(expression):
            addr=self.parse(expression.child_by_field_name('operand'),statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"mem_read": {"address": addr,"target":tmp_var}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '-', "operand": tmp_var,
                                           "operand2": '1'}})
            statements.append({"mem_write": {"address": addr,"source":tmp_var}})
            return
        target=self.parse(expression, statements)
        statements.append({"assign_stmt": {"target": target, "operator": '-', "operand": target,
                                           "operand2": '1'}})
        return

    def assignment_statement(self, node, statements):

        left=self.find_child_by_field(node, "left")#list
        right=self.find_child_by_field(node, "right")
        operator=self.find_child_by_field(node, "operator")
        shadow_operator=self.read_node_text(operator)
        # print("enter assign!")
        if len(shadow_operator)!=1:#complex assignment without expression list size>=2
            cut_operator=shadow_operator[:-1]#remove =
            ex_l=left.named_children[0]
            ex_r=right.named_children[0]
            et=ex_l.type
            if et=='index_expression':
                array,index=self.parse_array(ex_l,statements)
                tmp_var=self.tmp_variable(statements)
                statements.append({"array_read": {"target": tmp_var, "array": array, "index": index}})
                ex_r_v=self.parse(ex_r,statements)
                statements.append({"assign_stmt": {"target": tmp_var, "operator": cut_operator, "operand": tmp_var,
                                           "operand2": ex_r_v}})
                statements.append({"array_write": {"array": array, "index": index, "source": tmp_var}})
                return
            elif et=='selector_expression':
                target,field=self.parse_field(ex_l,statements)
                tmp_var=self.tmp_variable(statements)
                statements.append({"field_read": {"target": tmp_var, "receiver_object": target, "field": field}})
                ex_r_v=self.parse(ex_r,statements)
                statements.append({"assign_stmt": {"target": tmp_var, "operator": cut_operator, "operand": tmp_var,
                                           "operand2": ex_r_v}})
                statements.append({"field_write": {"receiver_object": target, "field": field, "source": tmp_var}})
                return
            elif self.is_star_expression(ex_l):
                addr=self.parse(ex_l.child_by_field_name('operand'),statements)
                tmp_var=self.tmp_variable(statements)
                statements.append({"mem_read": {"address": addr,"target":tmp_var}})
                ex_r_v=self.parse(ex_r,statements)
                statements.append({"assign_stmt": {"target": tmp_var, "operator": cut_operator, "operand": tmp_var,
                                           "operand2": ex_r_v}})
                statements.append({"mem_write": {"address": addr,"source":tmp_var}})
                return
            ex_l_v=self.parse(ex_l,statements)
            # print(ex_r.text)
            ex_r_v=self.parse(ex_r,statements)
            statements.append({"assign_stmt": {"target": ex_l_v, "operator": cut_operator, "operand": ex_l_v,
                                           "operand2": ex_r_v}})
            # print(shadow_operator," 1=1")
        else:#list assign
            left_list=left.named_children#expressions
            right_list=right.named_children#expressions
            # print(len(right_list),right_list[0].type)
            if len(right_list)==1 and right_list[0].type=='call_expression':#expand call return
                ret_arr=self.parse(right_list[0],statements)
                i=0
                for child in left_list:
                    tmp_var=self.tmp_variable(statements)
                    statements.append({"array_read": {"target": tmp_var, "array": ret_arr, "index": str(i)}})
                    i+=1
                    if child.type=='index_expression':
                        array,index=self.parse_array(child,statements)
                        statements.append({"array_write": {"array": array, "index": index, "source": tmp_var}})
                        continue
                    elif child.type=='selector_expression':
                        target,field=self.parse_field(child,statements)
                        statements.append({"field_write": {"receiver_object": target, "field": field, "source": tmp_var}})
                        continue
                    elif self.is_star_expression(child):
                        addr=self.parse(child.child_by_field_name('operand'),statements)
                        statements.append({"mem_write": {"address": addr,"source":tmp_var}})
                        continue
                    shadow_left=self.parse(child,statements)
                    statements.append({"assign_stmt": {"target": shadow_left, "operand":
                                                        tmp_var}})
                return
            #else list assign list,checks the len(left_list)==len(right_list),otherwise error occurs however shouldn't be judged in this procedure?
            if(len(left_list)!=len(right_list)):
                return
            for i in range(len(right_list)):
                left_exp=left_list[i]
                val=self.parse(right_list[i],statements)
                if left_exp.type=='index_expression':
                        array,index=self.parse_array(left_exp,statements)
                        statements.append({"array_write": {"array": array, "index": index, "source": val}})
                        continue
                elif left_exp.type=='selector_expression':
                        target,field=self.parse_field(left_exp,statements)
                        statements.append({"field_write": {"receiver_object": target, "field": field, "source": val}})
                        continue
                elif self.is_star_expression(left_exp):
                        addr=self.parse(left_exp.child_by_field_name('operand'),statements)
                        statements.append({"mem_write": {"address": addr,"source":val}})
                        continue
                shadow_left=self.parse(left_exp,statements)
                statements.append({"assign_stmt": {"target": shadow_left, "operand":
                                                        val}})
            return
        return

    def return_statement(self, node, statements):
        expression_list=self.find_child_by_type(node,'expression_list')
        if expression_list is None:
            statements.append({"return_stmt": {"target": None}})
            return 
        ret_var=self.tmp_variable(statements)
        # list_count=expression_list.named_child_count
        statements.append({"new_array":{"target":ret_var,"attr":None,"data_type":None}})
        index=0
        for child in expression_list.named_children:
            child_val=self.parse(child,statements)
            statements.append({"array_write":{"array":ret_var,"index":str(index),"source":child_val}})
            index+=1
        statements.append({"return_stmt": {"target": ret_var}})
        return 
            