#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type in ["line_comment", "block_comment"]

    def is_identifier(self, node):
        return node.type == "identifier"

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "null": self.regular_literal,
            "true": self.regular_literal,
            "false": self.regular_literal,
            "identifier": self.regular_literal,
            "number": self.regular_number_literal,
            "string": self.string_literal,
            "template_string": self.string_literal,
            "template_substitution": self.string_substitution,
            "this": self.this_literal,
            "super": self.super_literal,
            "private_property_identifier": self.regular_literal,
            "property_identifier": self.regular_literal
        }

        return LITERAL_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
            "function_declaration": self.method_declaration,
            "variable_declaration": self.variable_declaration,
            "lexical_declaration": self.variable_declaration,
            "class_declaration": self.class_declaration,
            "interface_declaration": self.interface_declaration,
            "enum_declaration": self.enum_declaration,
            "type_alias_declaration": self.type_alias_declaration,
            "method_declaration": self.method_declaration,   
            "abstract_class_declaration": self.class_declaration,
            "generator_function_declaration": self.method_declaration,
            "module": self.module_declaration,
            "inport_alis": self.import_declaration,
            "method_definition": self.method_declaration,
            "abstract_method_signature": self.method_declaration,
            "method_signature": self.method_declaration,
            "public_field_definition": self.public_field_definition,
            "function_signature": self.method_declaration,
        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "assignment_expression": self.assignment_expression,
            "assignment_pattern": self.assignment_expression,  # "assignment_pattern" is a special case of "assignment_expression
            "pattern": self.pattern,
            "rest_pattern": self.pattern,  
            "binary_expression": self.binary_expression,
            "subscript_expression": self.parse_subscript,
            "call_expression": self.call_expression,
            "unary_expression": self.unary_expression,
            "member_expression": self.member_expression,
            "ternary_expression": self.ternary_expression,
            "new_expression": self.new_expression,
            "yield_expression": self.yield_expression,
            "augmented_assignment_expression": self.augmented_assignment_expression,
            "non_null_expressopn": self.non_null_expression,
            "array": self.array,
            "parenthesized_expression": self.parenthesized_expression,
            "await_expression": self.await_expression,
            "as_expression": self.as_expression,
            "satisfies_expression": self.satisfies_expression,
            "type_assertion": self.type_assertion,
            "update_expression": self.update_expression,
            "object_assignment_pattern": self.assignment_expression,
            "pair_pattern": self.parse_pair_pattern,
            "object_pattern": self.parse_object,
            "object": self.parse_object,
            "pair": self.parse_pair_pattern,
            "spread_element": self.pattern,
            "arrow_function": self.arrow_function,
            "function_expression": self.method_declaration,
            # "required_parameter": self.formal_parameter,
            # "optional_parameter": self.formal_parameter,
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            "statement_block": self.statement_block,
            "for_statement": self.for_statement,
            "for_in_statement": self.for_in_statement,
            "if_statement": self.if_statement,
            "while_statement": self.while_statement,
            "do_statement": self.do_statement,
            "switch_statement": self.switch_statement,
            "break_statement": self.break_statement,
            "continue_statement": self.continue_statement,
            "return_statement": self.return_statement,
            "throw_statement": self.throw_statement,
            "try_statement": self.try_statement,
            "export_statement": self.export_statement,
            "import_statement": self.import_statement,
            "labeled_statement": self.labeled_statement,
            "expression_statement": self.expression_statement,
            "with_statement": self.with_statement,
            "empty_statement": self.empty_statement,
        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)

    def string_literal(self, node, statements, replacement):
        replacement = []
        for child in node.named_children:
            self.parse(child,statements,replacement)

        ret = self.read_node_text(node)
        if replacement:
            for r in replacement:
                (expr, value) = r
                ret = ret.replace(self.read_node_text(expr), value)

        ret = self.handle_hex_string(ret)
        return self.handle_hex_string(ret)
        
    def string_substitution(self, node, statements, replacement):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)
        replacement.append((node, shadow_expr))
        return shadow_expr

    def this_literal(self, node, statements, replacement):
        return self.global_this()

    def super_literal(self, node, statements, replacement):
        return self.global_super()



    def parse_subscript(self,node,statements,flag = 0):
        if flag == 1: # for write
            obj = self.parse(self.find_child_by_field(node, "object"), statements)
            optional_chain = self.find_child_by_field(node, "optional_chain")
            index = self.parse(self.find_child_by_field(node, "index"), statements)
            return obj,index
        else:
            obj = self.parse(self.find_child_by_field(node, "object"), statements)
            optional_chain = self.find_child_by_field(node, "optional_chain")
            index = self.parse(self.find_child_by_field(node, "index"), statements)
            tmp_var = self.tmp_variable(statements)
            statements.append({"array_read": {"target": tmp_var, "array": obj, "index": index}})
            return tmp_var

    def non_null_expression(self, node, statements):
        self.parse(node.named_children[0], statements)

    def assignment_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        shadow_right = self.parse(right, statements)

        if left.type == "parenthesized_expression":
            shadow_left = self.parse(left, statements)
            if type(shadow_left) == list:
                child_count = len(shadow_left)
                for i in range(child_count):
                    tmp_var = self.tmp_variable(statements)
                    statements.append({"array_read": {"target": tmp_var, "array": shadow_right, "index": i}})
                    statements.append({"assign_stmt": {"target": shadow_left[i], "operand": tmp_var}})
                return shadow_left
            else:
                statements.append({"assign_stmt": {"target": shadow_left, "operand": shadow_right}})
                return shadow_left

        if left.type == "array_pattern":
            shadow_left_list = self.parse_array_pattern(left, statements)
            for i in range(len(shadow_left_list)):
                shadow_left = shadow_left_list[i]
                if right.type == "array" and i < right.named_child_count:
                    tmp_var = self.tmp_variable(statements)
                    statements.append({"array_read": {"target": tmp_var, "array": shadow_right, "index": i}})
                    statements.append({"assign_stmt": {"target": shadow_left, "operand": tmp_var}})

            return shadow_left_list


        if left.type == "subscript_expression":
            shadow_array,shadow_index = self.parse_subscript(left, statements,1)
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": shadow_right}})
            return shadow_right

        if left.type == "member_expression":
            statements.append({"assign": self.read_node_text(node)})
            shadow_receiver_obj, shadow_field = self.member_expression(left, statements,1)
            statements.append({"field_write": {"receiver_object": shadow_receiver_obj, "field": shadow_field, "source": shadow_right}})
            return shadow_right

        shadow_left = self.read_node_text(left)
        statements.append({"assign_stmt":{"target": shadow_left, "operand": shadow_right}})
        return shadow_left


    def parse_array_pattern(self, node, statements):
        elements = node.named_children
        num_elements = len(elements)
        shadow_left_list = []
        for i in range(num_elements):
            element = elements[i]
            if self.is_comment(element):
                continue
            shadow_element = self.parse(element, statements)
            shadow_left_list.append(shadow_element)
        return shadow_left_list

    def pattern(self, node, statements):
        return self.parse(self.node.named_children[0], statements)


    def binary_expression(self, node, statements):
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)
        right = self.find_child_by_field(node, "right")
        shadow_right = self.parse(right, statements)
        left = self.find_child_by_field(node, "left")

        if shadow_operator == "in" and left.type == "private_property_identifier":
            shadow_left = self.parse_private_property_identifier(left, statements)
        else:
            shadow_left = self.parse(left, statements)

        tmp_var = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_left,
                                        "operand2": shadow_right}})
        return tmp_var

    def parse_private_property_identifier(self, node, statements):
            return self.read_node_text(node)

    def call_expression(self, node, statements):
        name = self.find_child_by_field(node, "function")
        shadow_name = self.parse(name, statements)

        type_arguments = self.find_child_by_field(node, "type_arguments")
        type_text = self.read_node_text(type_arguments)[1:-1] if type_arguments else ""

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
        statements.append({"call_stmt": {"target": tmp_return, "name": shadow_name, "args": args_list,"data_type": type_text}})

        return self.global_return()

    def unary_expression(self, node, statements):
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)
        argument = self.find_child_by_field(node, "argument")
        shadow_argument = self.parse(argument, statements)

        tmp_var = self.tmp_variable(statements)

        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_argument}})
        return tmp_var

    def member_expression(self, node, statements,flag = 0):
        if flag == 1: # for write
            obj = self.parse(self.find_child_by_field(node, "object"), statements)
            optional_chain = self.find_child_by_field(node, "optional_chain")
            property_ = self.parse(self.find_child_by_field(node, "property"), statements)
            return obj,property_
        else:
            obj = self.parse(self.find_child_by_field(node, "object"), statements)
            optional_chain = self.find_child_by_field(node, "optional_chain")
            property_ = self.parse(self.find_child_by_field(node, "property"), statements)
            tmp_var = self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": obj, "field": property_}})
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
        elsebody.append({"assign_stmt": {"target": tmp_var, "operand": expr2}})

        statements.append({"if": {"condition": condition, "body": body, "elsebody": elsebody}})
        return tmp_var

    def new_expression(self, node, statements):
        glang_node = {}
        constructor = self.find_child_by_field(node, "constructor")
        if constructor.type == "array":
            return self.array(constructor, statements)

        else:
            glang_node["data_type"] = self.read_node_text(constructor)

            type_parameters = self.find_child_by_field(node, "type_arguments")
            if type_parameters:
                glang_node["type_parameters"] = self.read_node_text(type_parameters)[1:-1]

            arguments = self.find_child_by_field(node, "arguments")
            argument_list = []
            if arguments.named_child_count > 0:
                for arg in arguments.named_children:
                    if self.is_comment(arg):
                        continue
                    shadow_arg = self.parse(arg, statements)
                    if shadow_arg:
                        argument_list.append(shadow_arg)

            glang_node["args"] = argument_list
            tmp_var = self.tmp_variable(statements)
            glang_node["target"] = tmp_var
            statements.append({"new_instance": glang_node})
            return tmp_var

    def yield_expression(self, node, statements):
        shadow_expr = ""
        if node.named_child_count > 0:
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)

        statements.append({"yield_stmt": {"target": shadow_expr}})
        return shadow_expr


    def augmented_assignment_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        shadow_right = self.parse(right, statements)
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator).replace("=", "")

        if left.type == "subscript_expression":
            shadow_array,shadow_index = self.parse_subscript(left, statements,1)
            
            tmp_var = self.tmp_variable(statements)
            statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index, }})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt":
                                   {"target": tmp_var2, "operator": shadow_operator,
                                    "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"array_write": {"array": shadow_array, "index": shadow_index, "source": tmp_var2}})
            return tmp_var2

        if left.type == "parenthesized_expression":
            shadow_left = self.parse(left, statements)
            if type(shadow_left) == list:
                child_count = len(shadow_left)
                for i in range(child_count):
                    tmp_var = self.tmp_variable(statements)
                    statements.append({"array_read": {"target": tmp_var, "array": shadow_right,"index": str(i)}})
                    statements.append({"assign_stmt": {"target": shadow_left[i], "operator": shadow_operator,
                                                         "operand": tmp_var, "operand2": shadow_left[i]}})
                    return shadow_left
            
            else:
                statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                               "operand": shadow_left, "operand2": shadow_right}})
                return shadow_left

        if left.type == "member_expression":
            shadow_receiver_obj, shadow_field = self.member_expression(left, statements,1)
            tmp_var = self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_receiver_obj, "field": shadow_field}})
            tmp_var2 = self.tmp_variable(statements)
            statements.append({"assign_stmt": {"target": tmp_var2, "operator": shadow_operator,
                                               "operand": tmp_var, "operand2": shadow_right}})
            statements.append({"field_write": {"receiver_object": shadow_receiver_obj, "field": shadow_field, "source": tmp_var2}})
            return tmp_var2


        shadow_left = self.read_node_text(left)
        statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                               "operand": shadow_left, "operand2": shadow_right}})
        return shadow_left


    def array(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        data_type = set()
        elements = node.named_children
        for element in elements:
            data_type.add(element.type)
        data_type = list(data_type)
        statements.append({"new_array": {"target": tmp_var, "data_type": data_type}})
        num_elements = len(elements)
        for i in range(num_elements):
            element = elements[i]
            if self.is_comment(element):
                continue
            shadow_element = self.parse(element, statements)
            statements.append({"array_write": {"array": tmp_var, "index": str(i), "source": shadow_element}})
        return tmp_var

    def parenthesized_expression(self, node, statements):
        sub_expressions = node.named_children
        if sub_expressions[0].type == "sequence_expression":
            return self.parse_sequence_expression(sub_expressions[0], statements)
        else:
            return self.parse(sub_expressions[0], statements)


    def regular_literal(self, node, statements, replacement):
        return self.read_node_text(node)

    def regular_number_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        value = self.common_eval(value)
        return str(value)

    def parse_sequence_expression(self, node, statements):
        sub_expressions = node.named_children
        sequence_list = []
        for sub_expression in sub_expressions:
            if self.is_comment(sub_expression):
                continue
            sequence_list.append(self.parse(sub_expression, statements))
        return sequence_list

    def await_expression(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)
        statements.append({"await_stmt": {"target": shadow_expr}})
        return shadow_expr

    def satisfies_expression(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr,statements)
        typ = node.named_children[1]
        shadow_type = self.read_node_text(typ)
        statements.append({"type_assertion": {"data_type": [shadow_type], "target": shadow_expr}})
        return shadow_expr
    
    def as_expression(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr,statements)
        typ = node.named_children[1]
        shadow_type = self.read_node_text(typ)
        statements.append({"type_assertion": {"data_type": [shadow_type], "target": shadow_expr}})
        return shadow_expr
    
    def parse_type_arg(self, node):
        # ???????
        ret = []
        for child in node.named_children:
            ret.append(self.read_node_text(child))
        return ret

    def type_assertion(self, node, statements):
        typ_arg = node.named_children[0]
        shadow_typ_arg = self.parse_type_arg(typ_arg)
        expr = node.named_children[1]
        shadow_expr = self.parse(expr, statements)
        statements.append({"type_assertion": {"data_type": shadow_typ_arg, "target": shadow_expr}})
        return shadow_expr

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


    def parse_pair_pattern(self, node, statements):
        key = self.parse(node.named_children[0], statements)
        value = self.parse(node.named_children[1], statements)
        tmp_var = self.tmp_variable(statements)
        statements.append({"new_map": {"target": tmp_var,"data_type": str(type(value))}})
        statements.append({"map_write": {"map": tmp_var, "key": key, "value": value}})
        return tmp_var


    def parse_object(self, node, statements):
        obj_children = node.named_children
        tmp_var = self.tmp_variable(statements)
        statements.append({"new_array": {"target": tmp_var, "data_type": "object"}})
        for i in range(len(obj_children)):
            if self.is_comment(obj_children[i]):
                continue
            res = self.parse(obj_children[i], statements)
            statements.append({"array_write": {"array": tmp_var, "index": str(i), "source": res}})
        return tmp_var

    def method_declaration(self,node,statements):
        child = self.find_child_by_field(node, "name")
        name = self.read_node_text(child)

        modifiers = []
        child = self.find_child_by_type(node, "accessibility_modifier")
        if child:
            modifiers.append(self.read_node_text(child))

        child = self.find_child_by_type(node, "override_modifier")
        if child:
            modifiers.append(self.read_node_text(child))

        child = self.find_child_by_field(node, "type_parameters")
        type_parameters = self.read_node_text(child)[1:-1]


        child = self.find_child_by_field(node, "return_type")
        return_type = ""
        if child:
            named_cld = child.named_children
            if named_cld:
                return_type = self.read_node_text(named_cld[0])


        new_parameters = []
        init = []
        child = self.find_child_by_field(node, "parameters")
        if child and child.named_child_count > 0:
            # need to deal with parameters
            for p in child.named_children:
                if self.is_comment(p):
                    continue

                self.formal_parameter(p, new_parameters,init)


        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                if self.is_comment(stmt):
                    continue

                self.parse(stmt, new_body)

        statements.append(
            {"method_decl": {"attr": modifiers, "data_type": return_type, "name": name, "type_parameters": type_parameters,
                             "parameters": new_parameters, "init": init, "body": new_body}})

        return name

    def module_declaration(self,node,statements):
        name = self.find_child_by_field(node, "name")
        name = self.read_node_text(name)

        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                if self.is_comment(stmt):
                    continue

                self.parse(stmt, new_body)
        
        statements.append(
            {"module_decl": {"name": name, "body": new_body}})

    def import_declaration(self,node,statements):
        pass


    def variable_declaration(self, node, statements):
        # declaration
        declarators = node.named_children

        child = self.find_child_by_type(node,"accessibility_modifier")
        attr=[]
        if child:
            attr.append(self.read_node_text(child))
        child = self.find_child_by_type(node,"override_modifier")
        if child:
            attr.append(self.read_node_text(child))

        for child in declarators:
            has_init = False

            data_type = self.find_child_by_field(child, "type")
            shadow_type=""
            if data_type:
                named_cld = data_type.named_children
                if named_cld:
                    shadow_type = self.read_node_text(named_cld[0])

            name = self.find_child_by_field(child, "name")
            name = self.read_node_text(name)
            value = self.find_child_by_field(child, "value")
            if value:
                has_init = True

            if value and value.type == "subscript_expression":
                tmp_var = self.parse_subscript(value,statements)

                shadow_value = tmp_var
            else:
                shadow_value = self.parse(value, statements)

            statements.append({"variable_decl": {"attr": attr, "data_type": shadow_type, "name": name}})
            if has_init:
                statements.append({"assign_stmt": {"target": name, "operand": shadow_value}})


    CLASS_TYPE_MAP = {
        "class_declaration": "class",
        "interface_declaration": "interface",
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

        child = self.find_child_by_type(node, "decorator")
        if child:
            modifiers = self.parse(child)
            glang_node["attr"].extend(modifiers)

        if "abstract" in self.read_node_text(node).split():
            glang_node["attr"].append("abstract")

        name = self.find_child_by_field(node, "name")
        if name:
            glang_node["name"] = self.read_node_text(name)

        child = self.find_child_by_field(node, "type_parameters")
        if child:
            type_parameters = self.read_node_text(child)
            glang_node["type_parameters"] = type_parameters[1:-1]

        glang_node["supers"] = []
        child = self.find_child_by_type(node,"class_heritage")
        if child:
            superclass = self.read_node_text(child)
            parent_class = superclass.replace("extends", "").replace("implements","").split()
            glang_node["supers"].append(parent_class)


        child = self.find_child_by_field(node, "body")
        self.class_body(child, glang_node)

        statements.append({f"{self.CLASS_TYPE_MAP[node.type]}_decl": glang_node})
        return glang_node["name"]


    def class_body(self, node, glang_node):
        if not node:
            return

        subtypes = ["method_signature", "method_definition","abstract_method_signature"]

        for st in subtypes:
            children = self.find_children_by_type(node, st)
            if not children:
                continue

            for child in children:
                self.parse(child, glang_node["member_methods"])

        children = self.find_children_by_type(node, "public_field_definition")
        if children:
            for child in children:
                statements = []
                extra = glang_node["init"]
                if 'static' in self.read_node_text(child).split():
                    extra = glang_node["static_init"]
                self.parse(child, statements)
                for stmt in statements:
                    if "variable_decl" in stmt:
                        glang_node["fields"].append(stmt)
                    elif "assign_stmt" in stmt:
                        field = stmt["assign_stmt"]
                        extra.append({"field_write": {"receiver_object": self.global_this(),
                                                            "field": field["target"], "source": field["operand"]}})


        children = self.find_children_by_type(node, "static_block")
        if children:
            for child in children:
                extra = glang_node["static_init"]
                statements = []
                self.statement_block(self.named_children[0], statements)
                for stmt in statements:
                    if 'variable_decl' in stmt:
                        glang_node["fields"].append(stmt)
                    elif 'assign_stmt' in stmt:
                        field = stmt["assign_stmt"]
                        extra.append({"field_write": {"receiver_object": self.global_this(),
                                                            "field": field["target"], "source": field["operand"]}})
                    elif 'method_decl' in stmt:
                        glang_node["member_methods"].append(stmt)
                    else:
                        glang_node["nested"].append(stmt)



    def public_field_definition(self, node, statements):

        child = self.find_child_by_type(node,"accessibility_modifier")
        attr=[]
        if child:
            attr.append(self.read_node_text(child))
        child = self.find_child_by_type(node,"override_modifier")
        if child:
            attr.append(self.read_node_text(child))

        if 'static' in self.read_node_text(node).split():
            attr.append("static")

        has_init = False

        data_type = self.find_child_by_field(node, "type")
        shadow_type=""
        if data_type:
            named_cld = data_type.named_children
            if named_cld:
                shadow_type = self.read_node_text(named_cld[0])

        name = self.find_child_by_field(node, "name")
        name = self.read_node_text(name)
        value = self.find_child_by_field(node, "value")
        if value:
            has_init = True

        if value and value.type == "subscript_expression":
            tmp_var = self.parse_subscript(value,statements)

            shadow_value = tmp_var
        else:
            shadow_value = self.parse(value, statements)

        statements.append({"variable_decl": {"attr": attr, "data_type": shadow_type, "name": name}})
        if has_init:
            statements.append({"assign_stmt": {"target": name, "operand": shadow_value}})
        



    def interface_declaration(self, node, statements):
        glang_node = {}

        glang_node["attr"] = []
        glang_node["init"] = []
        glang_node["static_init"] = []
        glang_node["fields"] = []
        glang_node["member_methods"] = []
        glang_node["nested"] = []

        if node.type in self.CLASS_TYPE_MAP:
            glang_node["attr"].append(self.CLASS_TYPE_MAP[node.type])

        name = self.find_child_by_field(node, "name")
        if name:
            glang_node["name"] = self.read_node_text(name)

        child = self.find_child_by_field(node, "type_parameters")
        if child:
            type_parameters = self.read_node_text(child)
            glang_node["type_parameters"] = type_parameters[1:-1]

        glang_node["supers"] = []
        child = self.find_child_by_type(node,"extends_type_clause")
        if child:
            superclass = self.read_node_text(child)
            parent_class = superclass.replace("extends", "").replace("implements","").split()
            glang_node["supers"].append(parent_class)

        child = self.find_child_by_field(node, "body")
        self.object_type(child, glang_node)

        statements.append({f"{self.CLASS_TYPE_MAP[node.type]}_decl": glang_node})
        return glang_node["name"]


    def object_type(self, node, glang_node):
        subtypes = ["method_signature", "construct_signature"]
        for st in subtypes:
            children = self.find_children_by_type(node, st)
            if not children:
                continue

            for child in children:
                self.method_declaration(child, glang_node["member_methods"])

        children = self.find_children_by_type(node, "call_signature")
        if children:
            for child in children:
                self.arrow_function(child, glang_node["member_methods"])

        children = self.find_children_by_type(node, "property_signature")
        if children:
            for child in children:
                self.public_field_definition(child, glang_node["fields"])

        # children = self.find_children_by_type(node, "index_signature")

        children = self.find_children_by_type(node, "export_statement")
        if children:
            for child in children:
                self.export_statement(child, glang_node["nested"])


    def enum_declaration(self, node, statements):
        glang_node = {}
        glang_node["attr"] = []
        glang_node["init"] = []
        glang_node["static_init"] = []
        glang_node["fields"] = []
        glang_node["member_methods"] = []
        glang_node["enum_constants"] = []
        glang_node["nested"] = []

        child = self.find_child_by_field(node, "name")
        glang_node["name"] = self.read_node_text(child)

        glang_node["supers"] = []

        child = self.find_child_by_field(node, "body")
        self.enum_body(child, glang_node)

        statements.append({"enum_decl": glang_node})

    def enum_body(self, node, glang_node):
        children = node.named_children
        if children:
            for child in children:
                if child.type == "property_identifier":
                    name = self.read_node_text(child)
                    glang_node["fields"].append(
                        {"variable_decl": {"data_type":"", "name":name}}
                    )
                else:
                    name = self.find_child_by_field(child, "name")
                    name = self.read_node_text(name)
                    glang_node["fields"].append(
                        {"variable_decl": {"data_type":"", "name":name}}
                    )
                    value = self.find_child_by_field(child, "value")
                    if value:
                        statements = []
                        shadow_value = self.parse(value, statements)
                        glang_node["init"].append(statements)
                        glang_node["init"].append({"assign_stmt": {"target": name, "operand": shadow_value}})


    def type_alias_declaration(self, node, statements):
        child = self.find_child_by_field(node, "name")
        name = self.read_node_text(child)

        type_parameters = self.find_child_by_field(node, "type_parameters")
        if type_parameters:
            type_parameters = self.read_node_text(child)
            type_parameters = type_parameters[1:-1]
        
        typ = self.find_child_by_field(node, "value")
        shadow_type = self.read_node_text(typ)
        
        statements.append({"type_alias_stmt": {"target": name, "type": type_parameters, "source": [shadow_type]}})


    def function_expression(self, node, statements):
        return self.method_declaration(node, statements)

    def arrow_function(self, node, statements):
        tmp_func = self.tmp_method()
        child = self.find_child_by_field(node, "type_parameters")
        type_parameters = self.read_node_text(child)[1:-1]


        child = self.find_child_by_field(node, "return_type")
        return_type = ""
        if child:
            named_cld = child.named_children
            if named_cld:
                return_type = self.read_node_text(named_cld[0])

        
        new_parameters = []
        init = []
        child = self.find_child_by_field(node, "parameters")
        if child and child.named_child_count > 0:
            # need to deal with parameters
            for p in child.named_children:
                if self.is_comment(p):
                    continue

                self.formal_parameter(p, new_parameters,init)


        new_body = []
        body = self.find_child_by_field(node, "body")
        if body:
            if body.type == "statement_block":
                for stmt in body.named_children:
                    if self.is_comment(stmt):
                        continue

                    shadow_expr = self.parse(body, new_body)
                    if stmt == body.named_children[-1]:
                        new_body.append({"return": {"target": shadow_expr}})
            else:
                shadow_expr = self.parse(body, new_body)
                new_body.append({"return": {"target": shadow_expr}})


        statements.append({"method_decl": {"name": tmp_func, "parameters": new_parameters, "body": new_body,"data_type": return_type}})

        return tmp_func


        

    
    def statement_block(self, node, statements):
        children = node.named_children
        for child in children:
            if self.is_comment(child):
                continue
            self.parse(child, statements)


    def formal_parameter(self, node, statements,init=[]):
        modifiers = []
        child = self.find_child_by_type(node, "accessibility_modifier")
        if child:
            modifiers.append(self.read_node_text(child))

        child = self.find_child_by_type(node, "override_modifier")
        if child:
            modifiers.append(self.read_node_text(child))

        # child = self. find readonly

        child = self.find_child_by_field(node, "pattern")
        name = self.parse(child, statements)

        child = self.find_child_by_field(node, "value")
        if child:    
            value = self.parse(child, statements)
            init.append({"assign_stmt": {"target": name, "operand": value}})



        child = self.find_child_by_field(node, "type")
        data_type = ""
        if child:
            named_cld = child.named_children
            if named_cld:
                data_type = self.read_node_text(named_cld[0])

        statements.append({"parameter_decl": {"attr": modifiers, "data_type": data_type, "name": name}})



    
     # /* TODO prerequisites: lexical_declaration, variable_declaration not implemented
    def for_statement(self, node, statements):
        init_children = self.find_children_by_field(node, "initializer")
        step_children = self.find_children_by_field(node, "increment")

        condition = self.find_child_by_field(node, "condition")

        init_body = []
        condition_init = []
        step_body = []

        shadow_condition = self.parse(condition, condition_init)
        for child in init_children:
            self.parse(child, init_body)

        # Change from Java: may contain no step expressions. Leave step_body blank.
        # if step_children and step_children.named_child_count > 0:
        if step_children:
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


    def for_in_statement(self, node, statements):

        name = []
        target = []
        attr = []
        data_type = ""

        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        kind = self.find_child_by_field(node, "kind")

        shadow_left = self.parse(left, statements)
        if type(shadow_left) == list:
            for i in range(len(shadow_left)):
                name.append(shadow_left[i])
        else:
            name.append(shadow_left)

        if kind:
            if self.read_node_text(kind) == "const":
                attr.append("const")

        target.append(self.parse(right, statements))
            
        body = []
        block = self.find_child_by_field(node, "body")
        self.parse(block, body)

        statements.append({"for_in_stmt": {"name": name, "target": target,"data_type":data_type, "attr": attr, "body": body}})




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
            # Change from Java: else_clause wraps another rule around the false body.
            statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body, "else_body": false_body}})
        else:
            statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body}})

    def while_statement(self, node, statements):
        # No change from Java.
        condition = self.find_child_by_field(node, "condition")
        body = self.find_child_by_field(node, "body")

        new_condition_init = []

        shadow_condition = self.parse(condition, new_condition_init)

        new_while_body = []
        self.parse(body, new_while_body)

        statements.extend(new_condition_init)
        new_while_body.extend(new_condition_init)

        statements.append({"while_stmt": {"condition": shadow_condition, "body": new_while_body}})

    def do_statement(self, node, statements):
        condition = self.find_child_by_field(node, "condition")
        body = self.find_child_by_field(node, "body")

        new_condition_init = []

        shadow_condition = self.parse(condition, new_condition_init)

        new_while_body = []
        self.parse(body, new_while_body)
        # Difference: condition not judged at the beginning
        # statements.extend(new_condition_init)
        new_while_body.extend(new_condition_init)

        statements.append({"dowhile_stmt": {"condition": shadow_condition, "body": new_while_body}})

    def switch_statement(self, node, statements):
        switch_block = self.find_child_by_field(node, "body")
        switch_stmt_list = []

        for child in switch_block.named_children:
            if self.is_comment(child):
                continue

            elif child.type == "switch_default":
                shadow_default_body = []
                default_statements = self.find_child_by_field(child, "body")
                self.parse(default_statements, shadow_default_body)
                switch_stmt_list.append({"default_stmt": {"body": shadow_default_body}})

            elif child.type == "switch_case":
                shadow_value = self.parse(self.find_child_by_field(child, "value"), statements)
                if child.named_child_count > 1:
                    shadow_case_body = []
                    case_statements = self.find_child_by_field(child, "body")
                    self.parse(case_statements, shadow_case_body)
                    switch_stmt_list.append({"case_stmt": {"condition": shadow_value, "body": shadow_case_body}})
                else:
                    switch_stmt_list.append({"case_stmt": {"condition": shadow_value}})

        condition = self.find_child_by_field(node, "value")
        shadow_condition = self.parse(condition, statements)   
        statements.append({"switch_stmt": {"condition": shadow_condition, "body": switch_stmt_list}})

    def empty_statement(self, node, statements):
        pass # FINAL, NOT A STUB

    def expression_statement(self, node, statement):
        expression = node.named_children[0]
        shadow_expression = self.parse(expression, statement)
        statement.append({"expression_stmt": {"target": shadow_expression}})

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

    def throw_statement(self, node, statements):
        target = self.parse(node.named_children[0], statements)
        statements.append({"throw_stmt": {"target": target}})

    def try_statement(self, node, statements):
        body = self.find_child_by_field(node, "body")
        try_body = []

        self.parse(body, try_body)

        catch_body = []
        catch_block = self.find_child_by_field(node, "handler")
        if catch_block:
            self.parse_catch_clause(catch_block, catch_body)
        
        finally_body = []
        finally_block = self.find_child_by_field(node, "finalizer")
        if finally_block:
            self.parse_finally_clause(finally_block, finally_body)

        else_body = []

        statements.append({"try_stmt": {"try_body": try_body,"else_body": else_body
        , "catch_body": catch_body, "finally_body": finally_body}})

    def parse_catch_clause(self, node, statements):
        body = self.find_child_by_field(node, "body")
        catch_body = []
        self.parse(body, catch_body)

        param = self.find_child_by_field(node, "parameter")
        shadow_param = self.parse(param, statements)

        type_list = []
        type_annotation = self.find_child_by_field(param, "type")
        if type_annotation:
            type_list.append(self.read_node_text(type_annotation)[1:-1])

        statements.append({"catch_clause": {"param": shadow_param, "type": type_list, "body": catch_body}})


    def parse_finally_clause(self, node, statements):
        body = self.find_child_by_field(node, "body")
        finally_body = []
        self.parse(body, finally_body)
        statements.append({"finally_stmt": {"body": finally_body}})

    def export_statement(self, node, statements):
        export_stmt = {}

        source = self.find_child_by_field(node, "source")
        if source:
            export_stmt["source"] = self.read_node_text(source)

        children = self.find_children_by_field(node, "declaration")
        if children:
            shadow_declare = self.parse(children[0], statements)
            export_stmt["name"] = shadow_declare

        child = self.find_child_by_type(node, "export_clause")
        if child:
            self.export_clause(child, statements, export_stmt)

        child = self.find_child_by_type(node,"namespace_export")
        if child:
            export_stmt["name"] = "*"
            als = self.read_node_text(child.children[2])
            export_stmt["alias"] = als

        if len(node.children) > 1:
            if self.read_node_text(node.children[1]) == "*":
                export_stmt["name"] = "*"

            elif self.read_node_text(node.children[1]) == "=":
                name = self.read_node_text(node.children[2])
                export_stmt["name"] = name

        if len(node.children) > 2:
            als = self.read_node_text(node.children[2])
            if als == "namespace":
                name = self.read_node_text(node.children[3])
                export_stmt["name"] = name
                export_stmt["alias"] = als

        

        statements.append({"export_stmt": export_stmt})


    def export_clause(self, node, statements, export_stmt):
        export_stmt["name"] = []
        export_stmt["alias"] = []


        children = self.find_children_by_type(node, "export_specifier")
        for child in children:
            name = self.read_node_text(self.find_child_by_field(child, "name"))
            export_stmt["name"].append(name)

            als = self.find_child_by_field(child, "alias")
            if als:
                alias = self.read_node_text(als)
                export_stmt["alias"].append(alias)



    def import_statement(self, node, statements):
        child = self.find_child_by_type(node,"import_clause")
        if child:
            source = self.read_node_text(self.find_child_by_field(node, "source"))
            self.import_clause(child, statements, source)
            return

        child = self.find_child_by_type(node,"import_require_clause")
        if child:
            require_clause = self.require_clause(child, statements)
            statements.append({"import_stmt": {"name": require_clause}})
            return require_clause


        child = self.find_child_by_field(node,"source")
        if child:
            source = self.read_node_text(child)
            statements.append({"import_stmt": {"name": source}})
            return source



    def import_clause(self, node, statements,source):
        child = self.find_child_by_type(node,"namespace_import")
        if child:
            als = self.read_node_text(self.find_child_by_type(child,"identifier"))
            statements.append({"import_as_stmt": {"name": "*", "alias": als,"source": source}})
            return als

        
        child = self.find_child_by_type(node,"named_imports")
        if child:
            import_specifiers = self.named_imports(child, statements)
            statements.append({"import_stmt": {"name": import_specifiers, "source": source}})
            return 

        child = node.named_children[0]
        name = self.read_node_text(child)
        statements.append({"import_stmt": {"name": name, "source": source}})
        return        



    
    def named_imports(self, node, statements):
        import_specifiers = []
        for child in node.named_children:
            name = self.read_node_text(self.find_child_by_field(child,"name"))
            als = self.find_child_by_field(child,"alias")
            if als:
                alias = self.read_node_text(als)
                statements.append({"type_alias_stmt":{"source": name, "target": alias}})
                import_specifiers.append(name)
            else:
                import_specifiers.append(name)

        return import_specifiers

        

    def require_clause(self, node, statements):
        child = self.find_child_by_type(node,"identifier")
        name = self.read_node_text(child)

        child = self.find_child_by_field(node,"source")
        source = self.read_node_text(child)

        statements.append({"require": {"name": name, "source": source}})

        return name


    def with_statement(self, node, statements):
        glang_node = {}
        glang_node["attr"] = []
        glang_node["with_init"] = []
        glang_node["body"] = []

        child = self.find_child_by_field(node, "object")
        shadow_object = self.parse(child, glang_node["with_init"])

        child = self.find_child_by_field(node, "body")
        self.parse(child, glang_node["body"])

        statements.append({"with_stmt": glang_node})


            

    def labeled_statement(self, node, statements):
        name = node.named_children[0]

        shadow_name = self.parse(name, statements)
        statements.append({"label_stmt": {"name": shadow_name}})

        if node.named_child_count > 1:
            stmt = node.named_children[1]
            self.parse(stmt, statements)


    def expression_statement(self, node, statements):
        return self.parse(node.named_children[0], statements)