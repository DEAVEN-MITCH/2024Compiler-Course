#!/usr/bin/env python3

import os,sys
import pandas as pd
import socket
import re

from lian.config import config, schema
from lian.init import module_symbols
from lian.util import dataframe_operation as do


class Exporter:
    def __init__(self, output_path, symbols: module_symbols.ModuleSymbols):
        self.accumulated_rows = []
        self.output_path = output_path
        self.max_rows = config.MAX_ROWS
        self.count = 0
        self.bundle_path = os.path.join(self.output_path, f"glang_bundle{self.count}")
        self.symbols = symbols
    
    @profile
    def add_data(self, flatten_nodes, unit_info):
        if flatten_nodes is None or len(flatten_nodes) == 0:
            return

        unit_id = unit_info.symbol_id
        for node in flatten_nodes:
            node["unit_id"] = unit_id
        self.accumulated_rows.extend(flatten_nodes)
        self.symbols.update_glang_path(unit_info, self.bundle_path)

        if len(self.accumulated_rows) >= self.max_rows:
            self.export()

    def export(self):
        if len(self.accumulated_rows) > 0:
            do.DataFrameAgent(self.accumulated_rows).save(self.bundle_path)

        self.accumulated_rows = []
        self.count += 1
        self.bundle_path = os.path.join(self.output_path, f"glang_bundle{self.count}")

if __name__ == "__main__":
    sys.path.append(os.path.realpath(os.path.dirname(os.path.realpath(__file__)) + "/../"))
    from lian.config import config
    from lian.util import util

    dataframe = [{"value": "4"}, {"value": "123"}]
    # export(dataframe)
