#!/usr/bin/env python3

import re


class Parser:
    def __init__(self):
        self.tmp_variable_list = []
        self.method_id = -1

    def create_new_tmp_variable_id(self, node, start_id):
        self.tmp_variable_list.append(([node], [start_id]))

    def sync_tmp_variable(self, node1, node2):
        node1_id = id(node1)
        node2_id = id(node2)
        for item in self.tmp_variable_list:
            if node1_id in item[0]:
                if node2_id not in item[0]:
                    item[0].append(node2_id)
                return
            if node2_id in item[0]:
                if node1_id not in item[0]:
                    item[0].append(node1_id)
                return

        self.tmp_variable_list.append(([node1_id, node2_id], [-1]))

    def have_same_id(self, node1, node2):
        node1_id = id(node1)
        node2_id = id(node2)
        myid1 = -2
        myid2 = -2
        for item in self.tmp_variable_list:
            if myid1 == -2 and node1_id in item[0]:
                myid1 = item[1][0]
            if myid2 == -2 and node2_id in item[0]:
                myid2 = item[1][0]
            if myid1 != -2 and myid2 != -2:
                break
        if -2 == myid1 and -2 == myid2:
            return False
        return myid2 == myid1

    def check_id(self, node):
        node_id = id(node)
        tmp_id = -1
        for item in self.tmp_variable_list:
            if node_id in item[0]:
                tmp_id = item[1][0]
                break

        return tmp_id

    def tmp_variable(self, node):
        node_id = id(node)
        tmp_id = -2
        for item in self.tmp_variable_list:
            if node_id in item[0]:
                item[1][0] += 1
                tmp_id = item[1][0]
                break

        if -2 == tmp_id:
            tmp_id = 0
            self.create_new_tmp_variable_id(node_id, tmp_id)
        return "%v" + str(tmp_id)

    def handle_hex_string(self, input_string):
        if self.is_hex_string(input_string):
            try:
                tmp_str = input_string.replace('\\x', "")
                tmp_str = bytes.fromhex(tmp_str).decode('utf8')
                return tmp_str
            except:
                pass

        return input_string

    def is_hex_string(self, input_string):
        if not input_string:
            return False
        # Check if the string is in the format "\\xHH" where HH is a hexadecimal value
        return len(input_string) % 4 == 0 and bool(re.match(r'^(\\x([0-9a-fA-F]{2}))+$', input_string))

    def is_string(self, input_string):
        if input_string is None:
            return False

        if not isinstance(input_string, str):
            return False

        return input_string[0] in ['"', "'"]

    def common_eval(self, input_string):
        try:
            return str(eval(input_string))
        except:
            pass
        return input_string

    def escape_string(self, input_string):
        if not input_string:
            return input_string

        if not isinstance(input_string, str):
            return input_string

        input_string = input_string.replace("'''", "")
        input_string = input_string.replace('"""', '')

        if len(input_string) == 0:
            return input_string

        if input_string[0] != '"' and input_string[0] != "'":
            return '"%s"' % input_string
        return input_string

    def tmp_method(self):
        self.method_id += 1
        return "%m" + str(self.method_id)

    def switch_return(self):
        return "@switch_return"

    def global_this(self):
        return "@this"

    def global_super(self):
        return "@super"

    def global_self(self):
        return "@self"

    def global_return(self):
        return "@return"

    def is_literal(self, node):
        return node.endswith("literal")

    def find_children_by_type(self, input_node, input_type):
        ret = []
        for child in input_node.named_children:
            if child.type == input_type:
                ret.append(child)
        return ret

    def find_child_by_type(self, input_node, input_type):
        for child in input_node.named_children:
            if child.type == input_type:
                return child

    def find_children_by_field(self, input_node, input_field):
        return input_node.children_by_field_name(input_field)

    def find_child_by_field(self, input_node, input_field):
        return input_node.child_by_field_name(input_field)

    def find_child_by_type_type(self, input_node, input_type, input_type2):
        node = self.find_child_by_type(input_node, input_type)
        if node:
            return self.find_child_by_type(node, input_type2)

    def find_child_by_field_type(self, input_node, input_field, input_type):
        node = self.find_child_by_field(input_node, input_field)
        if node:
            return self.find_child_by_type(node, input_type)

    def find_child_by_type_field(self, input_node, input_type, input_field):
        node = self.find_child_by_type(input_node, input_type)
        if node:
            return self.find_child_by_field(node, input_field)

    def find_child_by_field_field(self, input_node, input_field, input_field2):
        node = self.find_child_by_field(input_node, input_field)
        if node:
            return self.find_child_by_field(input_field2)

    def read_node_text(self, input_node):
        if not input_node:
            return ""
        return str(input_node.text, 'utf8')

    def parse(self, node, statements=[], replacement=[]):
        if not node:
            return ""

        elif self.is_comment(node):
            return

        elif self.is_identifier(node):
            return self.read_node_text(node)

        elif self.is_literal(node):
            return self.literal(node, statements, replacement)

        elif self.is_declaration(node):
            return self.declaration(node, statements)

        elif self.is_statement(node):
            return self.statement(node, statements)

        elif self.is_expression(node):
            return self.expression(node, statements)

        else:
            size = len(node.named_children)
            for i in range(size):
                ret = self.parse(node.named_children[i], statements, replacement)
                if i + 1 == size:
                    return ret
