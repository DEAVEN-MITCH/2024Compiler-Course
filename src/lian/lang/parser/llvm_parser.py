#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type in ["line_comment", "block_comment"]
        pass

    def is_identifier(self, node):
        return node.type == "identifier"
        pass

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
        }

        return LITERAL_MAP.get(node.type, None)

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

    def find_child_by_type(self, input_node, input_type):
        for child in input_node.children:
            if child.type == input_type:
                return child

    def find_children_by_type(self, input_node, input_type):
        ret = []
        for child in input_node.children:
            if child.type == input_type:
                ret.append(child)
        return ret

    def alloca_expression(self, node, statements):
        child1=self.find_child_by_type(node,"type")
        datatype=self.read_node_text(child1)
        tmp_var = self.tmp_variable(statements)
        statements.append(
            {"alloca_expr": 
            {"target":tmp_var,
             "datatype": datatype}})    

    def load_expression(self, node, statements):
        child=self.find_child_by_type(node,"type_and_value")
        address=self.read_node_text(child)
        tmp_var = self.tmp_variable(statements)
        statements.append(
            {"load_expr": 
            {"target":tmp_var,
             "address": address.split(' ')[-1]}})

    def store_expression(self, node, statements):
        children=self.find_children_by_type(node,"type_and_value")
        source=self.read_node_text(children[0])
        address=self.read_node_text(children[1])
        statements.append(
            {"store_expr": 
            {"source": source.split(' ')[-1],
             "address":address.split(' ')[-1]}})    

    def call_expression(self, node, statements):
        child1=self.find_child_by_type(node,"type")
        functype=self.read_node_text(child1)
        child2=self.find_child_by_field(node,"callee")
        prototype=self.read_node_text(child2)
        child3=self.find_child_by_field(node,"arguments")
        args=self.read_node_text(child3)
        tmp_var = self.tmp_variable(statements)
        statements.append(
            {"call_expr": 
            {"target":tmp_var,
             "functype": functype,
             "prototype":prototype,
             "args":args}})      

    def ret_expression(self, node, statements):
        child=self.find_child_by_type(node,"type_and_value")
        target=self.read_node_text(child)
        statements.append(
            {"ret_expr": {"target": target.split(' ')[-1]}})

    def getptr_expression(self, node, statements):
        children=self.find_children_by_type(node,"type_and_value")
        ptrtype=self.read_node_text(children[0])
        ptrval=self.read_node_text(children[1])
        typidx=[]
        for childs in children[2:]:
            child=self.read_node_text(childs)
            typidx.append(child)
        tmp_var = self.tmp_variable(statements)
        statements.append(
            {"getptr_expr": 
            {"target":tmp_var,
             "ptrtype": ptrtype,
             "ptrval":ptrval.split(' ')[-1],
             "typidx":typidx}})

    def binary_expression(self, node, statements):
        child1=self.find_child_by_type(node,"type_and_value")
        operand=self.read_node_text(child1)
        child2=self.find_child_by_field(node,"inst_name")
        operator=self.read_node_text(child2)
        child3=self.find_child_by_type(node,"value")
        operand2=self.read_node_text(child3)
        tmp_var = self.tmp_variable(statements)
        statements.append(
            {"binary_expr":
            {"target": tmp_var, 
             "operator": operator,
             "operand": operand.split(' ')[-1],
             "operand2": operand2.split(' ')[-1]}})

    def icmp_expression(self, node, statements):
        child1=self.find_child_by_type(node,"type_and_value")
        operand=self.read_node_text(child1)
        child2=self.find_child_by_type(node,"icmp_cond")
        operator=self.read_node_text(child2)
        child3=self.find_child_by_type(node,"value")
        operand2=self.read_node_text(child3)
        tmp_var = self.tmp_variable(statements)
        statements.append(
            {"icmp_expr":
            {"target": tmp_var, 
             "operator": operator,
             "operand": operand.split(' ')[-1],
             "operand2": operand2}})

    def fcmp_expression(self, node, statements):
        child1=self.find_child_by_type(node,"type_and_value")
        operand=self.read_node_text(child1)
        child2=self.find_child_by_type(node,"fcmp_cond")
        operator=self.read_node_text(child2)
        child3=self.find_child_by_type(node,"value")
        operand2=self.read_node_text(child3)
        tmp_var = self.tmp_variable(statements)
        statements.append(
            {"fcmp_expr":
            {"target": tmp_var, 
             "operator": operator,
             "operand": operand.split(' ')[-1],
             "operand2": operand2}})

    def cast_expression(self, node, statements):
        child1=self.find_child_by_type(node,"type_and_value")
        operand=self.read_node_text(child1)
        child2=self.find_child_by_field(node,"inst_name")
        operator=self.read_node_text(child2)
        child3=self.find_child_by_type(node,"type")
        operand2=self.read_node_text(child3)
        tmp_var = self.tmp_variable(statements)
        statements.append(
            {"cast_expr":
            {"target": tmp_var, 
             "operator": operator,
             "operand": operand.split(' ')[-1],
             "operand2": operand2}})


    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "instruction_alloca"        :self.alloca_expression,
            "instruction_load"          :self.load_expression,
            "instruction_store"         :self.store_expression,
            "instruction_call"          :self.call_expression,
            "instruction_ret"           :self.ret_expression,
            "instruction_getelementptr" :self.getptr_expression,
            "instruction_bin_op"        :self.binary_expression,
            "instruction_icmp"          :self.icmp_expression,
            "instruction_fcmp"          :self.fcmp_expression,
            "instruction_cast"          :self.cast_expression
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def is_expression(self, node):
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)


    def switch_statement(self, node, statements):
        children = self.find_children_by_type(node, "type_and_value")
        control_value = self.read_node_text(children[0])
        default_target = self.read_node_text(children[1])[6:]  
        cases = []
        for i in range(2, len(children), 2):
            case_value = self.read_node_text(children[i])
            case_target = self.read_node_text(children[i + 1])[6:] 
            cases.append({"case_value": case_value, "case_target": case_target})
        switch_statement = {
            "switch_stmt": {
                "control_value": control_value.split(' ')[-1],  
                "default_target": default_target,
                "cases": cases
            }
    }

    def invoke_statement(self, node, statements):
        child1 = self.find_child_by_type(node, "type")
        functype = self.read_node_text(child1)
        child2 = self.find_child_by_field(node, "callee")
        prototype = self.read_node_text(child2)
        child3 = self.find_child_by_field(node, "arguments")
        args = self.read_node_text(child3)
        child4 = self.find_child_by_field(node, "normal_dest")
        normal_dest = self.read_node_text(child4)[6:]  
        child5 = self.find_child_by_field(node, "exception_dest")
        exception_dest = self.read_node_text(child5)[6:]  
        tmp_var = self.tmp_variable(statements)
        statements.append({
            "invoke_stmt": {
                "target": tmp_var,
                "functype": functype.strip(),
                "prototype": prototype.strip(),
                "args": args.strip(),
                "normal_dest": normal_dest,
                "exception_dest": exception_dest
            }
    })

    def resume_statement(self, node, statements):
        child = self.find_child_by_type(node, "type_and_value")
        exception_data = self.read_node_text(child)
        statements.append({
            "resume_stmt": {
                "exception_data": exception_data.strip()
            }
        })

    def indirectbr_statement(self, node, statements):
        address_node = self.find_child_by_type(node, "type_and_value")
        address = self.read_node_text(address_node)
        targets = []
        labels = self.find_children_by_type(node, "_value_array")  
        for label in labels:
            target = self.read_node_text(label)[6:]  
            targets.append(target)
        statements.append({
            "indirectbr_stmt": {
                "address": address.strip(),
                "targets": targets
            }
        })

    def callbr_statement(self, node, statements):
        child1 = self.find_child_by_type(node, "type")  
        functype = self.read_node_text(child1)
        child2 = self.find_child_by_field(node, "callee")  
        prototype = self.read_node_text(child2)
        child3 = self.find_child_by_field(node, "arguments")  
        args = self.read_node_text(child3)
        targets_nodes = self.find_children_by_type(node, "type_and_value")
        print(targets_nodes)
        if len(targets_nodes) == 1:
            normal_dest = self.read_node_text(targets_nodes[0])[6:]  
            exception_dests = []
        else:
            normal_dest = self.read_node_text(targets_nodes[0])[6:]  
            exception_dests = [self.read_node_text(node)[6:] for node in targets_nodes[1:]]
        tmp_var = self.tmp_variable(statements)
        statements.append({
            "callbr_stmt": {
                "target": tmp_var,
                "functype": functype.strip(),
                "prototype": prototype.strip(),
                "args": args.strip(),
                "normal_dest": normal_dest,
                "exception_dests": exception_dests
            }
        })

    def br_statement(self, node, statements):
            children=self.find_children_by_type(node,"type_and_value")
            if len(children)==1:
                target=[]
                target=self.read_node_text(children[0])
                statements.append(
                    {"br_stmt": 
                    {"target":target[6:]}})
            else:
                then_target=[]
                then_target=self.read_node_text(children[1])
                else_target=[]
                else_target=self.read_node_text(children[2])
                condition=self.read_node_text(children[0])
                statements.append(
                    {"br_stmt": 
                    {"condition":condition.split(' ')[-1],
                    "then_target":then_target[6:],
                    "else_target":else_target[6:]}})

    def phi_statement(self, node, statements):
        child=self.find_child_by_type(node,"type")
        phitype=self.read_node_text(child)
        children1=self.find_children_by_type(node,"value")
        children2=self.find_children_by_type(node,"local_var")
        condition=[]
        for child1,child2 in zip(children1,children2):
            condition.append((self.read_node_text(child1), self.read_node_text(child2)))
        tmp_var = self.tmp_variable(statements)
        statements.append(
            {"phi_stmt": 
            {"target":tmp_var,
             "phitype": phitype,
             "condition":condition}})

    def landingpad_statement(self, node, statements):
        type_node = self.find_child_by_type(node, "type")
        type_text = self.read_node_text(type_node)
        clauses = []
        if 'cleanup' in [child.type for child in node.children]:
            clauses.append('cleanup')
        else:
            clause_nodes = self.find_children_by_type(node, "type_and_value")
            for clause_node in clause_nodes:
                clause_text = self.read_node_text(clause_node)
                clauses.append(clause_text.strip())
        statements.append({"landingpad_stmt": 
                          {"type": type_text.strip(),
                           "clauses": clauses}})

    def catchpad_statement(self, node, statements):
        within_node = self.find_child_by_type(node, "_within")
        within = self.read_node_text(within_node)
        values = []
        value_array_node = self.find_child_by_type(node, "_value_array")
        if value_array_node:
            value_nodes = self.find_children_by_type(value_array_node, "type_and_value")
            for value_node in value_nodes:
                value_text = self.read_node_text(value_node)
                formatted_value = value_text[6:].strip()  
                values.append(formatted_value)
        statements.append({"catchpad_stmt": 
                          {"within": within,
                           "value_array": values}})
         
    def cleanuppad_statement(self, node, statements):
        within_node = self.find_child_by_type(node, "_within")
        within = self.read_node_text(within_node)
        values = []
        value_array_node = self.find_child_by_type(node, "_value_array")
        if value_array_node:
            value_nodes = self.find_children_by_type(value_array_node, "type_and_value")
            for value_node in value_nodes:
                value_text = self.read_node_text(value_node)
                formatted_value = value_text[6:].strip()  
                values.append(formatted_value)
        statements.append({"cleanuppad_stmt": 
                          {"within": within,
                           "value_array": values}})

    def catchswitch_statement(self, node, statements):
        within_node = self.find_child_by_type(node, "_within")
        within = self.read_node_text(within_node)
        values = []
        value_array_node = self.find_child_by_type(node, "_value_array")
        if value_array_node:
            value_nodes = self.find_children_by_type(value_array_node, "type_and_value")
            for value_node in value_nodes:
                value_text = self.read_node_text(value_node)
                formatted_value = value_text[6:].strip()
                values.append(formatted_value)
        unwind_label_node = self.find_child_by_type(node, "_unwind_label")
        unwind_label = self.read_node_text(unwind_label_node) if unwind_label_node else None
        statements.append({"catchswitch_stmt": 
                          {"within": within,
                           "value_array": values,
                           "unwind_label":unwind_label}})

    def cleanupret_statement(self, node, statements):
        local_var_node = self.find_child_by_type(node, "local_var")
        local_var = self.read_node_text(local_var_node)
        unwind_label_node = self.find_child_by_type(node, "_unwind_label")
        unwind_label = self.read_node_text(unwind_label_node) if unwind_label_node else None
        statements.append({"cleanupret_stmt": 
                          {"from_var": local_var,
                           "unwind_label" : unwind_label}})

    def catchret_statement(self, node, statements):
        local_var_node = self.find_child_by_type(node, "local_var")
        local_var = self.read_node_text(local_var_node)
        type_and_value_node = self.find_child_by_type(node, "type_and_value")
        type_and_value = self.read_node_text(type_and_value_node)
        statements.append(
            {"catchret_stmt": 
            {"from_var": local_var,
            "to_target": type_and_value.split(' ')[-1]}})

    def freeze_statement(self, node, statements):
        child = self.find_child_by_type(node, "type_and_value")
        datatype_value = self.read_node_text(child)
        tmp_var = self.tmp_variable(statements)
        statements.append(
            {"freeze_stmt":
            {"target": tmp_var,
             "datatype_value": datatype_value}})


    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            "instruction_switch"        :self.switch_statement,
            "instruction_invoke"        :self.invoke_statement,
            "instruction_resume"        :self.resume_statement,
            "instruction_br"            :self.br_statement,
            "instruction_indirectbr"    :self.indirectbr_statement,
            "instruction_callbr"        :self.callbr_statement,
            "instruction_phi"           :self.phi_statement,
            "instruction_landingpad"    :self.landingpad_statement,
            "instruction_catchpad"      :self.catchpad_statement,
            "instruction_cleanuppad"    :self.cleanuppad_statement,
            "instruction_catchswitch"   :self.catchswitch_statement,
            "instruction_cleanupret"    :self.cleanupret_statement,
            "instruction_catchret"      :self.catchret_statement,
            "instruction_freeze"        :self.freeze_statement
        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)

    def is_statement(self, node):
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)
