#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type == "comment"

    def is_identifier(self, node):
        return node.type == "identifier"

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "composite_literal": self.regular_literal,
            "func_literal": self.regular_literal,
            "raw_string_literal": self.string_literal,
            "interpreted_string_literal":self.string_literal,
            "int_literal": self.regular_number_literal,
            "float_literal": self.regular_number_literal,
            "image_literal": self.regular_literal,
            "rune_literal": self.regular_literal,
            "nil": self.regular_literal,
            "true": self.regular_literal,
            "false": self.regular_literal,
            "itoa": self.regular_literal,
        }
        # print(node.type,self.read_node_text(node))
        return LITERAL_MAP.get(node.type, None)

    def regular_literal(self, node, statements, replacement):
        return self.read_node_text(node)

    def func_literal(self, node, statements,replacement):
        """function_declaration: $ => prec.right(1, seq(
          'func',
          field('name', $.identifier),
          field('type_parameters', optional($.type_parameter_list)),
          field('parameters', $.parameter_list),
          field('result', optional(choice($.parameter_list, $._simple_type))),
          field('body', optional($.block)),
        )),
                    func_literal: $ => seq(
              'func',
              field('parameters', $.parameter_list),
              field('result', optional(choice($.parameter_list, $._simple_type))),
              field('body', $.block),
            ),
                )),
        """
        child = self.find_child_by_field(node, "parameters")
        type_parameters = self.read_node_text(child)[1:-1]

        child = self.find_child_by_field(node, "type")
        mytype = self.read_node_text(child)
        tmp=self.tmp_variable(node)
        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                if self.is_comment(stmt):
                    continue

                self.parse(stmt, new_body)
        statements.append(
            {"method_decl": { "data_type": mytype, "name": tmp, "type_parameters": type_parameters,
                             "parameters": new_parameters,  "body": new_body}})
        statements.append({"method_decl": {"name": tmp,}})
        return self.read_node_text(node)

        

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
        statements.append({"method_decl": {"name": tmp,}})
        return self.read_node_text(node)

    def regular_number_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        value = self.common_eval(value)
        return str(value)

    def string_literal(self, node, statements, replacement):
        if node.type == "raw_string_literal":
            return self.read_node_text(node)[1:-1]#remove the surrounding ``
        # else type==interpreted_string_literal
        ret = self.read_node_text(node)[1:-1]#remove the surrounding ""
        ret = self.handle_hex_string(ret)
        # return ret
        return self.escape_string(ret)[1:-1]

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
        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

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
        statements.append({"slice_decl": {"target": shadow_operand, "start": shadow_start, "end": shadow_end, "step": shadow_capacity}})

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

        return self.global_return()
    
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

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        # print(node.type)
        return handler(node, statements)

    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)
