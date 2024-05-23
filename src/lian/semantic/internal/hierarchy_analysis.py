#!/usr/bin/env python3


import ast
import dataclasses
import os, sys, pprint
import pandas as pd
from collections import Counter
from itertools import count

from lian.config import schema,config
from lian.config.constants import (
    BuiltinOrCustomDataType,
    EXTENSIONS_LANG,
    BuiltinDataTypeName,
    ScopeKind
)
from lian.semantic.internal.internal_structure import (
    Scope,
    DataType,
    BasicSpace
)
from lian.util import util
from lian.util import dataframe_operation as do

SCOPE_STMT_TO_SCOPE_KIND = {
    "class_decl": ScopeKind.CLASS_SCOPE,
    "record_decl": ScopeKind.CLASS_SCOPE,
    "interface_decl": ScopeKind.CLASS_SCOPE,
    "enum_decl": ScopeKind.CLASS_SCOPE,
    "struct_decl": ScopeKind.CLASS_SCOPE,
    "method_decl": ScopeKind.METHOD_SCOPE,
    "body_start": ScopeKind.BLOCK_SCOPE,
}

CLASS_DECL_OPERATION = {
    "class_decl",
    "record_decl",
    "interface_decl",
    "enum_decl",
    "struct_decl",
}

IMPORT_OPERATION = {
    "import_stmt",
    "import_as_stmt",
    "include_stmt",
    "require_stmt"
}

METHOD_DECL_OPERATION = {
    "method_decl"
}

VARIABLE_DECL_OPERATION = {
    "variable_decl"
}

BLOCK_OPERATION = {
    "for_stmt",
    "forin_stmt",
}

