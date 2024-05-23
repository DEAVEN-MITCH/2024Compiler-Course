#!/usr/bin/env python3

import argparse
import importlib
import inspect
import os
import re
from dataclasses import dataclass, field

from lian.config import config 
from lian.config.constants import EXTENSIONS_LANG
from lian.util import util


@dataclass
class Options:
    """
    Class Options

    Represents a set of options that can be used to configure the behavior of a program.

    Attributes:
        recursive (bool): Flag indicating whether to operate recursively on directories.
        input (set): Set of input files or directories.
        workspace (str): Output directory for generated files.
        debug (bool): Flag indicating whether to enable debugging output.
        print_stmts (bool): Placeholder attribute.
        cores (int): Number of cores to use for parallel processing.
        android (bool): Flag indicating whether to perform Android-specific operations.
        apps (list): List of application instances.
        sub_command (str): Current sub-command of the program.
        language (str): Language code for the program.

    Methods:
        __post_init__(): Initializes the attributes of the Options class instance.
        __apps(): Retrieves concrete classes from app modules and creates instances.
        __output_dir(): Creates the output directory if it does not exist.
        __read_directory(dir_path): Reads files and directories in a given directory path based on the sub-command.
        __handle_lang_dir(dir_path): Handles files in the directory for the "lang" sub-command.
        __handle_semantic_dir(dir_path): Handles files in the directory for the "semantic" sub-command.
        __add_to_input_files(root, file_name): Adds a file to the input files set.
        __input(): Validates and processes the input files.
        __debug(): Prints debug information if debug is enabled.
    """
    recursive: bool = False
    input: list = field(default_factory=list)
    workspace: str = ""
    debug: bool = False
    force: bool = False
    benchmark: bool = False
    print_stmts: bool = False
    cores: int = None
    android: bool = False
    apps: list = field(default_factory=list)
    sub_command: str = ""
    language: str = ""

    def __post_init__(self):
        self.__apps()
        self.__output_dir()
        # self.__input()

    def __apps(self):

        def get_concrete_classes(module):
            classes = inspect.getmembers(module, inspect.isclass)

            for class_name, class_type in classes:
                if not inspect.isabstract(class_type) and len(class_type.__bases__) == 1 and class_type.__bases__[
                    0] != object:
                    # concrete_classes.append((class_name, class_type))
                    return class_type

            return None

        def create_instance_from_path(app_path):
            module_name = "temp_module"
            spec = importlib.util.spec_from_file_location(module_name, app_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            concrete_class = get_concrete_classes(module)
            if concrete_class:
                return concrete_class()
            return concrete_class

        self.apps = [create_instance_from_path(path) for path in self.apps]

    def __output_dir(self) -> None:
        if self.workspace and not os.path.exists(self.workspace):
            os.makedirs(self.workspace)

    # TODO: Not Sure What This Method Does
    def extend_langs_from_db(self):
        if len(self.input) == 0:
            return
        for f in self.input:
            lang = re.search(r'\.(.+)\.glang$', f)
            if lang:
                lang = lang.group(1)
                if lang in EXTENSIONS_LANG:
                    self.target_langs.add(EXTENSIONS_LANG[lang])


def parse_args(input_source=None) -> Options:
    """

    This method `parse_args` is used to parse command line arguments and return an instance of the `Options` class.

    Parameters:
    - `input_source` (optional): Input source to parse command line arguments from. If not provided, command line arguments will be parsed from the system's standard input.

    Return Type:
    - `Options`: An instance of the `Options` class containing the parsed command line arguments.

    Example Usage:
    ```
    options = parse_args()
    ```

    """
    # Create the top-level parser

    main_parser = argparse.ArgumentParser()
    subparsers = main_parser.add_subparsers(dest='sub_command')
    # Create the parser for the "lang" command
    parser_lang = subparsers.add_parser('lang')
    parser_semantic = subparsers.add_parser('semantic', help='Perform code semantic analysis', )
    parser_security = subparsers.add_parser('security', help='Conduct code security analysis', )
    parser_run = subparsers.add_parser('run', help='Run the code analysis end-to-end', )

    # Add the arguments to the main parser
    for parser in [parser_lang, parser_semantic, parser_security, parser_run]:
        parser.add_argument("-b", "--benchmark", action="store_true")
        # parser.add_argument("-r", "--recursive", action="store_true",
        #                    help="Recursively search the input directory")
        parser.add_argument('input', nargs='+', type=str, help='the input')
        parser.add_argument('-w', "--workspace", default=config.DEFAULT_WORKSPACE, type=str, help='the workspace directory (default:lian_workspace)')
        parser.add_argument("-f", "--force", action="store_true", help="Enable the FORCE mode for rewritting the workspace directory")
        parser.add_argument("-d", "--debug", action="store_true", help="Enable the DEBUG mode")
        parser.add_argument("-p", "--print_stmts", action="store_true", help="Print statements")
        parser.add_argument("-c", "--cores", default=1, help="Configure the available CPU cores")
        parser.add_argument("--android", action="store_true", help="Enable the Android analysis mode")
        parser.add_argument("-a", "--apps", default=[], action='append', help="Config the <plugin> dir")
        parser.add_argument('-l', "--language", default="", type=str, help='programming language')

    if input_source:
        return Options(**vars(main_parser.parse_args(input_source)))
    return Options(**vars(main_parser.parse_args()))


if __name__ == "__main__":
    options = parse_args(
        ["lang", "python", r"D:\repo\lian\tests\python\cases", r"D:\repo\lian\tests\python\cases2",
         r"D:\repo\lian\tests\python\output", "-p", "-d"])
