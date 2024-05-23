#!/usr/bin/env python3
# system modules
import os
import re
import sys
import pandas as pd
import numpy as np
import networkx as nx
import math
import keyword

from . import dataframe_operation as do
from lian.config import config

@profile
def is_empty(element):
    if isna(element):
        return True
    if isinstance(element, (pd.DataFrame, np.ndarray)):
        return element.size == 0
    if not element:
        return True
    return False

def isna(element):
    if element is None:
        return True
    return isinstance(element, float) and math.isnan(element)

def is_none(element):
    return is_empty(element)

def is_available(element):
    return not is_empty(element)

def file_md5(filename, chunksize=65536):
    m = _md5.md5()
    with open(filename, 'rb') as f:
        while chunk := f.read(chunksize):
            m.update(chunk)
    return m.hexdigest()

def error_and_quit(*msg):
    sys.stderr.write(f"[ERROR]: {''.join(msg)}\n")
    sys.exit(-1)

def error(*msg):
    # logging.error('这是一条debug级别的日志')
    sys.stderr.write(f"[ERROR]: {''.join(msg)}\n")

def debug(*msg):
    if config.DEBUG_FLAG:
        output = []
        for m in msg:
            output.append(str(m))
        sys.stdout.write(f"[DEBUG]: {' '.join(output)}\n")

def warn(*msg):
    sys.stderr.write(f"[WARNING]: {''.join(msg)}\n")
        
def log(*msg):
    print(*msg)

def remove_comments_and_newlines(input_string):
    # Remove single-line comments (// ...)
    input_string = re.sub(r'\/\/[^\n]*', '', input_string)

    # Remove multi-line comments (/* ... */)
    input_string = re.sub(r'\/\*[\s\S]*?\*\/', '', input_string)

    # Remove newline symbols and extra whitespaces
    input_string = re.sub(r'\n|\r|\s+', '', input_string)

    return input_string

def cut_string(input_string, last_element, max_length=1000):
    if not input_string:
        return ""

    last_plus_index = input_string[:max_length].rfind(last_element)

    if last_plus_index != -1:
        return input_string[:last_plus_index]

    return input_string[:max_length]

def count_lines_of_code(code_file, ignore_comments_spaceline=False):
    with open(code_file, 'r') as file:
        lines = file.readlines()

    if not ignore_comments_spaceline:
        return len(lines)

    code_lines = 0
    in_multiline_comment = False
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line in ["{", "}"]:
            continue
        if line.startswith('//'):
            continue
        if line.startswith('/*'):
            in_multiline_comment = True
        if line.endswith('*/'):
            in_multiline_comment = False
            continue
        if in_multiline_comment:
            continue
        code_lines += 1

    return code_lines

def replace_path_ext(input_path, new_ext):
    return os.path.splitext(input_path)[0] + new_ext

def generate_method_signature(method_info):
    return ""

def calc_path_distance(path1, path2):
    # Split the paths into components
    components1 = path1.split('/')
    components2 = path2.split('/')

    # Count the differing components
    length = max(len(components1), len(components2))

    distance = 0
    for i in range(length):
        if i >= len(components1) or i >= len(components2) or components1[i] != components2[i]:
            distance += 1

    return distance

FIRST_VAR_CHARS = {"%", "@", "$", "_"}
def is_variable(name):
    if isinstance(name, str) and len(name) > 0:
        # TODO:[rn] 程序中的关键字不能作为变量名。但因编程语言而异，此处排除了python中的关键字。
        if keyword.iskeyword(name):
            return False
        first_char = name[0]
        if first_char in FIRST_VAR_CHARS or first_char.isalpha():
            return True

    return False

def merge_list(first, second):
    return list(dict.fromkeys(first + second))

class SimpleEnum:
    def __init__(self, args):
        self._members = {}
        self._reverse_lookup = {}
        if isinstance(args, list):
            # Initialization from list
            for i, name in enumerate(args):
                self._members[name] = i
                self._reverse_lookup[i] = name
                setattr(self, name, i)
        elif isinstance(args, dict):
            # Initialization from dictionary
            for name, value in args.items():
                self._members[name] = value
                assert value not in self._reverse_lookup, f"The value {value} is repeative in the enum"
                self._reverse_lookup[value] = name  # Assuming the values are unique and hashable
                setattr(self, name, value)

    def __getitem__(self, value):
        return self._reverse_lookup.get(value)

    def __getattr__(self, item):
        return self._members.get(item)

def find_cfg_last_nodes(graph):
    leaf_stmts = set()
    for stmt in graph.nodes:
        if graph.out_degree(stmt) == 0:
            leaf_stmts.add(stmt)

    if -1 in leaf_stmts:
        leaf_stmts.remove(-1)
        leaf_stmts.update(graph.predecessors(-1))
    return leaf_stmts

    
