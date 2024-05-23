#!/usr/bin/env python3

from lian.util import util
from lian.util import dataframe_operation as do
from lian.config.constants import SymbolKind, EventKind
from lian.config import config, schema
from lian.semantic.internal import (
    hierarchy_analysis,
    control_flow
)

class InternalTraversal:
    def __init__(self, options, app_manager, module_symbols):
        self.analysis_phases = []
        self.options = options
        self.app_manager = app_manager
        self.module_symbols = module_symbols
        self.module_symbol_table = module_symbols.module_symbol_table
        # self.type_system = type_system.TypeSystem()

        self.analysis_phases = [
            control_flow.ControlFlowAnalysis(),
        ]

    def init_analysis_phases(self):
        for phase in self.analysis_phases:
            phase.options = self.options
            phase.app_manager = self.app_manager
            phase.module_symbols = self.module_symbols
            phase.module_symbol_table = self.module_symbol_table
            # phase.type_system = self.type_system

            phase.init()

    def phase_internal_analysis_start(self):
        for phase in self.analysis_phases:
            phase.internal_analysis_start()

    def phase_internal_analysis_end(self):
        for phase in self.analysis_phases:
            phase.internal_analysis_end()

    def phase_bundle_start(self, bundle_path):
        for phase in self.analysis_phases:
            phase.bundle_path = bundle_path
            phase.bundle_start()

    def phase_bundle_end(self):
        for phase in self.analysis_phases:
            phase.bundle_end()
            phase.bundle_path = None

    def phase_unit_start(self, scope_hierarchy, unit_info, unit_glang):
        for phase in self.analysis_phases:
            phase.scope_hierarchy = scope_hierarchy
            phase.unit_info = unit_info
            phase.unit_id = unit_info.symbol_id
            phase.unit_glang = unit_glang
            phase.lang = unit_info.lang

            phase.unit_analysis_start()

    def phase_unit_end(self):
        for phase in self.analysis_phases:
            phase.unit_analysis_end()

            phase.scope_hierarchy = None
            phase.unit_info = None
            phase.unit_glang = None
            phase.unit_id = -1
            phase.lang = None

    def phase_method_init(self, phase, method_stmt, parameter_decls, method_init, method_body):
        phase.method_stmt = method_stmt
        phase.method_id = method_stmt.stmt_id
        phase.parameter_decls = parameter_decls
        phase.method_init = method_init
        phase.method_body = method_body

    def run(self):
        """
        Input:
        - module_symbol_table
        - glang_bundles

        Procedures:
        - traversal all units in glang_bundles
        - call each phase for each unit and its glang IR
        """
        self.init_analysis_phases()
        self.phase_internal_analysis_start()

        tmp_counter = 0
        for bundle_path in self.module_symbol_table.unique_values_of_column("glang_path"):
            bundle = do.DataFrameAgent().load(bundle_path)
            unit_id_set = bundle.unique_values_of_column("unit_id")
            scope_hierarchy = hierarchy_analysis.ScopeHierarchy(self.module_symbols)
            self.phase_bundle_start(bundle_path)
            for unit_id in unit_id_set:
                if self.options.benchmark:
                    tmp_counter += 1
                    if tmp_counter >= config.MAX_BENCHMARK_TARGET:
                        return

                unit_info = self.module_symbols.find_unit_by_id(unit_id)
                unit_glang = bundle.query(bundle.unit_id == unit_id, reset_index = True)
                scope_hierarchy.analyze_unit(unit_info, unit_glang)
                self.phase_unit_start(scope_hierarchy, unit_info, unit_glang)
                all_method_stmt_ids = []
                for method_stmt in scope_hierarchy.get_all_methods_of_current_unit():
                    method_stmt = unit_glang.query_first(unit_glang.stmt_id == method_stmt.stmt_id)
                    all_method_stmt_ids.append(method_stmt.stmt_id)
                    if not method_stmt:
                        continue

                    method_parameters = unit_glang.read_block(method_stmt.parameters, reset_index = True)
                    method_init = unit_glang.read_block(method_stmt.init, reset_index = True)
                    method_body = unit_glang.read_block(method_stmt.body, reset_index = True)

                    # TODO: spawn _THREAD_ to launch self.method_analysis()
                    previous_results = {}
                    for index, phase in enumerate(self.analysis_phases):
                        if self.options.debug:
                            util.debug(f"analysis_phase name: {phase.name} index:{index}")
                            
                        self.phase_method_init(phase, method_stmt, method_parameters, method_init, method_body)
                        last_result = phase.method_analysis(previous_results)
                        previous_results[phase.name] = last_result

                self.phase_unit_end()

            scope_hierarchy.save_results()
            self.phase_bundle_end()

        self.phase_internal_analysis_end()
        self.module_symbols.export()
