#!/usr/bin/env python3
import os
import sys

import builtins
try:
    builtins.profile
except AttributeError:
    # No line profiler, provide a pass-through version
    def profile(func): return func
    builtins.profile = profile

# disable copy
import pandas as pd
pd.options.mode.copy_on_write = False

sys.path.append(os.path.realpath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))))

from lian.interfaces.args_parser import Options, parse_args
from lian.interfaces import lang, semantic, security
from lian.apps import app_manager
from lian.init import prepare, module_symbols
from lian.config import config, constants
from lian.util import util

class Lian:
    def __init__(self):
        self.command_handler = {
            "lang": self.lang_command,
            "semantic": self.semantic_command,
            "security": self.security_command,
            "run": self.run_command,
        }

    def adjust_options(self, options):
        options.language = options.language.split(",")
        if len(options.language) == 0:
            util.error_and_quit("The target language should be specified.")

        file_extensions = []
        for lang_option in options.language:
            file_extensions.extend(constants.LANG_EXTENSIONS.get(lang_option.strip(), []))
        options.language_extensions = file_extensions

        return options

    # app path -> options -> app_manager -> load app from the path (importlib) -> register app
    def run(self):
        options = parse_args()
        options = self.adjust_options(options)

        config.DEBUG_FLAG = options.debug
        if options.debug:
            util.debug(options)

        prepare.setup(options)
        apps = app_manager.AppManager(options)
        init_module_symbols = module_symbols.build_module_symbols(options)
        if init_module_symbols.module_symbol_table.is_empty():
            util.error_and_quit("No target file found.")
        handler = self.command_handler.get(options.sub_command)
        if handler:
            handler(options, apps, init_module_symbols)

    def lang_command(self, options: Options, apps, init_module_symbols):
        lang.run(options, apps, init_module_symbols)

    def semantic_command(self, options, apps, init_module_symbols):
        semantic.run(options, apps, init_module_symbols)

    def security_command(self, options, apps):
        pass

    def run_command(self, options, apps, init_module_symbols):
        self.lang_command(options, apps, init_module_symbols)
        self.semantic_command(options, apps, init_module_symbols)
        # self.security_command()

def main():
    Lian().run()


if __name__ == "__main__":
    main()
