#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type == "comment"

    """
        expression(含literal)部分 
    """ 

    def is_identifier(self, node):
        return node.type == "identifier"
    
    def regular_number_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        value = self.common_eval(value)
        return str(value)
    
    def regular_literal(self, node, statements, replacement):
        return self.read_node_text(node)

    def this_literal(self, node, statements, replacement):
        return self.global_this()

    def super_literal(self, node, statements, replacement):
        return self.global_super()
    
    def string_literal(self, node, statements, replacement):
        replacement = []
        for child in node.named_children:
            self.parse(child, statements, replacement)

        ret = self.read_node_text(node).replace('`', '"')
        if replacement:
            # 逐个进行替换，为了防止在字符串中的多个地方出现expr而发生误替换，因此将${expr}整体替换为${value}
            for r in replacement:
                (expr, value) = r
                ret = ret.replace("${" + self.read_node_text(expr) + "}", "${" + value + "}")

        ret = self.handle_hex_string(ret)
        return self.escape_string(ret)
    
    def template_substitution(self, node, statements, replacement):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)
        replacement.append((expr, shadow_expr))
        return shadow_expr

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
    
    def unary_expression(self, node, statements):
        operand = self.find_child_by_field(node, "argument")
        shadow_operand = self.parse(operand, statements)
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)

        tmp_var = self.tmp_variable(statements)

        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_operand}})
        return tmp_var
    
    def ternary_expression(self, node, statements):
        condition = self.find_child_by_field(node, "condition")
        consequence = self.find_child_by_field(node, "consequence")
        alternative = self.find_child_by_field(node, "alternative")

        condition = self.parse(condition, statements)

        then_body = []
        else_body = []
        tmp_var = self.tmp_variable(statements)

        expr1 = self.parse(consequence, then_body)
        then_body.append({"assign_stmt": {"target": tmp_var, "operand": expr1}})

        expr2 = self.parse(alternative, else_body)
        else_body.append({"assign_stmt": {"target": tmp_var, "operand": expr2}})

        statements.append({"if_stmt": {"condition": condition, "then_body": then_body, "else_body": else_body}})
        return tmp_var
    
    def update_expression(self, node, statements):
        shadow_node = self.read_node_text(node)
        
        operator = "-"
        if "+" == shadow_node[0] or "+" == shadow_node[-1]:
            operator = "+"

        is_after = False
        if shadow_node[-1] == operator:
            is_after = True

        tmp_var = self.tmp_variable(statements)

        expression = self.find_child_by_field(node, "argument")
        # 等号左边为array[index]或object.field时，先读后写
        if expression.type == "member_expression":
            shadow_object, field = self.parse_field(expression, statements)

            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": field}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append(
                {"assign_stmt": {"target": tmp_var2, "operator": operator, "operand": tmp_var, "operand2": "1"}})
            statements.append({"field_write": {"receiver_object": shadow_object, "field": field, "source": tmp_var2}})

            if is_after:
                return tmp_var
            return tmp_var2
        
        if expression.type == "subscript_expression":
            shadow_array, shadow_index = self.parse_array(expression, statements)

            statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append(
                {"assign_stmt": {"target": tmp_var2, "operator": operator, "operand": tmp_var, "operand2": "1"}})
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": tmp_var2}})

            if is_after:
                return tmp_var
            return tmp_var2

        shadow_expression = self.parse(expression, statements)

        # 注意下面两条glang指令的顺序
        # 如果++/--在后面，则tmp_var为原值
        if is_after:
            statements.append({"assign_stmt": {"target": tmp_var, "operand": shadow_expression}})
        
        statements.append({"assign_stmt": {"target": shadow_expression, "operator": operator,
                                           "operand": shadow_expression, "operand2": "1"}})
        
        # 如果++/--在前面，则tmp_var为更新后的值
        if not is_after:
            statements.append({"assign_stmt": {"target": tmp_var, "operand": shadow_expression}})

        return tmp_var

    def assignment_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator).replace("=", "")

        shadow_right = self.parse(right, statements)

        if left.type == "member_expression":
            shadow_object, field = self.parse_field(left, statements)
            if not shadow_operator:
                statements.append(
                    {"field_write": {"receiver_object": shadow_object, "field": field, "source": shadow_right}})
                return shadow_right

            tmp_var = self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": field}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"field_write": {"receiver_object": shadow_object, "field": field, "source": tmp_var2}})

            return tmp_var2
        
        if left.type == "subscript_expression":
            shadow_array, shadow_index = self.parse_array(left, statements)

            if not shadow_operator:
                statements.append(
                    {"array_write": {"array": shadow_array, "index": shadow_index, "source": shadow_right}})
                return shadow_right

            tmp_var = self.tmp_variable(statements)
            statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": tmp_var2}})

            return tmp_var2
        
        # 数组解构
        if left.type == "array_pattern":
            index = 0
            for p in left.named_children:
                if self.is_comment(p):
                    continue

                pattern = self.parse(p, statements)

                statements.append({"array_read": {"target": pattern, "array": shadow_right, "index": str(index)}})
                index += 1
            
            return shadow_right
        
        # 对象解构
        if left.type == "object_pattern":
            for p in left.named_children:
                if self.is_comment(p):
                    continue

                if p.type == "shorthand_property_identifier_pattern":
                    pattern = self.read_node_text(p)

                    statements.append({"field_read": {"target": pattern, "receiver_object": shadow_right, "field": pattern}})
                elif p.type == "pair_pattern":
                    left_child = self.find_child_by_field(p, "key")
                    right_child = self.find_child_by_field(p, "value")

                    shadow_left_child = self.property_name(left_child)
                    shadow_right_child = self.parse(right_child, statements)

                    statements.append({"field_read": {"target": shadow_right_child, "receiver_object": shadow_right, "field": shadow_left_child}})
            
            return shadow_right
        
        shadow_left = self.read_node_text(left)
        if not shadow_operator:
            statements.append({"assign_stmt": {"target": shadow_left, "operand": shadow_right}})
        else:
            statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                               "operand": shadow_left, "operand2": shadow_right}})
        return shadow_left

    def parse_field(self, node, statements):
        myobject = self.find_child_by_field(node, "object")
        shadow_object = self.parse(myobject, statements)

        field = self.find_child_by_field(node, "property")
        shadow_field = self.read_node_text(field)
        return (shadow_object, shadow_field)

    def member_expression(self, node, statements):
        shadow_object, shadow_field = self.parse_field(node, statements)
        tmp_var = self.tmp_variable(statements)
        statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": shadow_field}})
        return tmp_var
    
    def parse_array(self, node, statements):
        array = self.find_child_by_field(node, "object")
        shadow_object = self.parse(array, statements)

        index = self.find_child_by_field(node, "index")
        shadow_index = self.parse(index, statements)
        return (shadow_object, shadow_index)
    
    # 使用[]方式访问Object，本质上与数组访问相同
    def subscript_expression(self, node, statements):
        shadow_array, shadow_index = self.parse_array(node, statements)
        tmp_var = self.tmp_variable(statements)
        statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index}})
        return tmp_var
    
    def call_expression(self, node, statements):
        name = self.find_child_by_field(node, "function")
        shadow_name = self.parse(name, statements)

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
        statements.append({"call_stmt": {"target": tmp_return, "name": shadow_name, "args": args_list}})

        return tmp_return
    
    # 以[]的形式创建新数组，例如let arr = [1, 2, 3]
    def new_array(self, node, statements):
        # 创建数组
        tmp_var = self.tmp_variable(statements)
        statements.append({"new_array": {"target": tmp_var}})

        # 写入数组
        index = 0
        for child in node.named_children:
            if self.is_comment(child):
                continue

            shadow_child = self.parse(child, statements)
            statements.append({"array_write": {"array": tmp_var, "index": str(index), "source": shadow_child}})
            index += 1

        return tmp_var
    
    # 解析Object {} 中的key-value
    def parse_pair(self, node, statements):
        key = self.find_child_by_field(node, "key")
        value = self.find_child_by_field(node, "value")
        
        if key.type == "property_identifier":
            shadow_key = self.read_node_text(key)
        else:
            shadow_key = self.parse(key, statements)
        shadow_value = self.parse(value, statements)

        return (shadow_key, shadow_value)
    
    # 以{}的形式创建Object，例如let obj = { name: "Alice"}
    def new_object(self, node, statements):
        # 创建Object
        tmp_var = self.tmp_variable(statements)
        statements.append({"new_instance": {"data_type": "Object", "target": tmp_var}})

        # 写入Object
        for child in node.named_children:
            if self.is_comment(child):
                continue
            
            if child.type == "pair":
                # 处理键值对
                shadow_key, shadow_value = self.parse_pair(child, statements)
            elif child.type == "method_definition":
                """
                    处理方法定义, 例如下面的sayHello方法, 这里的处理方式为:
                	    将sayHello当作obj的一个field, field对应的value为一个名为sayHello的函数
                    const obj = {
                        sayHello(){

                        }
                    } 
                """
                shadow_key = shadow_value = self.function_declaration(child, statements)
            
            statements.append({"field_write": {"receiver_object": tmp_var, "field": shadow_key, "source": shadow_value}})

        return tmp_var

    # 处理new data_type(args)
    def new_expression(self, node, statements):
        glang_node = {}

        mytype = self.find_child_by_field(node, "constructor")
        shadow_mytype = self.read_node_text(mytype)
        glang_node["data_type"] = shadow_mytype

        arguments = self.find_child_by_field(node, "arguments")
        arguments_list = []
        if arguments.named_child_count > 0:
            for arg in arguments.named_children:
                if self.is_comment(arg):
                    continue

                shadow_arg = self.parse(arg, statements)
                if shadow_arg:
                    arguments_list.append(shadow_arg)
        
        glang_node["args"] = arguments_list

        tmp_var = self.tmp_variable(statements)
        glang_node["target"] = tmp_var
        
        statements.append({"new_instance": glang_node})
        return tmp_var

    def await_expression(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)

        statements.append({"await_stmt": {"target": shadow_expr}})
        return shadow_expr
    
    def yield_expression(self, node, statements):
        shadow_expr = ""
        if node.named_child_count > 0:
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)

        statements.append({"yield_stmt": {"target": shadow_expr}})
        return shadow_expr



    """
        statement部分 
    """ 

    def return_statement(self, node, statements):
        shadow_name = "undefined"   # 单用return时，返回undefined
        if node.named_child_count > 0:
            name = node.named_children[0]
            shadow_name = self.parse(name, statements)

        statements.append({"return_stmt": {"target": shadow_name}})
        return shadow_name
    
    def if_statement(self, node, statements):
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

    def while_statement(self, node, statements):
        condition = self.find_child_by_field(node, "condition")
        body = self.find_child_by_field(node, "body")

        new_condition_init = []

        shadow_condition = self.parse(condition, new_condition_init)

        new_while_body = []
        self.parse(body, new_while_body)

        # 保证了条件变量名的一致性
        statements.extend(new_condition_init)
        new_while_body.extend(new_condition_init)   # 有必要，比如条件为(i++ < 5)

        statements.append({"while_stmt": {"condition": shadow_condition, "body": new_while_body}})

    def dowhile_statement(self, node, statements):
        body = self.find_child_by_field(node, "body")
        condition = self.find_child_by_field(node, "condition")

        do_body = []
        self.parse(body, do_body)
        shadow_condition = self.parse(condition, do_body)

        statements.append({"dowhile_stmt": {"body": do_body, "condition": shadow_condition}})

    def for_statement(self, node, statements):
        init = self.find_child_by_field(node, "initializer")
        condition = self.find_child_by_field(node, "condition")
        update = self.find_child_by_field(node, "increment")

        init_body = []
        condition_init = []
        update_body = []

        self.parse(init, init_body)
        shadow_condition = self.parse(condition, condition_init)
        self.parse(update, update_body)

        for_body = []

        block = self.find_child_by_field(node, "body")
        self.parse(block, for_body)

        statements.append({"for_stmt":
                               {"init_body": init_body,
                                "condition_prebody": condition_init,
                                "condition": shadow_condition,
                                "update_body": update_body,
                                "body": for_body}})

    def forin_statement(self, node, statements):
        child = self.find_child_by_field(node, "kind")
        modifiers = self.read_node_text(child).split()  # modifiers中的内容为let/const/var

        for_body = []

        left = self.find_child_by_field(node, "left")
        if left.type == "array_pattern":
            '''
                for (const [key, value] of iterable) {
                    console.log(value);
                }
                对于这种形式的语句, forin_stmt指令中的name为一个临时变量, 
                    在body中将该临时变量解构赋值给key与value
            '''
            shadow_left = self.tmp_variable(statements)
            index = 0
            for p in left.named_children:
                if self.is_comment(p):
                    continue

                name = self.parse(p, statements)
                for_body.append({"array_read": {"target": name, "array": shadow_left, "index": str(index)}})
                index += 1
        else:
            shadow_left = self.parse(left, statements)

        right = self.find_child_by_field(node, "right")
        shadow_right = self.parse(right, statements)

        body = self.find_child_by_field(node, "body")
        self.parse(body, for_body)

        statements.append({"forin_stmt":
                               {"attr": modifiers,
                                "name": shadow_left,
                                "target": shadow_right,
                                "body": for_body}})

    def break_statement(self, node, statements):
        shadow_name = ""
        name = self.find_child_by_field(node, "label")
        if name:
            shadow_name = self.read_node_text(name)

        statements.append({"break_stmt": {"target": shadow_name}})
    
    def continue_statement(self, node, statements):
        shadow_name = ""
        name = self.find_child_by_field(node, "label")
        if name:
            shadow_name = self.read_node_text(name)

        statements.append({"continue_stmt": {"target": shadow_name}})

    def try_statement(self, node, statements):
        try_op = {}
        try_body = []
        catch_body = []
        finally_body = []

        # 处理try
        body = self.find_child_by_field(node, "body")
        self.parse(body, try_body)
        try_op["body"] = try_body

        # 处理catch
        catch_clause = self.find_child_by_field(node, "handler")
        if catch_clause:
            catch_op = {}
            shadow_catch_clause_body = []

            condition = self.find_child_by_field(catch_clause, "parameter")
            if condition:
                if condition.type == "array_pattern":
                    # 处理例如catch([a, b])

                    shadow_condition = self.tmp_variable(catch_body)
                    index = 0
                    for p in condition.named_children:
                        if self.is_comment(p):
                            continue
                        
                        name = self.parse(p, catch_body)
                        shadow_catch_clause_body.append({"array_read": {"target": name, "array": shadow_condition, "index": str(index)}})
                        index += 1

                elif condition.type == "object_pattern":
                    # 处理例如catch({a, b})或catch({a: v1, b: v2})

                    shadow_condition = self.tmp_variable(catch_body)

                    for p in condition.named_children:
                        if self.is_comment(p):
                            continue

                        if p.type == "shorthand_property_identifier_pattern":
                            name = self.read_node_text(p)

                            shadow_catch_clause_body.append({"field_read": {"target": name, "receiver_object": shadow_condition, "field": name}})
                        elif p.type == "pair_pattern":
                            left_child = self.find_child_by_field(p, "key")
                            right_child = self.find_child_by_field(p, "value")

                            shadow_left_child = self.property_name(left_child)
                            shadow_right_child = self.parse(right_child, catch_body)

                            shadow_catch_clause_body.append({"field_read": {"target": shadow_right_child, "receiver_object": shadow_condition, "field": shadow_left_child}})

                else:
                    shadow_condition = self.parse(condition, catch_body)
                
                catch_op["exception"] = shadow_condition

            catch_clause_body = self.find_child_by_field(catch_clause, "body")
            self.parse(catch_clause_body, shadow_catch_clause_body)
            catch_op["body"] = shadow_catch_clause_body
            catch_body.append({"catch_clause": catch_op})
        
        try_op["catch_body"] = catch_body

        # 处理finally
        finally_clause = self.find_child_by_field(node, "finalizer")
        if finally_clause:
            finally_clause_body = self.find_child_by_field(finally_clause, "body")
            self.parse(finally_clause_body, finally_body)
        try_op["final_body"] = finally_body

        statements.append({"try_stmt": try_op})

    def throw_statement(self, node, statements):
        shadow_expr = ""
        if node.named_child_count > 0:
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)
        statements.append({"throw_stmt": {"target": shadow_expr}})

    def labeled_statement(self, node, statements):
        name = self.find_child_by_field(node, "label")

        shadow_name = self.read_node_text(name)
        statements.append({"label_stmt": {"name": shadow_name}})

        stmt = self.find_child_by_field(node, "body")
        self.parse(stmt, statements)

    def with_statement(self, node, statements):
        obj = self.find_child_by_field(node, "object")
        body = self.find_child_by_field(node, "body")

        shadow_obj = self.parse(obj, statements)

        with_body = []
        self.parse(body, with_body)

        # 由于with_init不适用于JavaScript，因此这里给with_stmt加了一个名为name的field
        statements.append({"with_stmt": {"name": shadow_obj, "body": with_body}})

    def switch_statement(self, node, statements):
        condition = self.find_child_by_field(node, "value")
        shadow_condition = self.parse(condition, statements)

        switch_block = self.find_child_by_field(node, "body")

        switch_stmt_list = []

        for child in switch_block.named_children:
            if self.is_comment(child):
                continue
            
            stmts = self.find_children_by_field(child, "body")
            if child.type == "switch_default":
                if len(stmts) == 0:
                    continue

                new_body = []
                for default_stmt in stmts:
                    self.parse(default_stmt, new_body)

                switch_stmt_list.append({"default_stmt": {"body": new_body}})
            else:   # case语句
                case_condition = self.find_child_by_field(child, "value")
                shadow_case_condition = self.parse(case_condition, statements)

                if len(stmts) == 0:
                    switch_stmt_list.append({"case_stmt": {"condition": shadow_case_condition}})
                    continue

                new_body = []
                for case_stmt in stmts:
                    self.parse(case_stmt, new_body)

                switch_stmt_list.append({"case_stmt": {"condition": shadow_case_condition, "body": new_body}})
                            
        statements.append({"switch_stmt": {"condition": shadow_condition, "body": switch_stmt_list}})

    def import_statement(self, node, statements):
        # 为import_stmt和import_as_stmt加了一个名为source的field

        import_clause = self.find_child_by_type(node, "import_clause")
        import_source = self.find_child_by_field(node, "source")

        source_str = self.parse(import_source, statements)

        # side effect import, 格式为: import "module-name";
        if not import_clause:
            statements.append({"import_stmt": {"source": source_str}})
            return

        # 如何区分import x from "yyy" 与import {x} from "yyy"
        for import_clause_child in import_clause.named_children:
            if self.is_comment(import_clause_child):
                continue

            # default import, 格式为: import name from "module-name";
            if import_clause_child.type == "identifier":
                shadow_name = self.parse(import_clause_child, statements)
                statements.append({"import_stmt": {"name": shadow_name, "source": source_str}})

            # namespace import, 格式为: import * as alias from "module-name";
            elif import_clause_child.type == "namespace_import":
                alias = self.find_child_by_type(import_clause_child, "identifier")
                shadow_alias = self.parse(alias, statements)
                statements.append({"import_as_stmt": {"name": "*", "alias": shadow_alias, "source": source_str}})
            
            # named import, 格式为：import { name [as alias], ... } from "module-name";
            else:
                import_specifiers = self.find_children_by_type(import_clause_child, "import_specifier")
                if len(import_specifiers) == 0:
                    statements.append({"import_stmt": {"name": "", "source": source_str}})
                else:
                    for specifier in import_specifiers:
                        name = self.find_child_by_field(specifier, "name")
                        shadow_name = self.parse(name, statements)

                        alias = self.find_child_by_field(specifier, "alias")
                        if alias:
                            shadow_alias = self.parse(alias, statements)
                            statements.append({"import_as_stmt": {"name": shadow_name, "alias": shadow_alias, "source": source_str}})
                        else:
                            statements.append({"import_stmt": {"name": shadow_name, "source": source_str}})

    # source_str为None时对应export {...}，不为None时对应export {...} from ...
    def parse_export_clause(self, node, statements, source_str=None):
        export_specifiers = self.find_children_by_type(node, "export_specifier")

        if len(export_specifiers) == 0:
            # {}中没有内容，因此name为""
            if source_str == None:
                statements.append({"export": {"name": ""}})
            else:
                statements.append({"export": {"name": "", "source": source_str}})
        else:
            for specifier in export_specifiers:     # specifier的格式为：name [as alias]
                name = self.find_child_by_field(specifier, "name")
                shadow_name = self.parse(name, statements)

                alias = self.find_child_by_field(specifier, "alias")
                if alias:
                    shadow_alias = self.parse(alias, statements)
                    if source_str == None:
                        statements.append({"export": {"name": shadow_name, "alias": shadow_alias}})
                    else:
                        statements.append({"export": {"name": shadow_name, "alias": shadow_alias, "source": source_str}})
                else:
                    if source_str == None:
                        statements.append({"export": {"name": shadow_name}})
                    else:
                        statements.append({"export": {"name": shadow_name, "source": source_str}})

    def export_statement(self, node, statements):
        export_source = self.find_child_by_field(node, "source")

        if export_source:   # 带有from字句
            source_str = self.parse(export_source, statements)

            namespace_export = self.find_child_by_type(node, "namespace_export")
            if namespace_export:
                # 格式为：export * as ... from ...
                alias = namespace_export.named_children[-1]    # 索引取-1可以将comment过滤掉
                shadow_alias = self.parse(alias, statements)
                statements.append({"export": {"name": "*", "alias": shadow_alias, "source": source_str}})
            else:
                export_clause = self.find_child_by_type(node, "export_clause")
                if export_clause:
                    # 格式为：export { name1 , /* …, */ nameN } from ...
                    #       或者：export { import1 as name1, import2 as name2, /* …, */ nameN } from ...
                    self.parse_export_clause(export_clause, statements, source_str)
                else:
                    # 格式为：export * from ...
                    statements.append({"export": {"name": "*", "source": source_str}})
        
        else:   # 不带from字句
            export_clause = self.find_child_by_type(node, "export_clause")
            if export_clause:
                # 格式为：export { name1, /* …, */ nameN }
                #       或者：export { variable1 as name1, variable2 as name2, /* …, */ nameN }
                self.parse_export_clause(export_clause, statements)
            else:
                declaration = self.find_child_by_field(node, "declaration")
                if declaration: # 这里把default的存在与否归为一种情况
                    # 格式为：export [default] declaration
                    # 解析declaration语句得到的返回值，只是用于辅助确定定义了哪些变量
                    declared_list = self.parse(declaration, statements)

                    for i in range(len(declared_list)):
                        statements.append({"export": {"name": declared_list[i]}})
                else:
                    value = self.find_child_by_field(node, "value")
                    if value:
                        # 格式为： export default expression
                        shadow_value = self.parse(value, statements)
                        statements.append({"export": {"name": shadow_value}})

    def empty_statement(self, node, statements):
        return ""



    """
        declaration部分 
    """ 

    # 处理let/const/var变量声明
    def variable_and_constant_declaration(self, node, statements):
        attr = []
        kind = self.find_child_by_field(node, "kind")
        if kind:    # 使用let/const声明
            shadow_kind = self.read_node_text(kind)
            attr.append(shadow_kind)
        else:   # 使用var声明
            attr.append("var")

        # 用于返回声明的变量名，以便export语句导出
        return_vals = []

        # 逐个处理，先声明（variable_decl），如果有初始值，再进行赋值
        declarators = node.named_children
        for child in declarators: 
            if self.is_comment(child):
                continue

            has_init = False
            name = self.find_child_by_field(child, "name")
            value = self.find_child_by_field(child, "value")
            if value:
                has_init = True
                shadow_value = self.parse(value, statements)

            if name.type == "identifier":
                shadow_name = self.read_node_text(name)

                return_vals.append(shadow_name)

                statements.append({"variable_decl": {"attr": attr, "name": shadow_name}})

                if has_init:
                    statements.append({"assign_stmt": {"target": shadow_name, "operand": shadow_value}})
            elif name.type == "array_pattern":  # 数组解构
                index = 0
                for p in name.named_children:
                    if self.is_comment(p):
                        continue

                    pattern = self.parse(p, statements)

                    return_vals.append(pattern)

                    statements.append({"variable_decl": {"attr": attr, "name": pattern}})

                    if has_init:
                        statements.append({"array_read": {"target": pattern, "array": shadow_value, "index": str(index)}})
                    index += 1 
            elif name.type == "object_pattern": # 对象解构
                for p in name.named_children:
                    if self.is_comment(p):
                        continue

                    if p.type == "shorthand_property_identifier_pattern":
                        # 例如： const {name, age} = {name: "tom", age: 18}
                        pattern = self.read_node_text(p)

                        return_vals.append(pattern)

                        statements.append({"variable_decl": {"attr": attr, "name": pattern}})
                        
                        if has_init:
                            statements.append({"field_read": {"target": pattern, "receiver_object": shadow_value, "field": pattern}})
                    elif p.type == "pair_pattern":
                        # 例如： const {name: n, age: a} = {name: "tom", age: 18}
                        left_child = self.find_child_by_field(p, "key")
                        right_child = self.find_child_by_field(p, "value")

                        shadow_left_child = self.property_name(left_child, statements)
                        shadow_right_child = self.parse(right_child, statements)

                        return_vals.append(shadow_right_child)

                        statements.append({"variable_decl": {"attr": attr, "name": shadow_right_child}})

                        if has_init:
                            statements.append({"field_read": {"target": shadow_right_child, "receiver_object": shadow_value, "field": shadow_left_child}})

        return return_vals

    def function_declaration(self, node, statements):
        glang_node = {}

        # field: attr
        glang_node["attr"] = []
        shadow_children = list(map(self.read_node_text, node.children))
        if "async" in shadow_children:
            glang_node["attr"].append("async")
        if "*" in shadow_children:
            glang_node["attr"].append("*")
        
        # 以下三个专门用于method_definition
        if "static" in shadow_children:
            glang_node["attr"].append("static")
        if "get" in shadow_children:
            glang_node["attr"].append("get")
        if "set" in shadow_children:
            glang_node["attr"].append("set")

        # field: name
        name = self.find_child_by_field(node, "name")
        if not name:    # function_expression与arrow_function
            shadow_name = self.tmp_method() # 为匿名函数起一个临时名字
        elif node.type == "method_definition":
            shadow_name = self.property_name(name, statements)
        else:
            shadow_name = self.read_node_text(name)
        glang_node["name"] = shadow_name

        # field: parameters and init
        glang_node["parameters"] = []
        glang_node["init"] = []
        simple_param = self.find_child_by_field(node, "parameter")
        if simple_param:    # arrow_function, 仅有单个参数，外层没有"()"
            shadow_name = self.read_node_text(simple_param)
            glang_node["parameters"].append({"parameter_decl": {"attr": [], "name": shadow_name}})
        else:
            parameters = self.find_child_by_field(node, "parameters")
            for child in parameters.named_children:
                if self.is_comment(child):
                    continue

                self.formal_parameter(child, glang_node["init"])
                # 将parameter_decl从init移入parameters
                glang_node["parameters"].append(glang_node["init"].pop())

        # field: body
        glang_node["body"] = []
        body = self.find_child_by_field(node, "body")
        if (self.is_expression(body) or self.is_literal(body) or self.is_identifier(body)):
            # 函数体为表达式时(arrow_function)
            shadow_expr = self.parse(body, glang_node["body"])
            glang_node["body"].append({"return_stmt": {"target": shadow_expr}})
        else:
            # 函数体为代码块时
            self.parse(body, glang_node["body"])

        statements.append({"method_decl": glang_node})
        if (node.type == "function_declaration"
                or node.type == "generator_function_declaration"):
            return [shadow_name]    # 仅供export_statement使用
        else:
            return shadow_name
    
    def formal_parameter(self, node, statements):
        attr = []

        if node.type == "assignment_pattern":
            name = self.find_child_by_field(node, "left")
            value = self.find_child_by_field(node, "right")

            shadow_name = self.parse(name, statements)
            shadow_value = self.parse(value, statements)

            statements.append({"assign_stmt": {"target": shadow_name, "operand": shadow_value}})

        elif node.type == "rest_pattern":   # 处理形参列表中的剩余参数(...arg)
            attr.append("list")
            name = node.named_children[-1]
            shadow_name = self.parse(name, statements)
        
        else:
            shadow_name = self.parse(node, statements)

        statements.append({"parameter_decl": {"attr": attr, "name": shadow_name}})

    def class_declaration(self, node, statements):
        glang_node = {}

        # field: attr
        glang_node["attr"] = ["class"]

        # field: name
        name = self.find_child_by_field(node, "name")
        if name:
            shadow_name = self.read_node_text(name)
        else:
            shadow_name = self.tmp_variable(statements) # 匿名类
        glang_node["name"] = shadow_name

        # field: type_parameters
        glang_node["type_parameters"] = []

        # field: supers
        glang_node["supers"] = []
        class_heritage = self.find_child_by_type(node, "class_heritage")
        if class_heritage:
            expr = class_heritage.named_children[-1]
            shadow_expr = self.parse(expr, statements)
            glang_node["supers"].append(shadow_expr)
        
        # class_body
        body = self.find_child_by_field(node, "body")
        self.class_body(body, glang_node)

        statements.append({"class_decl": glang_node})
        if node.type == "class":
            return shadow_name
        else:
            return [shadow_name]    # 仅供export_statement使用
    
    def class_body(self, node, glang_node):
        glang_node["init"] = []
        glang_node["static_init"] = []
        glang_node["fields"] = []
        glang_node["methods"] = []
        glang_node["nested"] = []

        # field_definition
        field_defs = self.find_children_by_type(node, "field_definition")
        for field_def in field_defs:
            init_type = "init"
            shadow_children = list(map(self.read_node_text, field_def.children))
            if "static" in shadow_children:
                init_type = "static_init"

            self.field_definition(field_def, glang_node[init_type])
            # 将variable_decl从init/static_init移入fields
            glang_node["fields"].append(glang_node[init_type].pop())
        
        # class_static_block
        static_blocks = self.find_children_by_type(node, "class_static_block")
        for static_block in static_blocks:
            self.parse(static_block, glang_node["static_init"])

        # method_definition
        method_defs = self.find_children_by_type(node, "method_definition")
        for method_def in method_defs:
            self.function_declaration(method_def, glang_node["methods"])

    def field_definition(self, node, statements):
        attr = []
        shadow_children = list(map(self.read_node_text, node.children))
        if "static" in shadow_children:
            attr.append("static")

        prop_name = self.find_child_by_field(node, "property")
        shadow_name = self.property_name(prop_name, statements)

        init_value = self.find_child_by_field(node, "value")
        if init_value:
            shadow_value = self.parse(init_value, statements)
            statements.append({"field_write": {"receiver_object": self.global_this(), 
                                               "field": shadow_name, "source": shadow_value}})
        
        # 最后加入variable_decl，是为了便于之后将其从init移入fields
        statements.append({"variable_decl": {"attr": attr, "name": shadow_name}})
    
    def property_name(self, node, statements):
        if (node.type == "property_identifier" or
                node.type == "private_property_identifier"):
            shadow_name = self.read_node_text(node)
        else:
            shadow_name = self.parse(node, statements)
        
        return shadow_name

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "number"                            : self.regular_number_literal,
            "true"                          	: self.regular_literal,
            "false"                         	: self.regular_literal,
            "null"                           	: self.regular_literal,
            "undefined"                         : self.regular_literal,
            "regex"                             : self.regular_literal,
            "string"                            : self.string_literal,
            "template_string"                   : self.string_literal,
            "template_substitution"             : self.template_substitution,
            "this"                          	: self.this_literal,
            "super"                         	: self.super_literal,
        }

        return LITERAL_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
            "variable_declaration":             self.variable_and_constant_declaration,
            "lexical_declaration":              self.variable_and_constant_declaration,
            "class_declaration":                self.class_declaration,
            "function_declaration":             self.function_declaration,
            "generator_function_declaration":   self.function_declaration,
        }

        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "binary_expression"                 : self.binary_expression,
            "unary_expression"                  : self.unary_expression,
            "ternary_expression"                : self.ternary_expression,
            "update_expression"                 : self.update_expression,
            "assignment_expression"             : self.assignment_expression,
            "augmented_assignment_expression"   : self.assignment_expression,
            "member_expression"                 : self.member_expression,
            "subscript_expression"              : self.subscript_expression,
            "call_expression"                   : self.call_expression,
            "function_expression"               : self.function_declaration,
            "generator_function"                : self.function_declaration,
            "arrow_function"                    : self.function_declaration,
            "array"                             : self.new_array,
            "object"                            : self.new_object,
            "new_expression"                    : self.new_expression,
            "await_expression"                  : self.await_expression,
            "yield_expression"                  : self.yield_expression,
            "class"                             : self.class_declaration    # new
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            "return_statement":             self.return_statement,
            "if_statement":                 self.if_statement,
            "while_statement":              self.while_statement,
            "do_statement":                 self.dowhile_statement,
            "for_statement":                self.for_statement,
            "for_in_statement":             self.forin_statement,
            "break_statement":              self.break_statement,
            "continue_statement":           self.continue_statement,
            "try_statement":                self.try_statement,
            "throw_statement":              self.throw_statement,
            "labeled_statement":            self.labeled_statement,
            "with_statement":               self.with_statement,
            "switch_statement":             self.switch_statement,
            "import_statement":             self.import_statement,
            "export_statement":             self.export_statement,
            "empty_statement":              self.empty_statement,
        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)