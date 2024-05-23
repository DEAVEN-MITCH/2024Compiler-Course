#!/usr/bin/env python3

import numpy as np
import pandas as pd

from lian.config import config
from . import util

class DataFrameAgent:
    @profile
    def __init__(self, data = None, columns = None, reset_index = False):
        self._data = None
        self._columns = columns
        self._reset_index = reset_index
        self._schema = {}
        self._schema_list = []
        self._row_cache = []
        self._column_cache = {}
        self._column_name_cache = set()

        self._need_refresh_schema = True
        self._need_refresh_rows = True
        self._need_refresh_columns = True

        if data is None:
            return

        if isinstance(data, pd.DataFrame):
            self._data = data
        elif isinstance(data, DataFrameAgent):
            self._data = data._data
            self._row_cache = data._row_cache
            self._schema_list = data._schema_list
            self._schema = data._schema
        else:
            if columns is not None:
                if isinstance(columns, dict):
                    self._data = pd.DataFrame(data, columns = columns.keys())
                    # self.column_as_type(columns)
                else:
                    self._data = pd.DataFrame(data, columns = columns)
            else:
                self._data = pd.DataFrame(data)

        if reset_index:
            self.reset_index()

    @profile
    def __getitem__(self, item):
        # treat item as a column name if item is string
        if isinstance(item, str):
            return self.column(item)

        # item is a row index if item is a integer
        if isinstance(item, int):
            return self.access(item)

        # For other cases item is query mask
        return self.query(item)

    def __getattr__(self, column_name):
        return self.column(column_name)

    @profile
    def __iter__(self):
        self.refresh_schema()
        self.refresh_rows()

        counter = 0
        for row in self._row_cache:
            yield Row(row, self._schema, self._data.index[counter])
            counter += 1

    def __len__(self):
        return len(self._data.index)

    def __repr__(self):
        self.refresh_rows()
        self.refresh_schema()

        row_str = []
        for row in self._row_cache:
            row_str.append("  " + str(list(row)).replace("None,", "").replace("nan,", ""))
        result = "\n".join(row_str)
        return f'dataframeagent(length={len(self)}, _schema={str(self._schema)}, _rows = [\n{result}\n])'

    def is_empty(self):
        return self._data.empty

    def is_available(self):
        return not self._data.empty

    def refresh_schema(self):
        if not self._need_refresh_schema:
            return

        self._need_refresh_schema = False
        current_schema_list = self._data.columns
        if self._schema_list:
            if self._schema_list == current_schema_list:
                return

        self._schema = {}
        for i in range(len(current_schema_list)):
            self._schema[current_schema_list[i]] = i

    @profile
    def refresh_columns(self, column_name):
        flag = False
        if self._need_refresh_rows:
            flag = True
        if column_name not in self._column_name_cache:
            self._column_name_cache.add(column_name)
            flag = True
        if not flag:
            return

        self._column_cache = {}
        for column_name in self._column_name_cache:
            self._column_cache[column_name] = Column(self._data[column_name])

    @profile
    def refresh_rows(self):
        if not self._need_refresh_rows:
            return
        self._need_refresh_rows = False
        self._row_cache = self._data.values

    @profile
    def get_rows(self):
        self.refresh_rows()
        return list(self._row_cache)

    @profile
    def column_as_type(self, columns):
        self._data.astype(columns, copy = False)

    @profile
    def unique_values_of_column(self, column):
        return self._data[column].dropna().unique()

    def load(self, path):
        self._data = pd.read_feather(path)
        self._need_refresh_schema = True
        self._need_refresh_rows = True
        self._need_refresh_columns = True
        return self

    def save(self, path):
        self.reset_index()._data.to_feather(path)
        return self

    def column(self, column_name):
        self.refresh_columns(column_name)
        return self._column_cache[column_name]

    @profile
    def access(self, row_index):
        self.refresh_schema()
        self.refresh_rows()
        if row_index >= 0 and row_index < len(self._row_cache):
            return Row(self._row_cache[row_index], self._schema, self._data.index[row_index])
        return None

    @profile
    def slice(self, start_index, end_index):
        return DataFrameAgent(self._data.iloc[start_index: end_index], columns = self._schema_list)

    @profile
    def append_data_model(self, extra_data):
        target_to_be_merged = extra_data
        if isinstance(extra_data, DataFrameAgent):
            target_to_be_merged = extra_data._data
        self._data = pd.concat([self._data, target_to_be_merged], ignore_index=True, copy = False)

        self._need_refresh_rows = True
        self._need_refresh_columns = True
        self._need_refresh_schema = True


    @profile
    def modify_row(self, row_index, new_row):
        self._data.iloc[row_index] = new_row
        self._need_refresh_rows = True
        self._need_refresh_columns = True

    def modify_column(self, column_name, value):
        self._data[column_name] = value
        self._need_refresh_rows = True
        self._need_refresh_columns = True

    def rename_column(self, columns):
        self._data.rename(columns=columns, inplace=True, copy = False)
        self._need_refresh_schema = True
        self._need_refresh_columns = True

    @profile
    def modify_element(self, row_index, column_name, value):
        self._data.loc[row_index, column_name] = value
        self._need_refresh_rows = True
        self._need_refresh_columns = True
        self._need_refresh_schema = True


    @profile
    def query(self, mask, reset_index = False):
        # result = self._data.loc[mask]
        df = self._data.loc[mask]
        return DataFrameAgent(df, columns = self._schema_list, reset_index = reset_index)

    @profile
    def query_first(self, mask):
        self.refresh_schema()
        self.refresh_rows()
        result = np.where(mask)[0]
        if len(result) == 0:
            return None
        first_index = result[0]
        return Row(self._row_cache[first_index], self._schema, first_index)

    def fillna(self, value):
        self._data.fillna(value, inplace = True)

    def remove_blocks(self):
        """
        remove all internal blocks from current data model
        """
        self.refresh_schema()
        self.refresh_rows()

        block_start_end = np.where(self.operation.isin(["block_start", "block_end"]))[0]
        if len(block_start_end) == 0:
            return self

        pos = self._schema["stmt_id"]

        stmt_ids_and_indices = []
        for i in block_start_end:
            stmt_ids_and_indices.append((self._row_cache[i][pos], self._data.index[i]))

        id_to_indices = {}
        for id_and_index in stmt_ids_and_indices:
            the_id = id_and_index[0]
            the_index = id_and_index[1]
            if the_id not in id_to_indices:
                id_to_indices[the_id] = []
            id_to_indices[the_id].append(the_index)

        result = set()
        for key in id_to_indices:
            value = id_to_indices[key]
            start_index = value[0]
            end_index =  value[1]
            result.update(range(start_index, end_index + 1))
        return DataFrameAgent(self._data.drop(result), columns = self._schema_list)

    @profile
    def reset_index(self, move_index_to_column = False, directly_modify_current_dataframe = True):
        new_data = self._data.reset_index(
            drop=(not move_index_to_column),
            inplace = directly_modify_current_dataframe
        )
        if not directly_modify_current_dataframe:
            self._data = new_data
        return self

    @profile
    def search_block_id(self, block_id):
        if util.isna(block_id):
            return None
        query = (self.stmt_id.values == block_id)
        block_start_end = np.where(query)[0]
        if len(block_start_end) < 2:
            return None
        return block_start_end

    @profile
    def read_block(self, block_id, reset_index = False):
        block_start_end = self.search_block_id(block_id)
        if block_start_end is None:
            return None

        block = self.slice(block_start_end[0] + 1, block_start_end[1])
        if reset_index:
            block.reset_index()
        return block

    @profile
    def boundary_of_multi_blocks(self, multi_block_ids):
        ids = [-1]
        for block_id in multi_block_ids:
            if not util.isna(block_id):
                block_start_end = self.search_block_id(block_id)
                if block_start_end is not None:
                    ids.extend(block_start_end)
        return max(ids)

    def display(self):
        self.refresh_schema()
        self.refresh_rows()
        if config.DEBUG_FLAG:
            util.debug(self._row_cache)

class Row:
    def __init__(self, row, schema, index):
        self._row = row
        self._schema = schema
        self._index = index

    def __getattr__(self, item):
        pos = self._schema.get(item, -1)
        if pos != -1:
            return self._row[pos]
        return None

    def __repr__(self):
        return f"Row({self._row})"

    def get_index(self):
        return self._index

    def __len__(self):
        return len(self._row)


class Column(pd.Series):
    # def __new__(cls, input_array, *args, **kwargs):
    #     obj = pd.Series(input_array, *args, **kwargs).view(cls)
    #     return obj

    def isna(self):
        return pd.isna(self)

    def is_empty(self):
        return len(self) == 0

    def is_available(self):
        return not self.is_empty()

    def isin(self, target_list: list):
        return np.isin(self, target_list)

    def isof(self, target_list):
        return np.isin(self, target_list)