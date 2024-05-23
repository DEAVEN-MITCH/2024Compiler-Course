#!/usr/bin/env python3

from enum import auto
from lian.util import util

LANG_EXTENSIONS = {
    "c"             : [".c", ".h"],
    "cpp"           : [".cpp", ".cxx", ".cc", ".h", ".hpp"],
    "csharp"        : [".cs"],
    "rust"          : [".rs"],
    "go"            : [".go"],
    "java"          : [".java"],
    "javascript"    : [".js"],
    "typescript"    : [".ts"],
    "kotlin"        : [".kt", ".kts"],
    "scala"         : [".scala"],
    "llvm"          : [".ll"],
    "python"        : [".py"],
    "ruby"          : [".rb"],
    "smali"         : [".smali"],
    "swift"         : [".swift"],
    "php"           : [".php"],
    "codeql"        : [".ql"],
    "ql"            : [".ql"],
}

EXTENSIONS_LANG = {
    ".c"             : "c",
    ".h"             : "c",
    ".cpp"           : "cpp",
    ".cxx"           : "cpp",
    ".cc"            : "cpp",
    ".hpp"           : "cpp",
    ".cs"            : "csharp",
    ".rs"            : "rust",
    ".go"            : "go",
    ".java"          : "java",
    ".js"            : "javascript",
    ".ts"            : "typescript",
    ".kt"            : "kotlin",
    ".scala"         : "scala",
    ".ll"            : "llvm",
    ".py"            : "python",
    ".rb"            : "ruby",
    ".smali"         : "smali",
    ".swift"         : "swift",
    ".php"           : "php",
    ".ql"            : "codeql"
}

# """
# The EventKind class is a subclass of util.SimpleEnum and represents different types of events.
# Attributes:
#     NONE: Indicates a null event type.
#     GLANGIR: Indicates a Glangir event type.
#     CONTROL_FLOW: Indicates a control flow event type.
#     STATE_FLOW: Indicates a state flow event type.
#     METHOD_SUMMARY: Indicates a method summary event type.
#     ENTRY_POINT: Indicates an entry point event type.
#     CALL_GRAPH: Indicates a call graph event type.
#     TAINT_ANALYSIS: Indicates a taint analysis event type.
# """
EventKind = util.SimpleEnum({
    "NONE"                  : 0,
    "GLANGIR"               : 1,
    "CONTROL_FLOW"          : 2,
    "STATE_FLOW"            : 3,
    "METHOD_SUMMARY"        : 4,
    "ENTRY_POINT"           : 5,
    "CALL_GRAPH"            : 6,
    "TAINT_ANALYSIS"        : 7,
})

# """
# The `LangKind` class is an enumeration class that represents different programming languages.
# Attributes:
#     - C: Represents the C programming language.
#     - CPP: Represents the C++ programming language.
#     - CSHARP: Represents the C# programming language.
#     - RUST: Represents the Rust programming language.
#     - GO: Represents the Go programming language.
#     - JAVA: Represents the Java programming language.
#     - JAVASCRIPT: Represents the JavaScript programming language.
#     - TYPESCRIPT: Represents the TypeScript programming language.
#     - KOTLIN: Represents the Kotlin programming language.
#     - SCALA: Represents the Scala programming language.
#     - LLVM: Represents the LLVM programming language.
#     - PYTHON: Represents the Python programming language.
#     - RUBY: Represents the Ruby programming language.
#     - SMALI: Represents the Smali programming language.
#     - SWIFT: Represents the Swift programming language.
#     - PHP: Represents the PHP programming language.
#     - CODEQL: Represents the CodeQL programming language.
#     - QL: Represents the QL programming language.
# """
LangKind = util.SimpleEnum({
    "C"                 : 0,
    "CPP"               : 1,
    "CSHARP"            : 2,
    "RUST"              : 3,
    "GO"                : 4,
    "JAVA"              : 5,
    "JAVASCRIPT"        : 6,
    "TYPESCRIPT"        : 7,
    "KOTLIN"            : 8,
    "SCALA"             : 9,
    "LLVM"              : 10,
    "PYTHON"            : 11,
    "RUBY"              : 12,
    "SMALI"             : 13,
    "SWIFT"             : 14,
    "PHP"               : 15,
    "CODEQL"            : 16,
    "QL"                : 17,
})

