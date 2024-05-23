#!/usr/bin/env python3

import os

import pandas as pd

from lian.config import schema, constants, config
from lian.util import dataframe_operation as do

SymbolKind = constants.SymbolKind
EXTENSIONS_LANG = constants.EXTENSIONS_LANG

class PathManager:
    def __init__(self, a):
        self.index_id = config.START_INDEX
        self.index_to_path = {}
        self.path_to_index = {}

    def get_index_id(self):
        i = self.index_id
        self.index_id += 1
        return i

    def add_path(self, path):
        if path in self.path_to_index:
            return self.path_to_index[path]
        i = self.get_index_id()
        self.path_to_index[path] = i
        self.index_to_path[i] = path
        return i

    def find_index_by_path(self, path):
        return self.path_to_index.get(path, -1)

    def find_path_by_index(self, index):
        return self.index_to_path.get(index, -1)

class ModuleSymbols:
    def __init__(self, options):
        self.global_symbol_id = config.START_INDEX
        self.module_symbol_results = []

        self.options = options
        self.module_symbol_table = None

    def save_results(self):
        self.module_symbol_table = do.DataFrameAgent(
            # self.module_symbol_results, columns=schema.module_symbol_table_schema
            self.module_symbol_results
        )

        del self.module_symbol_results
        self.module_symbol_results = []

    def export(self):
        path = os.path.join(self.options.workspace, "module_symbol_table")
        self.module_symbol_table.save(path)

    def generate_symbol_id(self):
        result = self.global_symbol_id
        self.global_symbol_id += 1
        return result

    def find_unit_by_id(self, unit_id):
        self.module_symbol_table.symbol_id
        return self.module_symbol_table.query_first(
            self.module_symbol_table.symbol_id == unit_id
        )

    def scan_modules(self, module_path=None, parent_module_id=-1):
        if module_path is None:
            module_path = os.path.join(self.options.workspace, "src")

        # Only scan current directory, _not_ recursively
        for entry in os.scandir(module_path):
            # 1. scan all folders and build the module-level symbols
            if entry.is_dir():
                module_id = self.generate_symbol_id()
                self.module_symbol_results.append({
                    "symbol_id": module_id,
                    "symbol_name": entry.name,
                    "parent_symbol_id": parent_module_id,
                    "symbol_type": SymbolKind.MODULE_SYMBOL
                })

                self.scan_modules(entry.path, module_id)

            # 2. scan each .gl file, and extract the unit-level symbols
            # TODO How to find the target files
            elif entry.is_file():
                unit_id = self.generate_symbol_id()
                unit_name, unit_ext = os.path.splitext(entry.name)
                self.module_symbol_results.append({
                    "symbol_id": unit_id,
                    "symbol_name": unit_name,
                    "unit_ext": unit_ext,
                    "lang": EXTENSIONS_LANG.get(unit_ext),
                    "unit_path": entry.path,
                    "parent_symbol_id": parent_module_id,
                    "symbol_type": SymbolKind.UNIT_SYMBOL
                })

    def update_glang_path(self, unit_info, glang_path):
        self.module_symbol_table.modify_element(
            unit_info.get_index(), "glang_path", glang_path)

    def update_cfg_path_by_glang_path(self, glang_path, cfg_path):
        satisfied = self.module_symbol_table.query(self.module_symbol_table.glang_path == glang_path)
        for index in satisfied._data.index:
            self.module_symbol_table.modify_element(index, "control_flow_graph_path", cfg_path)

    def update_sdg_path_by_glang_path(self, glang_path, sdg_path):
        satisfied = self.module_symbol_table.query(self.module_symbol_table.glang_path == glang_path)
        for index in satisfied._data.index:
            self.module_symbol_table.modify_element(index, "symbol_dependency_graph_path", sdg_path)

    def update_scope_space_path_by_glang_path(self, glang_path, scope_space_path):
        satisfied = self.module_symbol_table.query(self.module_symbol_table.glang_path == glang_path)
        for index in satisfied._data.index:
            self.module_symbol_table.modify_element(index, "scope_space_path", scope_space_path)

    def update_stmt_status_path_by_glang_path(self, glang_path, stmt_status_path):
        satisfied = self.module_symbol_table.query(self.module_symbol_table.glang_path == glang_path)
        for index in satisfied._data.index:
            self.module_symbol_table.modify_element(index, "stmt_status_path", stmt_status_path)

    def update_symbols_states_path_by_glang_path(self, glang_path, symbols_states_path):
        satisfied = self.module_symbol_table.query(self.module_symbol_table.glang_path == glang_path)
        for index in satisfied._data.index:
            self.module_symbol_table.modify_element(index, "symbols_states_path", symbols_states_path)
    
    def update_method_summary_path_by_glang_path(self, glang_path, method_summary_path):
        satisfied = self.module_symbol_table.query(self.module_symbol_table.glang_path == glang_path)
        for index in satisfied._data.index:
            self.module_symbol_table.modify_element(index, "method_summary_path", method_summary_path)


def build_module_symbols(options):
    ss = ModuleSymbols(options)
    ss.scan_modules()
    ss.save_results()

    return ss
