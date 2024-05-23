#!/usr/bin/env python3

import os,sys

DEBUG_FLAG						= False
START_INDEX						= 1
STRING_MAX_LEN                  = 200
MAX_PRIORITY                    = 100
MIN_ID_INTERVAL                 = 100

LANGS_SO_PATH                   = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "lib/langs.so")

DEFAULT_WORKSPACE               = "lian_workspace"
MODULE_SYMBOLS_FILE             = "module_symbols"

SRC_DIR                       	= "src"
GLANG_DIR                       = "glang"
SEMANTIC_DIR					= "semantic"

BIT_VECTOR_FILE  				= "bit_vector_schema"
TYPE_TABLE_FILE                 = "type_table"

CONTROL_FLOW_GRAPH_EXT			= ".cfg"
SYMBOL_DEPENDENCY_EXT           = ".sdg"
STMT_STATUS_EXT                 = ".stmt_status"
SYMBOLS_STATES_EXT              = ".symbols_states"
METHOD_SUMMARY_EXT              = ".method_summary"

MAX_ROWS                        = 40 * 10000
MAX_BENCHMARK_TARGET	   		= 10_000
MAX_STMT_STATE_ANALYIS_ROUND	= 6

LRU_CACHE_CAPACITY              = 100

