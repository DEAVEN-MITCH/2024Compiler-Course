#!/usr/bin/env python3

from lian.config import config
from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type in ["line_comment", "block_comment"]

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

        ret = self.handle_hex_string(ret)

        return self.escape_string(ret)

    def string_interpolation(self, node, statements, replacement):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)
        replacement.append[(expr, shadow_expr)]
        return shadow_expr

    def regular_number_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        value = self.common_eval(value)
        return str(value)

    def hex_float_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        try:
            value = float.fromhex(value)
        except:
            pass
        return str(value)

    def regular_literal(self, node, statements, replacement):
        return self.read_node_text(node)

    def character_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        return "'%s'" % value

    def this_literal(self, node, statements, replacement):
        return self.global_this()

    def super_literal(self, node, statements, replacement):
        return self.global_super()

    def is_constant_literal(self, node):
        return node.type in [
            "decimal_integer_literal",
            "hex_integer_literal",
            "octal_integer_literal",
            "binary_integer_literal",
            "decimal_floating_point_literal",
            "hex_floating_point_literal",
            "true",
            "false",
            "character_literal",
            "null_literal",
            "class_literal",
            "string_literal",
            "string_interpolation",
        ]

    CLASS_TYPE_MAP = {
        "class_declaration": "class",
        "interface_declaration": "interface",
        "record_declaration": "record",
    }

    def class_declaration(self, node, statements):
        glang_node = {}

        glang_node["attr"] = []
        glang_node["init"] = []
        glang_node["static_init"] = []
        glang_node["fields"] = []
        glang_node["member_methods"] = []
        glang_node["nested"] = []

        if node.type in self.CLASS_TYPE_MAP:
            glang_node["attr"].append(self.CLASS_TYPE_MAP[node.type])

        child = self.find_child_by_type(node, "modifiers")
        modifiers = self.read_node_text(child).split()
        glang_node["attr"].extend(modifiers)

        child = self.find_child_by_field(node, "name")
        if child:
            glang_node["name"] = self.read_node_text(child)

        child = self.find_child_by_field(node, "type_parameters")
        if child:
            type_parameters = self.read_node_text(child)
            glang_node["type_parameters"] = type_parameters[1:-1]

        if (glang_node["attr"][0] == "record"):
            glang_node["parameters"] = []
            child = self.find_child_by_field(node, "parameters")
            if child and child.named_child_count > 0:
                # need to deal with parameters
                for p in child.named_children:
                    self.parse(p, glang_node["init"])
                    if len(glang_node["init"]) > 0:
                        parameter = glang_node["init"][-1]
                        glang_node["fields"].append({
                            "variable_decl": {
                                "attr": ["private", "final"],
                                "data_type": parameter["parameter_decl"]["data_type"],
                                "name": parameter["parameter_decl"]["name"]}})
                        glang_node["parameters"].append(parameter)

        glang_node["supers"] = []
        child = self.find_child_by_field(node, "superclass")
        if child:
            superclass = self.read_node_text(child)
            parent_class = superclass.replace("extends", "").split()[0]
            glang_node["supers"].append(parent_class)

        for name in ["interfaces", "permits"]:
            child = self.find_child_by_field(node, name)
            if not child:
                continue

            for c in child.named_children[0].named_children:
                class_name = self.read_node_text(c)
                glang_node["supers"].append(class_name)

        for name in ["extends_interfaces"]:
            child = self.find_child_by_type(node, name)
            if not child:
                continue

            for c in child.named_children[0].named_children:
                name = self.read_node_text(c)
                glang_node["supers"].append(name)

        child = self.find_child_by_field(node, "body")
        self.class_body(child, glang_node)

        statements.append({f"{self.CLASS_TYPE_MAP[node.type]}_decl": glang_node})

    def class_body(self, node, glang_node):
        if not node:
            return
        # static_member_field -> static_init -> member_field -> init -> constructor
        children = self.find_children_by_type(node, "field_declaration")
        children.extend(self.find_children_by_type(node, "constant_declaration"))
        if children:
            for child in children:
                statements = []
                extra = glang_node["init"]
                modifiers = self.find_child_by_type(child, "modifiers")
                if modifiers:
                    if "static" in self.read_node_text(modifiers).split():
                        extra = glang_node["static_init"]

                self.parse(child, statements)
                if statements:
                    for stmt in statements:
                        if "variable_decl" in stmt:
                            glang_node["fields"].append(stmt)
                        elif "constant_decl" in stmt:
                            glang_node["fields"].append(stmt)
                        elif "assign_stmt" in stmt:
                            field = stmt["assign_stmt"]
                            extra.append({"field_write": {"receiver_object": self.global_this(),
                                                          "field": field["target"], "source": field["operand"]}})

        static_init = self.find_children_by_type(node, "static_initializer")
        if static_init:
            for child in static_init:
                self.parse(child, glang_node["static_init"])

        init = self.find_children_by_type(node, "block")
        if init:
            for child in init:
                self.parse(child, glang_node["init"])

        subtypes = ["constructor_declaration", "compact_constructor_declaration", "method_declaration"]
        for st in subtypes:
            children = self.find_children_by_type(node, st)
            if not children:
                continue

            for child in children:
                self.parse(child, glang_node["member_methods"])

        if ("attr" in glang_node and glang_node["attr"] and glang_node["attr"][0] == "record" and glang_node[
            "parameters"]):
            for parameter in glang_node["parameters"]:
                parameter_name = parameter["parameter_decl"]["name"]
                # GL: Don't write the code in this fancy way. It is hard to read
                # is_name_in_member_methods = any(parameter_name == method["method_decl"]["name"] for method in glang_node["member_methods"])
                is_name_in_member_methods = False
                for method in glang_node["member_methods"]:
                    if parameter_name == method["method_decl"]["name"]:
                        is_name_in_member_methods = True
                        break
                if not is_name_in_member_methods:
                    variable = self.tmp_variable(glang_node)
                    glang_node["member_methods"].append({"method_decl": {
                        "data_type": parameter["parameter_decl"]["data_type"],
                        "name": parameter_name,
                        "type_parameters": "",
                        "body": [
                            {"field_read": {
                                "target": variable,
                                "receiver_object": self.global_this(),
                                "field": parameter_name
                            }
                            },
                            {"return": {
                                "target": variable
                            }
                            }
                        ]
                    }})

        subtypes = ["class_declaration", "interface_declaration", "record_declaration",
                    "annotation_type_declaration", "enum_declaration"]
        for st in subtypes:
            children = self.find_children_by_type(node, st)
            if not children:
                continue

            for child in children:
                self.parse(child, glang_node["nested"])

    def method_declaration(self, node, statements):
        child = self.find_child_by_type(node, "modifiers")
        modifiers = self.read_node_text(child).split()

        child = self.find_child_by_field(node, "type_parameters")
        type_parameters = self.read_node_text(child)[1:-1]

        child = self.find_child_by_field(node, "type")
        mytype = self.read_node_text(child)

        child = self.find_child_by_field(node, "name")
        name = self.read_node_text(child)

        new_parameters = []
        init = []
        child = self.find_child_by_field(node, "parameters")
        if child and child.named_child_count > 0:
            # need to deal with parameters
            for p in child.named_children:
                if self.is_comment(p):
                    continue

                self.parse(p, init)
                if len(init) > 0:
                    new_parameters.append(init.pop())

        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                if self.is_comment(stmt):
                    continue

                self.parse(stmt, new_body)

        statements.append(
            {"method_decl": {"attr": modifiers, "data_type": mytype, "name": name, "type_parameters": type_parameters,
                             "parameters": new_parameters, "init": init, "body": new_body}})

    def package_declaration(self, node, statements):
        name = self.read_node_text(node.named_children[0])
        if name:
            statements.append({"package_stmt": {"name": name}})

    def import_declaration(self, node, statements):
        name = self.read_node_text(node).split()[-1][:-1]
        if name:
            statements.append({"import_stmt": {"name": name}})

    def parse_field(self, node, statements):
        myobject = self.find_child_by_field(node, "object")
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
        array = self.find_child_by_field(node, "array")
        shadow_array = self.parse(array, statements)
        index = self.find_child_by_field(node, "index")
        shadow_index = self.parse(index, statements)

        return (shadow_array, shadow_index)

    def array(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        shadow_array, shadow_index = self.parse_array(node, statements)
        statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index}})
        return tmp_var

    def field(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        shadow_object, shadow_field = self.parse_field(node, statements)
        statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": shadow_field}})
        return tmp_var

    def assignment_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator).replace("=", "")

        shadow_right = self.parse(right, statements)

        if left.type == "field_access":
            shadow_object, field = self.parse_field(left, statements)
            if not shadow_operator:
                statements.append(
                    {"field_write": {"receiver_object": shadow_object, "field": field, "source": shadow_right}})
                return shadow_right

            tmp_var = self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": field, }})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"field_write": {"receiver_object": shadow_object, "field": field, "source": tmp_var2}})

            return tmp_var2

        if left.type == "array_access":
            shadow_array, shadow_index = self.parse_array(left, statements)

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

        shadow_left = self.read_node_text(left)
        if not shadow_operator:
            statements.append({"assign_stmt": {"target": shadow_left, "operand": shadow_right}})
        else:
            statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                               "operand": shadow_left, "operand2": shadow_right}})
        return shadow_left

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

    def instanceof_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        shadow_left = self.parse(left, statements)
        # how to deal with right?
        # check the detail at java.grammar.js
        right = self.find_child_by_field(node, "right")

        tmp_var = self.tmp_variable(statements)
        if right:
            statements.append({"assign_stmt":
                                   {"target": tmp_var, "operator": "instanceof", "operand": shadow_left,
                                    "operand2": self.read_node_text(right)}})
        else:
            record_pattern = self.find_child_by_field(node, "pattern")
            if not record_pattern:
                return ""

            # how to deal with this record pattern
            statements.append({"assign_stmt":
                                   {"target": tmp_var, "operator": "instanceof",
                                    "operand": shadow_left, "operand2": self.read_node_text(record_pattern)}})

        return tmp_var

    def unary_expression(self, node, statements):
        operand = self.find_child_by_field(node, "operand")
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

        body = []
        elsebody = []
        tmp_var = self.tmp_variable(statements)

        expr1 = self.parse(consequence, body)
        body.append({"assign_stmt": {"target": tmp_var, "operand": expr1}})

        expr2 = self.parse(alternative, elsebody)
        body.append({"assign_stmt": {"target": tmp_var, "operand": expr2}})

        statements.append({"if": {"condition": condition, "body": body, "elsebody": elsebody}})
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

        expression = node.named_children[0]
        if expression.type == "field_access":
            shadow_object, field = self.parse_field(expression, statements)

            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": field}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append(
                {"assign_stmt": {"target": tmp_var2, "operator": operator, "operand": tmp_var, "operand2": "1"}})
            statements.append({"field_write": {"receiver_object": shadow_object, "field": field, "source": tmp_var2}})

            if is_after:
                return tmp_var
            return tmp_var2

        if expression.type == "array_access":
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

        statements.append({"assign_stmt": {"target": tmp_var, "operand": shadow_expression}})
        statements.append({"assign_stmt": {"target": shadow_expression, "operator": operator,
                                           "operand": shadow_expression, "operand2": "1"}})

        if is_after:
            return tmp_var
        return shadow_node

    def cast_expression(self, node, statements):
        value = self.find_child_by_field(node, "value")
        shadow_value = self.parse(value, statements)

        types = self.find_children_by_field(node, "type")
        for t in types:
            statements.append(
                {"assign_stmt": {"target": shadow_value, "operator": "cast", "operand": self.read_node_text(t)}})

        return shadow_value

    def lambda_expression(self, node, statements):
        tmp_func = self.tmp_method()

        parameters = []
        tmp_body = []
        child = self.find_child_by_field(node, "parameters")
        if child.named_child_count == 0:
            parameters.append({"parameter_decl": {"name": self.read_node_text(child)}})
        else:
            for p in child.named_children:
                if self.is_comment(p):
                    continue

                self.parse(p, tmp_body)
                if len(tmp_body) > 0:
                    parameters.append(tmp_body.pop())

        new_body = []
        body = self.find_child_by_field(node, "body")
        if self.is_expression(body):
            shadow_expr = self.parse(body, new_body)
            new_body.append({"return": {"target": shadow_expr}})
        else:
            for stmt in body.named_children:
                if self.is_comment(stmt):
                    continue

                shadow_expr = self.parse(body, new_body)
                if stmt == body.named_children[-1]:
                    new_body.append({"return": {"target": shadow_expr}})

        statements.append({"method_decl": {"name": tmp_func, "parameters": parameters, "body": new_body}})

        return tmp_func

    """
    # need break
    switch (day) {
        case MONDAY:
        case FRIDAY:
        case SUNDAY:
            numLetters = 6;
            break;

    # no break
    numLetters = switch (day) {
            case MONDAY, FRIDAY, SUNDAY -> 6;
    """

    def switch_expression(self, node, statements):
        switch_ret = self.switch_return()

        is_switch_rule = False
        switch_block = self.find_child_by_field(node, "body")
        for child in switch_block.named_children:
            if self.is_comment(child):
                continue

            if child.type == "switch_rule":
                is_switch_rule = True

            break

        condition = self.find_child_by_field(node, "condition")
        shadow_condition = self.parse(condition, statements)

        switch_stmt_list = []

        for child in switch_block.named_children:
            if self.is_comment(child):
                continue

            if self.read_node_text(child.children[0]) == "default":
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

        statements.append({"switch_stmt": {"condition": shadow_condition, "body": switch_stmt_list}})
        return switch_ret

    def call_expression(self, node, statements):
        # SomeClass.super.<ArgType>genericMethod()

        name = self.find_child_by_field(node, "name")
        shadow_name = self.parse(name, statements)

        shadow_object = ""
        myobject = self.find_child_by_field(node, "object")
        type_text = ""
        if myobject:
            shadow_object = self.parse(myobject, statements)
            type_arguments = self.find_child_by_field(node, "type_arguments")
            if type_arguments:
                type_text = self.read_node_text(type_arguments)[1:-1]

            tmp_var = self.tmp_variable(statements)
            statements.append(
                {"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": shadow_name}})
            shadow_name = tmp_var

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

        return self.global_return()

    def new_array(self, node, statements):
        mytype = self.find_child_by_field(node, "type")
        shadow_type = self.read_node_text(mytype)

        tmp_var = self.tmp_variable(statements)
        statements.append({"new_array": {"type": shadow_type, "target": tmp_var}})

        value = self.find_child_by_field(node, "value")
        if value and value.named_child_count > 0:
            index = 0
            for child in value.named_children:
                if self.is_comment(child):
                    continue

                shadow_child = self.parse(child, statements)
                statements.append({"array_write": {"array": tmp_var, "index": str(index), "source": shadow_child}})
                index += 1

        return tmp_var

    def new_instance(self, node, statements):
        glang_node = {}

        type_parameters = self.find_child_by_field(node, "type_arguments")
        if type_parameters:
            glang_node["type_parameters"] = self.read_node_text(type_parameters)[1:-1]

        mytype = self.find_child_by_field(node, "type")
        glang_node["data_type"] = self.read_node_text(mytype)

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

        class_body = self.find_child_by_type(node, "class_body")
        self.class_body(class_body, glang_node)

        tmp_var = self.tmp_variable(statements)
        glang_node["target"] = tmp_var

        statements.append({"new_instance": glang_node})

        return tmp_var

    def annotation(self, node, statements):
        return self.read_node_text(node)

    def ignore(self, node=None, statements=[], replacement=[]):
        pass

    def formal_parameter(self, node, statements):
        child = self.find_child_by_type(node, "modifiers")
        modifiers = self.read_node_text(child).split()

        mytype = self.find_child_by_field(node, "type")
        shadow_type = self.read_node_text(mytype)

        if "[]" in shadow_type:
            modifiers.append("array")

        name = self.find_child_by_field(node, "name")
        shadow_name = self.read_node_text(name)

        statements.append({"parameter_decl": {"attr": modifiers, "data_type": shadow_type, "name": shadow_name}})

    def arg_list(self, node, statements):
        child = self.find_child_by_type(node, "modifiers")
        modifiers = self.read_node_text(child).split()
        modifiers.append("list")

        type_index = 0
        if child:
            type_index = 1

        mytype = node.named_children[type_index]
        shadow_type = self.read_node_text(mytype)

        if "[]" in shadow_type:
            modifiers.append("array")

        name = node.named_children[type_index + 1]
        shadow_name = self.read_node_text(name)

        statements.append({"parameter_decl": {"attr": modifiers, "data_type": shadow_type, "name": shadow_name}})

    def label_statement(self, node, statements):
        name = node.named_children[0]

        shadow_name = self.parse(name, statements)
        statements.append({"label_stmt": {"name": shadow_name}})

        if node.named_child_count > 1:
            stmt = node.named_children[1]
            self.parse(stmt, statements)

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

        statements.extend(new_condition_init)
        new_while_body.extend(new_condition_init)

        statements.append({"while_stmt": {"condition": shadow_condition, "body": new_while_body}})

    def for_statement(self, node, statements):
        init_children = self.find_children_by_field(node, "init")
        step_children = self.find_children_by_field(node, "update")

        condition = self.find_child_by_field(node, "condition")

        init_body = []
        condition_init = []
        step_body = []

        shadow_condition = self.parse(condition, condition_init)
        for child in init_children:
            self.parse(child, init_body)

        for child in step_children:
            self.parse(child, step_body)

        for_body = []

        block = self.find_child_by_field(node, "body")
        self.parse(block, for_body)

        statements.append({"for_stmt":
                               {"init_body": init_body,
                                "condition": shadow_condition,
                                "condition_prebody": condition_init,
                                "update_body": step_body,
                                "body": for_body}})

    def forin_statement(self, node, statements):
        child = self.find_child_by_type(node, "modifiers")
        modifiers = self.read_node_text(child).split()

        mytype = self.find_child_by_field(node, "type")
        shadow_type = self.read_node_text(mytype)

        name = self.find_child_by_field(node, "name")
        shadow_name = self.parse(name, statements)

        value = self.find_child_by_field(node, "value")
        shadow_value = self.parse(value, statements)

        for_body = []

        body = self.find_child_by_field(node, "body")
        self.parse(body, for_body)

        statements.append({"forin_stmt":
                               {"attr": modifiers,
                                "data_type": shadow_type,
                                "name": shadow_name,
                                "target": shadow_value,
                                "body": for_body}})

    def assert_statement(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)

        statements.append({"assert_stmt": {"condition": shadow_expr}})

    def dowhile_statement(self, node, statements):
        body = self.find_child_by_field(node, "body")
        condition = self.find_child_by_field(node, "condition")

        do_body = []
        self.parse(body, do_body)
        shadow_condition = self.parse(condition, do_body)

        statements.append({"dowhile_stmt": {"body": do_body, "condition": shadow_condition}})

    def break_statement(self, node, statements):
        shadow_name = ""
        if node.named_child_count > 0:
            name = node.named_children[0]
            shadow_name = self.parse(name, statements)

        statements.append({"break_stmt": {"target": shadow_name}})

    def continue_statement(self, node, statements):
        shadow_name = ""
        if node.named_child_count > 0:
            name = node.named_children[0]
            shadow_name = self.parse(name, statements)

        statements.append({"continue_stmt": {"target": shadow_name}})

    def return_statement(self, node, statements):
        shadow_name = ""
        if node.named_child_count > 0:
            name = node.named_children[0]
            shadow_name = self.parse(name, statements)

        statements.append({"return_stmt": {"target": shadow_name}})
        return shadow_name

    def yield_statement(self, node, statements):
        shadow_expr = ""
        if node.named_child_count > 0:
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)

        statements.append({"yield_stmt": {"target": shadow_expr}})
        return shadow_expr

    def throw_statement(self, node, statements):
        shadow_expr = ""
        if node.named_child_count > 0:
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)
        statements.append({"throw_stmt": {"target": shadow_expr}})

    def try_statement(self, node, statements):
        try_op = {}
        try_body = []
        catch_body = []
        else_body = []
        finally_body = []

        body = self.find_child_by_field(node, "body")
        self.parse(body, try_body)
        try_op["body"] = try_body

        except_clauses = self.find_children_by_type(node, "except_clause")
        if except_clauses:
            for clause in except_clauses:
                except_clause = {}

                condition = clause.children[1 : -2]
                if len(condition) > 0:
                    shadow_condition = self.parse(condition[0], catch_body)
                    except_clause["expcetion"] = shadow_condition

                shadow_except_clause_body = []
                except_clause_body = clause.children[-1]
                self.parse(except_clause_body, shadow_except_clause_body)
                except_clause["body"] = shadow_except_clause_body
                catch_body.append({"catch_clause": except_clause})
        try_op["catch_body"] = catch_body

        finally_clause = self.find_child_by_type(node, "finally_clause")
        if finally_clause:
            finally_clause_body = finally_clause.children[-1]
            self.parse(finally_clause_body, finally_body)
        try_op["final_body"] = finally_body

        statements.append({"try_stmt": try_op})

    def variable_and_constand_declaration(self, node, statements):
        child = self.find_child_by_type(node, "modifiers")
        modifiers = self.read_node_text(child).split()

        mytype = self.find_child_by_field(node, "type")
        shadow_type = self.read_node_text(mytype)

        declarators = self.find_children_by_field(node, "declarator")
        for child in declarators:
            has_init = False
            name = self.find_child_by_field(child, "name")
            name = self.read_node_text(name)
            value = self.find_child_by_field(child, "value")
            if value:
                has_init = True

            if value and value.type == "array_initializer":
                tmp_var = self.tmp_variable(statements)
                statements.append({"new_array": {"type": shadow_type, "target": tmp_var}})

                if value and value.named_child_count > 0:
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

            if "final" in modifiers:
                statements.append({"constant_decl": {"attr": modifiers, "data_type": shadow_type, "name": name}})
                if has_init:
                    statements.append({"assign_stmt": {"target": name, "operand": shadow_value}})

            else:
                statements.append({"variable_decl": {"attr": modifiers, "data_type": shadow_type, "name": name}})
                if has_init:
                    statements.append({"assign_stmt": {"target": name, "operand": shadow_value}})

    def enum_declaration(self, node, statements):
        glang_node = {}
        glang_node["attr"] = []
        glang_node["init"] = []
        glang_node["static_init"] = []
        glang_node["fields"] = []
        glang_node["member_methods"] = []
        glang_node["enum_constants"] = []
        glang_node["nested"] = []

        child = self.find_child_by_type(node, "modifiers")
        glang_node["attr"].extend(self.read_node_text(child).split())

        child = self.find_child_by_field(node, "name")
        glang_node["name"] = self.read_node_text(child)

        glang_node["supers"] = []
        child = self.find_child_by_field(node, "interfaces")
        if (child and child.named_children_count > 0):
            for c in child.named_children[0].named_children:
                if self.is_comment(c):
                    continue
                class_name = self.read_node_text(c)
                glang_node["supers"].append(class_name)

        child = self.find_child_by_field(node, "body")
        self.enum_body(child, glang_node)

        statements.append({"enum_decl": glang_node})

    def enum_body(self, node, glang_node):
        child = self.find_child_by_type(node, "enum_body_declarations")
        if (child):
            self.class_body(child, glang_node)

        children = self.find_children_by_type(node, "enum_constant")
        if children:
            for child in children:
                enum_constant = {}
                enum_constant["attr"] = []
                enum_constant["name"] = []
                enum_constant["args"] = []

                modifiers = self.find_child_by_type(node, "modifiers")
                enum_constant["attr"].extend(self.read_node_text(modifiers).split())

                name = self.find_child_by_field(child, "name")
                enum_constant["name"] = self.read_node_text(name)

                args = self.find_child_by_field(child, "arguments")
                args_list = []

                if args and args.named_child_count > 0:
                    for arg in args.named_children:
                        if self.is_comment(arg):
                            continue
                        shadow_variable = self.parse(child, [])
                        args_list.append(shadow_variable)
                        # args_list.append(self.read_node_text(arg))
                        enum_constant["args"].extend(args_list)

                enum_constant_body = self.find_child_by_field(child, "body")
                if enum_constant_body:
                    enum_constant["init"] = []
                    enum_constant["static_init"] = []
                    enum_constant["fields"] = []
                    enum_constant["member_methods"] = []
                    enum_constant["enum_constants"] = []
                    enum_constant["nested"] = []
                    self.class_body(enum_constant_body, enum_constant)

                glang_node["enum_constants"].append({"enum_constant": enum_constant})

    def annotation_type_declaration(self, node, statements):
        glang_node = {}
        glang_node["attr"] = []
        glang_node["init"] = []
        glang_node["fields"] = []
        glang_node["nested"] = []
        glang_node["annotation_type_elements"] = []

        child = self.find_child_by_type(node, "modifiers")
        modifiers = self.read_node_text(child).split()
        glang_node["attr"].extend(modifiers)

        child = self.find_child_by_field(node, "name")
        glang_node["name"] = self.read_node_text(child)

        child = self.find_child_by_field(node, "body")
        self.annotation_type_body(child, glang_node)

        statements.append({"annotation_type_decl": glang_node})

    def annotation_type_body(self, node, glang_node):
        if not node:
            return

        children = self.find_children_by_type(node, "constant_declaration")
        if children:
            for child in children:
                statements = []

                extra = glang_node["init"]
                modifiers = self.find_child_by_type(child, "modifiers")
                if modifiers:
                    if "static" in self.read_node_text(modifiers).split():
                        extra = glang_node["static_init"]

                self.parse(child, statements)
                if statements:
                    for stmt in statements:
                        if "variable_decl" in stmt:
                            glang_node["fields"].append(stmt)
                        elif "constant_decl" in stmt:
                            glang_node["fields"].append(stmt)
                        elif "assign_stmt" in stmt:
                            field = stmt["assign_stmt"]
                            extra.append({"field_write": {"receiver_object": self.global_this(),
                                                          "field": field["target"], "source": field["operand"]}})

        children = self.find_children_by_type(node, "annotation_type_element_declaration")
        if (children):
            annotation_type_elements = []
            for child in children:
                modifiers = self.find_child_by_type(child, "modifiers")
                modifiers = self.read_node_text(modifiers).split()

                mytype = self.find_child_by_field(child, "type")
                shadow_type = self.read_node_text(mytype)

                name = self.find_child_by_field(child, "name")
                name = self.read_node_text(name)

                is_dimensions = self.find_child_by_field(child, "dimensions") is not None
                value = self.find_child_by_field(child, "value")

                if not value:
                    continue
                if is_dimensions and value and value.named_child_count > 0:
                    annotation_type_elements.append(
                        {"new_array": {"attr": modifiers, "type": shadow_type, "target": name}})
                    index = 0
                    for child in value.named_children:
                        if self.is_comment(child):
                            continue

                        shadow_child = self.parse(child, annotation_type_elements)
                        annotation_type_elements.append(
                            {"array_write": {"array": name, "index": str(index), "source": shadow_child}})
                        index += 1
                else:
                    shadow_value = self.parse(value, annotation_type_elements)
                    annotation_type_elements.append({"annotation_type_elements_decl":
                                                         {"attr": modifiers, "data_type": shadow_type, "name": name,
                                                          "value": shadow_value}})
            glang_node["annotation_type_elements"].extend(annotation_type_elements)

        subtypes = ["class_declaration", "interface_declaration",
                    "annotation_type_declaration", "enum_declaration"]
        for st in subtypes:
            children = self.find_children_by_type(node, st)
            if not children:
                continue

            for child in children:
                self.parse(child, glang_node["nested"])

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "decimal_integer_literal"       	: self.regular_number_literal,
            "hex_integer_literal"           	: self.regular_number_literal,
            "octal_integer_literal"         	: self.regular_number_literal,
            "binary_integer_literal"        	: self.regular_number_literal,
            "decimal_floating_point_literal"	: self.regular_number_literal,
            "hex_floating_point_literal"    	: self.hex_float_literal,
            "true"                          	: self.regular_literal,
            "false"                         	: self.regular_literal,
            "character_literal"             	: self.character_literal,
            "null_literal"                  	: self.regular_literal,
            "class_literal"                 	: self.regular_literal,
            "identifier"                    	: self.regular_literal,
            "this"                          	: self.this_literal,
            "super"                         	: self.super_literal,
            "string_literal"                	: self.string_literal,
            "string_interpolation"          	: self.string_interpolation
        }

        return LITERAL_MAP.get(node.type, None)

    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "assignment_expression"     : self.assignment_expression,
            "binary_expression"         : self.binary_expression,
            "instanceof_expression"     : self.instanceof_expression,
            "unary_expression"          : self.unary_expression,
            "ternary_expression"        : self.ternary_expression,
            "update_expression"         : self.update_expression,
            "cast_expression"           : self.cast_expression,
            "lambda_expression"         : self.lambda_expression,
            "switch_expression"         : self.switch_expression,
            "field_access"              : self.field,
            "array_access"              : self.array,
            "method_invocation"         : self.call_expression,
            "array_creation_expression" : self.new_array,
            "object_creation_expression": self.new_instance,
            "marker_annotation"         : self.annotation,
            "annotation"                : self.annotation,
            "receiver_parameter"        : self.ignore,
            "formal_parameter"          : self.formal_parameter,
            "spread_parameter"          : self.arg_list,
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
            "package_declaration":              self.package_declaration,
            "import_declaration":               self.import_declaration,
            "variable_declaration":             self.variable_and_constand_declaration,
            "local_variable_declaration":       self.variable_and_constand_declaration,
            "field_declaration":                self.variable_and_constand_declaration,
            "constant_declaration":             self.variable_and_constand_declaration,
            "class_declaration":                self.class_declaration,
            "interface_declaration":            self.class_declaration,
            "record_declaration":               self.class_declaration,
            "constructor_declaration":          self.method_declaration,
            "compact_constructor_declaration":  self.method_declaration,
            "method_declaration":               self.method_declaration,
            "enum_declaration":                 self.enum_declaration,
            "annotation_type_declaration":      self.annotation_type_declaration
        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            "labeled_statement":            self.label_statement,
            "if_statement":                 self.if_statement,
            "while_statement":              self.while_statement,
            "for_statement":                self.for_statement,
            "enhanced_for_statement":       self.forin_statement,
            "assert_statement":             self.assert_statement,
            "do_statement":                 self.dowhile_statement,
            "break_statement":              self.break_statement,
            "continue_statement":           self.continue_statement,
            "return_statement":             self.return_statement,
            "yield_statement":              self.yield_statement,
            "throw_statement":              self.throw_statement,
            "try_statement":                self.try_statement,
        }

        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)
