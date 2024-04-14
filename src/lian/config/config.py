#!/usr/bin/env python3

import os,sys

DEBUG                           = False

LANG                            = None
PRINT_STMTS                     = False
STRING_MAX_LEN                  = 200

WORKDIR                         = "/app"
LANGS_SO_PATH                   = WORKDIR + "/experiment_2/lib/langs.so"
FILES_TO_BE_ANALYZED            = set()
COMMON_INPUT_DIR                = None
OUTPUT_DIR                      = "./output"

MAX_CPU_CORE_NUM                = 1

SEMANTIC_SERVER_MODE            = False
SEMANTIC_SERVER_IP              = None
SEMANTIC_SERVER_PORT            = None


DUMP_AST                        = False
DUMP_GLANG_IR                   = False
DUMP_CONTROL_FLOW_GRAPH         = False
DUMP_STATE_GRAPH                = False
DUMP_METHOD_SUMMARY				= False
DUMP_CALL_GRAPH                 = False


DUMP_AST_DIR                    = "ast"
DUMP_GLANG_IR_DIR               = "glang_ir"
DUMP_CONTROL_FLOW_GRAPH_DIR     = "control_flow_graph"
DUMP_STATE_GRAPH_DIR            = "state_graph"
DUMP_METHOD_SUMMARY_DIR         = "method_summary"
DUMP_CALL_GRAPH_DIR             = "call_graph"