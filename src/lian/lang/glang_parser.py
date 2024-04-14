#!/usr/bin/env python3

import os,sys
import pprint
from ctypes import c_void_p, cdll
import tree_sitter

from lian.config import constants
from lian.util import util
from lian.config import (
    config,
    constants
)
from lian.lang.parser import *

def determine_lang_by_path(file_path):
    ext = os.path.splitext(file_path)[1]
    return constants.EXTENSIONS_LANG.get(ext, None)

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
    def __init__(self, node_id):
        self.node_id = node_id
    
    def assign_id(self):
        previous = self.node_id
        self.node_id += 1
        return previous

    def get_id_from_node(self, node):
        if "stmt_id" not in node:
            node["stmt_id"] = self.assign_id()
        return node["stmt_id"]

    def init_stmt_id(self, stmt, parent_stmt_id):
        stmt["parent_stmt_id"] = parent_stmt_id
        stmt["stmt_id"] = self.assign_id()

    def is_glang_format(self, stmts):
        if stmts and isinstance(stmts, list) and len(stmts) > 0 \
           and stmts[0] and isinstance(stmts[0], dict):
            return True

        return False

    def flatten_stmt(self, stmt, dataframe, parent_stmt_id = 0):
        if not isinstance(stmt, dict):
            util.error("[Input format error] The input node should not be a dictionary: " + str(stmt))
            return
        
        flattened_node = {}
        dataframe.append(flattened_node)

        flattened_node["operation"] = list(stmt.keys())[0]
        stmt_content = stmt[flattened_node["operation"]]

        self.init_stmt_id(flattened_node, parent_stmt_id)

        if not isinstance(stmt_content, dict):
            return

        for mykey, myvalue in stmt_content.items():
            if isinstance(myvalue, list):
                if not self.is_glang_format(myvalue):
                    if myvalue == []:
                        flattened_node[mykey] = None
                    else:
                        flattened_node[mykey] = str(myvalue)
                else:
                    block_id = self.flatten_block(myvalue, flattened_node["stmt_id"], dataframe)
                    flattened_node[mykey] = block_id
                        
            elif isinstance(myvalue, dict):
                util.error("[Input format error] Dictionary in expression: " + str(myvalue))
                continue
            else:
                flattened_node[mykey] = myvalue

    def flatten_block(self, block, parent_stmt_id, dataframe):
        block_id = self.assign_id()
        dataframe.append({"operation": "block_start", "stmt_id": block_id, "parent_stmt_id": parent_stmt_id})
        for child in block:
            self.flatten_stmt(child, dataframe, block_id)
        dataframe.append({"operation": "block_end", "stmt_id": block_id, "parent_stmt_id": parent_stmt_id})
        return block_id

    def flatten_glang(self, stmts):
        flattened_nodes = []
        for stmt in stmts:
            self.flatten_stmt(stmt, flattened_nodes)

        return flattened_nodes

    def adjust_node_id(self, flattened_nodes):
        self.node_id += max(len(flattened_nodes), config.MIN_ID_INTERVAL)
        self.node_id = (self.node_id // config.MIN_ID_INTERVAL + 1) * config.MIN_ID_INTERVAL
    
    def flatten(self, stmts):
        if not self.is_glang_format(stmts):
            util.error_and_quit("The input fromat of GLang IR is not correct.")
            return

        flattened_nodes = self.flatten_glang(stmts)
        self.adjust_node_id(flattened_nodes)
        return (self.node_id, flattened_nodes)


PARSERS = {
    "c"         	: c_parser,
    "cpp"       	: cpp_parser,
    "csharp"    	: csharp_parser,
    "rust"      	: rust_parser,
    "go"        	: go_parser,
    "java"      	: java_parser,
    "javascript"	: javascript_parser,
    "typescript"	: typescript_parser,
    "kotlin"    	: kotlin_parser,
    "scala"     	: scala_parser,
    "llvm"      	: llvm_parser,
    "python"      	: python_parser,
    "ruby"      	: ruby_parser,
    "smali"     	: smali_parser,
    "swift"     	: swift_parser,
    "php"       	: php_parser,
    "codeql"    	: ql_parser,
    "ql"        	: ql_parser,
}
    

def parse(options, file_path):
    lang_option = determine_lang_by_path(file_path)
    if lang_option is None:
        return

    glang_ir_parser = PARSERS.get(lang_option)
    if not glang_ir_parser:
        util.error_and_quit("Unsupported language: " + options.language)

    # to avoid warning
    lib = cdll.LoadLibrary(os.fspath(config.LANGS_SO_PATH))
    language_function = getattr(lib, "tree_sitter_%s" % lang_option)
    language_function.restype = c_void_p
    language_id = language_function()
    tree_sitter_parser = tree_sitter.Parser()
    tree_sitter_lang = tree_sitter.Language(language_id, lang_option)
    tree_sitter_parser.set_language(tree_sitter_lang)
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        tree = tree_sitter_parser.parse(bytes(code, 'utf8'))
    except:
        util.error("Failed to parse AST:", file_path)
        return

    glang_statements = []
    parser = glang_ir_parser.Parser()
    parser.parse(tree.root_node, glang_statements)
    return glang_statements

def deal_with_file_unit(current_node_id, file_unit, options, apps):
    if options.debug:
        util.debug("Lang-Parser:", file_unit)

    glang_statements = parse(options, file_unit)
    if not glang_statements:
        return (current_node_id, None)
    if options.debug and options.print_stmts:
        pprint.pprint(glang_statements, compact=True, sort_dicts=False)

    apps.notify(constants.EventKind.GLANGIR, glang_statements)
    current_node_id, flatten_nodes = GLangProcess(current_node_id).flatten(glang_statements)
    if not flatten_nodes:
        return (current_node_id, flatten_nodes)

    if options.debug and options.print_stmts:
        pprint.pprint(flatten_nodes, compact=True, sort_dicts=False)

    return (current_node_id, flatten_nodes)