class ScopeHierarchy:
    def __init__(self, module_symbols):
        self.module_symbols = module_symbols
        self.scope_space = []
        self.reset()

    def save_results(self):
        semantic_path = self.unit_info.glang_path.replace(f"/{config.GLANG_DIR}/", f"/{config.SEMANTIC_DIR}/")
        scope_space_path = semantic_path + ".scope_space"
        do.DataFrameAgent(self.scope_space, columns = schema.scope_space_schema).save(scope_space_path)
        self.module_symbols.update_scope_space_path_by_glang_path(self.unit_info.glang_path, scope_space_path)

    def reset(self):
        self.unit_info = None
        self.unit_id = None
        self.unit_glang = None
        self.stmt_id_to_glang_index = {}
        self.unit_level_id_to_scope = {}
        self.stmt_id_to_scope_id_cache = {}

    def analyze_unit(self, unit_info, unit_glang):
        self.reset()
        self.unit_info = unit_info
        self.unit_id = unit_info.symbol_id
        self.unit_glang = unit_glang

        self.discover()
        self.add_results()

    def get_all_methods_of_current_unit(self):
        method_stmts = []
        for scope in self.unit_level_id_to_scope.values():
            if len(scope.method_decls) == 0:
                continue
            for method_stmt in scope.method_decls:
                method_stmts.append(self.access_by_stmt_id(method_stmt[0])) 
        return method_stmts 

    def access_by_stmt_id(self, stmt_id):
        index = self.stmt_id_to_glang_index.get(stmt_id, -1)
        return self.unit_glang.access(index)

    def determine_scope(self, stmt_id):
        if stmt_id == 0:
            return 0

        if stmt_id in self.stmt_id_to_scope_id_cache:
            return self.stmt_id_to_scope_id_cache[stmt_id]

        stmt = self.access_by_stmt_id(stmt_id)
        if stmt is None:
            return 0

        result = stmt.stmt_id
        if stmt.stmt_id not in self.unit_level_id_to_scope:
            result = self.determine_scope(stmt.parent_stmt_id)

        self.stmt_id_to_scope_id_cache[stmt_id] = result

        return result

    def discover(self):
        counter = 0
        self.unit_level_id_to_scope[0] = Scope(self.unit_id, 0, 0, ScopeKind.UNIT_SCOPE)
        for row in self.unit_glang:
            self.stmt_id_to_glang_index[row.stmt_id] = counter
            counter += 1

            if row.operation == "package_stmt":
                parent_scope_id = self.determine_scope(row.parent_stmt_id)
                parent_scope = self.unit_level_id_to_scope[parent_scope_id]
                parent_scope.package_stmts.append(row.stmt_id)
            elif row.operation in IMPORT_OPERATION:
                parent_scope_id = self.determine_scope(row.parent_stmt_id)
                parent_scope = self.unit_level_id_to_scope[parent_scope_id]
                parent_scope.import_stmts.append(row.stmt_id)
            elif row.operation in VARIABLE_DECL_OPERATION:
                parent_scope_id = self.determine_scope(row.parent_stmt_id)
                parent_scope = self.unit_level_id_to_scope[parent_scope_id]
                parent_scope.variable_decls.append(row.stmt_id)
            elif row.operation in METHOD_DECL_OPERATION:
                parent_scope_id = self.determine_scope(row.parent_stmt_id)
                parent_scope = self.unit_level_id_to_scope[parent_scope_id]
                parent_scope.method_decls.append((row.stmt_id, row.name))

                self.unit_level_id_to_scope[row.stmt_id] = Scope(
                    self.unit_id, row.stmt_id, parent_scope_id, ScopeKind.METHOD_SCOPE
                )
            elif row.operation in CLASS_DECL_OPERATION:
                parent_scope_id = self.determine_scope(row.parent_stmt_id)
                parent_scope = self.unit_level_id_to_scope[parent_scope_id]
                parent_scope.class_decls.append(row.stmt_id)

                self.unit_level_id_to_scope[row.stmt_id] = Scope(
                    self.unit_id, row.stmt_id, parent_scope_id, ScopeKind.CLASS_SCOPE
                )
            elif row.operation == "block_start":
                final_scope_id = self.determine_scope(row.parent_stmt_id)
                if final_scope_id not in self.unit_level_id_to_scope:
                    self.unit_level_id_to_scope[final_scope_id] = Scope(
                        self.unit_id, row.parent_stmt_id, final_scope_id, ScopeKind.BLOCK_SCOPE
                    )

    def display_results(self):
        pprint.pprint(self.unit_level_id_to_scope)

    def add_results(self):
        for scope in self.unit_level_id_to_scope.values():
            self.scope_space.extend(scope.to_dict())

    # TODO: fix this method
    def resolve_imported_scope(self, unit_info, imported_content):
        # if unit["unit_ext"].endswith(".py"):
        #     pass

        # if unit["unit_ext"].endswith((".h", ".hpp", ".c", ".cpp", ".cc")):
        #     pass

        return lang_specific_scope_table.resolve_imported_scope(self.scope_table, unit_info, imported_content)

    # TODO: fix this method
    def process_imports(self, unit):
        import_stmts = self.scope_table.loc[
            (self.scope_table["parent_scope_id"] == unit["scope_id"])
            & (self.scope_table["scope_type"] == ScopeKind.IMPORT),
        ]

        for myimport in import_stmts:
            imported_content = myimport.imported_scope
            import_id = self.resolve_imported_scope(unit, imported_content)
            if import_id > 0:
                util.dataframe_modify(self.scope_table, myimport.name, "import_id", import_id)

    # TODO: fix this method
    def resolve_inherited_scope(self, class_info, inherited_class):
        return lang_specific_scope_table.resolve_inherited_scope(self.scope_table, class_info, imported_content)

    # TODO: fix this method
    def process_inherits(self, myclass):
        inherit_stmts = self.scope_table.loc[
            (self.scope_table["parent_scope_id"] == myclass["scope_id"])
            & (self.scope_table["scope_type"] == ScopeKind.PARENT_CLASS),
        ]

        for parent_class in inherit_stmts:
            inherited_class = parent_class.inherit
            parent_class_id = self.resolve_inherited_scope(myclass, inherited_class)
            if parent_class_id > 0:
                util.dataframe_modify(self.scope_table, parent_class.name, "parent_class_id", parent_class_id)

    # TODO: fix this method
    def process_connection(self):
        # 1. scanning inter-unit connections
        unit_stmts = self.scope_table.loc[
            (self.scope_table["scope_type"] == ScopeKind.UNIT)
        ]

        for unit in unit_stmts:
            self.process_imports(unit)

        # 2. scanning inter-class connections
        class_stmts = self.scope_table.loc[
            (self.scope_table["scope_type"] == ScopeKind.CLASS)
        ]

        for myclass in class_stmts:
            self.process_inherits(myclass)


C_BUILTIN_TYPE_TABLE = [
    DataType("void"),
    DataType("bool"),
    DataType("char"),
    DataType("wchar_t"),
    DataType("char16_t"),
    DataType("char32_t"),
    DataType("int"),
    DataType("short"),
    DataType("long"),
    DataType("signed"),
    DataType("unsigned"),
    DataType("float"),
    DataType("double"),
    DataType("long double"),
    DataType("wchar_t"),
    DataType("enum"),
    DataType("struct"),
    DataType("union"),
    DataType("auto"),
    DataType("complex"),
    DataType("imaginary"),
    DataType("int8_t"),
    DataType("int16_t"),
    DataType("int32_t"),
    DataType("int64_t"),
    DataType("uint8_t"),
    DataType("uint16_t"),
    DataType("uint32_t"),
    DataType("uint64_t"),
    DataType("size_t"),
    DataType("ssize_t"),
    DataType("uintptr_t"),
    DataType("nullptr_t")
]

