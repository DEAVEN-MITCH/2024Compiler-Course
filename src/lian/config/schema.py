#!/usr/bin/env python3

import os,sys
import numpy as np


module_symbol_table_schema = {
    "symbol_id"                     : 0,
    "parent_symbol_id"              : 0,
    "symbol_type"                   : 0,
    "symbol_name"                   : "",
    "alias"                         : "",
    "unit_ext"                     	: "",
    "lang"                          : "",
    "unit_path"                     : "",
    "glang_path"                    : "",
    "scope_space_path"				: "",
    "control_flow_graph_path"       : "",
    "symbol_dependency_graph_path"  : "",
    "stmt_status_path"				: "",
    "symbols_states_path"			: "",
    "abstract_state_graph_path"     : "",
    "method_summary_path"           : "",
}

glang_schema = [
    "operation",
    "stmt_id",
    "parent_stmt_id",
    "name",
    "alias",
    "attr",
    "data",
    "data_type",
    "supers",
    "init",
    "static_init",
    "fields",
    "methods",
    "member_fields",
    "nested",
    "parameters",
    "type_parameters",
    "args",
    "array",
    "index",
    "source",
    "target",
    "condition",
    "body",
    "init_body",
    "then_body",
    "else_body",
    "condition_prebody",
    "update_body",
    "catch_body",
    "final_body",
    "receiver_object",
    "field",
    "key",
    "operator",
    "operand",
    "operand2",
    "start",
    "end",
    "step",
    "value",
    "return_type",
    "prototype",
    "with_init",
    "address",
    "expcetion",
    "unit_id"
]

scope_space_schema = [
    "unit_id",
    "stmt_id",
    "parent_stmt_id",
    "scope_kind",
    "package_stmt",
    "import_stmt",
    "variable_decl",
    "method_decl",
    "class_decl"
]

unit_symbol_table_schema = [
    "unit_id",
    "symbol_id",
    "parent_symbol_id",
    "symbol_type",
    "stmt_id",
    "package",
    "imported_symbol",
    "imported_symbol_id",
    "target",
    "attr",
    "variable_type",
    "variable_name",
    "method_return_type",
    "method_name",
    "method_signature",
    "class_name",
    "parent_class",
    "parent_class_id",
    "is_override",
    "field",
    "field_type",
    # "class_method_return_type", "class_method", "class_method_signature",
]

control_flow_graph_schema = {
    "unit_id"                     : 0,
    "method_id"                   : 0,
    "src_stmt_id"                 : 0,
    "dst_stmt_id"                 : 0,
    "control_flow_type"           : 0
}

symbol_dependency_graph_schema = {
    "unit_id"						: 0,
    "method_id"                     : 0,
    "src_stmt_id"                   : 0,
    "dst_stmt_id"                   : 0,
    "symbol_dependency_type"        : ""
}

method_summary_schema = [
    'unit_id',                      
    'method_id',                                             
    'symbol_type',
    'symbol',
    'last_all_states'
]

abstract_method_graph_schema = [
    "unit_id",
    "method_id",
    "is_init",
    "operation",
    "in1",
    "id1" "state1",
    "in2",
    "id2",
    "state2",
    "out",
    "out_id",
    "out_state"
]


stmt_status_schema = [
    "unit_id",
    "method_id",
    "stmt_id",
    "defined_symbol",
    "used_symbols",
    "field",
    "operation",
    "in_bits",
    "out_bits",
]

bit_vector_schema = [
    "unit_id",
    "method_id",
    "bit_pos",
    "stmt",
]

symbols_states_schema = [
    "unit_id",
    "method_id",
    "stmt_id",
    "index",
    "symbol_or_state",
    "symbol_id",
    "name",
    "states",
    "default_data_type",
    "state_id",
    "state_type",
    "data_type",
    "array",
    "array_tangping_flag",
    "fields",
    "value" # [rn]少这一行，dataframe中打印不出value
]

call_graph_schema = [
    "caller",
    "callee",
    "call_site" # at which stmt_id caller calls callee
]