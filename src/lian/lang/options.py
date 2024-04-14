#!/usr/bin/env python3

import os,sys

from lian.config import config
from lian.util import util


LANG_EXTENSIONS = {
    "c"         	: [".c", ".h"],
    "cpp"       	: [".cpp", ".cxx", ".cc", ".h", ".hpp"],
    "csharp"    	: [".cs"],
    "rust"      	: [".rs"],
    "go"        	: [".go"],
    "java"      	: [".java"],
    "javascript"	: [".js"],
    "typescript"	: [".ts"],
    "kotlin"    	: [".kt", ".kts"],
    "llvm"      	: [".ll"],
    "python"      	: [".py"],
    "ruby"      	: [".rb"],
    "smali"     	: [".smali"],
    "php"       	: [".php"],
}


def find_lang_files(directory):
    extensions = LANG_EXTENSIONS.get(config.LANG, [])
    for root, _, files in os.walk(directory):
        for f in files:
            for ext in extensions:
                if f.endswith(ext):
                    config.FILES_TO_BE_ANALYZED.add(os.path.abspath(os.path.join(root, f)))

def extract_lang_and_assert():
    for arg in sys.argv:
        if arg.startswith("--lang=") or arg.startswith("-lang="):
            config.LANG = arg.split("=")[1]
            break

    if not config.LANG:
        print_usage_and_quit()

def print_usage_and_quit():
    util.error_and_quit("Need args: [-debug -print_statements] [-output=<output_dir>] -lang=xxxx <directory1/file1> <directory2/file2> ...")

def check_debug():
    for arg in sys.argv:
        if arg.startswith("-debug"):
            config.DEBUG = True

        if arg.startswith("-print_statements"):
            config.PRINT_STMTS = True

def check_output():
    for arg in sys.argv:
        if arg.startswith("-output=") or arg.startswith("--output="):
            config.OUTPUT = arg.split("=")[1]
            break
            
def asert_argv_size():
    if len(sys.argv) == 1:
        print_usage_and_quit()

def check_paths():
    for path in sys.argv[1:]:
        if os.path.isdir(path):
            find_lang_files(path)
        if os.path.isfile(path):
            config.FILES_TO_BE_ANALYZED.add(os.path.abspath(path))

def find_common_path():
    path_components = []
    for path in config.FILES_TO_BE_ANALYZED:
        path_components.append(path.split('/')[:-1])

    min_length = len(path_components[0])
    for components in path_components:
        min_length = min(min_length, len(components))

    common_prefix = ''
    for i in range(min_length):
        common_component = path_components[0][i]
        for components in path_components:
            if components[i] != common_component:
                break
        else:
            common_prefix += common_component + '/'

    return common_prefix
            
def parse():
    asert_argv_size()
    check_debug()
    extract_lang_and_assert()
    check_output()
    check_paths()    

    length = len(config.FILES_TO_BE_ANALYZED)
    if length == 0:
        util.error_and_quit("No files found. Exit.")
        
    config.COMMON_INPUT_DIR = find_common_path()
    if not config.COMMON_INPUT_DIR:
        util.error_and_quit("Failed to find the common input directory.")

    if config.DEBUG:
        print("Setting DEBUG to True")
        print("Setting debug.print_statements to True")

        print("Setting config.lang to", config.LANG)

        print("Found", len(config.FILES_TO_BE_ANALYZED), "files to be analyzed.")

        print("Setting common_input_dir: ", config.COMMON_INPUT_DIR)
        print("Setting output_dir: ", config.OUTPUT_DIR)
