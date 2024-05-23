#!/usr/bin/env python3

import dataclasses
import os
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
from itertools import count
from collections import defaultdict
from typing import List, Set, Tuple

from lian.util import util
from lian.config.constants import (
    BuiltinOrCustomDataType,
    ScopeKind,
    StateKind,
    SymbolOrState
)
from lian.config.constants import ComputeOperation
from lian.util.dataframe_operation import Row
from lian.config import config

class InternalAnalysisTemplate:
    def __init__(self):
        self.name = "command"
        self.description = ""

        self.glang_path = None
        self.scope_hierarchy = None
        self.unit_info = None
        self.unit_glang = None
        self.unit_id = -1
        self.lang = None

        self.method_stmt = None
        self.method_id = -1
        self.parameter_decls = None
        self.method_init = None
        self.method_body = None
        

    def init(self):
        # self.name = "command"
        # self.description = ""
        pass

    def internal_analysis_start(self):
        pass

    def internal_analysis_end(self):
        pass

    def bundle_start(self):
        pass

    def bundle_end(self):
        pass

    def unit_analysis_start(self):
        pass

    def unit_analysis_end(self):
        pass

    def method_analysis(self, previous_results):
        pass

class BasicElement:
    def get_id(self):
        pass

    def change_id(self):
        pass

class ToDict:
    def to_dict(self):
        """
        Converts the dataclass to a dict
        """
        result = {}
        for field in dataclasses.fields(self):
            result[field.name] = getattr(self, field.name)
        return result

class BasicSpace:
    def __init__(self, space=None):
        # [rn] 不能在参数列表中指定默认值为[]。如果默认值是个列表这样的可变对象，在每次调用这个方法时并不会创建一个新的对象，而是指向同一个对象。
        if space is None:
            space = []
        # [rn]以防万一，加上copy
        self.space = space.copy()
        self.id_to_index = {}
        
        global global_state_symbol_id
        global_state_symbol_id = count(1)
        
    def change_id(self, index, new_id):
        element = self.space[index]
        old_id = element.get_id()
        element.change_id(new_id)
        self.id_to_index[old_id].remove(index)
        if new_id not in self.id_to_index:
            self.id_to_index[new_id] = []
        self.id_to_index[new_id].append(index)

    def find_by_id(self, _id):
        if _id in self.id_to_index:
            index = self.id_to_index[_id]
            return self.space[index]
        return None

    def __getitem__(self, index):
        if index >= 0 and index < len(self.space):
            return self.space[index]
        return None

    def add(self, item):
        index = -1
        if util.is_empty(item):
            return index

        self.space.append(item)
        index = len(self.space) - 1

        _id = item.get_id()
        if _id not in self.id_to_index:
            self.id_to_index[_id] = []
        self.id_to_index[_id].append(index)

        return index

    def save_results(self):
        pass

    def __iter__(self):
        for index, row in enumerate(self.space):
            yield index, row

class BasicStmtSpace(BasicSpace):
    def __init__(self, space=[]):
        self.space = space
        self.stmt_to_index = {}

    def find_by_stmt(self, _id):
        if _id in self.stmt_to_index:
            index = self.stmt_to_index[_id]
            return self.space[index]
        return None

    def __getitem__(self, index):
        if index >= 0 and index < len(self.space):
            return self.space[index]
        return None

    def add(self, item):
        index = -1
        if util.is_empty(item):
            return index

        self.space.append(item)
        index = len(self.space) - 1

        _id = item.get_id()
        if _id not in self.stmt_to_index:
            self.stmt_to_index[_id] = []
        self.stmt_to_index[_id].append(index)

        return index

    def save_results(self):
        pass

    def __iter__(self):
        for index, row in enumerate(self.space):
            yield index, row

class BasicGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def visible(self):
        # dot_graph = nx.drawing.nx_pydot.to_pydot(G)
        # dot_file_path = "graph.dot"
        # dot_graph.write_dot(dot_file_path)
        self.draw_graph()
        plt.show()

    def draw_graph(self):
        plt.clf()
        pos = nx.circular_layout(self.graph)
        nx.draw(
            self.graph, pos, with_labels=True, node_color='skyblue', node_size=700,
            edge_color='k', linewidths=1, font_size=15, arrows=True
        )
        edge_labels = dict([((u, v,), d['weight']) for u, v, d in self.graph.edges(data=True)])
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels)

    def save_png(self, path):
        self.draw_graph()
        plt.savefig(path)

    def _add_one_edge(self, src_stmt_id, dst_stmt_id, weight):
        if src_stmt_id == dst_stmt_id:
            return
        if src_stmt_id < 0:
            return
        if config.DEBUG_FLAG:
            util.debug(f"_add_one_edge:{src_stmt_id}->{dst_stmt_id}, weight={weight}")
        self.graph.add_edge(src_stmt_id, dst_stmt_id, weight = weight)

    def add_edge(self, src_stmt, dst_stmt, weight = None):
        src_stmt_id = -1
        dst_stmt_id = -1
        if util.is_empty(src_stmt) or util.is_empty(dst_stmt) :
            return

        if isinstance(src_stmt, int):
            src_stmt_id = src_stmt
        elif isinstance(src_stmt, list):
            for src in src_stmt:
                self.add_edge(src, dst_stmt, weight)
            return
        else:
            src_stmt_id = src_stmt.stmt_id

        if isinstance(dst_stmt, int):
            dst_stmt_id = dst_stmt
        else:
            dst_stmt_id = dst_stmt.stmt_id

        self._add_one_edge(src_stmt_id, dst_stmt_id, weight)

    def backward_search(self, node, node_constraint):
        """
        query_constraint_over_node: given an node, check if the node meet the requirements or not.

        [return]
        true/false: the current node will be kept
        the list or set of the nodes, which meet the requirements: the list or set will be saved
        """
        satisfying_nodes = set()
        visited = set()

        if node not in self.graph:
            return satisfying_nodes

        stack = [node]

        while stack:
            current_node = stack.pop()
            if current_node in visited:
                continue
            visited.add(current_node)

            tmp_result = node_constraint(current_node)
            if tmp_result:
                if isinstance(tmp_result, bool):
                    satisfying_nodes.add(current_node)
                else:
                    satisfying_nodes = satisfying_nodes.union(tmp_result)

                # stop this path
                continue

            for parent in self.graph.predecessors(current_node):
                if parent not in visited:
                    stack.append(parent)

        return satisfying_nodes


@dataclasses.dataclass
class Scope:
    unit_id: int = -1
    stmt_id: int = -1
    parent_stmt_id: int = -1
    scope_kind: ScopeKind = ScopeKind.METHOD_SCOPE
    package_stmts: List[int] = dataclasses.field(default_factory=list)
    import_stmts: List[int] = dataclasses.field(default_factory=list)
    variable_decls: List[int] = dataclasses.field(default_factory=list)
    method_decls: List[Tuple[int, str]] = dataclasses.field(default_factory=list)
    class_decls: List[int] = dataclasses.field(default_factory=list)

    def to_dict(self):
        result = []
        if (
                len(self.package_stmts) == 0 and
                len(self.import_stmts) == 0 and
                len(self.variable_decls) == 0 and
                len(self.method_decls) == 0 and
                len(self.class_decls) == 0
        ):
            result.append(
                {
                    "unit_id": self.unit_id,
                    "stmt_id": self.stmt_id,
                    "parent_stmt_id": self.parent_stmt_id,
                    "scope_kind": self.scope_kind,
                 }
            )
            return result

        for stmt in self.package_stmts:
            result.append(
                {
                    "unit_id": self.unit_id,
                    "stmt_id": self.stmt_id,
                    "parent_stmt_id": self.parent_stmt_id,
                    "scope_kind": self.scope_kind,
                    "package_stmt": stmt
                }
            )

        for stmt in self.import_stmts:
            result.append(
                {
                    "unit_id": self.unit_id,
                    "stmt_id": self.stmt_id,
                    "parent_stmt_id": self.parent_stmt_id,
                    "scope_kind": self.scope_kind,
                    "import_stmt": stmt
                }
            )

        for stmt in self.variable_decls:
            result.append(
                {
                    "unit_id": self.unit_id,
                    "stmt_id": self.stmt_id,
                    "parent_stmt_id": self.parent_stmt_id,
                    "scope_kind": self.scope_kind,
                    "variable_decl": stmt
                }
            )

        for stmt in self.method_decls:
            result.append(
                {
                    "unit_id": self.unit_id,
                    "stmt_id": self.stmt_id,
                    "parent_stmt_id": self.parent_stmt_id,
                    "scope_kind": self.scope_kind,
                    "method_decl": str(stmt)
                }
            )

        for stmt  in self.class_decls:
            result.append(
                {
                    "unit_id": self.unit_id,
                    "stmt_id": self.stmt_id,
                    "parent_stmt_id": self.parent_stmt_id,
                    "scope_kind": self.scope_kind,
                    "class_decl": stmt
                }
            )

        return result

    def __repr__(self):
        result = self.to_dict()
        l = []
        l.append(f"Scope [")
        for row in result:
            l.append(" " + str(row))
        l.append("]")
        return "\n".join(l)

