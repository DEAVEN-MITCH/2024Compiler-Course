#!/usr/bin/env python3
from lian.util import util


def is_empty_strict_version(node):
    if not node:
        return True

    if isinstance(node, list) or isinstance(node, set):
        for child in node:
            if not is_empty(child):
                return False
        return True

    elif isinstance(node, dict):
        for myvalue in node.values():
            if not is_empty(myvalue):
                return False
        return True

    return False

def is_empty(node):
    if not node:
        return True

    if isinstance(node, list) or isinstance(node, set):
        for child in node:
            if not is_empty(child):
                return False
        return True

    elif isinstance(node, dict):
        if len(node) > 0:
            return False
        return True

    return False
    

class GLangProcess:
    node_id = 0

    def assign_id(self):
        self.node_id += 1
        return self.node_id

    def get_id_from_node(self, node):
        if "id" not in node:
            node["id"] = self.assign_id()
        return node["id"]

    def init_statement_id(self, statement):
        if "stmt_id" not in statement:
            statement["stmt_id"] = self.assign_id()

    def is_glang_format(self, statements):
        if statements and isinstance(statements, list) and len(statements) > 0 \
           and statements[0] and isinstance(statements[0], dict):
            return True

        return False

    def flatten_statement(self, statement, dataframe):
        if not isinstance(statement, dict):
            util.error("[Input format error] The input node should not be a dictionary: " + str(statement))
            return
        
        flattened_node = {}
        dataframe.append(flattened_node)

        flattened_node["operation"] = list(statement.keys())[0]
        statement_content = statement[flattened_node["operation"]]

        self.init_statement_id(flattened_node)

        if not isinstance(statement_content, dict):
            return

        for mykey, myvalue in statement_content.items():
            if isinstance(myvalue, list):
                if not self.is_glang_format(myvalue):
                    if myvalue == []:
                        flattened_node[mykey] = None
                    else:
                        flattened_node[mykey] = str(myvalue)
                else:
                    block_id = self.flatten_block(myvalue, flattened_node, dataframe)
                    flattened_node[mykey] = block_id
                        
            elif isinstance(myvalue, dict):
                util.error("[Input format error] Dictionary in expression: " + str(myvalue))
                continue
            else:
                flattened_node[mykey] = myvalue


    def flatten_block(self, block, parent_node, dataframe):
        block_id = self.assign_id()
        dataframe.append({"operation": "block_start", "stmt_id": block_id, "parent_stmt_id": parent_node["stmt_id"]})

        for child in block:
            self.flatten_statement(child, dataframe)

        dataframe.append({"operation": "block_end", "stmt_id": block_id, "parent_stmt_id": parent_node["stmt_id"]})


        return block_id

    def flatten_glang(self, statements):
        flattened_nodes = []
        for stmt in statements:
            self.flatten_statement(stmt, flattened_nodes)

        return flattened_nodes
    
    def flatten(self, statements):
        if not self.is_glang_format(statements):
            util.error_and_quit("[Input format error] The input is not of glang statements. Exit.")
            return

        return self.flatten_glang(statements)