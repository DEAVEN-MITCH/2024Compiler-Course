#!/usr/bin/env python3

# system modules
import os
import pprint

# sys.setrecursionlimit(10000)
from lian.config import config, constants
from lian.lang import glang_parser, storage
from lian.util import util

def init_start_stmt_id(symbol_table):
    init_len = (len(symbol_table) + 10) // 10 * 10
    return init_len

def run(options, apps, module_symbols):
    symbol_table = module_symbols.module_symbol_table
    all_units = symbol_table.query(
            (symbol_table.symbol_type == constants.SymbolKind.UNIT_SYMBOL)
            & (symbol_table.unit_ext.isin(options.language_extensions))
    )
    if options.benchmark:
        all_units = all_units.slice(0, config.MAX_BENCHMARK_TARGET)

    if len(all_units) == 0:
        util.error_and_quit("No files found for analysis.")

    current_node_id = init_start_stmt_id(symbol_table)
    exporter = storage.Exporter(
        os.path.join(options.workspace, config.GLANG_DIR), module_symbols
    )
    for row in all_units:
        # if row.symbol_type == constants.SymbolKind.UNIT_SYMBOL and row.unit_ext in extensions:
        current_node_id, glang_ir = glang_parser.deal_with_file_unit(
            current_node_id, row.unit_path, options, apps
        )
        exporter.add_data(glang_ir, row)
    exporter.export()
