#!/usr/bin/env python3

from lian.config import config
from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type in ["line_comment", "block_comment"]

    def is_identifier(self, node):
        return node.type == "identifier" or node.type == "keyword_identifier"

    def regular_number_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        value = self.common_eval(value)
        return str(value)

    def regular_literal(self, node, statements, replacement):
        return self.read_node_text(node)

    def string(self, node, statements, replacement):
        replacement = []
        ret = self.read_node_text(node)
        for child in node.named_children:
            self.parse(child, statements, replacement)
            if replacement:
                for r in replacement:
                    (expr, value) = r
                    ret = ret.replace(self.read_node_text(expr), value)
            replacement = []

        ret = self.handle_hex_string(ret)

        return self.escape_string(ret)

    def concatenated_string(self, node, statements, replacement):
        pass

    def interpolation(self, node, statements, replacement):
        child = node.named_children[0]
        if child.type == "expression_list":
            if child.named_child_count > 0:
                for expr in child.named_children:
                    shadow_expr = self.parse(expr, statements)
                    replacement.append((expr, shadow_expr))
        else:
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)
            replacement.append((expr, shadow_expr))

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

    def is_constant_literal(self, node):
        return node.type in [
            "string",
            "concatenated_string",
            "integer",
            "float",
            "true",
            "false",
            "none",
        ]

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "integer"       	                : self.regular_number_literal,
            "float"    	                        : self.regular_number_literal,
            "true"                          	: self.regular_literal,
            "false"                         	: self.regular_literal,
            "none"                              : self.regular_literal,
            "string"                            : self.string,
            "concatenated_string"               : self.concatenated_string,
            "interpolation"                     : self.interpolation,
            "identifier"                    	: self.regular_literal,
        }

        return LITERAL_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def function_definition(self, node, statements):
        modifiers = []
        if node.named_child_count > 0 and self.read_node_text(node.children[0]) == "async":
            modifiers.append("async")

        child = self.find_child_by_field(node, "return_type")
        mytype = self.read_node_text(child)

        child = self.find_child_by_field(node, "name")
        name = self.read_node_text(child)

        parameter_decl = []
        init = []
        
        parameters = self.find_child_by_field(node, "parameters")
        if parameters and parameters.named_child_count > 0:
            # need to deal with parameters
            for parameter in parameters.named_children:
                if self.is_comment(parameter):
                    continue
                parameter_type = parameter.type
                if (parameter_type == "identifier"):
                    init.append({"parameter_decl": {"name": self.read_node_text(parameter)}})
                elif (parameter_type in ["typed_parameter", "default_parameter", "typed_default_parameter"]):
                    self.parse(parameter, init)
                # TODO: Need to deal with $.list_splat_pattern, $.tuple_pattern, $.keyword_separator, 
                # $.positional_separator, $.dictionary_splat_pattern,

        if init:
            for new_parameter in init:
                if "parameter_decl" in new_parameter:
                    parameter_decl.append(new_parameter)
        new_body = []
        self.sync_tmp_variable(new_body, init)
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                if self.is_comment(stmt):
                    continue

                self.parse(stmt, new_body)

        statements.append({"method_decl": {"attr": modifiers, "data_type": mytype, "name": name,
                                           "parameters": parameter_decl, "init": init, "body": new_body}})
        return name

    def class_definition(self, node, statements):
        glang_node = {}

        glang_node["attr"] = []
        glang_node["init"] = []
        glang_node["methods"] = []
        glang_node["fields"] = []
        glang_node["supers"] = []
        glang_node["nested"] = []

        glang_node["attr"].append("class")

        child = self.find_child_by_field(node, "name")
        if child:
            glang_node["name"] = self.read_node_text(child)

        child = self.find_child_by_field(node, "type_parameters")
        if child:
            type_parameters = self.read_node_text(child)
            glang_node["type_parameters"] = type_parameters[1:-1]

        child = self.find_child_by_field(node, "superclasses")
        if child:
            superclass = self.parse(child, statements)
            if superclass:
                parent_class = superclass.replace("extends", "").split()[0]
                glang_node["supers"].append(parent_class)

        child = self.find_child_by_field(node, "body")
        self.class_body(child, glang_node)

        statements.append({"class_decl": glang_node})

    def class_body(self, node, glang_node):
        for child in node.named_children:
            if child.type == "function_definition":
                self.parse(child, glang_node["methods"])
            elif child.type == "class_definition":
                self.parse(child, glang_node["nested"])
            else:
                statements = []
                extra = glang_node["init"]
                self.sync_tmp_variable(statements, extra)
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

    def decorated_definition(self, node, statements):
        definition = self.find_child_by_field(node, "definition")
        name = self.parse(definition, statements)
        decorator = self.find_child_by_type(node, "decorator")
        shadow_decorator = self.parse(decorator, statements)

        statements.append({"call_stmt": {"target": name, "name": shadow_decorator, "args": [name]}})
        # statements.append({"assign_stmt": {"target": name, "operand": self.global_return()}})

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
            "function_definition": self.function_definition,
            "class_definition": self.class_definition,
            "decorated_definition": self.decorated_definition,
        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

    def await_expression(self, node, statements):
        shadow_expr = ""
        if node.named_child_count > 0:
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)
        statements.append({"await": {"target": shadow_expr}})

    def expression_list(self, node, statements):
        shadow_expr_list = []
        if node.named_child_count > 0:
            for expr in node.named_children:
                shadow_expr = self.parse(expr, statements)
                shadow_expr_list.append(shadow_expr)

        tmp_var = self.tmp_variable(statements)
        statements.append({"new_array": {"target": tmp_var}})
        if len(shadow_expr_list) > 0:
            for index, item in enumerate(shadow_expr_list):
                statements.append({"array_write": {"array": tmp_var, "index": str(index), "source": item}})

        return tmp_var

    def pattern_list(self, node, statements):
        shadow_pattern_list = []
        if node.named_child_count > 0:
            for pattern in node.named_children:
                shadow_pattern = self.parse(pattern, statements)
                shadow_pattern_list.append(shadow_pattern)

        tmp_var = self.tmp_variable(statements)
        statements.append({"new_array": {"target": tmp_var}})
        if len(shadow_pattern_list) > 0:
            for index, item in enumerate(shadow_pattern_list):
                statements.append({"array_write": {"array": tmp_var, "index": str(index), "source": item}})

        return tmp_var

    def call_expression(self, node, statements):
        name = self.find_child_by_field(node, "function")
        shadow_name = self.parse(name, statements)

        args = self.find_child_by_field(node, "arguments")
        args_list = []

        if args.named_child_count > 0:
            for child in args.named_children:
                shadow_variable = self.parse(child, statements)
                if shadow_variable:
                    args_list.append(shadow_variable)

        tmp_var = self.tmp_variable(statements)

        statements.append({"call_stmt": {"target": tmp_var, "name": shadow_name, "args": args_list}})
        return tmp_var

    def lambda_expression(self, node, statements):
        tmp_func = self.tmp_method()

        parameters = []
        tmp_body = []
        child = self.find_child_by_field(node, "parameters")
        if child is not None:
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
            new_body.append({"return_stmt": {"target": shadow_expr}})
        else:
            for stmt in body.named_children:
                if self.is_comment(stmt):
                    continue

                shadow_expr = self.parse(body, new_body)
                if stmt == body.named_children[-1]:
                    new_body.append({"return_stmt": {"target": shadow_expr}})

        statements.append({"method_decl": {"name": tmp_func, "parameters": parameters, "body": new_body}})

        return tmp_func

    def conditional_expression(self, node, statements):
        consequence = node.named_children[0]
        condition = node.named_children[1]
        alternative = node.named_children[2]

        condition = self.parse(condition, statements)

        body = []
        elsebody = []

        self.sync_tmp_variable(statements, body)
        self.sync_tmp_variable(statements, elsebody)
        tmp_var = self.tmp_variable(statements)

        expr1 = self.parse(consequence, body)
        body.append({"assign_stmt": {"target": tmp_var, "operand": expr1}})

        expr2 = self.parse(alternative, elsebody)
        body.append({"assign_stmt": {"target": tmp_var, "operand": expr2}})

        statements.append({"if_stmt": {"condition": condition, "then_body": body, "else_body": elsebody}})
        return tmp_var

    def named_expression(self, node, statements):
        name = self.find_child_by_field(node, "name")
        shadow_name = self.parse(name, statements)

        value = self.find_child_by_field(node, "value")
        shadow_value = self.parse(value, statements)

        statements.append({"assign_stmt": {"target": shadow_name, "operand": shadow_value}})

        return shadow_name

    def list_stmt(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        statements.append({"new_array": {"target": tmp_var}})
        if node and node.named_child_count > 0:
            for index, item in enumerate(node.named_children):
                if self.is_comment(item):
                    continue

                source = self.parse(item, statements)
                statements.append({"array_write": {"array": tmp_var, "index": str(index), "source": source}})

        return tmp_var

    def as_pattern(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)

        alias = self.find_child_by_field(node, "alias")
        shadow_alias = self.parse(alias, statements)

        statements.append({"assign_stmt": {"target": shadow_alias, "operand": shadow_expr}})
        return shadow_alias

    def tuple(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        statements.append({"new_array": {"target": tmp_var, "attr": ["tuple"]}})
        if node and node.named_child_count > 0:
            for index, item in enumerate(node.named_children):
                if self.is_comment(item):
                    continue

                source = self.parse(item, statements)
                statements.append({"array_write": {"array": tmp_var, "index": str(index), "source": source}})

        return tmp_var

    def dictionary(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        statements.append({"new_map": {"target": tmp_var}})
        pairs = self.find_children_by_type(node, "pair")
        if pairs:
            for pair in pairs:
                key = self.find_child_by_field(pair, "key")
                value = self.find_child_by_field(pair, "value")

                shadow_key = self.parse(key, statements)
                shadow_value = self.parse(value, statements)

                statements.append({"map_write": {"target": tmp_var, "key": shadow_key, "value": shadow_value}})

        return tmp_var

    def subscript(self, node, statements):
        tmp_var = self.tmp_variable(statements)        
        array = self.find_child_by_field(node, "value")
        shadow_array = self.parse(array, statements)
        subscripts = self.find_children_by_field(node, "subscript")
        shadow_index = self.parse(subscripts[0], statements)
        if isinstance(shadow_index, tuple):
            start, end, step = shadow_index
            statements.append({"slice_stmt": {"target": tmp_var, "array": shadow_array, "start": str(start), "end": str(end), "step": str(step) }})
        else:
            statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index}})
    
        return tmp_var

    def attribute(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        shadow_object, shadow_field = self.parse_field(node, statements)
        statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": shadow_field}})
        return tmp_var

    def slice(self, node, statements):
        start, end, step = None, None, None
        index_list = node.children
        colon_indices = []
        for i, symbol in enumerate(index_list):
            if self.read_node_text(symbol) == ':':
                colon_indices.append(i)
        if len(colon_indices) == 1:
            start = None if colon_indices[0] == 0 else index_list[colon_indices[0] - 1]
            end = None if colon_indices[0] + 1 == len(index_list) else index_list[colon_indices[0] + 1]
        elif len(colon_indices) == 2:
            start = None if colon_indices[0] == 0 else index_list[colon_indices[0] - 1]
            end = None if colon_indices[0] + 1 == colon_indices[1] else index_list[colon_indices[1] - 1]
            step = None if colon_indices[1] + 1 == len(index_list) else index_list[colon_indices[1] + 1]
        start = self.parse(start)
        end = self.parse(end)
        step = self.parse(step)
        return start, end, step

    def keyword_argument(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        name = self.find_child_by_field(node, "name")
        value = self.find_child_by_field(node, "value")

        shadow_name = self.parse(name, statements)
        shadow_value = self.parse(value, statements)
        statements.append({"keyword_argument": {"target": tmp_var, "name": shadow_name, "value": shadow_value}})

        return tmp_var

    def parse_comprehension_clauses(self, body, target, clauses, statements):
        if len(clauses) == 0:
            return
        elif len(clauses) == 1:
            clause = clauses.pop(0)
            if clause.type == "for_in_clause":
                modifiers = []
                if clause.named_child_count > 0 and self.read_node_text(clause.children[0]) == "async":
                    modifiers.append("async")
                left = self.find_child_by_field(clause, "left")
                right = self.find_child_by_field(clause, "right")
                shadow_left = self.parse(left, statements)
                shadow_right = self.parse(right, statements)
                for_body = []
                self.sync_tmp_variable(statements, for_body)
                if body.type == "pair":
                    key = self.find_child_by_field(body, "key")
                    value = self.find_child_by_field(body, "value")
                    shadow_key = self.parse(key, for_body)
                    shadow_value = self.parse(value, for_body)
                    for_body.append({"map_write": {"target": target, "key": shadow_key, "value": shadow_value}})
                else:
                    shadow_body = self.parse(body, for_body)
                    for_body.append({"array_write": {"array": target,  "index": "", "source":shadow_body}})
                statements.append({"forin_stmt":
                                        {"attr": modifiers,
                                         "name": shadow_left,
                                         "target": shadow_right,
                                         "body": for_body}})
            else:
                expr = clause.named_children[0]
                shadow_condition = self.parse(expr, statements)
                true_body = []
                self.sync_tmp_variable(statements, true_body)
                if body.type == "pair":
                    key = self.find_child_by_field(body, "key")
                    value = self.find_child_by_field(body, "value")
                    shadow_key = self.parse(key, true_body)
                    shadow_value = self.parse(value, true_body)
                    true_body.append({"map_write": {"target": target, "key": shadow_key, "value": shadow_value}})
                else:
                    shadow_body = self.parse(body, true_body)
                    true_body.append({"array_write": {"array": target,  "index": "", "source": shadow_body}})
                statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body}})
        else:
            clause = clauses.pop(0)
            if clause.type == "for_in_clause":
                modifiers = []
                if clause.named_child_count > 0 and self.read_node_text(clause.children[0]) == "async":
                    modifiers.append("async")
                left = self.find_child_by_field(clause, "left")
                right = self.find_child_by_field(clause, "right")
                shadow_left = self.parse(left, statements)
                shadow_right = self.parse(right, statements)
                for_body = []
                self.sync_tmp_variable(statements, for_body)
                shadow_body = self.parse_comprehension_clauses(body, target, clauses, for_body)
                statements.append({"forin_stmt":
                                        {"attr": modifiers,
                                         "name": shadow_left,
                                         "target": shadow_right,
                                         "body": for_body}})
            else:
                expr = clause.named_children[0]
                shadow_condition = self.parse(expr, statements)
                true_body = []
                self.sync_tmp_variable(statements, true_body)
                shadow_body = self.parse_comprehension_clauses(body, target, clauses, true_body)
                statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body}})

    def list_set_dictionary_comprehension(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        if node.type == "dictionary_comprehension":
            statements.append({"new_map": {"target": tmp_var}})
        else:
            statements.append({"new_array": {"target": tmp_var}})
        body = self.find_child_by_field(node, "body")
        comprehension_clauses = [x for x in node.named_children[1:] if x.type == "for_in_clause" or x.type == "if_clause"]
        self.parse_comprehension_clauses(body, tmp_var, comprehension_clauses, statements)

        return tmp_var

    def evaluate_literal_binary_expression(self, root, statements):
        node_list = [root]
        nodes_to_be_computed = []
        binary_expr_value_map = {}

        if not root:
            return

        # determine if it is a real literal_binary_expression
        while (len(node_list) > 0):
            node = node_list.pop()
            if not node:
                return

            if node.id in binary_expr_value_map:
                # This node cannot be evaluated
                if binary_expr_value_map.get(node.id) is None:
                    return
                continue

            if not self.is_constant_literal(node) and node.type != "binary_expression":
                return

            # literal
            if self.is_constant_literal(node):
                continue

            operator = self.find_child_by_field(node, "operator")
            left = self.find_child_by_field(node, "left")
            right = self.find_child_by_field(node, "right")

            node_list.append(left)
            node_list.append(right)

            if self.is_constant_literal(left) and self.is_constant_literal(right):
                shadow_operator = self.read_node_text(operator)
                shadow_left = self.parse(left, statements)
                shadow_right = self.parse(right, statements)
                content = shadow_left + shadow_operator + shadow_right
                value = self.common_eval(content)
                if value is None:
                    binary_expr_value_map[node.id] = None
                    binary_expr_value_map[root.id] = None
                    return

                if self.is_string(shadow_left):
                    value = self.escape_string(value)

                binary_expr_value_map[node.id] = value
                nodes_to_be_computed.append(node)

        # conduct evaluation from bottom to top
        while len(nodes_to_be_computed) > 0:
            node = nodes_to_be_computed.pop(0)
            if node == root:
                return binary_expr_value_map[root.id]

            parent = node.parent
            if not parent or parent.type not in ["binary_operator", "comparison_operator"]:
                return

            nodes_to_be_computed.append(parent)

            if parent.id in binary_expr_value_map:
                continue

            left = self.find_child_by_field(parent, "left")
            right = self.find_child_by_field(parent, "right")

            if not left or not right:
                return

            shadow_left = None
            shadow_right = None

            if left.id in binary_expr_value_map:
                shadow_left = binary_expr_value_map.get(left.id)
            elif self.is_constant_literal(left):
                shadow_left = self.parse(left, statements)
            else:
                return

            if right.id in binary_expr_value_map:
                shadow_right = binary_expr_value_map.get(right.id)
            elif self.is_constant_literal(right):
                shadow_right = self.parse(right, statements)
            else:
                return

            eval_content = ""
            try:
                eval_content = str(shadow_left) + str(shadow_operator) + str(shadow_right)
            except:
                return
            value = self.common_eval(eval_content)
            if value is None:
                return

            if self.is_string(shadow_left):
                value = self.escape_string(value)

            if isinstance(value, str):
                if len(value) > config.STRING_MAX_LEN:
                    return value[:-1] + '..."'

            binary_expr_value_map[parent.id] = value

        return binary_expr_value_map.get(root.id)

    def binary_comparison_operator(self, node, statements):
        evaluated_value = self.evaluate_literal_binary_expression(node, statements)
        if evaluated_value is not None:
            return evaluated_value

        left = node.named_children[0]
        right = node.named_children[-1]
        if node.type == "binary_operator":
            operator = self.find_child_by_field(node, "operator")
        else:
            operator = self.find_child_by_field(node, "operators")

        shadow_operator = self.read_node_text(operator)
        shadow_left = self.parse(left, statements)
        shadow_right = self.parse(right, statements)

        tmp_var = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_left,
                                           "operand2": shadow_right}})

        return tmp_var

    def unary_operator(self, node, statements):
        operand = self.find_child_by_field(node, "argument")
        shadow_operand = self.parse(operand, statements)
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)

        tmp_var = self.tmp_variable(statements)

        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_operand}})
        return tmp_var

    def not_operator(self, node, statements):
        arg = self.find_child_by_field(node, "argument")
        shadow_arg = self.parse(arg, statements)

        tmp_var = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_var, "operator": "not", "operand": shadow_arg}})

        return tmp_var

    def boolean_operator(self, node, statements):
        left = node.named_children[0]
        right = node.named_children[-1]
        operator = self.find_child_by_field(node, "operator")

        shadow_operator = self.read_node_text(operator)
        shadow_left = self.parse(left, statements)
        shadow_right = self.parse(right, statements)

        tmp_var = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_left,
                                           "operand2": shadow_right}})

        return tmp_var

    def typed_parameter(self, node, statements):
        if node.named_child_count > 0:
            name = node.named_children[0]
            shadow_name = self.parse(name, statements)

        mytype = self.find_child_by_field(node, "type")
        shadow_type = self.read_node_text(mytype)

        statements.append({"parameter_decl": {"data_type": shadow_type, "name": shadow_name}})

    def default_parameter(self, node, statements):
        name = self.find_child_by_field(node, "name")
        value = self.find_child_by_field(node, "value")

        shadow_name = self.parse(name, statements)
        statements.append({"parameter_decl": {"name": shadow_name}})
        shadow_value = self.parse(value, statements)

        statements.append({"assign_stmt": {"target": shadow_name, "operand": shadow_value}})

    def typed_default_parameter(self, node, statements):
        name = self.find_child_by_field(node, "name")
        value = self.find_child_by_field(node, "value")
        type = self.find_child_by_field(node, "type")

        shadow_type = self.read_node_text(type)
        shadow_name = self.parse(name, statements)
        statements.append({"parameter_decl": {"data_type": shadow_type, "name": shadow_name}})

        shadow_value = self.parse(value, statements)
        statements.append({"assign_stmt": {"target": shadow_name, "operand": shadow_value}})

    def keyword_separator(self, node, statements):
        pass

    def parse_type(self, node, statements):
        if not node:
            return ""

        node = node.named_children[0]
        if node.type == "generic_type":
            identifier = self.find_child_by_type(node, "identifier")
            type_parameter = self.find_child_by_type(node, "type_parameter")

            shadow_identifier = self.parse(identifier)
            if shadow_identifier == "tuple" or shadow_identifier == "Tuple":
                return self.tuple(type_parameter, statements)

            if shadow_identifier == "list" or shadow_identifier == "List":
                return self.list_stmt(type_parameter, statements)

        elif node.type == "union_type":
            tmp_var = self.tmp_variable(statements)
            children = self.find_children_by_type(node, "type")
            left = children[0]
            right = children[1]

            shadow_left = self.parse(left, statements)
            shadow_right = self.parse(right, statements)

            statements.append({"assign_stmt": {"target": tmp_var, "operator": "|",
                                               "operand": shadow_left, "operand2": shadow_right}})
            return tmp_var

        elif node.type == "member_type":
            type = self.find_child_by_type(node, "type")
            identifier = self.find_child_by_type(node, "identifier")

            shadow_array = self.parse_type(type, statements)
            shadow_index = self.parse(identifier, statements)
            tmp_var = self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_array, "field": shadow_index}})
            return tmp_var

        else:
            return self.parse(node, statements)

    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "await"                     : self.await_expression,
            "expression_list"           : self.expression_list,
            "pattern_list"              : self.pattern_list,
            "lambda"                    : self.lambda_expression,
            "conditional_expression"    : self.conditional_expression,
            "named_expression"          : self.named_expression,
            "as_pattern"                : self.as_pattern,
            "call"                      : self.call_expression,
            "list"                      : self.list_stmt,
            "list_pattern"              : self.list_stmt,
            "tuple"                     : self.tuple,
            "tuple_pattern"             : self.tuple,
            "dictionary"                : self.dictionary,
            "subscript"                 : self.subscript,
            "attribute"                 : self.attribute,
            "slice"                     : self.slice,
            "keyword_argument"          : self.keyword_argument,
            "list_comprehension"        : self.list_set_dictionary_comprehension,
            "dictionary_comprehension"  : self.list_set_dictionary_comprehension,
            "set_comprehension"         : self.list_set_dictionary_comprehension,
            "generator_expression"      : self.list_set_dictionary_comprehension,
            "binary_operator"           : self.binary_comparison_operator,
            "comparison_operator"       : self.binary_comparison_operator,
            "not_operator"              : self.not_operator,
            "boolean_operator"          : self.boolean_operator,
            "unary_operator"            : self.unary_operator,
            "typed_parameter"           : self.typed_parameter,
            "default_parameter"         : self.default_parameter,
            "typed_default_parameter"   : self.typed_default_parameter,
            "keyword_separator"         : self.keyword_separator
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def import_statement(self, node, statements):
        if node.type == "import_from_statement":
            import_name = node.named_children[1:]
        else:
            import_name = node.named_children

        if node.type == "import_from_statement":
            module_name = self.read_node_text(self.find_child_by_field(node, "module_name"))
        elif node.type == "future_import_statement":
            module_name = "__future__"
        else:
            module_name = ""

        for child in import_name:
            if child.type == "dotted_name":
                if module_name:
                    statements.append({"import_stmt": {"name": module_name + "." + self.read_node_text(child)}})
                else:
                    statements.append({"import_stmt": {"name": self.read_node_text(child)}})
            else:
                name = self.read_node_text(self.find_child_by_field(child, "name"))
                alias = self.read_node_text(self.find_child_by_field(child, "alias"))
                if module_name:
                    statements.append({"import_as_stmt": {"name": module_name + "." + name, "alias": alias}})
                else:
                    statements.append({"import_as_stmt": {"name": name, "alias": alias}})

    def assert_statement(self, node, statements):
        expr = node.named_children[0]
        shadow_expr = self.parse(expr, statements)

        statements.append({"assert_stmt": {"condition": shadow_expr}})

    def return_statement(self, node, statements):
        shadow_name = ""
        if node.named_child_count > 0:
            name = node.named_children[0]
            shadow_name = self.parse(name, statements)

        statements.append({"return_stmt": {"target": shadow_name}})
        return shadow_name

    def delete_statement(self, node, statements):
        expression_list = self.find_child_by_type(node, "expression_list")
        shadow_expr = ""
        if expression_list:
            if expression_list.named_child_count > 0:
                for child in expression_list.named_children:
                    shadow_expr = self.parse(child, statements)
                    statements.append({"del_stmt": {"target": shadow_expr}})
        else:
            for child in node.named_children:
                shadow_expr = self.parse(child, statements)
                statements.append({"del_stmt": {"target": shadow_expr}})

    def raise_statement(self, node, statements):
        shadow_expr = ""
        if node.named_child_count > 0:
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)
        statements.append({"raise_stmt": {"target": shadow_expr}})

    def pass_statement(self, node, statements):
        statements.append({"pass_stmt": {}})

    def break_statement(self, node, statements):
        statements.append({"break_stmt": {"target": ""}})

    def continue_statement(self, node, statements):
        statements.append({"continue_stmt": {"target": ""}})

    def global_statement(self, node, statements):
        shadow_expr = ""
        if node.named_child_count > 0:
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)
        statements.append({"global_stmt": {"target": shadow_expr}})

    def nonlocal_statement(self, node, statements):
        shadow_expr = ""
        if node.named_child_count > 0:
            expr = node.named_children[0]
            shadow_expr = self.parse(expr, statements)
        statements.append({"nonlocal_stmt": {"target": shadow_expr}})

    def type_alias_statement(self, node, statements):
        types = self.find_children_by_type(node, "type")
        type1 = self.parse_type(types[0], statements)
        type2 = self.parse_type(types[1], statements)
        statements.append({"type_alias_stmt": {"target": type1, "source": type2}})

    def parse_alternative(self, alter_list, statements):
        if len(alter_list) == 0:
            return

        node = alter_list[0]

        if node.type == "else_clause":
            child = self.find_child_by_field(node, "body")
            if child:
                for stmt in child.named_children:
                    self.parse(stmt, statements)
            return

        condition_part = self.find_child_by_field(node, "condition")
        true_part = self.find_child_by_field(node, "consequence")

        true_body = []
        self.sync_tmp_variable(statements, true_body)
        false_body = []
        self.sync_tmp_variable(statements, false_body)

        shadow_condition = self.parse(condition_part, statements)
        self.parse(true_part, true_body)
        self.parse_alternative(alter_list[1:], false_body)
        statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body,
                                  "else_body": false_body}})

    def if_statement(self, node, statements):
        condition_part = self.find_child_by_field(node, "condition")
        true_part = self.find_child_by_field(node, "consequence")
        false_part = self.find_children_by_field(node, "alternative")

        true_body = []
        self.sync_tmp_variable(statements, true_body)
        false_body = []
        self.sync_tmp_variable(statements, false_body)

        shadow_condition = self.parse(condition_part, statements)
        self.parse(true_part, true_body)
        self.parse_alternative(false_part, false_body)

        statements.append({"if_stmt": {"condition": shadow_condition, "then_body": true_body, "else_body": false_body}})

    def for_statement(self, node, statements):
        modifiers = []
        if node.named_child_count > 0 and self.read_node_text(node.children[0]) == "async":
            modifiers.append("async")

        name = self.find_child_by_field(node, "left")
        shadow_name = self.parse(name, statements)

        value = self.find_child_by_field(node, "right")
        shadow_value = self.parse(value, statements)

        for_body = []
        self.sync_tmp_variable(statements, for_body)

        body = self.find_child_by_field(node, "body")
        self.parse(body, for_body)

        statements.append({"forin_stmt":
                               {"attr": modifiers,
                                "name": shadow_name,
                                "target": shadow_value,
                                "body": for_body}})

    def while_statement(self, node, statements):
        condition = self.find_child_by_field(node, "condition")
        body = self.find_child_by_field(node, "body")
        alternative = self.find_child_by_field(node, "alternative")

        shadow_condition = self.parse(condition, statements)

        new_while_body = []
        self.sync_tmp_variable(new_while_body, statements)
        self.parse(body, new_while_body)

        new_else_body = []
        self.sync_tmp_variable(new_else_body, statements)
        if alternative is not None:
            for stmt in alternative.named_children:
                self.parse(stmt, new_else_body)

        statements.append(
            {"while_stmt": {"condition": shadow_condition, "body": new_while_body, "else_body": new_else_body}})

    def try_statement(self, node, statements):
        try_op = {}
        try_body = []
        catch_body = []
        else_body = []
        finally_body = []

        self.sync_tmp_variable(try_body, statements)
        body = self.find_child_by_field(node, "body")
        self.parse(body, try_body)
        try_op["body"] = try_body

        self.sync_tmp_variable(catch_body, statements)
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

        self.sync_tmp_variable(else_body, statements)
        else_clause = self.find_child_by_type(node, "else_clause")
        if else_clause:
            else_clause_body = else_clause.children[-1]
            self.parse(else_clause_body, else_body)
        try_op["else_body"] = else_body

        self.sync_tmp_variable(finally_body, statements)
        finally_clause = self.find_child_by_type(node, "finally_clause")
        if finally_clause:
            finally_clause_body = finally_clause.children[-1]
            self.parse(finally_clause_body, finally_body)
        try_op["final_body"] = finally_body

        statements.append({"try_stmt": try_op})

    def with_statement(self, node, statements):
        modifiers = []
        if node.named_child_count > 0 and self.read_node_text(node.children[0]) == "async":
            modifiers.append("async")

        with_clause = self.find_child_by_type(node, "with_clause")
        with_init = []
        for with_item in with_clause.named_children:
            value = self.find_child_by_field(with_item, "value")
            self.parse(value, with_init)

        body = self.find_child_by_field(node, "body")
        new_body = []
        self.sync_tmp_variable(new_body, statements)
        for stmt in body.named_children:
            self.parse(stmt, new_body)

        statements.append({"with_stmt": {"attr": modifiers, "with_init": with_init, "body": new_body}})

    def match_statement(self, node, statements):
        switch_ret = self.switch_return()
        condition = self.find_child_by_field(node, "subject")
        shadow_condition = self.parse(condition, statements)

        switch_stmt_list = []
        self.sync_tmp_variable(statements, switch_stmt_list)
        statements.append({"switch_stmt": {"condition": shadow_condition, "body": switch_stmt_list}})

        body = self.find_child_by_field(node, "body")
        alternatives = self.find_children_by_field(body, "alternative")
        for alternative in alternatives:
            case_init = []
            new_body = []
            self.sync_tmp_variable(statements, new_body)
            case_patterns = self.find_children_by_type(alternative, "case_pattern")
            consequence = self.find_child_by_field(alternative, "consequence")
            if self.read_node_text(case_patterns[0]) == "_":
                self.parse(consequence, new_body)
                switch_stmt_list.append({"default_stmt": {"body": new_body}})
                continue
            for case_pattern in case_patterns:
                shadow_condition = self.parse(case_pattern, case_init)
                if case_init != []:
                    statements.insert(-1, case_init)
                if case_pattern != case_patterns[-1]:
                    switch_stmt_list.append({"case_stmt": {"condition": shadow_condition}})
                else:
                    self.parse(consequence, new_body)
                    switch_stmt_list.append({"case_stmt": {"condition": shadow_condition, "body": new_body}})

        return switch_ret

    def expression_statement(self, node, statements):
        assign = self.find_child_by_type(node, "assignment")
        if assign is None:
            assign = self.find_child_by_type(node, "augmented_assignment")
        if assign:
            left = self.find_child_by_field(assign, "left")
            right = self.find_child_by_field(assign, "right")
            type = self.find_child_by_field(assign, "type")
            operator = self.find_child_by_field(assign, "operator")
            shadow_operator = self.read_node_text(operator).replace("=", "")
            shadow_right = self.parse(right, statements)
            if type:
                type = self.read_node_text(type)
            else:
                type = None
            if left.type == "attribute":
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

            elif left.type == "subscript":   
                array = self.find_child_by_field(left, "value")
                shadow_array = self.parse(array, statements)
                subscripts = self.find_children_by_field(left, "subscript")
                shadow_index = self.parse(subscripts[0], statements)
                if isinstance(shadow_index, tuple):
                    start, end, step = shadow_index
                    statements.append({"slice_stmt": {"target": tmp_var, "array": shadow_array, "start": str(start), "end": str(end), "step": str(step) }})

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

            elif left.type == "tuple_pattern":
                pattern_count = left.named_child_count
                if not shadow_operator:
                    for index in range(pattern_count):
                        tmp_var = self.tmp_variable(statements)
                        statements.append(
                            {"array_read": {"target": tmp_var, "array": shadow_right, "index": str(index), }})
                        pattern = self.parse(left.named_children[index])
                        statements.append({"variable_decl": {"data_type": type, "name": pattern}})
                        statements.append({"assign_stmt": {"target": pattern, "operand": tmp_var}})
                    return shadow_right

                tmp_var = self.tmp_variable(statements)
                for index in range(pattern_count):
                    tmp_var = self.tmp_variable(statements)
                    statements.append({"array_read": {"target": tmp_var, "array": shadow_right, "index": str(index), }})
                    pattern = self.parse(left.named_children[index])
                    tmp_var2 = self.tmp_variable(statements)
                    statements.append({"assign_stmt":
                                           {"target": tmp_var2, "operator": shadow_operator,
                                            "operand": pattern, "operand2": tmp_var}})
                    statements.append({"assign_stmt": {"target": pattern, "operand": tmp_var2}})
                return shadow_right

            elif left.type == "list_pattern" or left.type == "pattern_list":
                pattern_count = left.named_child_count
                has_splat = False
                if not shadow_operator:
                    for index in range(pattern_count):
                        if left.named_children[index].type == "list_splat_pattern":
                            has_splat = True
                            tmp_var = self.tmp_variable(statements)
                            start = index
                            end = -(pattern_count - index - 1)
                            statements.append(
                                {"slice_stmt": {"target": tmp_var, "array": shadow_right, "start": str(start), "end": str(end), "step": "", }})
                            pattern = self.parse(left.named_children[index])
                            statements.append({"assign_stmt": {"target": pattern, "operand": tmp_var}})
                            continue
                        if has_splat:
                            index = -(pattern_count - index)
                        tmp_var = self.tmp_variable(statements)
                        statements.append(
                            {"array_read": {"target": tmp_var, "array": shadow_right, "index": str(index), }})
                        pattern = self.parse(left.named_children[index])
                        statements.append({"variable_decl": {"data_type": type, "name": pattern}})
                        statements.append({"assign_stmt": {"target": pattern, "operand": tmp_var}})
                    return shadow_right

                tmp_var = self.tmp_variable(statements)
                for index in range(pattern_count):
                    if left.named_children[index].type == "list_splat_pattern":
                        has_splat = True
                        tmp_var = self.tmp_variable(statements)
                        start = index
                        end = -(pattern_count - index - 1)
                        statements.append(
                                {"slice_stmt": {"target": tmp_var, "array": shadow_right, "start": str(start), "end": str(end), "step": "", }})
                        tmp_var2 = self.tmp_variable(statements)
                        pattern = self.parse(left.named_children[index])
                        statements.append({"assign_stmt":
                                               {"target": tmp_var2, "operator": shadow_operator,
                                                "operand": pattern, "operand2": tmp_var}})
                        statements.append({"assign_stmt": {"target": pattern, "operand": tmp_var2}})
                        continue

                    if has_splat:
                        index = -(pattern_count - index)
                    tmp_var = self.tmp_variable(statements)
                    statements.append({"array_read": {"target": tmp_var, "array": shadow_right, "index": str(index), }})
                    pattern = self.parse(left.named_children[index])
                    tmp_var2 = self.tmp_variable(statements)
                    statements.append({"assign_stmt":
                                           {"target": tmp_var2, "operator": shadow_operator,
                                            "operand": pattern, "operand2": tmp_var}})
                    statements.append({"assign_stmt": {"target": pattern, "operand": tmp_var2}})
                return shadow_right
            else:
                shadow_left = self.read_node_text(left)
                if not shadow_operator:
                    statements.append({"variable_decl": {"data_type": type, "name": shadow_left}})
                    statements.append({"assign_stmt": {"target": shadow_left, "operand": shadow_right}})
                else:
                    statements.append({"assign_stmt": {"target": shadow_left, "operator": shadow_operator,
                                                       "operand": shadow_left, "operand2": shadow_right}})
                return shadow_left

        if node.named_child_count > 0:
            for child in node.named_children:
                if child.type != "assignment" and child.type != "augmented_assignment":
                    self.parse(child, statements)

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

        field = self.find_child_by_field(node, "attribute")
        shadow_field = self.read_node_text(field)
        return (shadow_object, shadow_field)

    def yield_statement(self, node, statements):
        expression_list = self.find_child_by_type(node, "expression_list")
        shadow_expr = ""
        if expression_list:
            if expression_list.named_child_count > 0:
                for child in expression_list.named_children:
                    shadow_expr = self.parse(child, statements)
                    statements.append({"yield": {"target": shadow_expr}})
        else:
            for child in node.named_children:
                shadow_expr = self.parse(child, statements)
                statements.append({"yield": {"target": shadow_expr}})


    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            "future_import_statement"   : self.import_statement,
            "import_statement"          : self.import_statement,
            "import_from_statement"     : self.import_statement,
            "assert_statement"          : self.assert_statement,
            "expression_statement"      : self.expression_statement,
            "return_statement"          : self.return_statement,
            "delete_statement"          : self.delete_statement,
            "raise_statement"           : self.raise_statement,
            "pass_statement"            : self.pass_statement,
            "break_statement"           : self.break_statement,
            "continue_statement"        : self.continue_statement,
            "global_statement"          : self.global_statement,
            "nonlocal_statement"        : self.nonlocal_statement,
            "type_alias_statement"      : self.type_alias_statement,
            "if_statement"              : self.if_statement,
            "for_statement"             : self.for_statement,
            "while_statement"           : self.while_statement,
            "try_statement"             : self.try_statement,
            "with_statement"            : self.with_statement,
            "match_statement"           : self.match_statement,
            "yield"                     : self.yield_statement,
        }

        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)
