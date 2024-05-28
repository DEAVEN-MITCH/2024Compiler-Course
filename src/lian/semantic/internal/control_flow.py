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
class specialBind():
    def __init__(self,stmt,next):
        self.stmt=stmt#label_stmt
        self.next_stmt=next
    def match(self,label):
        return self.stmt.name==label
    def label_for(self,for_stmt):
        return self.next_stmt.stmt_id==for_stmt.stmt_id
    def __str__(self):
        return 'current:'+str(self.stmt.operation)+' next:'+(str(self.next_stmt.operation) if self.next_stmt is not None else '')
    def __repr__(self) -> str:
        return str(self)
class ControlFlowAnalysis(InternalAnalysisTemplate):
    def init(self):
        self.name = AnalysisPhaseName.ControlFlowGraph
        self.description = "control flow graph analysis"

        self.stmt_handlers = {
            "if_stmt"       : self.analyze_if_stmt,
            "for_stmt"      : self.analyze_for_stmt,
            "forin_stmt"    : self.analyze_forin_stmt,
            "break_stmt"    : self.analyze_break_stmt,
            "continue_stmt" : self.analyze_continue_stmt,
            "return_stmt"   : self.analyze_return_stmt,
            "method_decl"   : self.analyze_method_decl_stmt,
            # "goto_stmt":self.analyze_goto_stmt,
            "label_stmt":self.analyze_label_stmt,
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

    def analyze_forin_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        #abstract break/continue in global_special_stmts first to avoid outer break interacts with current loop
        global_special_stmts_without_outer_bc=global_special_stmts.copy()
        labelBind=None
        for stmt in global_special_stmts:
            # print(stmt,"int gs:")
            if isinstance(stmt,specialBind):
                # print(stmt.next_stmt,current_stmt)
                if(stmt.label_for(current_stmt)):
                    labelBind=stmt
                continue
            if stmt.operation=="break_stmt" or stmt.operation=="continue_stmt":
                global_special_stmts_without_outer_bc.remove(stmt)
        # print(str(labelBind),'''**********''')
        previous=[]
        #parent to init
        last_stmts_of_init_body = parent_stmts
        init_body_id = current_stmt.array_read
        if not util.isna(init_body_id):
            init_body = self.read_block(current_block, init_body_id)
            if len(init_body) != 0:
                last_stmts_of_init_body = self.analyze_block(init_body,parent_stmts, global_special_stmts_without_outer_bc)
        
        #init to forin
        self.link_parent_stmts_to_current_stmt_with_type(last_stmts_of_init_body, current_stmt,ControlFlowKind.FOR_CONDITION)
        
        #for to body or outof loop
        last_stmts_of_body = [CFGNode(current_stmt, ControlFlowKind.LOOP_TRUE)]
        previous.append(CFGNode(current_stmt, ControlFlowKind.LOOP_FALSE))
        body_id = current_stmt.body
        first_stmt_of_body=None
        if not util.isna(body_id):
            body = self.read_block(current_block, body_id)
            if len(body) != 0:
                last_stmts_of_body = self.analyze_block(body, last_stmts_of_body, global_special_stmts_without_outer_bc)
                first_stmt_of_body =body.access(0)

        #body to forin
        self.link_parent_stmts_to_current_stmt_with_type(last_stmts_of_body,current_stmt,ControlFlowKind.FOR_CONDITION)

        for stmt in global_special_stmts_without_outer_bc.copy():
            if isinstance(stmt,specialBind):
                continue
            if stmt.operation=="break_stmt":
                label=stmt.target
                if len(label)==0 or (labelBind is not None and labelBind.match(label)):
                    #matched break;
                    previous.append(CFGNode(stmt,ControlFlowKind.BREAK))
                    global_special_stmts_without_outer_bc.remove(stmt)

                continue
            if stmt.operation=="continue_stmt":
                label=stmt.target
                if len(label)==0 or (labelBind is not None and labelBind.match(label)):
                    #matched continue;
                    t=[CFGNode(stmt,ControlFlowKind.CONTINUE)]
                    self.link_parent_stmts_to_current_stmt(t,current_stmt)
                        
                    global_special_stmts_without_outer_bc.remove(stmt)
                continue
        for stmt in global_special_stmts_without_outer_bc:
            if stmt not in global_special_stmts:
                global_special_stmts.append(stmt)
        #return 
        boundary = self.boundary_of_multi_blocks(current_block, [init_body_id,body_id])
        # print(init_body_id, condition_prebody_id, body_id, update_body_id)
        if util.isna(init_body_id) and util.isna(body_id):
            boundary=current_stmt._index
        return (previous,boundary)

    def analyze_while_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_dowhile_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_for_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        
        #abstract break/continue in global_special_stmts first to avoid outer break interacts with current loop
        global_special_stmts_without_outer_bc=global_special_stmts.copy()
        labelBind=None
        for stmt in global_special_stmts:
            # print(stmt,"int gs:")
            if isinstance(stmt,specialBind):
                # print(stmt.next_stmt,current_stmt)
                if(stmt.label_for(current_stmt)):
                    labelBind=stmt
                continue
            if stmt.operation=="break_stmt" or stmt.operation=="continue_stmt":
                global_special_stmts_without_outer_bc.remove(stmt)
        # print(str(labelBind),'''**********''')
        previous=[]

        #parent to init
        last_stmts_of_init_body = parent_stmts
        init_body_id = current_stmt.init_body
        if not util.isna(init_body_id):
            init_body = self.read_block(current_block, init_body_id)
            if len(init_body) != 0:
                last_stmts_of_init_body = self.analyze_block(init_body,parent_stmts, global_special_stmts_without_outer_bc)
        

        #init to condition
        last_stmts_of_condition_prebody=last_stmts_of_init_body
        condition_prebody_id = current_stmt.condition_prebody
        first_stmt_of_condition = None
        if not util.isna(condition_prebody_id):
            condition_prebody = self.read_block(current_block, condition_prebody_id)
            if len(condition_prebody) != 0:
                last_stmts_of_condition_prebody = self.analyze_block(condition_prebody, last_stmts_of_condition_prebody, global_special_stmts_without_outer_bc)
                first_stmt_of_condition = condition_prebody.access(0)

            
        #condition to for

        self.link_parent_stmts_to_current_stmt_with_type(last_stmts_of_condition_prebody, current_stmt,ControlFlowKind.FOR_CONDITION)

        #for to body or outof loop
        last_stmts_of_body = [CFGNode(current_stmt, ControlFlowKind.LOOP_TRUE)]
        previous.append(CFGNode(current_stmt, ControlFlowKind.LOOP_FALSE))
        body_id = current_stmt.body
        first_stmt_of_body=None
        if not util.isna(body_id):
            body = self.read_block(current_block, body_id)
            if len(body) != 0:
                last_stmts_of_body = self.analyze_block(body, last_stmts_of_body, global_special_stmts_without_outer_bc)
                first_stmt_of_body =body.access(0)
        #body to update
        last_stmts_of_update_body = last_stmts_of_body
        update_body_id = current_stmt.update_body
        first_stmt_of_update_body = None
        if not util.isna(update_body_id):
            update_body = self.read_block(current_block, update_body_id)
            if len(update_body) != 0:
                last_stmts_of_update_body = self.analyze_block(update_body, last_stmts_of_update_body, global_special_stmts_without_outer_bc)
                first_stmt_of_update_body = update_body.access(0)

        #update to condition
        logstr=''
        for stmt in last_stmts_of_update_body:
            if isinstance(stmt,CFGNode):
                logstr+=stmt.stmt.operation+str(stmt.stmt.stmt_id)+str(stmt.edge)+' '
            else:
                logstr+=stmt.operation+str(stmt.stmt_id)+' '
        # print(logstr)
        if  first_stmt_of_condition is not None:
            #link to condition
             self.link_parent_stmts_to_current_stmt(last_stmts_of_update_body,first_stmt_of_condition)
            
        else:
             #link to for when condition empty
            # print(logstr,'with type add edge!')
            self.link_parent_stmts_to_current_stmt_with_type(last_stmts_of_update_body,current_stmt,ControlFlowKind.FOR_CONDITION)
        #after analyze all block,deal with the break/continue in global_special_stmts_without_outer_bc and  modify global_special_stmts
        # print(global_special_stmts_without_outer_bc)
        for stmt in global_special_stmts_without_outer_bc.copy():
            if isinstance(stmt,specialBind):
                continue
            if stmt.operation=="break_stmt":
                label=stmt.target
                if len(label)==0 or (labelBind is not None and labelBind.match(label)):
                    #matched break;
                    previous.append(CFGNode(stmt,ControlFlowKind.BREAK))
                    global_special_stmts_without_outer_bc.remove(stmt)

                continue
            if stmt.operation=="continue_stmt":
                label=stmt.target
                if len(label)==0 or (labelBind is not None and labelBind.match(label)):
                    #matched continue;
                    t=[CFGNode(stmt,ControlFlowKind.CONTINUE)]
                    if first_stmt_of_update_body is not None:
                        self.link_parent_stmts_to_current_stmt(t,first_stmt_of_update_body)
                    elif first_stmt_of_condition is not None:
                        self.link_parent_stmts_to_current_stmt(t,first_stmt_of_condition)
                    else:
                        self.link_parent_stmts_to_current_stmt(t,current_stmt)
                        
                    global_special_stmts_without_outer_bc.remove(stmt)
                continue
        for stmt in global_special_stmts_without_outer_bc:
            if stmt not in global_special_stmts:
                global_special_stmts.append(stmt)
        #return 
        boundary = self.boundary_of_multi_blocks(current_block, [init_body_id,condition_prebody_id,body_id,update_body_id ])
        # print(init_body_id, condition_prebody_id, body_id, update_body_id)
        if util.isna(init_body_id) and util.isna(body_id) and util.isna(update_body_id) and util.isna(condition_prebody_id):
            boundary=current_stmt._index
        # print('in for',current_stmt.stmt_id,'.previous:')
        # for stmt in previous:
        #     if isinstance(stmt,CFGNode):
        #         print(stmt.stmt.operation,stmt.stmt.stmt_id,stmt.edge)
        #     else:

        #         print(stmt.operation,stmt.stmt_id)
        # print('special_stmts:')
        # for child in global_special_stmts:
        #     if isinstance(child,specialBind):
        #         print(str(child))
        #     else:
        #         print(child.operation,child.stmt_id)
        # print('boundary',boundary)
        return (previous,boundary)

    def analyze_try_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_method_decl_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_decl_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_return_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_break_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        global_special_stmts.append(current_stmt)
        #return -1 to exit the block analyze because the rest won't be excecuted and break should link to the next stmt which is processed by the matched outer loop
        return ([], -1)
    def analyze_continue_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        global_special_stmts.append(current_stmt)
        #return -1 to exit the block analyze because the rest won't be excecuted and continue should link to the next stmt which is processed by the matched outer loop
        return ([], -1)
    
    def analyze_label_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        #deal with previous goto
        for stmt in global_special_stmts.copy():
            if isinstance(stmt,specialBind):
                continue
            if isinstance(stmt, CFGNode) and stmt.stmt.operation=="goto_stmt"and stmt.stmt.target==current_stmt.name :
                # if stmtstmt.operation == "goto_stmt" and stmt.name == current_stmt.name:
                self.cfg.add_edge(stmt.stmt,current_stmt,stmt.edge)
                global_special_stmts.remove(stmt)
            elif stmt.operation == "goto_stmt" and stmt.target == current_stmt.name:
                self.cfg.add_edge(stmt,current_stmt)
                global_special_stmts.remove(stmt)
        next_index=current_stmt._index+1
        next_stmt=current_block.access(next_index) if next_index<len(current_block) else None
        newBind=specialBind(current_stmt,next_stmt)
        global_special_stmts.append(newBind)
        return ([current_stmt], next_index-1)
    
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

    def link_parent_stmts_to_current_stmt_with_type(self, parent_stmts: list, current_stmt,type):
        # print('in the with type add edge')
        # logstr=''
        # for stmt in parent_stmts:
        #     if isinstance(stmt,CFGNode):
        #         logstr+=stmt.stmt.operation+str(stmt.stmt.stmt_id)+str(stmt.edge)+' '
        #     else:
        #         logstr+=stmt.operation+str(stmt.stmt_id)+' '
        # logstr+="current st:"+current_stmt.operation+str(current_stmt.stmt_id)+'\n'
        # print(logstr)


        for node in parent_stmts:
            if isinstance(node, CFGNode):
                # Assumes node.stmt and node.edge are valid attributes for CFGNode
                if node.edge!=ControlFlowKind.EMPTY:
                    self.cfg.add_edge(node.stmt, current_stmt, node.edge)
                else:
                    self.cfg.add_edge(node.stmt, current_stmt,type)
            else:
                # Links non-CFGNode items
                self.cfg.add_edge(node, current_stmt,type)
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