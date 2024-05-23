#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type in ["line_comment", "block_comment"]
        

    def is_identifier(self, node):
        return node.type == "identifier" or node.type == "scoped_identifier" or node.type == "type_identifier"

    def number_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        value = self.common_eval(value)
        return str(value)

    
    def string_literal(self, node, statements, replacement):
        replacement = []
        for child in node.named_children:
            self.parse(child, statements, replacement)

        ret = self.read_node_text(node)
        if replacement:
            for r in replacement:
                (expr, value) = r
                ret = ret.replace(self.read_node_text(expr), value)


        return self.escape_string(ret)
    
    def char_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        return "'%s'" % value
    
    def boolean_literal(self, node, statements, replacement):
        return self.read_node_text(node)

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "string_literal"       : self.string_literal,
            "char_literal"          : self.char_literal,
            "boolean_literal"       : self.boolean_literal,
            "integer_literal"       : self.number_literal,
            "float_literal"         : self.number_literal,
            #"negative_literal"      : self.number_literal,
        }

        return LITERAL_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

  

####  Section expression

    # range
    def range_expression(self, node, statements):
        shadow_start, shadow_end = "", ""

        if node.named_child_count > 0:
            if node.named_child_count == 1:
                expr = node.named_children[0]
                shadow_node = self.read_node_text(node)
                if shadow_node[0] == '.':    # 无头有尾
                    shadow_end = self.parse(expr, statements)
                elif shadow_node[-1] == '.': # 有头无尾
                    shadow_start = self.parse(expr, statements)

                tmp_var = self.tmp_variable(statements)
                # 自定义格式
                statements.append({"range": {"target": tmp_var, "start": shadow_start, "end": shadow_end}})
                return tmp_var
                
            else: # node.named_child_count > 1  有头有尾
                shadow_node = self.read_node_text(node)
                
                start_expr, end_expr = node.named_children[0], node.named_children[-1]
                shadow_start, shadow_end = self.parse(start_expr, statements), self.parse(end_expr, statements)
                # 获取operator
                len_start, len_end = len(self.read_node_text(start_expr)), len(self.read_node_text(end_expr))
                shadow_operator = shadow_node[len_start: len(shadow_node) - len_end]

                tmp_var = self.tmp_variable(statements)
                # 自定义格式
                statements.append({"range": {"target": tmp_var, "start": shadow_start, 
                                "operator": shadow_operator, "end": shadow_end}})
                return tmp_var
        else: #无头无尾
            tmp_var = self.tmp_variable(statements)
            statements.append({"range": {"target": tmp_var, "start": shadow_start, "end": shadow_end}})
            return tmp_var  
            
    # unary
    def unary_expression(self, node, statements):
        shadow_operator = self.read_node_text(node)[0]
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)

        tmp_var = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_expr}})
        return tmp_var

    # reference
    def reference_expression(self, node, statements):
        value = self.find_child_by_field(node,"value")
        shadow_value = self.parse(value, statements)
        specifier = self.find_child_by_type(node, "mutable_specifier")
        if specifier:
            tmp_var = self.tmp_variable(statements)
            statements.append({"assign_stmt": {"target": tmp_var, "specifier": self.read_node_text(specifier), 
                                               "operator":"ref", "operand": shadow_value}})
            return tmp_var
        
        tmp_var = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_var, "operator":"ref", "operand": shadow_value}})
        return tmp_var
    # try
    def try_expression(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)
        tmp_var = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_var, "operator": "try", "operand": shadow_expr}})
        return tmp_var 
    # binary
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
    
    # assignment
    def assignment_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        
        shadow_right = self.parse(right, statements)
        if left.type == "index_expression":
            shadow_array, shadow_index = self.parse_array(left, statements)
            statements.append(
                    {"array_write": {"array": shadow_array, "index": shadow_index, "source": shadow_right}})
            return shadow_right
        elif left.type == "field_expression":
            shadow_array, shadow_field = self.parse_field(left, statements)
            statements.append(
                    {"field_write": {"receiver_object": shadow_array, "field": shadow_field, "source": shadow_right}})
            return shadow_right

        shadow_left = self.parse(left, statements)
        statements.append({"assign_stmt": {"target": shadow_left, "operand": shadow_right}})
        
        return shadow_left 

    def parse_array(self, node, statements):
        array = node.named_children[0]
        shadow_array = self.parse(array, statements)
        index = node.named_children[1]
        shadow_index = self.parse(index, statements)

        return (shadow_array, shadow_index)

    def parse_field(self, node, statements):
        myobject = self.find_child_by_field(node, "value")
        shadow_object = self.parse(myobject, statements)

        field = self.find_child_by_field(node, "field")
        shadow_field = self.read_node_text(field)
        return (shadow_object, shadow_field)

    # compound_assignment_expr
    def compound_assignment_expr(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator).replace("=", "")

        shadow_right = self.parse(right, statements)
        if left.type == "index_expression":
            shadow_array, shadow_index = self.parse_array(left, statements)
            tmp_var = self.tmp_variable(statements)
            statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index, }})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": tmp_var2}})
            return tmp_var2

        elif left.type == "field_expression":
            shadow_object, field = self.parse_field(left, statements)
            tmp_var = self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": field, }})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"field_write": {"receiver_object": shadow_object, "field": field, "source": tmp_var2}})

            return tmp_var2

        shadow_left = self.parse(left, statements)
        statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                "operand": shadow_left, "operand2": shadow_right}})
        return shadow_left 

    # type_cast   
    def type_cast_expression(self, node, statements):
        value = self.find_child_by_field(node, "value")
        type = self.find_child_by_field(node, "type")

        shadow_value = self.parse(value, statements)

        shadow_type = self.read_node_text(type)
        
        statements.append(
                {"assign_stmt": {"target": shadow_value, "operator": "type_cast", "operand": shadow_type}})

        return shadow_value

    # call
    def call_expression(self, node, statements):
        function = self.find_child_by_field(node,"function")
        shadow_func = self.parse(function, statements)

        args = self.find_child_by_field(node,"arguments")
        args_list = []

        if args.named_child_count > 0:
            for child in args.named_children:
                #if self.is_comment(child):
                #    continue

                shadow_variable = self.parse(child, statements)
                if shadow_variable:
                    args_list.append(shadow_variable)

        tmp_return = self.tmp_variable(statements)
        statements.append({"call_stmt": {"target": tmp_return, "name": shadow_func, "args": args_list}})
    
        return tmp_return #self.global_return()

    # return
    def return_expression(self, node, statements):
        shadow_target = ""
        if node.named_child_count > 0:
            child = node.named_children[0]
            shadow_target = self.parse(child, statements)

        statements.append({"return_stmt": {"target": shadow_target}})
        return shadow_target
         

    # yield
    def yield_expression(self, node, statements):
        shadow_target = ""
        if node.named_child_count > 0:
            child = node.named_children[0]
            shadow_target = self.parse(child, statements)

        statements.append({"yield_stmt": {"target": shadow_target}})
        return shadow_target 

    # generic_function
    def generic_function(self, node, statements):
        function = self.find_child_by_field(node, "function")
        if function.type == "scoped_identifier":
            pass # 这个分支以后再来探索吧
        elif function.type == "field_expression":
            shadow_function = self.parse(function, statements)
        
        elif function.type == "identifier":
            shadow_function = self.read_node_text(function)

        type_args = self.find_child_by_field(node, "type_arguments")
        type_args_list = []
        
        for child in type_args.named_children:
            shadow_type = self.read_node_text(child)
            type_args_list.append(shadow_type)
        tmp_return = self.tmp_variable(statements)
        statements.append({"generic_function": {"target": tmp_return, "name": shadow_function, "type_args_list": type_args_list}})
        return tmp_return

    # await
    def await_expression(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)

        tmp_var = self.tmp_variable(statements)
        statements.append({"await_stmt": {"target": tmp_var, "operand": shadow_expr}})
        return tmp_var

    # field
    def field_expression(self, node, statements):
        value = self.find_child_by_field(node, "value")
        shadow_value = self.parse(value, statements)

        field = self.find_child_by_field(node, "field")
        if self.is_literal(field):  # 类似数组的index
            shadow_index = self.read_node_text(field)
            tmp_var = self.tmp_variable(statements)
            statements.append({"tuple_read": {"target": tmp_var, "tuple": shadow_value, "index": shadow_index}})
        else:
            shadow_field = self.read_node_text(field)
            tmp_var = self.tmp_variable(statements)
            statements.append({"field_read": {"target":tmp_var, "receiver_object": shadow_value, "field": shadow_field}})

        return tmp_var

    # array
    def array_expression(self, node, statements):
        # 没有考虑attribute_item
        array_list = []
        length = self.find_child_by_field(node, "length")
        if length:  # 形如：[expr; length] 重复expr length次
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)
            shadow_length = self.parse(length, statements)

            for _ in range(int(shadow_length)):
                array_list.append(shadow_expr)
        else:       # 形如 [expr1, ..., exprn]
            for child in node.named_children:
                shadow_expr = self.parse(child, statements)
                array_list.append(shadow_expr)
        

        tmp_var = self.tmp_variable(statements)
        statements.append({"array": {"target": tmp_var, "array_list": array_list}})

        return tmp_var

    # tuple
    def tuple_expression(self, node, statements):
        # 没有考虑attribute_item
        tuple_list = []
        for child in node.named_children:
                shadow_expr = self.parse(child, statements)
                tuple_list.append(shadow_expr)
        

        tmp_var = self.tmp_variable(statements)
        statements.append({"tuple": {"target": tmp_var, "tuple_list": tuple_list}})
        return tmp_var
    # unit
    def unit_expression(self, node, statements):
        # 不知道有什么意义的expression
        tmp_var = self.tmp_variable(statements)
        statements.append({"unit": {"target": tmp_var}})
        return tmp_var
    # 用于处理label
    def parse_label(self, node, statements):
        name = self.parse(node.named_children[0], statements)
        return name

    # break
    def break_expression(self, node, statements):
        label = self.find_child_by_type(node, "label")
        shadow_label = ""
        shadow_expr = ""
        if node.named_child_count == 0 :
            statements.append({"break_stmt": {"target": shadow_label}})
            return
        elif node.named_child_count == 1:
            if label:  # parse_label 得到labelname
                shadow_label = self.parse_label(label, statements)
                statements.append({"break_stmt": {"target": shadow_label}})
                return
            else:
                expr = node.named_children[0]
                shadow_expr = self.parse(expr, statements)
                statements.append({"break_stmt": {"target": shadow_label, "return_val":shadow_expr }})
                return shadow_expr
        else:
            shadow_label = self.read_node_text(label)
            expr = node.named_children[1]
            shadow_expr = self.parse(expr, statements)
            statements.append({"break_stmt": {"target": shadow_label, "return_val":shadow_expr }})
            return shadow_expr

    # continue
    def continue_expression(self, node, statements):
        label = self.find_child_by_type(node, "label")
        shadow_label = ""
        if label:  # parse_label 得到labelname
            shadow_label = self.parse_label(label, statements)
        statements.append({"continue_stmt": {"target": shadow_label}})
         
    # index
    def index_expression(self, node, statements):
        array = self.parse(node.named_children[0], statements)
        index = self.parse(node.named_children[1], statements)
        tmp_var = self.tmp_variable(statements)
        statements.append({"array_read": {"target": tmp_var, "array": array, "index": index}})
        return tmp_var

    def parameter(self, node, statements):
        attr = ""
        mutable_specifier = self.find_child_by_type(node, "mutable_specifier")
        if mutable_specifier:
            attr = self.read_node_text(mutable_specifier)
        
        pattern = self.find_child_by_field(node, "pattern")
        if pattern.type == "self":
            name = self.read_node_text(pattern)
        else:  # _pattern大类
            # 姑且直接读取字面值
            name = self.read_node_text(pattern)

        type = self.find_child_by_field(node, "type")
        data_type = self.read_node_text(type)

        statements.append({"parameter_decl": {"attr":attr , "data_type": data_type, "name": name}})
    # closure
    def closure_expression(self, node, statements):
        parameters = self.find_child_by_field(node, "parameters")

        params_list = []
        if parameters.named_child_count == 0:
            params_list.append({"parameter_decl": {"name": self.read_node_text(parameters)[1:-1]}})
        elif parameters.named_child_count > 0:
            for child in parameters.named_children:
                if child.type == "parameter":
                    # 用辅助函数parameter添加params_list
                    self.parameter(child, params_list)
                else: # _pattern大类 
                    shadow_param = self.read_node_text(child)
                    params_list.append({"parameter_decl": {"name": shadow_param}})

                
        data_type = ""
        return_type = self.find_child_by_field(node,"return_type")
        if return_type:
            data_type = self.read_node_text(return_type)

        body = self.find_child_by_field(node, "body")
        body_list = []
        if self.is_expression(body):
            shadow_expr = self.parse(body, body_list)
            if body.type != "return_expression":  # rust里return是expr，没有出现显式return就新增
                body_list.append({"return_stmt": {"target": shadow_expr}})
        else:
            for stmt in body.named_children:
                    
                    shadow_expr = self.parse(stmt, body_list)
                    if stmt == body.named_children[-1]:  # 处理尾语句/尾表达式
                        # 当前语句或子节点都不是显式的return
                        if stmt.type != "return_expression" and not self.find_child_by_type(stmt, "return_expression"):
                            
                            body_list.append({"return_stmt": {"target": shadow_expr}})
        
        tmp_func = self.tmp_method()
        statements.append({"method_decl": {"data_type": data_type, "name": tmp_func, 
                           "parameters": params_list, "body": body_list}})
        
        return tmp_func
 
   ####  Section statement 

    ## 辅助函数，用于解析condition，在if 和 while 中出现
    def parse_condition_chain(self, node, statements):
        # 区分 普通条件 与 let_condition 与 混合使用
        if node.type == "let_condition":
            pattern = self.find_child_by_field(node, "pattern")
            value = self.find_child_by_field(node, "value")
            # 直接read pattern
            shadow_pattern = self.read_node_text(pattern)
            shadow_value = self.parse(value, statements)
            tmp_var = self.tmp_variable(statements)
            statements.append({"let_condition": {"target": tmp_var, "operand": shadow_pattern, "operand2": shadow_value}})
            return tmp_var
        elif node.type == "let_chain": # 其中至少有一个let_condition
            ## 循环解析整个链，用`&&`连接，
            tmp_left = self.parse_condition_chain(node.named_children[0], statements)
            for idx in range(1, len(node.named_children)):
                child = node.named_children[idx]
                shadow_child = self.parse_condition_chain(child, statements)
                
                tmp_target = self.tmp_variable(statements)
                statements.append({"assign_stmt": {"target": tmp_target, "operand": tmp_left, 
                                    "operator": "&&", "operand2": shadow_child}})
                tmp_left = tmp_target
                
            return tmp_left
                
        else: # 普通条件，一般是一个 expression， 直接parse           
            return self.parse(node, statements)

    # if
    def if_expression(self, node, statements):
        condition_node = self.find_child_by_field(node, "condition")
        consequence_node = self.find_child_by_field(node, "consequence")
        alternative_node = self.find_child_by_field(node, "alternative")

        condition = self.parse_condition_chain(condition_node, statements)
        
        consequence_body = []
        self.parse(consequence_node, consequence_body)

        if alternative_node:
            alternative_body = []
            self.parse(alternative_node, alternative_body)
            statements.append({"if_stmt": {"condition": condition, "then_body": consequence_body, "else_body": alternative_body}})
        else:
            statements.append({"if_stmt": {"condition": condition, "then_body": consequence_body}})


    # match
    def match_expression(self, node, statements):
        switch_ret = self.switch_return()

        is_switch_rule = False
        switch_block = self.find_child_by_field(node, "body")
        for child in switch_block.named_children:
            if self.is_comment(child):
                continue

            if child.type == "match_arm":
                is_switch_rule = True

            break

        condition = self.find_child_by_field(node, "value")
        shadow_condition = self.parse(condition, statements)

        switch_stmt_list = []

        for child in switch_block.named_children:
            if self.is_comment(child):
                continue

            if self.read_node_text(child.children[0]) == "_":
                new_body = []
                if child.named_child_count <= 1:
                    continue

                shadow_return = None
                for child_index in range(child.named_child_count):
                    if child_index < 1:
                        continue
                    expression_block = child.named_children[child_index]
                    shadow_return = self.parse(expression_block, new_body)

                if is_switch_rule:
                    new_body.append({"assign_stmt": {"target": switch_ret, "operand": shadow_return}})

                switch_stmt_list.append({"default_stmt": {"body": new_body}})
            else:
                label = child.named_children[0]
                for case_condition in label.named_children:
                    if self.is_comment(case_condition):
                        continue

                    shadow_condition = self.parse(case_condition, statements)
                    if case_condition != label.named_children[-1]:
                        # if case_init != []:
                        #     statements.insert(-1, case_init)
                        switch_stmt_list.append({"case_stmt": {"condition": shadow_condition}})
                    else:
                        if child.named_child_count > 1:
                            new_body = []
                            for stat in child.named_children[1:]:
                                shadow_return = self.parse(stat, new_body)
                                if is_switch_rule:
                                    new_body.append({"assign_stmt": {"target": switch_ret, "operand": shadow_return}})
                                    new_body.append({"break_stmt": ""})
                            # if case_init != []:
                            #     statements.insert(-1, case_init)

                            switch_stmt_list.append({"case_stmt": {"condition": shadow_condition, "body": new_body}})
                        else:
                            # if case_init != []:
                            #     statements.insert(-1, case_init)
                            switch_stmt_list.append({"case_stmt": {"condition": shadow_condition}})

        statements.append({"match_stmt": {"condition": shadow_condition, "body": switch_stmt_list}})
        return switch_ret

    # while
    def while_expression(self, node, statements):
        label_node = self.find_child_by_type(node, "label")
        condition_node = self.find_child_by_field(node, "condition")
        body_node = self.find_child_by_field(node, "body")

        if label_node:
            label = self.parse_label(label_node, statements)

        condition_init = []
        condition = self.parse_condition_chain(condition_node, condition_init)

        while_body = []
        self.parse(body_node, while_body)

        while_body.extend(condition_init)
        if label_node:
            
            statements.append({"while_stmt": {"label": label, "condition": condition, "body": while_body}})
        else:
            statements.append({"while_stmt": {"condition": condition, "body": while_body}})
        return


    # loop
    def loop_expression(self, node, statements):
        label_node = self.find_child_by_type(node, "label")
        body_node = self.find_child_by_field(node, "body")
        loop_body = []
        self.parse(body_node, loop_body)
        if label_node:
            label = self.parse_label(label_node, statements)
            statements.append({"loop_stmt": {"label": label, "body": loop_body}})
        else:
            statements.append({"loop_stmt": {"body": loop_body}})      
        return

    # for
    def for_expression(self, node, statements):
        label_node = self.find_child_by_type(node, "label")
        value = self.parse(self.find_child_by_field(node, "value"), statements)

        for_body = []
        body_node = self.find_child_by_field(node, "body")
        self.parse(body_node, for_body)
        
        pattern_node = self.find_child_by_field(node, "pattern")
        # 直接read pattern，暂时不多处理
        pattern = self.read_node_text(pattern_node)
        

        if label_node:
            label = self.parse_label(label_node, statements)
            statements.append({"for_stmt": {"label": label, "pattern": pattern, "value": value, "body": for_body}})
        else:
            statements.append({"for_stmt": {"pattern": pattern, "value": value, "body": for_body}})
    

    
    # 辅助parse use_args
    def parse_use_args(self, node, statements):
        if node.type == "use_as_clause":
            path_node = self.find_child_by_field(node, "path")
            alias_node = self.find_child_by_field(node, "alias")
            # 直接读取_path
            path = self.read_node_text(path_node)
            alias = self.read_node_text(alias_node)

            statements.append({"use_args": {"path": path, "alias": alias}})

        elif node.type == "use_list":
            use_list = []
            for child in node.named_children:
                shadow_child = self.parse_use_args(child, use_list)
            statements.append({"use_args": { "use_list": use_list}})

        elif node.type == "scoped_use_list":
            path_node = self.find_child_by_field(node, "path")
            list_node = self.find_child_by_field(node, "list")

            if path_node:
                path = self.read_node_text(path_node)
            else:
                path = ""

            use_list = []
            for child in list_node.named_children:
                shadow_child = self.parse_use_args(child, use_list)
            statements.append({"use_args": {"path": path, "use_list": use_list}})


        elif node.type == "use_wildcard":
            path_node = self.find_child_by_field(node, "path")
            if path_node:
                path = self.read_node_text(path_node)
            else:
                path = ""
            # `*`应该是表示path下的所有name吧
            statements.append({"use_args": {"path": path, "use_list": "*"}})

        else:    # _path 直接read
            path = self.read_node_text(node)
            statements.append({"use_args": {"path": path}})


    # use_declaration
    def use_declaration(self, node, statements):
        modifier_node = self.find_child_by_type(node, "visibility_modifier")
        # 暂时不进一步解析visibility_modifier

        args_node = self.find_child_by_field(node, "argument")

        arg_list = []
        self.parse_use_args(args_node, arg_list)
        if modifier_node:
            modifier = self.read_node_text(modifier_node)
            statements.append({"use_stmt": {"visibility_modifier": modifier, "use_args": arg_list}})
        else:
            statements.append({"use_stmt": {"use_args": arg_list}})

