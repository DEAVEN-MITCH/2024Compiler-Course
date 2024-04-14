#!/usr/bin/env python3

import os,sys
import pprint
import tree_sitter

sys.path.append(os.path.realpath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

import options
import flatten_glang
import storage

from parser.parser_list import PARSERS 
from lian.config import config
from lian.util import util
from ctypes import c_void_p, cdll


def parse(file_path):
    glang_ir_parser = PARSERS.get(config.LANG)
    if not glang_ir_parser:
        util.error_and_quit("Unsupported language: " + options.language)

    # to avoid warning
    lib = cdll.LoadLibrary(os.fspath(config.LANGS_SO_PATH))
    language_function = getattr(lib, "tree_sitter_%s" % config.LANG)
    language_function.restype = c_void_p
    language_id = language_function()
    tree_sitter_parser = tree_sitter.Parser()
    tree_sitter_lang = tree_sitter.Language(language_id, config.LANG)
    tree_sitter_parser.set_language(tree_sitter_lang)
    try:
        with open(file_path, 'r') as f:
            code = f.read()
        tree = tree_sitter_parser.parse(bytes(code, 'utf8'))
    except:
        util.error("Failed to parse AST:", file_path)
        return

    glang_statements = []
    parser = glang_ir_parser()
    parser.parse(tree.root_node, glang_statements)

    return glang_statements

def deal_with_file_unit(file_unit):
    if config.DEBUG:
        print("Lang-Parser:", file_unit)

    glang_statements = parse(file_unit)
    if not glang_statements:
        return

    if config.DEBUG and config.PRINT_STMTS:
        pprint.pprint(glang_statements, compact=True, sort_dicts=False)

    flattened_nodes = flatten_glang.GLangProcess().flatten(glang_statements)
    if not flattened_nodes:
        return

    if config.DEBUG and config.PRINT_STMTS:
        pprint.pprint(flattened_nodes, compact=True, sort_dicts=False)

    storage.export(file_unit, flattened_nodes)
    

def main():
    options.parse()
    for file_unit in sorted(config.FILES_TO_BE_ANALYZED):
        deal_with_file_unit(file_unit)
        
if __name__ == "__main__":
    main()
