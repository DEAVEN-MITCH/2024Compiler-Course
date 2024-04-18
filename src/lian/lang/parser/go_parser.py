#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type == "comment"

    def is_identifier(self, node):
        return node.type == "identifier"

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
        }

        return LITERAL_MAP.get(node.type, None)

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


    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            # "assignment_expression"     : self.assignment_expression,
            "binary_expression"         : self.binary_expression,
            # "instanceof_expression"     : self.instanceof_expression,
            "unary_expression"          : self.unary_expression,
            # "ternary_expression"        : self.ternary_expression,
            # "update_expression"         : self.update_expression,
            # "cast_expression"           : self.cast_expression,
            # "lambda_expression"         : self.lambda_expression,
            # "switch_expression"         : self.switch_expression,
            "selector_expression"       : self.field,
            "index_expression"          : self.array,
            "slice_expression"          : self.slice_expression,
            # "method_invocation"         : self.call_expression,
            # "array_creation_expression" : self.new_array,
            # "object_creation_expression": self.new_instance,
            # "marker_annotation"         : self.annotation,
            # "annotation"                : self.annotation,
            # "receiver_parameter"        : self.ignore,
            # "formal_parameter"          : self.formal_parameter,
            # "spread_parameter"          : self.arg_list,
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
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