@dataclasses.dataclass
class ScopeGraph(BasicGraph):
    pass

global_type_id = count(1)

@dataclasses.dataclass
class DataType(BasicElement, ToDict):
    name: str = ""
    size: int = 8
    full_name: str = ""
    stmt_id: int = -1
    unit_id: int = -1
    builtin_or_custom: BuiltinOrCustomDataType = BuiltinOrCustomDataType.BUILTIN
    type_id: int = dataclasses.field(default_factory=lambda: next(global_type_id))

    def get_id(self):
        return self.type_id

class DataTypeSpace(BasicSpace):
    def __init__(self):
        super().__init__()
        self.stmt_to_index = {}

    def add(self, item):
        _index = super().add(item)
        self.stmt_to_index[item.stmt_id] = _index

    def find_by_stmt(self, stmt):
        return self.stmt_to_index.get(stmt, None)

class DataTypeGraph(BasicGraph):
    # node: stmt
    # edge: alias or inherit
    pass


class CFGNode:
    def __init__(self, stmt, edge = None):
        self.stmt = stmt
        self.edge = edge

class ControlFlowGraph(BasicGraph):
    def __init__(self, unit_info, method_stmt):
        self.unit_info = unit_info
        self.method_stmt = method_stmt
        self.unit_id = unit_info.symbol_id
        self.method_id = method_stmt.stmt_id

        self.graph = nx.MultiDiGraph()

    def add_edge(self, src_stmt, dst_stmt, control_flow_type = None):
        if isinstance(src_stmt, CFGNode):
            self.add_edge(src_stmt.stmt, dst_stmt, src_stmt.edge)
        else:
            super().add_edge(src_stmt, dst_stmt, control_flow_type)


@dataclasses.dataclass
class State(BasicElement):
    """
    state_id: id
    data_type: the state's data type
    value: state content
    stmt_id: stmt_id, indicating where the state is defined
    """
    stmt_id: int = -1
    data_type: DataType = ""
    state_type: StateKind = StateKind.REGULAR
    state_id: int = dataclasses.field(default_factory=lambda: next(global_state_symbol_id))
    value: any = "" 
    # fields is a dict containing all the field_name and corresponding state_ids
    # example - {field_name1:[state1,state2],field_name2:[state3]}
    fields: dict = dataclasses.field(default_factory=lambda: {}) 
    array: List[set] = dataclasses.field(default_factory=list)
    array_tangping_flag: bool = False

    def to_dict(self, unit_id, method_id, counter):
        return {
            "unit_id": unit_id,
            "method_id": method_id,
            "index": counter,
            "symbol_or_state": SymbolOrState.STATE,
            "stmt_id": self.stmt_id,
            "symbol_id": None,
            "name": None,
            "default_data_type": None,
            "states": None,
            "state_type": self.state_type,
            "state_id": self.state_id,
            "data_type": self.data_type,
            "value": str(self.value),
            "fields": str(self.fields),
            "array": str(self.array),
            "array_tangping_flag": self.array_tangping_flag
        }

    def get_id(self):
        return self.state_id

    def get_data_type(self):
        return self.data_type

    def __eq__(self, other):
        if not isinstance(other, State):
            return False
        return (
            self.data_type == other.data_type and
            self.value == other.value and
            self.fields == other.fields and
            self.array == other.array
        )
    
    def clone(self, stmt_id = -1):
        return State(
            stmt_id = stmt_id,
            data_type = self.data_type,
            value = self.value,
            state_type = self.state_type,
            state_id = self.state_id,
            fields = self.fields.copy(),
            array = self.array.copy(),
            array_tangping_flag = self.array_tangping_flag,
        )