####  Section declaration

    # macro_invocation  属于多个类别
    def macro_invocation(self, node, statements):
        macro_node = self.find_child_by_field(node, "macro")
        # scoped_identifier, identifier, _reserved_identifier
        macro = self.read_node_text(macro_node)

        token_tree = []
        token_tree_stack = []
        token_tree_node = self.find_child_by_type(node, "token_tree")

        while token_tree_node:
            if token_tree_node.type == "token_tree":
                token_tree_stack.append(token_tree)
                token_tree = []
                token_tree_node = token_tree_node.children[0]
            else:
                token = self.read_node_text(token_tree_node)
                token_tree.append(token)
                if len(token_tree_node.children) > 1:
                    token_tree_node = token_tree_node.children[1]
                else:
                    if token_tree_stack:
                        parent_tree = token_tree_stack.pop()
                        parent_tree.append(token_tree)
                        token_tree = parent_tree
                    else:
                        break
        tmp_target = self.tmp_variable(statements)
        statements.append({"macro_invocation": {"target": tmp_target, "macro": macro, "token_tree": token_tree}})                    
            
    def parse_token_pattern(self, node, statements):
        if node.type == "token_tree_pattern":
            token_tree_pattern = []
            for child in node.named_children:
                self.parse_token_pattern(child, token_tree_pattern)
            statements.append({"token_pattern": {"token_tree_pattern": token_tree_pattern}})

        elif node.type == "token_repetition_pattern":
            # 以正则表达式匹配传入参数
            name_pattern = self.read_node_text(node)
            statements.append({"token_pattern": {"name": name_pattern}})
            pass
        elif node.type == "token_binding_pattern":
            name_node = self.find_child_by_field(node, "name")
            type_node = self.find_child_by_field(node, "type")

            name = self.read_node_text(name_node)
            type = self.read_node_text(type_node)
            statements.append({"token_pattern": {"name": name, "type": type}})

        elif node.type == "metavariable":
            name = self.read_node_text(node)
            statements.append({"token_pattern": {"name": name}})

        else:  # _non_special_token
            token = self.read_node_text(node)
            statements.append({"token_pattern": {"name": token}})
        

    def parse_token(self, node, statements):
        if node.type == "token_tree":
            token_tree = []
            for child in node.named_children:
                self.parse_token(child, token_tree)
            statements.append({"token": {"token_tree": token_tree}})
        elif node.type == "token_repetition":
            # 正则表达式匹配token
            token_pattern = self.read_node_text(node)
            statements.append({"token": {"token": token_pattern}})
        elif node.type == "metavariable":
            token = self.read_node_text(node)
            statements.append({"token": {"token": token}})
        else: # _non_special_token
            token = self.read_node_text(node)
            statements.append({"token": {"token": token}})

    def macro_definition(self, node, statements):
        name = self.find_child_by_field(node, "name")
        shadow_name = self.read_node_text(name)

        macro_rule_list = []
        macro_rules = self.find_children_by_type(node, "macro_rule")

        for macro_rule in macro_rules:
            left_node = self.find_child_by_field(macro_rule, "left")
            right_node = self.find_child_by_field(macro_rule, "right")
            token_tree_pattern = []
            # left : token_tree_pattern
            self.parse_token_pattern(left_node, token_tree_pattern)
            
            # right : token_tree
            token_tree = []
            self.parse_token(right_node, token_tree)
            macro_rule_list.append({"macro_rule": {"left": token_tree_pattern, "right": token_tree}})
        
        statements.append({"macro_def": {"name": shadow_name, "macro_rule_list": macro_rule_list}})
    # function_item
    def function_item(self, node, statements):
        visibility_modifier = self.find_child_by_type(node, "visibility_modifier")
        # async, unsafe,...可以有多个
        function_modifiers = self.find_child_by_type(node, "function_modifiers")
        modifiers = []
        if visibility_modifier:
            modifiers.append(self.read_node_text(visibility_modifier))
        if function_modifiers:
            modifiers.extend(self.read_node_text(function_modifiers).split(','))

        name_node = self.find_child_by_field(node, "name")
        # identifier, metavariable
        name = self.read_node_text(name_node)
        type_param_node = self.find_child_by_field(node, "type_parameters")
        type_parameters = []
        if type_param_node:
            # 去掉前后`<>`
            type_parameters.extend(self.read_node_text(type_param_node)[1:-1].split(','))
        param_node = self.find_child_by_field(node, "parameters")
        # 解析简单的parameter，暂时不考虑optional的attribute_item
        #attributes = self.find_children_by_type(param_node, "attribute_item")
        parameters = self.find_children_by_type(param_node, "parameter")
        parameter_list = []
        for child in parameters:
            self.parameter(child, parameter_list)

        return_t_node = self.find_child_by_field(node, "return_type")
        return_t = self.read_node_text(return_t_node)

        where_node = self.find_child_by_type(node, "where_clause")
        where_clause = []
        if where_node:
            self.parse_where_clause(where_node, where_clause)

        body_node = self.find_child_by_field(node, "body")
        body_list = []
        self.parse(body_node, body_list)

        statements.append(
            {"method_decl": {"attr": modifiers, "return_type": return_t, "name": name, "type_parameters": type_parameters,
                             "parameters": parameter_list, "where_clause": where_clause, "body": body_list}})
    
    # attribute
    def parse_attribute(self, node, statements):
        glang_dict = {}

        path_node = node.named_children[0]
        path = self.read_node_text(path_node)
        glang_dict["path"] = path

        value_node = self.find_child_by_field(node, "value")
        if value_node:
            value = self.parse(value_node, statements)
            glang_dict["value"] = value

        arguments_node = self.find_child_by_field(node, "arguments")
        if arguments_node:
            arguments = self.read_node_text(arguments_node)
            glang_dict["arguments"] = arguments
        
        statements.append({"attribute": glang_dict})   
        return

    def attribute_item(self, node, statements):
        glang_dict = {}
        
        attribute = []
        attribute_node = node.named_children[0]
        self.parse_attribute(attribute_node, attribute)
        glang_dict["attribute_item"] = attribute[0]

        return

    def inner_attribute_item(self, node, statements):
        glang_dict = {}
        
        attribute = []
        attribute_node = node.named_children[0]
        self.parse_attribute(attribute_node, attribute)
        glang_dict["inner_attribute_item"] = attribute[0]
        
        return

    # associated_type
    def associated_type(self, node, statements):
        glang_dict = {}

        name_node = self.find_child_by_field(node, "name")
        name = self.read_node_text(name_node)
        glang_dict["name"] = name

        type_parameters_node = self.find_child_by_field(node, "type_parameters")
        if type_parameters_node:
            type_parameters= []
            self.parse_type_parameters(type_parameters_node, type_parameters)
            glang_dict["type_parameters"] = type_parameters

        bounds_node = self.find_child_by_field(node, "bounds")
        if bounds_node:
            trait_bounds= []
            self.parse_trait_bounds(trait_bounds_node, trait_bounds)
            glang_dict["trait_bounds"] = trait_bounds

        where_clause_node = self.find_child_by_type(node, "where_clause")
        if where_clause_node:
            where_clause = []
            self.parse_where_clause(where_clause_node, where_clause)
            glang_dict["where_clause"] = where_clause
        
        statements.append({"associated_type": glang_dict})   
        return


    def parse_type_parameters(self, node, statements):
        type_paras_list = []
        for child in node.named_children:
            statements.append(self.read_node_text(child))
        return

    def parse_trait_bounds(self, node, statements):
        trait_list = []
        for child in node.named_children:
            statements.append(self.read_node_text(child))
        return
        
    def parse_where_clause(self, node, statements):
        where_predicate_nodes = self.find_children_by_type(node, "where_predicate")
        where_predicate_list = []

        for child in where_predicate_nodes:
            bounds_node = self.find_child_by_field(child, "bounds")
            bounds = []
            self.parse_trait_bounds(bounds_node, bounds)
            left = self.read_node_text(self.find_child_by_field(child, "left"))
            where_predicate_list.append({"where_predicate": {"left": left, "bounds": bounds}})

        statements.append({"where_predicate_list": where_predicate_list})
        return 

    def parse_field_declaration(self, node, statements):
        glang_dict = {}

        visibility_modifier_node = self.find_child_by_type(node, "visibility_modifier")
        if visibility_modifier_node:
            glang_dict["visibility_modifier"] = self.read_node_text(visibility_modifier_node)

        name_node = self.find_child_by_field(node, "name")
        glang_dict["name"] = self.read_node_text(name_node)

        type_node = self.find_child_by_field(node, "type")
        my_type = self.read_node_text(type_node)
        glang_dict["type"] = my_type

        statements.append({"field_declaration": glang_dict})
        return

    def parse_field_declaration_list(self, node, statements):
        # []
        for child in node.named_children:
            if child.type == "attribute_item":
                attribute_item = []
                self.parse(child, attribute_item)
                statements.append(attribute_item)
            else: # field_declaration {"field_declaration": {}}
                field_declaration = []
                self.parse_field_declaration(child, field_declaration)
                statements.append(field_declaration)
        return 

    # struct_item
    def struct_item(self, node, statements):
        struct_item_dict = {}

        visibility_modifier_node = self.find_child_by_type(node, "visibility_modifier")
        if visibility_modifier_node:
            struct_item_dict["visibility_modifier"] = self.read_node_text(visibility_modifier_node)

        name_node = self.find_child_by_field(node, "name")
        struct_item_dict["name"] = self.read_node_text(name_node)

        type_parameters = []
        type_parameters_node = self.find_child_by_field(node, "type_parameters")
        self.parse_type_parameters(type_parameters_node, type_parameters)
        struct_item_dict["type_parameters"] = type_parameters

        body = []
        body_node = self.find_child_by_field(node, "body")
        self.parse_field_declaration_list(body_node, body)
        struct_item_dict["body"] = body

        where_clause_node = self.find_child_by_type(node, "where_clause")
        if where_clause_node:
            where_clause = []
            self.parse_where_clause(where_clause_node, where_clause)
            struct_item_dict["where_clause"] = where_clause

        statements.append({"struct_item": struct_item_dict})
        return

    # const_item
    def const_item(self, node, statements):
        glang_dict = {}

        visibility_modifier_node = self.find_child_by_type(node, "visibility_modifier")
        if visibility_modifier_node:
            glang_dict["visibility_modifier"] = self.read_node_text(visibility_modifier_node)

        name_node = self.find_child_by_field(node, "name")
        glang_dict["name"] = self.read_node_text(name_node)

        type_node = self.find_child_by_field(node, "type")
        my_type = self.read_node_text(type_node)
        glang_dict["type"] = my_type

        value_node = self.find_child_by_field(node, "value")
        if value_node:
            value = []
            self.parse(value_node, value)
            glang_dict["value"] = value

        statements.append({"const_item": glang_dict})
        return

    # mod_item
    def mod_item(self, node, statements):
        name_node = self.find_child_by_field(node, "name")
        name = self.parse(name_node, statements)
        
        body = []
        body_node = self.find_child_by_field(node, "body")
        self.parse(body_node, body)
        
        visibility_modifier_node = self.find_child_by_type(node, "visibility_modifier")
        if visibility_modifier_node:
            visibility_modifier = self.read_node_text(visibility_modifier_node)
            statements.append({"mod_item": {"visibility_modifier": visibility_modifier, "name": name, "body": body}})
        else:
            statements.append({"mod_item": {"name": name, "body": body}})      
        return
    
    # foreign_mod_item
    def foreign_mod_item(self, node, statements):
        extern_modifier_node = self.find_child_by_field(node, "extern_modifier")
        extern_modifier = self.read_node_text(extern_modifier_node)
        
        body = []
        body_node = self.find_child_by_field(node, "body")
        self.parse(body_node, body)
        
        visibility_modifier_node = self.find_child_by_type(node, "visibility_modifier")
        if visibility_modifier_node:
            visibility_modifier = self.read_node_text(visibility_modifier_node)
            statements.append({"foreign_mod_item": {"visibility_modifier": visibility_modifier, "extern_modifier": extern_modifier, "body": body}})
        else:
            statements.append({"foreign_mod_item": {"extern_modifier": extern_modifier, "body": body}})      
        return

    
    # enum_item
    def parse_enum_variant(self, node, statements):
        glang_dict = {}

        visibility_modifier_node = self.find_child_by_type(node, "visibility_modifier")
        if visibility_modifier_node:
            glang_dict["visibility_modifier"] = self.read_node_text(visibility_modifier_node)

        name_node = self.find_child_by_field(node, "name")
        glang_dict["name"] = self.read_node_text(name_node)

        body = []
        body_node = self.find_child_by_field(node, "body")
        if body_node:
            self.parse_field_declaration_list(body_node, body)
            glang_dict["body"] = body

        value = []
        value_node = self.find_child_by_field(node, "value")
        if value_node:
            self.parse(value_node, value)
            glang_dict["value"] = value

        statements.append({"parse_enum_variant": glang_dict})
        return

    def parse_enum_variant_list(self, node, statements):
        # []
        for child in node.named_children:
            if child.type == "attribute_item":
                attribute_item = []
                self.parse(child, attribute_item)
                statements.append(attribute_item)
            else: # field_declaration {"field_declaration": {}}
                field_declaration = []
                self.parse_enum_variant(child, field_declaration)
                statements.append(field_declaration)
        return 
    
    def enum_item(self, node, statements):
        glang_dict = {}

        visibility_modifier_node = self.find_child_by_type(node, "visibility_modifier")
        if visibility_modifier_node:
            glang_dict["visibility_modifier"] = self.read_node_text(visibility_modifier_node)

        name_node = self.find_child_by_field(node, "name")
        glang_dict["name"] = self.read_node_text(name_node)

        type_parameters_node = self.find_child_by_field(node, "type_parameters")
        if type_parameters_node:
            type_parameters= []
            self.parse_type_parameters(type_parameters_node, type_parameters)
            glang_dict["type_parameters"] = type_parameters

        where_clause_node = self.find_child_by_type(node, "where_clause")
        if where_clause_node:
            where_clause = []
            self.parse_where_clause(where_clause_node, where_clause)
            glang_dict["where_clause"] = where_clause

        body_node = self.find_child_by_field(node, "body")
        if body_node:
            body = []
            self.parse_enum_variant_list(body_node, body)
            glang_dict["body"] = body

        statements.append({"enum_item": glang_dict})
        return
    
    # type_item
    def type_item(self, node, statements):
        glang_dict = {}

        visibility_modifier_node = self.find_child_by_type(node, "visibility_modifier")
        if visibility_modifier_node:
            glang_dict["visibility_modifier"] = self.read_node_text(visibility_modifier_node)

        name_node = self.find_child_by_field(node, "name")
        glang_dict["name"] = self.read_node_text(name_node)

        type_parameters_node = self.find_child_by_field(node, "type_parameters")
        if type_parameters_node:
            type_parameters= []
            self.parse_type_parameters(type_parameters_node, type_parameters)
            glang_dict["type_parameters"] = type_parameters

        type_node = self.find_child_by_field(node, "type")
        my_type = self.read_node_text(type_node)
        glang_dict["type"] = my_type

        where_clause_node = self.find_child_by_type(node, "where_clause")
        if where_clause_node:
            where_clause = []
            self.parse_where_clause(where_clause_node, where_clause)
            glang_dict["where_clause"] = where_clause

        statements.append({"type_item": glang_dict})
        return

    # let_declaration
    def let_declaration(self, node, statements):
        pattern = self.find_child_by_field(node, "pattern")
        # 首先获取变量信息
        info = []
        if pattern.type == "_":
            value = self.find_child_by_field(node, "value")
            self.parse(value)
            return
        elif pattern.type == "identifier":
            mutable_specifier = self.find_child_by_type(node, "mutable_specifier")
            pattern_node = self.find_child_by_field(node, "pattern")
            name = self.read_node_text(pattern_node)
            if mutable_specifier:
                info.append(("mut", name))
            else:
                info.append(("normal", name))
        else:
            self.parse_pattern_in_let_declaration(pattern, statements, info)
        # 再获取类型信息
        type_list = []
        mytype = self.find_child_by_field(node, "type")
        if mytype:
            self.parse_type_in_let_declaration(mytype, statements, type_list)
        # 对应赋值
        value = self.find_child_by_field(node, "value")
        if mytype:
            self.parse_value_in_let_declaration(value, statements, info[0], type_list[0])
        else:
            self.parse_value_in_let_declaration(value, statements, info[0], [])


    def parse_pattern_in_let_declaration(self, node, statements, info):
        if node.type == "tuple_pattern" or node.type == "slice_pattern":
            info_temp = []
            
            # 首先要提取出占位符
            underline_pos = [] # 占位符的位置
            content_temp = self.read_node_text(node)[1:-1]  # 为了找到_占位符的位置，删去前后的括号
            
            content_cleaned = ""  # 为了避免被类似(_,(_),_)中的第二个_干扰，要排除括号内的内容
            count = 0
            for c in content_temp:
                if c == "(" or c == "[":
                    count+=1
                elif c ==")" or c== "]":
                    count-=1
                else:
                    if count==0:
                        content_cleaned +=c

            for idx, identifier_temp in enumerate(content_cleaned.split(',')):
                if identifier_temp.strip() == "_":
                    underline_pos.append(idx)
            for pattern_node in node.named_children:
                self.parse_pattern_in_let_declaration(pattern_node, statements, info_temp)
            for idx in underline_pos:
                info_temp.insert(idx, ("empty", ))

            if node.type == "tuple_pattern":
                info.append(("tuple",info_temp))
            elif node.type == "slice_pattern":
                info.append(("array",info_temp))
        elif node.type == "ref_pattern":
            identifier = self.find_child_by_type(node, "identifier")
            name = self.read_node_text(identifier)
            info.append(("ref", name))
        elif node.type == "identifier":
            name = self.read_node_text(node)
            info.append(("normal", name))
        elif node.type == "mut_pattern":
            identifier = self.find_child_by_type(node, "identifier")
            name = self.read_node_text(identifier)
            info.append(("mut", name))

        return info

    def parse_type_in_let_declaration(self, node, statements, info):
        if node.type == "tuple_type":
            info_temp = []
            
            # 首先要提取出占位符
            underline_pos = [] # 占位符的位置
            content_temp = self.read_node_text(node)[1:-1]  # 为了找到_占位符的位置，删去前后的括号
            
            content_cleaned = ""  # 为了避免被类似(_,(_),_)中的第二个_干扰，要排除括号内的内容
            count = 0
            for c in content_temp:
                if c == "(":
                    count+=1
                elif c ==")":
                    count-=1
                else:
                    if count==0:
                        content_cleaned +=c
            
            for idx, identifier_temp in enumerate(content_cleaned.split(',')):
                if identifier_temp.strip() == "_":
                    underline_pos.append(idx)
            for pattern_node in node.named_children:
                self.parse_type_in_let_declaration(pattern_node, statements, info_temp)
            for idx in underline_pos:
                info_temp.insert(idx, ("empty", ))
            info.append(("tuple_type",info_temp))
        elif node.type == "array_type":
            pattern_node = self.find_child_by_field(node, "element")
            info_temp = []
            self.parse_type_in_let_declaration(pattern_node, statements, info_temp)
            if info_temp:
                info.append(("array_type",info_temp[0][1]))
            else:
                info.append(("array_type", ""))
        else:
            name = self.read_node_text(node)
            if name!="_":
                info.append(("normal", name))
        return info
            

    def parse_value_in_let_declaration(self, node, statements, info, type_list):
        if info[0] == "tuple":  # 如果记录的信息是tuple，则递归处理
            has_type=False
            if type_list and type_list[0] != "empty":
                has_type = True
            for idx, son_node in enumerate(node.named_children):
                if has_type:
                    self.parse_value_in_let_declaration(son_node, statements, info[1][idx], type_list[1][idx])
                else:
                    self.parse_value_in_let_declaration(son_node, statements, info[1][idx], [])                  
        elif info[0] == "array":
            has_type=False
            if type_list and type_list[0] != "empty":
                has_type = True
                shadow_type = type_list[1]
            length = self.find_child_by_field(node, "length")
            if node and length:
                length_value = int(self.parse(length))
                value = node.named_children[0]
                shadow_value = self.parse(value)
                for index in range(length_value):
                    if info[1][index][0]=="empty":
                        continue
                    if has_type:
                        statements.append({"variable_decl": {"data_type": shadow_type, "name": info[1][index][1]}})
                    else:
                        statements.append({"variable_decl": {"data_type": "", "name": info[1][index][1]}})
                    statements.append({"assign_stmt": {"target": info[1][index][1], "operand": shadow_value}})
            elif node and node.named_child_count > 0:
                for index, item in enumerate(node.named_children):
                    if info[1][index][0]=="empty":
                        continue
                    if self.is_comment(item):
                        continue
                    source = self.parse(item, statements)
                    if has_type:
                        statements.append({"variable_decl": {"data_type": shadow_type, "name": info[1][index][1]}})
                    else:
                        statements.append({"variable_decl": {"data_type": "", "name": info[1][index][1]}})
                    statements.append({"assign_stmt": {"target": info[1][index][1], "operand": source}})
        elif info[0] == "mut" or info[0] == "ref":
            mytype = node.type
            has_type = False
            if type_list and type_list[0] != "empty":
                has_type = True
                shadow_type = type_list[1]
            
            if mytype == "tuple_expression":
                tmp_var = self.tmp_variable(statements)
                statements.append({"new_tuple": {"target": tmp_var}})
                if node and node.named_child_count > 0:
                    index = 0
                    for item in node.named_children:
                        if self.is_comment(item):
                            continue

                        source = self.parse(item, statements)
                        
                        if has_type:
                            statements.append({"tuple_write": {"tuple": tmp_var, "type": shadow_type[index][1], "index": str(index), "source": source}})
                        else:
                            statements.append({"tuple_write": {"tuple": tmp_var, "type": "", "index": str(index), "source": source}})
                        index += 1
                shadow_value = tmp_var
                if has_type:
                    statements.append({"variable_decl": {"data_type": shadow_type, "name": info[1]}})
                else:
                    statements.append({"variable_decl": {"data_type": "", "name": info[1]}})
                if info[0]=="mut":
                    statements.append({"assign_stmt": {"target": info[1], "operand": shadow_value}})
                elif info[0]=="ref":
                    statements.append({"assign_stmt": {"target": info[1], "operator":"ref", "operand": shadow_value}})
            elif mytype == "array_expression":
                tmp_var = self.tmp_variable(statements)
                statements.append({"new_array": {"type": shadow_type, "target": tmp_var}})
                
                length = self.find_child_by_field(node, "length")
                if node and length:
                    length_value = int(self.parse(length))
                    value = node.named_children[0]
                    shadow_value = self.parse(value)
                    for index in range(length_value):
                        if has_type:
                            statements.append({"array_write": {"array": tmp_var, "type": shadow_type, "index": str(index), "source": shadow_value}})
                        else:
                            statements.append({"array_write": {"array": tmp_var, "type": "", "index": str(index), "source": shadow_value}})
                        
                        
                elif node and node.named_child_count > 0:
                    index = 0
                    for item in node.named_children:
                        if self.is_comment(item):
                            continue

                        source = self.parse(item, statements)
                        if has_type:
                            statements.append({"array_write": {"array": tmp_var, "type": shadow_type, "index": str(index), "source": source}})
                        else:
                            statements.append({"array_write": {"array": tmp_var, "type": "", "index": str(index), "source": source}})
                        index += 1
                shadow_value = tmp_var
                if has_type:
                    statements.append({"variable_decl": {"data_type": shadow_type, "name": info[1]}})
                else:
                    statements.append({"variable_decl": {"data_type": "", "name": info[1]}})
                if info[0]=="mut":
                    statements.append({"assign_stmt": {"target": info[1], "operand": shadow_value}})
                elif info[0]=="ref":
                    statements.append({"assign_stmt": {"target": info[1], "operator":"ref", "operand": shadow_value}})
            else:
                shadow_value = self.parse(node, statements)
                if has_type:
                    statements.append({"variable_decl": {"data_type": shadow_type, "name": info[1]}})
                else:
                    statements.append({"variable_decl": {"data_type": "", "name": info[1]}})
                if info[0]=="mut":
                    statements.append({"assign_stmt": {"target": info[1], "operand": shadow_value}})
                elif info[0]=="ref":
                    statements.append({"assign_stmt": {"target": info[1], "operator":"ref", "operand": shadow_value}})
        elif info[0] == "normal":
            mytype = node.type
            has_type = False
            if type_list and type_list[0] != "empty":
                has_type = True
                shadow_type = type_list[1]
            if mytype == "tuple_expression":
                tmp_var = self.tmp_variable(statements)
                statements.append({"new_tuple": {"target": tmp_var}})
                if node and node.named_child_count > 0:
                    index = 0
                    for item in node.named_children:
                        if self.is_comment(item):
                            continue

                        source = self.parse(item, statements)
                        
                        if has_type:
                            statements.append({"tuple_write": {"tuple": tmp_var, "type": shadow_type[index][1], "index": str(index), "source": source}})
                        else:
                            statements.append({"tuple_write": {"tuple": tmp_var, "type": "", "index": str(index), "source": source}})
                        index += 1
                shadow_value = tmp_var
                if has_type:
                    statements.append({"constant_decl": {"data_type": shadow_type, "name": info[1]}})
                else:
                    statements.append({"constant_decl": {"data_type": "", "name": info[1]}})
                statements.append({"assign_stmt": {"target": info[1], "operand": shadow_value}})
            elif mytype == "array_expression":
                tmp_var = self.tmp_variable(statements)
                statements.append({"new_array": {"type": shadow_type, "target": tmp_var}})
                
                length = self.find_child_by_field(node, "length")
                if node and length:
                    length_value = int(self.parse(length))
                    value = node.named_children[0]
                    shadow_value = self.parse(value)
                    for index in range(length_value):
                        if has_type:
                            statements.append({"array_write": {"array": tmp_var, "type": shadow_type, "index": str(index), "source": shadow_value}})
                        else:
                            statements.append({"array_write": {"array": tmp_var, "type": "", "index": str(index), "source": shadow_value}})
                        
                        
                elif node and node.named_child_count > 0:
                    index = 0
                    for item in node.named_children:
                        if self.is_comment(item):
                            continue

                        source = self.parse(item, statements)
                        if has_type:
                            statements.append({"array_write": {"array": tmp_var, "type": shadow_type, "index": str(index), "source": source}})
                        else:
                            statements.append({"array_write": {"array": tmp_var, "type": "", "index": str(index), "source": source}})
                        index += 1
                shadow_value = tmp_var
                if has_type:
                    statements.append({"constant_decl": {"data_type": shadow_type, "name": info[1]}})
                else:
                    statements.append({"constant_decl": {"data_type": "", "name": info[1]}})
                statements.append({"assign_stmt": {"target": info[1], "operand": shadow_value}})
            else:
                shadow_value = self.parse(node, statements)
                if has_type:
                    statements.append({"constant_decl": {"data_type": shadow_type, "name": info[1]}})
                else:
                    statements.append({"constant_decl": {"data_type": "", "name": info[1]}})
                statements.append({"assign_stmt": {"target": info[1], "operand": shadow_value}})
        else:
            return
        
        return statements

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "range_expression"          : self.range_expression,

            # expression without range

            "unary_expression"          : self.unary_expression,
            "reference_expression"      : self.reference_expression,
            "try_expression"            : self.try_expression,
            "binary_expression"         : self.binary_expression,
            "assignment_expression"     : self.assignment_expression,
            "compound_assignment_expr"  : self.compound_assignment_expr,
            "type_cast_expression"      : self.type_cast_expression,
            "call_expression"           : self.call_expression,
            "return_expression"         : self.return_expression,
            "yield_expression"          : self.yield_expression,
            "generic_function"          : self.generic_function,
            "await_expression"          : self.await_expression,
            "field_expression"          : self.field_expression,
            "array_expression"          : self.array_expression, 
            "tuple_expression"          : self.tuple_expression,
            "unit_expression"           : self.unit_expression,
            "break_expression"          : self.break_expression,
            "continue_expression"       : self.continue_expression,
            "index_expression"          : self.index_expression,
            "closure_expression"        : self.closure_expression,
          
        
            # expression ending with block
            # .... goto stmt 

            # others
            
        }
        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
            "macro_definition":  self.macro_definition,
            "function_item":     self.function_item,
            "struct_item":       self.struct_item,
            "attribute_item":    self.attribute_item,
            "associated_type":   self.associated_type,
            "const_item":        self.const_item,
            "mode_item":         self.mod_item,
            "foreign_mod_item":  self.foreign_mod_item,
            "enum_item":         self.enum_item,
            "type_item":         self.type_item,
            # not yet
            

        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)


    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            "use_declaration"           : self.use_declaration,
            "if_expression"             : self.if_expression,
            "match_expression"          : self.match_expression,
            "while_expression"          : self.while_expression,
            "loop_expression"           : self.loop_expression,
            "for_expression"            : self.for_expression,
            "let_declaration"           : self.let_declaration,
        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)
