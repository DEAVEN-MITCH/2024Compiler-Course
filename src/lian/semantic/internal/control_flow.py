#!/usr/bin/env python3

import networkx as nx

from lian.config import config,schema
from lian.util import util
from lian.util import dataframe_operation as do
from lian.config.constants import (
    ControlFlowKind,
    AnalysisPhaseName
)
from lian.semantic.internal.internal_structure import (
    ControlFlowGraph,
    CFGNode,
    InternalAnalysisTemplate
)

class ControlFlowAnalysis(InternalAnalysisTemplate):
    def init(self):
        self.name = AnalysisPhaseName.ControlFlowGraph
        self.description = "control flow graph analysis"

        self.stmt_handlers = {
            "if_stmt"       : self.analyze_if_stmt,
            "while_stmt"    : self.analyze_while_stmt,
            "dowhile_stmt"  : self.analyze_dowhile_stmt,
            "for_stmt"      : self.analyze_for_stmt,
            "forin_stmt"    : self.analyze_while_stmt,
            "break_stmt"    : self.analyze_break_stmt,
            "continue_stmt" : self.analyze_continue_stmt,
            "try_stmt"      : self.analyze_try_stmt,
            "return_stmt"   : self.analyze_return_stmt,
            "yield"         : self.analyze_yield_stmt,
            "method_decl"   : self.analyze_method_decl_stmt,
            "class_decl"    : self.analyze_decl_stmt,
            "record_decl"   : self.analyze_decl_stmt,
            "interface_decl": self.analyze_decl_stmt,
            "struct_decl"   : self.analyze_decl_stmt,
        }


    def unit_analysis_start(self):
        pass

    def unit_analysis_end(self):
        pass

    def bundle_start(self):
        self.all_cfg_edges = []
        self.cfg = None

    def bundle_end(self):
        semantic_path = self.bundle_path.replace(f"/{config.GLANG_DIR}/", f"/{config.SEMANTIC_DIR}/")
        cfg_final_path = semantic_path + config.CONTROL_FLOW_GRAPH_EXT
        data_model = do.DataFrameAgent(self.all_cfg_edges, columns = schema.control_flow_graph_schema)
        data_model.save(cfg_final_path)
        self.module_symbols.update_cfg_path_by_glang_path(self.bundle_path, cfg_final_path)
        if self.options.debug and self.cfg is not None:
            cfg_png_path = semantic_path + "_cfg.png"
            self.cfg.save_png(cfg_png_path)

    def replace_multiple_edges_with_single(self):
        flag = True
        old_graph = self.cfg.graph
        for u, v in old_graph.edges():
            if old_graph.number_of_edges(u, v) > 1:
                flag = False
                break

        if flag:
            return

        new_graph = nx.DiGraph()
        for u, v in old_graph.edges():
            if old_graph.number_of_edges(u, v) > 1:
                # total_weight = sum(old_graph[u][v][key]['weight'] for key in old_graph[u][v])
                new_graph.add_edge(u, v, weight = ControlFlowKind.EMPTY)
            else:
                if not new_graph.has_edge(u, v):
                    new_graph.add_edge(u, v, weight = old_graph[u][v][0]['weight'])
        self.cfg.graph = new_graph

    def save_current_cfg(self):
        edges = []
        edges_with_weights = self.cfg.graph.edges(data='weight', default = 0)
        for e in edges_with_weights:
            edges.append((
                self.cfg.unit_id,
                self.cfg.method_id,
                e[0],
                e[1],
                0 if util.is_empty(e[2]) else e[2]
            ))
        self.all_cfg_edges.extend(edges)
            
    def read_block(self, parent, block_id):
        return parent.read_block(block_id, reset_index = True)
        # return self.method_body.read_block(block_id, reset_index = True)

    def boundary_of_multi_blocks(self, block, block_ids):
        return block.boundary_of_multi_blocks(block_ids)

    def method_analysis(self, previous_results):
        self.cfg = ControlFlowGraph(self.unit_info, self.method_stmt)

        last_stmts_init = self.analyze_init_block(self.method_init)
        last_stmts = self.analyze_block(self.method_body, last_stmts_init)
        if last_stmts:
            self.cfg.add_edge(last_stmts, -1)
        self.replace_multiple_edges_with_single()
        self.save_current_cfg()
        return self.cfg.graph

    def analyze_while_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_dowhile_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_for_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_try_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_method_decl_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_decl_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_return_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_break_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_continue_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_yield_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_if_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        last_stmts_of_then_body = [CFGNode(current_stmt, ControlFlowKind.IF_TRUE)]
        then_body_id = current_stmt.then_body
        if not util.isna(then_body_id):
            then_body = self.read_block(current_block, then_body_id)
            if len(then_body) != 0:
                last_stmts_of_then_body = self.analyze_block(then_body, last_stmts_of_then_body, global_special_stmts)
            
        last_stmts_of_else_body = [CFGNode(current_stmt, ControlFlowKind.IF_FALSE)]
        else_body_id = current_stmt.else_body
        if not util.isna(else_body_id):
            else_body = self.read_block(current_block, else_body_id)
            if len(else_body) != 0:
                last_stmts_of_else_body = self.analyze_block(else_body, last_stmts_of_else_body, global_special_stmts)

        boundary = self.boundary_of_multi_blocks(current_block, [then_body_id, else_body_id])
        return (last_stmts_of_then_body + last_stmts_of_else_body, boundary)

    def link_parent_stmts_to_current_stmt(self, parent_stmts: list, current_stmt):
        for node in parent_stmts:
            if isinstance(node, CFGNode):
                # Assumes node.stmt and node.edge are valid attributes for CFGNode
                self.cfg.add_edge(node.stmt, current_stmt, node.edge)
            else:
                # Links non-CFGNode items
                self.cfg.add_edge(node, current_stmt)

    def analyze_init_block(self, current_block, parent_stmts = [], special_stmts = []):
        counter = 0
        previous = parent_stmts
        last_parameter_decl_stmts = []
        last_parameter_init_stmts = []
        first_init_stmt = True

        if util.is_empty(current_block):
            return previous

        while counter < len(current_block):
            current = current_block.access(counter)
            if current.operation == "parameter_decl":
                self.link_parent_stmts_to_current_stmt(parent_stmts, current)
                last_parameter_init_stmts.extend(previous)
                last_parameter_decl_stmts.append(CFGNode(current, ControlFlowKind.PARAMETER_INPUT_TRUE))
                previous = [current]
                counter += 1
                first_init_stmt = True
            else:
                handler = self.stmt_handlers.get(current.operation)
                if first_init_stmt:
                    previous = [CFGNode(previous, ControlFlowKind.PARAMETER_INPUT_FALSE)]
                    first_init_stmt = False
                if handler is None:
                    self.link_parent_stmts_to_current_stmt(previous, current)
                    previous = [current]
                    counter += 1
                else:
                    previous, boundary = handler(current_block, current, previous, special_stmts)
                    if boundary < 0:
                        break
                    counter = boundary + 1
                if counter >= len(current_block):
                    last_parameter_init_stmts.extend(previous)

        return last_parameter_decl_stmts + last_parameter_init_stmts

    def analyze_block(self, current_block, parent_stmts = [], special_stmts = []):
        """
        This function is going to deal with current block and extract its control flow graph.
        It returns the last statements inside this block.
        """
        counter = 0
        boundary = 0
        previous = parent_stmts

        if util.is_empty(current_block):
            return previous

        while counter < len(current_block):
            current = current_block.access(counter)
            handler = self.stmt_handlers.get(current.operation)
            if handler is None:
                self.link_parent_stmts_to_current_stmt(previous, current)
                previous = [current]
                counter += 1
            else:
                previous, boundary = handler(current_block, current, previous, special_stmts)
                if boundary < 0:
                    break
                counter = boundary + 1

        return previous