@dataclasses.dataclass
class Symbol(BasicElement):
    """
    symbol_id: id
    name: symbol name
    state: list of state
        # a = 3; a.value -> 3
        # a = b; a.value -> b.value
        # a = &b; a.value -> addr_of(b) = b.state.state_id
        # if () {} [merge] value -> [state1, state2, 3, b.value, b.state.state_id]
    stmt_id: it is a stmt_id, indicating which scope the symbol is located at
    alias: another alias name (or symbol_id?) of this symbol
    """
    stmt_id: int = -1
    symbol_id: int = dataclasses.field(default_factory=lambda: next(global_state_symbol_id))
    name: str = ""
    default_data_type: str = ""
    states: Set[int] = dataclasses.field(default_factory=set)

    def to_dict(self, unit_id, method_id, counter):
        return {
            "unit_id": unit_id,
            "method_id": method_id,
            "index": counter,
            "symbol_or_state": SymbolOrState.SYMBOL,
            "stmt_id": self.stmt_id,
            "symbol_id": str(self.symbol_id),
            "name": self.name,
            "default_data_type": self.default_data_type,
            "states": str(self.states),
            "state_type": 0,
            "state_id": -1,
            "data_type": None,
            "value": None,
            "fields": None,
            "array": None,
            "array_tangping_flag": None
        }
    
    def get_id(self):
        return self.symbol_id

    def set_id(self, symbol_id):
        self.symbol_id = symbol_id

    def __eq__(self, other):
        if not isinstance(other, Symbol):
            return False
        return (
            self.name == other.name and
            self.states == other.states
        )

class SymbolStateSpace(BasicSpace):
    def to_dict(self, unit_id, method_id):
        results = []
        for counter in range(len(self.space)):
            element = self.space[counter]
            results.append(element.to_dict(unit_id, method_id, counter))

        return results

@dataclasses.dataclass
class StmtStatus:
    stmt_id: int = -1
    defined_symbol: int = -1
    used_symbols: List[int] = dataclasses.field(default_factory=list)
    field: str = ""
    operation:ComputeOperation = ComputeOperation.REGULAR

    in_bits : int = 0
    out_bits: int = 0

    def to_dict(self, unit_id, method_id):
        return {
            "unit_id": unit_id,
            "method_id":method_id,
            "stmt_id": self.stmt_id,
            "defined_symbol": self.defined_symbol,
            "used_symbols": str(self.used_symbols),
            "field": self.field,
            "operation": self.operation,
            "in_bits": repr(self.in_bits),
            "out_bits": repr(self.out_bits)
        }

class StateFlowGraph(BasicGraph):
    def __init__(self, unit_info, method_stmt):
        self.unit_info = unit_info
        self.method_stmt = method_stmt
        self.unit_id = unit_info.symbol_id
        self.method_id = method_stmt.stmt_id
        super().__init__()

    def _add_one_edge(self, src_stmt_id, dst_stmt_id, weight):
        # [rn] 如果不允许添加自己流向自己的边，会导致sdg中，a+=1这样的语句找不到自己的def
        # if src_stmt_id == dst_stmt_id:
        #     return
        if src_stmt_id < 0:
            return
        util.debug(f"_add_one_edge:{src_stmt_id}->{dst_stmt_id}, weight={weight}")
        self.graph.add_edge(src_stmt_id, dst_stmt_id, weight = str(weight))

class SymbolDependencyGraph(StateFlowGraph):
    pass