# """
# This class represents the types of symbols in a program.
# Symbols can be of various types, such as module, unit, parent module, import, variable, method, class, parent class, field, and class method.
# The class extends the util.SimpleEnum class.
# Attributes:
#     MODULE: Represents a module symbol.
#     UNIT: Represents a unit symbol.
#     PARENT_MODULE: Represents a parent module symbol.
#     IMPORT: Represents an import symbol.
#     VARIABLE: Represents a variable symbol.
#     METHOD: Represents a method symbol.
#     CLASS: Represents a class symbol.
#     PARENT_CLASS: Represents a parent class symbol.
#     FIELD: Represents a field symbol.
#     CLASS_METHOD: Represents a class method symbol.
# """
SymbolKind = util.SimpleEnum({
    'MODULE'                : 0,
    'UNIT_SYMBOL'           : 1,
    'PARENT_MODULE'         : 2,
    'IMPORT'                : 3,
    'VARIABLE'              : 4,
    'METHOD'                : 5,
    'CLASS'                 : 6,
    'PARENT_CLASS'          : 7,
    'FIELD'                 : 8,
    'CLASS_METHOD'          : 9,
    'PACKAGE'               : 10,
    'MEMBER_METHOD'         : 11,
    'MODULE_SYMBOL'         : 12,
})

MethodSummarySymbolKind = util.SimpleEnum({
    'PARARMETER_SYMBOL'             : 1,
    'DEFINED_EXTERNAL_SYMBOL'       : 2,
    'USED_EXTERNAL_SYMBOL'          : 3,
    'RETURN_SYMBOL'                 : 4,
    'DYNAMIC_CALL'                  : 5,
    'DIRECT_CALL'                   : 6
})

# """
# A class that represents different types of control flow in a program.
# Attributes:
#     EMPTY: Control flow type for an empty block of code.
#     IF_TRUE: Control flow type for an 'if' statement where the condition is true.
#     IF_FALSE: Control flow type for an 'if' statement where the condition is false.
#     FOR_CONDITION: Control flow type for a 'for' loop condition.
#     LOOP_TRUE: Control flow type for a loop where the condition is true.
#     LOOP_FALSE: Control flow type for a loop where the condition is false.
#     BREAK: Control flow type for breaking the flow of execution.
# Note:
#     This class is an enumeration that extends the `SimpleEnum` class.
# """
ControlFlowKind = util.SimpleEnum({
    "EMPTY"                 : 0,
    "IF_TRUE"               : 1,
    "IF_FALSE"              : 2,
    "FOR_CONDITION"         : 3,
    "LOOP_TRUE"             : 4,
    "LOOP_FALSE"            : 5,
    "BREAK"                 : 6,
    "CONTINUE"              : 7,
    "RETURN"                : 8,
    "CATCH_TRUE"            : 9,
    "CATCH_FALSE"           : 10,
    "CATCH_FINALLY"         : 11,
    "PARAMETER_UNINIT"  	: 12,
    "PARAMETER_INIT" 		: 13
})

# """
# Class representing the different types of state flows.
# This class is a subclass of util.SimpleEnum. It defines various state flow types that can be used in a program.
# Attributes:
#     REGULAR: Represents a regular state flow.
#     DATA_FLOW: Represents a data flow state flow.
#     CONTROL_FLOW: Represents a control flow state flow.
#     VAR_DECL: Represents a variable declaration state flow.
#     NEW_INSTANCE: Represents a new instance state flow.
#     ADDR_OF: Represents an address of state flow.
#     MEM_LOAD: Represents a memory load state flow.
#     MEM_STORE: Represents a memory store state flow.
#     FIELD_LOAD: Represents a field load state flow.
#     FILED_STORE: Represents a field store state flow.
#     ARRAY_LOAD: Represents an array load state flow.
#     ARRAY_STORE: Represents an array store state flow.
# """
ComputeOperation = util.SimpleEnum({
    'REGULAR'                 : 0,
    'CONTROL_FLOW'            : 1,
    'DATA_FLOW'               : 2,
    'VARIABLE_DECL'           : 3,
    'PARAMETER_DECL'          : 4,
    'ADDR_OF'                 : 6,
    'MEM_READ'                : 8,
    'MEM_WRITE'               : 9,
    'FIELD_READ'              : 10,
    'FIELD_WRITE'             : 11,
    'ARRAY_READ'              : 12,
    'ARRAY_WRITE'             : 13,
    'CALL'                    : 14,
    'RETURN'                  : 15,
    'NEW_ARRAY'               : 16,
    'NEW_MAP'                 : 17,
    'REQUIRED_MODULE'         : 18,
    'SLICE'                   : 19,
    'GLOBAL'                  : 20,
    'NONLOCAL'                : 21,
    'REQUIRED_MODULE'         : 22,
    'METHOD_DECL'             : 23,
})