CPP_BUILTIN_TYPE_TABLE = [
    DataType("void"),
    DataType("bool"),
    DataType("char"),
    DataType("wchar_t"),
    DataType("char16_t"),
    DataType("char32_t"),
    DataType("int"),
    DataType("short"),
    DataType("long"),
    DataType("signed"),
    DataType("unsigned"),
    DataType("float"),
    DataType("double"),
    DataType("long double"),
    DataType("wchar_t"),
    DataType("enum"),
    DataType("struct"),
    DataType("union"),
    DataType("auto"),
    DataType("complex"),
    DataType("imaginary"),
    DataType("int8_t"),
    DataType("int16_t"),
    DataType("int32_t"),
    DataType("int64_t"),
    DataType("uint8_t"),
    DataType("uint16_t"),
    DataType("uint32_t"),
    DataType("uint64_t"),
    DataType("size_t"),
    DataType("ssize_t"),
    DataType("uintptr_t"),
    DataType("nullptr_t"),
]

GO_BUILTIN_TYPE_TABLE = [
    DataType("bool"),
    DataType("byte"),
    DataType("int"),
    DataType("int8"),
    DataType("int16"),
    DataType("int32"),
    DataType("int64"),
    DataType("uint"),
    DataType("uint8"),
    DataType("uint16"),
    DataType("uint32"),
    DataType("uint64"),
    DataType("float32"),
    DataType("float64"),
    DataType("complex64"),
    DataType("complex128"),
    DataType("string"),
    DataType("rune"),
    DataType("uintptr"),
    DataType("error"),
    DataType("struct"),
]

RUST_BUILTIN_TYPE_TABLE = [
    DataType("bool"),
    DataType("char"),
    DataType("str"),
    DataType("u8"),
    DataType("u16"),
    DataType("u32"),
    DataType("u64"),
    DataType("u128"),
    DataType("usize"),
    DataType("i8"),
    DataType("i16"),
    DataType("i32"),
    DataType("i64"),
    DataType("i128"),
    DataType("isize"),
    DataType("f32"),
    DataType("f64"),
    DataType("array"),
    DataType("slice"),
    DataType("tuple"),
    DataType("struct"),
    DataType("enum"),
]

LLVM_BUILTIN_TYPE_TABLE = [
    DataType("void"),
    DataType("half"),
    DataType("float"),
    DataType("double"),
    DataType("fp128"),
    DataType("i1"),
    DataType("i2"),
    DataType("i4"),
    DataType("i8"),
    DataType("i16"),
    DataType("i32"),
    DataType("i64"),
    DataType("i128"),
    DataType("label"),
    DataType("metadata"),
    DataType("ptr"),
    DataType("vector"),
    DataType("array"),
    DataType("struct"),
    DataType("opaque"),
]

JAVA_BUILTIN_TYPE_TABLE = [
    DataType("boolean"),
    DataType("char"),
    DataType("byte"),
    DataType("short"),
    DataType("int"),
    DataType("long"),
    DataType("float"),
    DataType("double"),
    DataType("Boolean"),
    DataType("Integer"),
    DataType("Float"),
    DataType("Enum"),
    DataType("Array"),
    DataType("String"),
    DataType("Enum"),
]

PYTHON_BUILTIN_TYPE_TABLE = [
    DataType("bool"),
    DataType("int"),
    DataType("float"),
    DataType("complex"),
    DataType("list"),
    DataType("tuple"),
    DataType("dict"),
    DataType("string"),
    DataType("set"),
    DataType("bytes"),
    DataType("NoneType"),
]

LANG_TO_DAT_TYPE_TABLE = {
    "c": C_BUILTIN_TYPE_TABLE,
    "cpp": CPP_BUILTIN_TYPE_TABLE,
    "go": GO_BUILTIN_TYPE_TABLE,
    "rust": RUST_BUILTIN_TYPE_TABLE,
    "llvm" : LLVM_BUILTIN_TYPE_TABLE,
    "python" : PYTHON_BUILTIN_TYPE_TABLE,
    "java" : JAVA_BUILTIN_TYPE_TABLE,
}


class DataTypeHierarchy(BasicSpace):
    def __init__(self, lang):
        self.lang = ""
        self.lang_to_data_type_space = {}
        self.lang_to_data_type_hierarchy = {}

        self.init_data_type()

    def init_data_type(self):
        for lang in LANG_TO_DAT_TYPE_TABLE:
            type_table = LANG_TO_DAT_TYPE_TABLE[lang]
            for data_type in type_table:
                if lang not in self.lang_to_data_type_space:
                    self.lang_to_data_type_space[lang] = DataTypeSpace()
                self.lang_to_data_type_space[lang].add(data_type)

    def save_results(self):
        pass

    def build_graph(self):
        pass