class MethodCall:
    def __init__(self, unit_id, stmt_id, name, method_state = None):
        self.unit_id = unit_id
        self.stmt_id = stmt_id
        self.name = name
        self.method_state = method_state

@dataclasses.dataclass
class BitVectorManager:
    counter: int = 0
    stmt_to_bit_pos: dict = dataclasses.field(default_factory=dict)
    bit_pos_to_stmt: dict = dataclasses.field(default_factory=dict)

    def init(self, stmt_list):
        for stmt_id in stmt_list:
            self.add_stmt(stmt_id)

    def to_dict(self, unit_id, method_id):
        results = []
        for bit_pos, stmt in self.bit_pos_to_stmt.items():
            results.append({
                "unit_id": unit_id,
                "method_id": method_id,
                "bit_pos": bit_pos,
                "stmt": stmt,
            })
        return results

    def add_stmt(self, stmt_id):
        self.stmt_to_bit_pos[stmt_id] = self.counter
        self.bit_pos_to_stmt[self.counter] = stmt_id
        self.counter += 1

    def find_bit_pos_by_stmt(self, stmt_id):
        return self.stmt_to_bit_pos.get(stmt_id, -1)

    # find all 1s -> stmt_id
    def explain(self, bit_vector):
        result = set()
        # still remain 1
        while bit_vector:
            # Brian Kernighan algorithm to find all 1
            next_bit_vector = bit_vector & (bit_vector - 1)
            rightmost_1_vector = bit_vector ^ next_bit_vector
            bit_pos = rightmost_1_vector.bit_length() - 1
            def_stmt_id = self.bit_pos_to_stmt[bit_pos]
            result.add(def_stmt_id)
            bit_vector = next_bit_vector
        return result

    def kill_stmts(self, bit_vector, stmts):
        killed_stmts = []
        for stmt_id in stmts:
            bit_pos = self.stmt_to_bit_pos.get(stmt_id)
            if bit_pos is not None:
                target_mask = (1 << bit_pos)
                if bit_vector & target_mask != 0:
                    killed_stmts.append(self.bit_pos_to_stmt.get(bit_pos, -1))
                    bit_vector &= ~target_mask

        return (bit_vector, killed_stmts)

    def gen_stmts(self, bit_vector, stmts):
        for stmt_id in stmts:
            bit_pos = self.stmt_to_bit_pos.get(stmt_id)
            if bit_pos is not None:
                bit_vector |= (1 << bit_pos)
        return bit_vector

    def is_stmt_alive(self, bit_vector, stmt_id):
        bit_pos = self.stmt_to_bit_pos.get(stmt_id)
        if bit_pos is not None:
            if (bit_vector & (1 << bit_pos)) != 0:
                return True
        return False

@dataclasses.dataclass
class MethodSummary:
    unit_id: int = -1
    method_id: int = -1
    parameter_symbols: List[int] = dataclasses.field(default_factory=list)
    defined_external_symbols: List[int] = dataclasses.field(default_factory=list)
    used_external_symbols: List[int] = dataclasses.field(default_factory=list)
    return_symbol: List[int] = dataclasses.field(default_factory=list)
    call_summary: List[int] = dataclasses.field(default_factory=list)
    symbol_state_space: SymbolStateSpace = dataclasses.field(default_factory=SymbolStateSpace)
    stmt_to_status: dict = dataclasses.field(default_factory=dict)

    def to_dict(self):
        return {
            "unit_id": self.unit_id,
            "method_id": self.method_id,
            "parameter_symbols": str(self.parameter_symbols),
            "defined_external_symbols": str(self.defined_external_symbols),
            "used_external_symbols": str(self.used_external_symbols),
            "return_symbol": str(self.return_symbol),
            "call_summary": str(self.call_summary),
        }
    
    def __str__(self):
        return f"unit_id={self.unit_id}, method_id={self.method_id}, parameter_symbols={self.parameter_symbols}, defined_external_symbols={self.defined_external_symbols}, used_external_symbols={self.used_external_symbols}, return_symbol={self.return_symbol}, call_summary={self.call_summary}"
    

class CallGraph(BasicGraph):
    pass

    def find_paths(self, src_node, dst_node):
        pass