# """A class that represents the possible value types for a state.
# Attributes:
#     REGULAR: Represents a regular value type.
#     UNINIT: Represents an uninitialized value type.
#     ANY: Represents anything.
# """
StateKind = util.SimpleEnum({
    "EMPTY"                 : 0,
    "REGULAR"               : 1,
    "UNSOLVED"              : 2,
    "ANYTHING"              : 3,
})


BuiltinOrCustomDataType = util.SimpleEnum({
    "BUILTIN"               : 0,
    "CUSTOM"                : 1,
})

ScopeKind = util.SimpleEnum({
    "BLOCK_SCOPE"           : 0,
    "METHOD_SCOPE"          : 1,
    "CLASS_SCOPE"           : 2,
    "UNIT_SCOPE"            : 3,
    "BUILTIN_SCOPE"         : 4,
})

BuiltinDataTypeName = util.SimpleEnum({
    "TUPLE"             : "tuple",
    "ARRAY"             : "array",
    "MAP"               : "map",
    "JSON"              : "json",
    "STRING"            : "string",

    "NULL"              : "null",
    "NONE"              : "none",
    "BOOL"              : "bool",
    "BYTE"              : "byte",
    "SHORT"             : "short",
    "INT"               : "int",
    "UINT"              : "uint",
    "LONG"              : "long",
    "FLOAT"             : "float",
    "DOUBLE"            : "double",
    "USIZE"             : "usize",
    "ISIZE"             : "isize",

    "INT8"              : "int8",
    "INT16"             : "int16",
    "INT32"             : "int32",
    "INT64"             : "int64",
    "INT128"            : "int128",
    "UINT8"             : "uint8",
    "UINT16"            : "uint16",
    "UINT32"            : "uint32",
    "UINT64"            : "uint64",
    "UINT128"           : "uint128",

    "I8"                : "i8",
    "I16"               : "i16",
    "I32"               : "i32",
    "I64"               : "i64",
    "I128"              : "i128",
    "UI8"               : "ui8",
    "U16"               : "u16",
    "U32"               : "u32",
    "U64"               : "u64",
    "U128"              : "u128",

    "UINTPTR"           : "uintptr",
    "FLOAT32"           : "float32",
    "FLOAT64"           : "float64",
    "COMPLEX64"         : "complex64",
    "COMPLEX128"        : "complex128",

    "REQUIRED_MODULE"   : "__required_module",
})

BuiltinSymbolName = util.SimpleEnum({
    "RETURN_SYMBOL"     : "@return",
})

AnalysisPhaseName = util.SimpleEnum({
    "ScopeHierarchy"  	: "scope_hierarchy",
    "TypeHierarchy"  	: "type_hierarchy",
    "ControlFlowGraph"  : "control_flow",
    "SymbolFlowGraph"   : "symbol_flow",
    "StateFlowGraph"    : "state_flow",
    "MethodSummary"     : "method_summary",
    "AbstractCompute"   : "abstract_compute",
    "CallGraph"         : "call_graph",
})


DataTypeCorrelationKind = util.SimpleEnum({
    "alias"               : 0,
    "inherit"             : 1,
})

StateChangeFlag = util.SimpleEnum({
    "CHANGED"               : 1,
    "UNCHANGED"             : 0,
})

SymbolOrState = util.SimpleEnum({
    "SYMBOL"				: 0,
    "STATE"					: 1,
})
