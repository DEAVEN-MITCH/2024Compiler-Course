#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def is_comment(self, node):
        return node.type == "comment"

    def is_identifier(self, node):
        return node.type == "identifier"

    def obtain_literal_handler(self, node):
        LITERAL_MAP = {
            "composite_literal": self.composite_literal,
            "func_literal": self.func_literal,
            "raw_string_literal": self.string_literal,
            "interpreted_string_literal":self.string_literal,
            "int_literal": self.regular_number_literal,
            "float_literal": self.regular_number_literal,
            "imaginary_literal": self.regular_imaginary_literal,
            "rune_literal": self.regular_rune_literal,
            "nil": self.regular_literal,
            "true": self.regular_literal,
            "false": self.regular_literal,
            "itoa": self.regular_literal,
        }
        # print(node.type,self.read_node_text(node))
        return LITERAL_MAP.get(node.type, None)

    def parse_literal_value(self, node,statements):#accept literal_value as input node
        literal_elements=self.find_children_by_type(node,'literal_element')
        keyed_element=self.find_children_by_type(node,'keyed_element')
        tmp_var=self.tmp_variable(statements)
        type_parameters=[]
        args=[]
        init=[]
        fields=[]
        methods=[]
        nested=[]
        for child in literal_elements:
            n=child.named_children[0]#ex or literal
            v=''
            if n.type=='literal_value':
                v=self.parse_literal_value(n,init)
            else:
                v=self.parse(n,init)
            args.append(v)
        for child in keyed_element:
            # print('#debug in keyed_element')
            key=child.named_children[0]#literal_element
            m=key.named_children[0]
            t_key=''
            if m.type=='literal_value':
                t_key=self.parse_literal_value(m,init)
            else:
                t_key=self.parse(m,init)
            value=child.named_children[1]
            m=value.named_children[0]
            t_value=''
            if m.type=='literal_value':
                t_value=self.parse_literal_value(m,init)
            else:
                t_value=self.parse(m,init)
            init.append({"field_write": {"receiver_object": self.global_this(), "field": t_key, "source": t_value}})
        statements.append({"new_instance":{"target":tmp_var,       "type_parameters":type_parameters,"data_type":None,"args":args,"init":init,"fields":fields,"methods":methods,"nested":nested}})
        return tmp_var
    def composite_literal(self,node,statements,replacement):
        type_node=node.child_by_field_name('type')
        shadow_type=self.read_node_text(type_node)
        nt=type_node.type
        body_node=node.child_by_field_name('body')#literal_value
        literal_elements=self.find_children_by_type(body_node,'literal_element')
        keyed_element=self.find_children_by_type(body_node,'keyed_element')
        tmp_var=self.tmp_variable(statements)
        type_parameters=[]
        args=[]
        init=[]
        fields=[]
        methods=[]
        nested=[]
        if nt=='generic_type':
            bt=type_node.child_by_field_name('type')
            nt=bt.type
            shadow_type=self.type_parser(bt,statements)
            tp=type_node.child_by_field_name('type_arguments').named_children
            for child in tp:
                if child.type==',':
                    continue
                type_parameters.append(self.read_node_text(child))
        for child in literal_elements:
            n=child.named_children[0]#ex or literal
            v=''
            if n.type=='literal_value':
                v=self.parse_literal_value(n,init)
            else:
                v=self.parse(n,init)
            args.append(v)
        for child in keyed_element:
            # print('#debug in c keyed')
            key=child.named_children[0]#literal_element
            m=key.named_children[0]
            t_key=''
            if m.type=='literal_value':
                t_key=self.parse_literal_value(m,init)
            else:
                t_key=self.parse(m,init)
            value=child.named_children[1]
            m=value.named_children[0]
            t_value=''
            if m.type=='literal_value':
                t_value=self.parse_literal_value(m,init)
            else:
                t_value=self.parse(m,init)
            if nt=='struct_type':#init use field_write
                init.append({"field_write": {"receiver_object": self.global_this(), "field": t_key, "source": t_value}})
            elif nt=='map_type':#init use map_write
                init.append({"map_write": {"target": self.global_this(),"key": t_key, "value": t_value}})
            elif nt=='slice_type' or nt == 'array_type':#init use array_write
                init.append({"array_write": {"array": self.global_this(), "index": t_key, "source": t_value}})
            else:#default use field_write for the moment
                init.append({"field_write": {"receiver_object": self.global_this(), "field": t_key, "source": t_value}})
            
        statements.append({"new_instance":{"target":tmp_var,       "type_parameters":type_parameters,"data_type":shadow_type,"args":args,"init":init,"fields":fields,"methods":methods,"nested":nested}})
        return tmp_var
    



    def regular_imaginary_literal(self, node, statements, replacement):
        #print(f"node: {self.read_node_text(node)}")
        #print(f"node: {node.sexp()}")
        """处理虚数字面量"""
        imaginary_value = self.read_node_text(node)  # 获取虚数字面量
        return f"Imaginary literal: {imaginary_value}"


    def regular_rune_literal(self, node, statements, replacement):
        #print(f"node: {self.read_node_text(node)}")
        #print(f"node: {node.sexp()}")
        """处理rune字面量"""
        rune_value = self.read_node_text(node)  # 获取rune字面量
        return f"Rune literal: {rune_value}"


    def regular_literal(self, node, statements, replacement):
        return self.read_node_text(node)

    def func_literal(self, node, statements,replacement):
        #parameters_list是泛型参数列表，parameters是参数列表，匿名函数没有泛型？
        #parameters processing
        child = self.find_child_by_field(node, "parameters")
        parameters =[]
        init = []
        # tn=child
        # print(child.type)
        # while child and child.named_child_count > 0:
        #     child=child.named_children[0]
        #     print(child.type)

        #outcome
        #parameter_list
        # parameter_declaration
        # identifier
        if child and child.named_child_count > 0:
            # need to deal with parameters
            for p in child.named_children:#parameter_declaration或variadic_parameter_declaration
                self.parse_parameters(p,init)
                while len(init) > 0:
                    parameters.append(init.pop())
        #return type processing
        child = self.find_child_by_field(node, "result")
        mytype = self.read_node_text(child)
        #new variable for ret
        tmp=self.tmp_method()

        type_parameters = []
        attr=[]
        #body stmt processing
        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                self.parse(stmt, new_body)
        statements.append(
            {"method_decl": { "attr":attr,"data_type": mytype, "name": tmp, "parameters": parameters,"body": new_body,"init": init,"type_parameters": type_parameters,}})
    
        return tmp

    def parse_parameters(self,node,statements):
        modifiers = []
        mytype = self.find_child_by_field(node, "type")
        shadow_type = self.read_node_text(mytype)
        name = self.find_child_by_field(node, "name")
        shadow_name=self.read_node_text(name)   
        if node.type=='variadic_parameter_declaration':
            modifiers.append('variadic')
            statements.append({"parameter_decl": {"name": shadow_name, "data_type": shadow_type, "modifiers": modifiers}})
        else :
            children=node.children_by_field_name('name')
            for child in children:#all the parameter decl of the same type processing
                    shadow_name=self.read_node_text(child)
                    statements.append({"parameter_decl": {"name": shadow_name, "data_type": shadow_type, "modifiers": modifiers}})
           

        
    def regular_number_literal(self, node, statements, replacement):
        value = self.read_node_text(node)
        if node.type=='float_literal' and  "x" in value.lower():
            try:
                value = float.fromhex(value)
            except:
                value = self.common_eval(value)
        else:
            value = self.common_eval(value)
        # tn=node
        # print(node.type)
        # while len(tn.named_children)>0:
        #     tn=tn.named_children[0]
        #     print(tn.type)
            
        return str(value)

    def string_literal(self, node, statements, replacement):
        ret=''
        if node.type == "raw_string_literal":
            ret ='"'+self.read_node_text(node)[1:-1]+'"'#remove the surrounding ``
            return ret#no need for escape processing for it's raw
        # else type==interpreted_string_literal
        else:
            ret = self.read_node_text(node)#[1:-1]#remove the surrounding ""
        ret = self.handle_hex_string(ret)
        # return ret
        return self.escape_string(ret)

    def handle_hex_string(self, input_string):
        if self.is_hex_string(input_string):
            try:
                tmp_str = input_string.replace('\\x', "")
                tmp_str = bytes.fromhex(tmp_str).decode('utf8')
                return tmp_str
            except:
                pass

        return input_string

    def is_literal(self, node):
        return self.obtain_literal_handler(node) is not None

    def literal(self, node, statements, replacement):
        handler = self.obtain_literal_handler(node)
        return handler(node, statements, replacement)

    def check_declaration_handler(self, node):
        DECLARATION_HANDLER_MAP = {
            'const_declaration':self.const_declaration,
            'type_declaration':self.type_declaration,
            'var_declaration':self.var_declaration,
            'short_var_declaration':self.short_var_declaration,
            'method_declaration':self.method_declaration,
            'import_declaration':self.import_declaration,
            'function_declaration':self.function_declaration,
            'package_clause':self.package_clause,

        }
        return DECLARATION_HANDLER_MAP.get(node.type, None)
    def package_clause(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
        name = self.read_node_text(node.named_children[0])
        if name:
            statements.append({"package_stmt": {"name": name}})
        
    def function_declaration(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
        # 获取函数名节点
        name_node = node.child_by_field_name('name')
        function_name = name_node.text if name_node else "UnnamedFunction"

        # 获取类型参数节点列表
        type_parameters_node = node.child_by_field_name('type_parameters')
        type_parameters = []
        if type_parameters_node:
            for tp in type_parameters_node.named_children:
                type_parameters.append(tp.text)

        # 获取参数列表节点
        parameters_node = node.child_by_field_name('parameters')
        parameters = []
        if parameters_node:
            for param in parameters_node.named_children:
                parameters.append(self.parameter_declaration(param))

        # 获取返回结果类型节点
        result_node = node.child_by_field_name('result')
        result_type = result_node.text if result_node else None

        # 获 取函数体节点
        body_node = node.child_by_field_name('body')
        function_body = []
        if body_node:
            for stmt in body_node.named_children:
                self.parse_statement(stmt, function_body)

        # 构建并添加函数声明
        function_stmt = {
            "function_decl": {
                "name": function_name,
                "type_parameters": type_parameters,
                "parameters": parameters,
                "result_type": result_type,
                "body": function_body
            }
        }
        statements.append(function_stmt)
        print(f"已声明函数: {function_name}")

    def parameter_declaration(self, node):
        # 解析参数声明
        return {
            "parameter_decl": {
                "name": node.child_by_field_name('name').text,
                "data_type": node.child_by_field_name('data_type').text if node.child_by_field_name('data_type') else None
            }
        }

    def parse_statement(self, node, body):
        # 简化的语句解析逻辑
        stmt = {
            "type": node.type,
            "content": node.text
        }
        body.append(stmt)

    def is_declaration(self, node):
        return self.check_declaration_handler(node) is not None

    def declaration(self, node, statements):
        handler = self.check_declaration_handler(node)
        return handler(node, statements)

    def const_declaration(self,node,statements):
        const_specs=self.find_children_by_type(node,'const_spec')
        attr=['const']
        for child in const_specs:
            identifiers=child.children_by_field_name('name')
            type_node=child.child_by_field_name('type')
            value_nodes=child.child_by_field_name('value')
            if value_nodes:
                value_nodes=value_nodes.named_children
            shadow_type=None
            if type_node:
                shadow_type=self.read_node_text(type_node)
            shadow_names=[]
            for identifier in identifiers:
                if identifier.type !='identifier':
                    continue
                shadow_name=self.read_node_text(identifier)
                shadow_names.append(shadow_name)
                statements.append({"variable_decl": {"name": shadow_name, "data_type": shadow_type, "attr": attr}})
            if value_nodes and len(value_nodes)==1 and value_nodes[0].type=='call_expression':#expand call return
                ret_arr=self.parse(value_nodes[0],statements)
                i=0
                for shadow_left in shadow_names:
                    statements.append({"array_read": {"target": shadow_left, "array": ret_arr, "index": str(i)}})
                    i+=1 
                continue
            if value_nodes and len(shadow_names)==len(value_nodes):
                for i in range(len(shadow_names)):
                    shadow_value=self.parse(value_nodes[i],statements)
                    statements.append({"assign_stmt": {"target": shadow_names[i], "operand": shadow_value}})

    
    def type_parser(self,node,statements)->str:#非直接声明_type节点的处理
        while node.type == 'parenthesized_type':
            node=node.named_children[0]#remove the parentheses
        tt=node.type
        if tt=='struct_type':   #anonymous struct
                shadow_name=self.tmp_variable(statements)
                nested=[]
                fields=[]
                field_declarations=self.find_children_by_type(node.named_children[0],'field_declaration')
                nested_type=[]
                for fd in field_declarations:
                    tag=fd.child_by_field_name('tag')
                    shadow_tag=None
                    if tag is not None:
                        shadow_tag=self.parse(tag,nested)
                    type_node=fd.child_by_field_name('type')
                    name_nodes=fd.children_by_field_name('name') 
                    if len(name_nodes)>0:#  choice 1
                        shadow_type=self.type_parser(type_node,nested)
                        for name_node in name_nodes:
                            t_shadow_name=self.read_node_text(name_node)
                            fields.append({"variable_decl": {"name": t_shadow_name, "data_type": shadow_type, "attr": [str({'tag':shadow_tag})]}})
                    else:#choice 2
                        pre=type_node.prev_sibling
                        prestr=''
                        if pre is not None:
                            prestr=self.read_node_text(pre)#*
                        shadow_type=prestr+self.type_parser(type_node,nested)
                        nested_type.append(shadow_type)
                statements.append({"class_decl": {"name": shadow_name, "attr": [str({'nested_type':nested_type})],"supers":None,"type_parameters":None,"static_init":None,"init":None,"fields":fields,"methods":None,"nested":nested}})
                return shadow_name
        elif tt=='interface_type':#anonymous struct
                methods=[]
                fields=[]
                nested=[]
                nested_type=[]
                nested_constraints=[]
                shadow_name=self.tmp_variable(statements)
                methods_specs=self.find_children_by_type(node,'method_spec')
                struct_elems=self.find_children_by_type(node,'struct_elem')
                constraint_elems=self.find_children_by_type(node,'constraint_elem')
                for child in methods_specs:
                    parameters=node.child_by_field_name('parameters')
                    shadow_parameters=[]
                    for parameter in parameters.named_children:
                        self.parse_parameters(parameter,shadow_parameters)

                    result=node.child_by_field_name('result')
                    shadow_result=''
                    if result is not None:
                        if result.type=='parameter_list':
                            shadow_result=self.read_node_text(result)
                        else:#simple_type
                            shadow_result=self.type_parser(result,nested)
                    methods.append({'method_decl':{"name":self.read_node_text(child.child_by_field_name('name')),"parameters":shadow_parameters,"data_type":shadow_result,'attr':[],'init':None,'body':None}})
                
                for child in struct_elems:
                    nested_type.append(self.read_node_text(child))
                for child in constraint_elems:
                    nested_constraints.append(self.read_node_text(child))
                statements.append({"interface_decl": {"name": shadow_name, "attr": [str({'nested_type':nested_type,'nested_constraints':nested_constraints})],"supers":None,"type_parameters":None,"static_init":None,"init":None,"fields":None,"methods":methods,"nested":nested}})
                return shadow_name
        elif tt=='pointer_type':
            return '*'+self.type_parser(node.named_children[0],statements)
        elif tt=='array_type':
            length=node.child_by_field_name('length')
            shadow_length=self.parse(length,statements)
            element=node.child_by_field_name('element')
            shadow_element=self.type_parser(element,statements)
            return '['+str(shadow_length)+']'+shadow_element
        elif tt=='implicit_length_array_type':
            element=node.child_by_field_name('element')
            shadow_element=self.type_parser(element,statements)
            return '[...]'+shadow_element
        elif tt=='slice_type':
            element=node.child_by_field_name('element')
            shadow_element=self.type_parser(element,statements)
            return '[]'+shadow_element
        elif tt=='map_type':
            key=node.child_by_field_name('key')
            shadow_key=self.type_parser(key,statements)
            value=node.child_by_field_name('value')
            shadow_value=self.type_parser(value,statements)
            return 'map['+shadow_key+']'+shadow_value
            
        elif tt=='channel_type':
            value=node.child_by_field_name('value')
            shadow_value=self.type_parser(value,statements)
            pre=''
            prenode=value.prev_sibling#DEBUG
            while prenode is not None:
                pre=self.read_node_text(prenode)+pre
                prenode=prenode.prev_sibling
            return pre+' '+shadow_value
        elif tt=='function_type':
            parameters=node.child_by_field_name('parameters')
            shadow_parameters=self.read_node_text(parameters)
            result=node.child_by_field_name('result')
            shadow_result=''
            if result is not None:
                if result.type=='parameter_list':
                    shadow_result=self.read_node_text(result)
                else:#simple_type
                    shadow_result=self.type_parser(result,statements)
            return 'func'+shadow_parameters+shadow_result
        elif tt=='union_type':  
            left=node.children[0]
            right=node.children[2]
            shadow_left=self.type_parser(left,statements)
            shadow_right=self.type_parser(right,statements)
            return shadow_left+'|'+shadow_right
        elif tt=='negated_type':
            t=node.named_children[0]
            shadow_t=self.type_parser(t,statements)
            return '~'+shadow_t
        elif tt=='generic_type':
            type=node.child_by_field_name('type')
            shadow_type=self.type_parser(type,statements)
            type_arguments=node.child_by_field_name('type_arguments')
            shadow_type_arguments=''
            for child in type_arguments.children:
                if child.is_named:#DEBUG
                    shadow_type_arguments+=self.type_parser(child,statements)
                else:
                    shadow_type_arguments+=self.read_node_text(child)
            return shadow_type+shadow_type_arguments
            
        else:#_type_identifier或qualified_type
            return self.read_node_text(node)

    def type_declaration(self,node,statements):
        for child in node.named_children:#all type_spec or type_alias,deal with them respectively
            if child.type=='type_spec':
                type_name=child.child_by_field_name('name')
                type_parameters=child.child_by_field_name('type_parameters')
                shadow_type_parameters=[]#泛型参数
                shadow_name=self.read_node_text(type_name)
                if type_parameters:
                    for tp in type_parameters.named_children:#parameter declaration
                        shadow_type_parameters.append(self.read_node_text(tp.child_by_field_name('name')))#type identifier's names as parameters
                
                type_def=child.child_by_field_name('type')#include struct、interface and so on
                while type_def.type == 'parenthesized_type':
                    type_def=type_def.named_children[0]#remove the parentheses
                
                type_type=type_def.type
                if type_type=='struct_type':    
                    nested=[]
                    fields=[]
                    field_declarations=self.find_children_by_type(type_def.named_children[0],'field_declaration')
                    nested_type=[]
                    for fd in field_declarations:
                        tag=fd.child_by_field_name('tag')
                        shadow_tag=None
                        if tag is not None:
                            shadow_tag=self.parse(tag,nested)
                        type_node=fd.child_by_field_name('type')
                        name_nodes=fd.children_by_field_name('name') 
                        if len(name_nodes)>0:#  choice 1
                            shadow_type=self.type_parser(type_node,nested)
                            for name_node in name_nodes:
                                t_shadow_name=self.read_node_text(name_node)
                                fields.append({"variable_decl": {"name": t_shadow_name, "data_type": shadow_type, "attr": [str({'tag':shadow_tag})]}})
                        else:#choice 2
                            pre=type_node.prev_sibling
                            prestr=''
                            if pre is not None:
                                prestr=self.read_node_text(pre)#*
                            shadow_type=prestr+self.type_parser(type_node,nested)
                            nested_type.append(shadow_type)
                    statements.append({"class_decl": {"name": shadow_name, "attr": [str({'nested_type':nested_type})],"supers":None,"type_parameters":shadow_type_parameters,"static_init":None,"init":None,"fields":fields,"methods":None,"nested":nested}})
                elif type_type=='interface_type':
                    methods=[]
                    fields=[]
                    nested=[]
                    nested_type=[]
                    nested_constraints=[]
                    methods_specs=self.find_children_by_type(type_def,'method_spec')
                    struct_elems=self.find_children_by_type(type_def,'struct_elem')
                    constraint_elems=self.find_children_by_type(type_def,'constraint_elem')
                    for child in methods_specs:
                        parameters=child.child_by_field_name('parameters')
                        shadow_parameters=[]
                        for parameter in parameters.named_children:
                            self.parse_parameters(parameter,shadow_parameters)

                        result=child.child_by_field_name('result')
                        shadow_result=''
                        if result is not None:
                            if result.type=='parameter_list':
                                shadow_result=self.read_node_text(result)
                            else:#simple_type
                                shadow_result=self.type_parser(result,nested)
                        methods.append({'method_decl':{"name":self.read_node_text(child.child_by_field_name('name')),"parameters":shadow_parameters,"data_type":shadow_result,'attr':[],'init':None,'body':None}})

                    for child in struct_elems:
                        nested_type.append(self.read_node_text(child))
                    for child in constraint_elems:
                        nested_constraints.append(self.read_node_text(child))
                    statements.append({"interface_decl": {"name": shadow_name, "attr": [str({'nested_type':nested_type,'nested_constraints':nested_constraints})],"supers":None,"type_parameters":shadow_type_parameters,"static_init":None,"init":None,"fields":None,"methods":methods,"nested":nested}})
                else:
                    nested_type=[]
                    nested=[]
                    nested_type.append(self.type_parser(type_def,nested))
                    statements.append({"class_decl": {"name": shadow_name, "attr": [str({'nested_type':nested_type})],"supers":None,"type_parameters":shadow_type_parameters,"static_init":None,"init":None,"fields":None,"methods":None,"nested":nested}})
            elif child.type=='type_alias':
                shadow_name=self.read_node_text(child.child_by_field_name('name'))
                type_def=child.child_by_field_name('type')
                shadow_type=self.type_parser(type_def,statements)
                statements.append({'type_alias_stmt':{'target':shadow_name,'source':shadow_type}})


    def var_declaration(self,node,statements):
        var_specs=self.find_children_by_type(node,'var_spec')
        attr=['var']
        for child in var_specs:
            identifiers=child.children_by_field_name('name')
            type_node=child.child_by_field_name('type')
            value_nodes=child.child_by_field_name('value')
            if value_nodes:
                value_nodes=value_nodes.named_children
            shadow_type=None
            if type_node:
                shadow_type=self.read_node_text(type_node)
            shadow_names=[]
            for identifier in identifiers:
                if identifier.type !='identifier':
                    continue
                shadow_name=self.read_node_text(identifier)
                shadow_names.append(shadow_name)
                statements.append({"variable_decl": {"name": shadow_name, "data_type": shadow_type, "attr": attr}})
            if value_nodes and len(value_nodes)==1 and value_nodes[0].type=='call_expression':#expand call return
                ret_arr=self.parse(value_nodes[0],statements)
                i=0
                for shadow_left in shadow_names:
                    statements.append({"array_read": {"target": shadow_left, "array": ret_arr, "index": str(i)}})
                    i+=1 
                continue
            if value_nodes and len(shadow_names)==len(value_nodes):
                for i in range(len(shadow_names)):
                    shadow_value=self.parse(value_nodes[i],statements)
                    statements.append({"assign_stmt": {"target": shadow_names[i], "operand": shadow_value}})

    def short_var_declaration(self,node,statements):
        left_ex=node.child_by_field_name('left').named_children
        right_ex=node.child_by_field_name('right').named_children
        attr=['var']
        if len(right_ex)==1 and right_ex[0].type=='call_expression':#expand call return
                ret_arr=self.parse(right_ex[0],statements)
                i=0
                for leftexpr in left_ex:
                    if leftexpr.type !='identifier':
                        continue
                    shadow_name=self.parse(leftexpr,statements)
                    statements.append({"variable_decl": {"name": shadow_name, "data_type": None, "attr": attr}})
                    statements.append({"array_read": {"target": shadow_name, "array": ret_arr, "index": str(i)}})
                    i+=1 
        elif len(left_ex)==len(right_ex):
            for i in range(len(left_ex)):
                shadow_name=self.parse(left_ex[i],statements)
                statements.append({"variable_decl": {"name": shadow_name, "data_type": None, "attr": attr}})
                shadow_value=self.parse(right_ex[i],statements)
                statements.append({"assign_stmt": {"target": shadow_name, "operand": shadow_value}})
    def method_declaration(self, node, statements):
        child = self.find_child_by_field(node, "result")
        mytype = self.read_node_text(child)

        child = self.find_child_by_field(node, "name")
        name = self.read_node_text(child)

        new_parameters = []
        init = []
        child = self.find_child_by_field(node, "receiver")
        for p in child.named_children:
            self.parse_parameters(p,new_parameters)
        child = self.find_child_by_field(node, "parameters")
        for p in child.named_children:
            self.parse_parameters(p,new_parameters)

        new_body = []
        child = self.find_child_by_field(node, "body")
        if child:
            for stmt in child.named_children:
                if self.is_comment(stmt):
                    continue

                self.parse(stmt, new_body)

        statements.append(
            {"method_decl": {"attr": "interface_method", "data_type": mytype, "name": name, "parameters" : new_parameters,
                              "body": new_body}})

    def import_declaration(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
        child = self.find_child_by_type(node, "import_spec_list")
        stmt = self.find_child_by_type(node, "import_spec")
        if child:
            for stmt in child.named_children:
                child2 = self.find_child_by_field(stmt, "name")
                name = self.read_node_text(child2)
                child2 = self.find_child_by_field(stmt, "path")
                path = self.read_node_text(child2)
                if name:
                    statements.append(
                        {"import_as_stmt": {"name": path, 
                              "alias": name}})
                else :
                    statements.append(
                        {"import_stmt": {"name": path}})
        else:
            child2 = self.find_child_by_field(stmt, "name")
            name = self.read_node_text(child2)
            child2 = self.find_child_by_field(stmt, "path")
            path = self.read_node_text(child2)
            if name:
                statements.append(
                    {"import_as_stmt": {"name": path, 
                              "alias": name}})
            else :
                statements.append(
                        {"import_stmt": {"name": path}})
    def unary_expression(self, node, statements):
        operand = self.find_child_by_field(node, "operand")
        shadow_operand = self.parse(operand, statements)
        operator = self.find_child_by_field(node, "operator")
        shadow_operator = self.read_node_text(operator)

        tmp_var = self.tmp_variable(statements)

        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_operand}})
        return tmp_var

    def binary_expression(self, node, statements):
        left = self.find_child_by_field(node, "left")
        right = self.find_child_by_field(node, "right")
        operator = self.find_child_by_field(node, "operator")

        shadow_operator = self.read_node_text(operator)

        shadow_left = self.parse(left, statements)
        shadow_right = self.parse(right, statements)

        tmp_var = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_var, "operator": shadow_operator, "operand": shadow_left,
                                           "operand2": shadow_right}})

        return tmp_var

    def field(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        shadow_object, shadow_field = self.parse_field(node, statements)
        statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": shadow_field}})
        return tmp_var

    def parse_field(self, node, statements):
        myobject = self.find_child_by_field(node, "operand")
        shadow_object = self.parse(myobject, statements)

        # to deal with super
        remaining_content = self.read_node_text(node).replace(self.read_node_text(myobject) + ".", "").split(".")[:-1]
        if remaining_content:
            for child in remaining_content:
                tmp_var = self.tmp_variable(statements)
                statements.append({"field_read": {"target": tmp_var, "receiver_object": shadow_object, "field": child}})
                shadow_object = tmp_var

        field = self.find_child_by_field(node, "field")
        shadow_field = self.read_node_text(field)
        return (shadow_object, shadow_field)
    def parse_array(self, node, statements):
        array = self.find_child_by_field(node, "operand")
        shadow_array = self.parse(array, statements)
        index = self.find_child_by_field(node, "index")
        shadow_index = self.parse(index, statements)

        return (shadow_array, shadow_index)

    def array(self, node, statements):
        tmp_var = self.tmp_variable(statements)
        shadow_array, shadow_index = self.parse_array(node, statements)
        statements.append({"array_read": {"target": tmp_var, "array": shadow_array, "index": shadow_index}})
        return tmp_var

    def slice_expression(self, node, statements):
        operand = self.find_child_by_field(node, "operand")
        start = self.find_child_by_field(node, "start")
        end = self.find_child_by_field(node, "end")
        capacity = self.find_child_by_field(node, "capacity")
        shadow_operand = self.parse(operand, statements)
        shadow_start = self.parse(start, statements) if start else None
        shadow_end = self.parse(end, statements) if end else None
        shadow_capacity = self.parse(capacity, statements) if capacity else None
        tmp_var = self.tmp_variable(statements)
        statements.append({"slice_stmt": {"target":tmp_var,"array": shadow_operand, "start": shadow_start, "end": shadow_end, "step": shadow_capacity}})
        return tmp_var
    
    def call_expression(self, node, statements):
        name = self.find_child_by_field(node, "function")
        shadow_name = self.parse(name, statements)
        # print(f"node: {self.read_node_text(node)}")
        # print(f"node: {node.sexp()}")

    
        type_arguments = self.find_child_by_field(node, "type_arguments")
        type_text = ""
        if type_arguments:
            type_text = self.read_node_text(type_arguments)[1:-1]
        args = self.find_child_by_field(node, "arguments")
        args_list = []

        if args.named_child_count > 0:
            for child in args.named_children:
                if self.is_comment(child):
                    continue

                shadow_variable = self.parse(child, statements)
                if shadow_variable:
                    args_list.append(shadow_variable)

        tmp_return = self.tmp_variable(statements)
        statements.append({"call_stmt": {"target": tmp_return, "name": shadow_name, "type_parameters": type_text, "args": args_list}})

        return tmp_return
    
    def type_conversion_expression(self, node, statements):
        operand = self.find_child_by_field(node, "operand")#the expression to be converted
        type = self.find_child_by_field(node, "type")
        shadow_operand = self.parse(operand, statements)
        statements.append({"assign_stmt": {"target": shadow_operand, "operand": self.read_node_text(type), "operator": 'cast'}})
        return shadow_operand
    
    def cast_expression(self, node, statements):
        value = self.find_child_by_field(node, "operand")
        shadow_value = self.parse(value, statements)

        types = self.find_children_by_field(node, "type")
        for t in types:
            statements.append(
                {"assign_stmt": {"target": shadow_value, "operator": "cast", "operand": self.read_node_text(t)}})

        return shadow_value
    
    def check_expression_handler(self, node):
        EXPRESSION_HANDLER_MAP = {
            "unary_expression"          : self.unary_expression,
            "binary_expression"         : self.binary_expression,
            "selector_expression"       : self.field,
            "index_expression"          : self.array,
            "slice_expression"          : self.slice_expression,
            "call_expression"           : self.call_expression,
            "type_assertion_expression"        : self.cast_expression,
            "type_conversion_expression"         : self.type_conversion_expression,
            "parenthesized_expression"             : self.parenthesized_expression,
        }

        return EXPRESSION_HANDLER_MAP.get(node.type, None)

    def parenthesized_expression(self, node, statements):
        #print(f"node: {self.read_node_text(node)}")
        #print(f"node: {node.sexp()}")
        """处理括号表达式"""
        return self.parse(node.named_children[0])  # 解析括号中的表达式


    def is_expression(self, node):
        # print(node.type)
        return self.check_expression_handler(node) is not None

    def expression(self, node, statements):
        handler = self.check_expression_handler(node)
        return handler(node, statements)

    def go_statement(self, node, statements):
        #print(f"node: {self.read_node_text(node)}")
        #print(f"node: {node.sexp()}")
        expr = self.find_child_by_type(node, "call_expression")
        tmp_return=""
        shadow_name=""
        type_text=""
        args_list=[]
        if expr:
            name = self.find_child_by_field(expr, "function")
            shadow_name = self.parse(name, statements)  
            type_arguments = self.find_child_by_field(expr, "type_arguments")
            if type_arguments:
                type_text = self.read_node_text(type_arguments)[1:-1]
            args = self.find_child_by_field(expr, "arguments")

            if args.named_child_count > 0:
                for child in args.named_children:
                    if self.is_comment(child):
                        continue

                    shadow_variable = self.parse(child, statements)
                    if shadow_variable:
                        args_list.append(shadow_variable)

            tmp_return = self.tmp_variable(statements)
        statements.append({"call_stmt": {"attr":"go", "target": tmp_return, "name": shadow_name, "type_parameters": type_text, "args": args_list}})

    def defer_statement(self, node, statements):
        expr = self.find_child_by_type(node, "call_expression")
        tmp_return=""
        shadow_name=""
        type_text=""
        args_list=[]
        if expr:
            name = self.find_child_by_field(expr, "function")
            shadow_name = self.parse(name, statements)  
            type_arguments = self.find_child_by_field(expr, "type_arguments")
            if type_arguments:
                type_text = self.read_node_text(type_arguments)[1:-1]
            args = self.find_child_by_field(expr, "arguments")

            if args.named_child_count > 0:
                for child in args.named_children:
                    if self.is_comment(child):
                        continue

                    shadow_variable = self.parse(child, statements)
                    if shadow_variable:
                        args_list.append(shadow_variable)

            tmp_return = self.tmp_variable(statements)
        statements.append({"call_stmt": {"attr":"defer", "target": tmp_return, "name": shadow_name, "type_parameters": type_text, "args": args_list}})


    def if_statement(self, node, statements):
        init_part = self.find_child_by_field(node, "initializer")
        init_body = []
        if init_part:
            self.parse(init_part,init_body)
        condition_part = self.find_child_by_field(node, "condition")
        true_part = self.find_child_by_field(node, "consequence")
        false_part = self.find_child_by_field(node, "alternative")

        true_body = []

        shadow_condition = self.parse(condition_part, statements)
        self.parse(true_part, true_body)
        if false_part:
            false_body = []
            self.parse(false_part, false_body)
            statements.append({"if_stmt": {"init_body": init_body,"condition": shadow_condition, "then_body": true_body, "else_body": false_body}})
        else:
            statements.append({"if_stmt": {"init_body": init_body,"condition": shadow_condition, "then_body": true_body}})

    def for_statement(self, node, statements):
        exp = self.find_child_by_type(node, "binary_expression")
        for_clause = self.find_child_by_type(node, "for_clause")
        range_clause = self.find_child_by_type(node, "range_clause")
        for_body = []
        block = self.find_child_by_field(node, "body")
        self.parse(block, for_body)
        if for_clause:
            init = self.find_child_by_field(for_clause, "initializer")
            condition = self.find_child_by_field(for_clause, "condition")
            step = self.find_child_by_field(for_clause, "update")
            init_body = []
            condition_init = []
            step_body = []

            shadow_condition = self.parse(condition, condition_init)
            self.parse(init, init_body)
            self.parse(step, step_body)

            statements.append({"for_stmt":
                                {"init_body": init_body,
                                "condition": shadow_condition,
                                "condition_prebody": condition_init,
                                "update_body": step_body,
                                "body": for_body}})
        elif range_clause:
            left = self.find_child_by_field(range_clause, "left")
            if left:
                for child in left.named_children:
                    child_val=self.parse(child,statements)
            value = self.find_child_by_field(range_clause, "right")
            shadow_value = self.parse(value, statements)

            statements.append({"forin_stmt":
                                {"attr": None,
                                    "data_type": None,
                                    "name": child_val,
                                    "target": shadow_value,
                                    "body": for_body}})
        elif exp:
            condition_init = []
            shadow_condition = self.parse(exp, condition_init)
            statements.append({"for_stmt":
                                {
                                "condition": shadow_condition,
                                "condition_prebody": condition_init,
                                "body": for_body}})
    
    def expression_switch_statement(self, node, statements):
        switch_stmt_list = []
        init = self.find_child_by_field(node, "initializer")
        init_m = []
        self.parse(init,init_m)
        condition = self.find_child_by_field(node, "value")
        shadow_condition2 = self.parse(condition, statements)
        cases = []
        for child in self.find_children_by_type(node, "expression_case"):
            label = child.named_children[0]
            for case_condition in label.named_children:
                shadow_condition = self.parse(case_condition, statements)
                if case_condition != label.named_children[-1]:
                    switch_stmt_list.append({"case_stmt": {"condition": case_condition}})
                else:
                    if child.named_child_count > 1:
                        new_body = []
                        for stat in child.named_children[1:]:
                            shadow_return = self.parse(stat, new_body)
                            # if case_init != []:
                            #     statements.insert(-1, case_init)

                        switch_stmt_list.append({"case_stmt": {"condition": shadow_condition, "body": new_body}})
                    else:
                            # if case_init != []:
                            #     statements.insert(-1, case_init)
                        switch_stmt_list.append({"case_stmt": {"condition": shadow_condition}})
        for child in self.find_children_by_type(node, "default_case"):
            new_body = []
            shadow_return = None
            for child_index in range(child.named_child_count):
                expression_block = child.named_children[child_index]
                shadow_return = self.parse(expression_block, new_body)

            switch_stmt_list.append({"default_stmt": {"body": new_body}})

        statements.append({"switch_stmt": {"init_body":init_m,"condition": shadow_condition2, "body": switch_stmt_list}})

    def type_switch_statement(self, node, statements):
        # print(f"node: {self.read_node_text(node)}")
        # print(f"node: {node.sexp()}")
        gettype_stmt = []
        switch_stmt_list = []
        init = self.find_child_by_field(node, "initializer")
        init_m = []
        self.parse(init,init_m)
        expression_list = self.find_child_by_field(node, "alias")
        ali_m=[]
        for child in expression_list.named_children:
            child_val=self.parse(child,ali_m)
            ali_m.append(f"[{{'assign_stmt': {{'target': '{child_val}'}}}}]")      
        condition = self.find_child_by_field(node, "value")
        shadow_condition2 = self.parse(condition, statements)
        gettype_stmt.append(f"[{{'gettype_stmt': {{'target': '{shadow_condition2}'}}}}]")
        
        for child in self.find_children_by_type(node, "type_case"):
            case_type = self.read_node_text(child.named_children[0])
            case_body = []
            if child.named_child_count > 1:
                for statement_node in child.named_children[1:]:
                    self.parse(statement_node, case_body)
            switch_stmt_list.append({
                "case_stmt": {
                    "condition": case_type,
                    "body": case_body
                }
            })

        for child in self.find_children_by_type(node, "default_case"):
            default_body = []
            for statement_node in child.named_children:
                self.parse(statement_node, default_body)
            switch_stmt_list.append({
                "default_stmt": {
                    "body": default_body
                }
            })

        statements.append({
            "switch_stmt": {
                "init_body":ali_m+init_m,
                "condition": gettype_stmt,
                "body": switch_stmt_list
            }
        })

    def select_statement(self,node,statements):
        switch_stmt_list = []
        
        for child in self.find_children_by_type(node, "communication_case"):
            comm = []
            self.parse(child.named_children[0],comm)
            case_body = []
            if child.named_child_count > 1:
                for statement_node in child.named_children[1:]:
                    self.parse(statement_node, case_body)
            switch_stmt_list.append({
                "case_stmt": {
                    "condition": comm,
                    "body": case_body
                }
            })

        for child in self.find_children_by_type(node, "default_case"):
            default_body = []
            for statement_node in child.named_children:
                self.parse(statement_node, default_body)
            switch_stmt_list.append({
                "default_stmt": {
                    "body": default_body
                }
            })

        statements.append({
            "switch_stmt": {
                "condition": [],
                "body": switch_stmt_list
            }
        })

    def check_statement_handler(self, node):
        STATEMENT_HANDLER_MAP = {
            'expression_statement':self.expression_statement,
            'send_statement':self.send_statement,
            'inc_statement':self.inc_statement,
            'dec_statement':self.dec_statement,
            'assignment_statement':self.assignment_statement,
            'return_statement':self.return_statement,

            "go_statement"          : self.go_statement,
            "defer_statement"         : self.defer_statement,
            "if_statement"          : self.if_statement,
            "for_statement"          : self.for_statement,
            "expression_switch_statement"          : self.expression_switch_statement,
            "type_switch_statement"          : self.type_switch_statement,
            "select_statement"          : self.select_statement,
            #"empty_labeled_statement"    :self.empty_labeled_statement,
            "labeled_statement"          :self.label_statement,
            "fallthrough_statement"      :self.fallthrough_statement,
            "break_statement"            :self.break_statement,
            "continue_statement"         :self.continue_statement,
            "goto_statement"             :self.goto_statement,
            "block"                      :self.block_statement,
            "empty_statement"            :self.empty_statement,
        }
        return STATEMENT_HANDLER_MAP.get(node.type, None)
    
    def label_statement(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")

        # 检查标签语句是否为空
        if node.named_child_count == 0:
            # 添加空标签语句到语句列表中
            self.empty_labeled_statement(node, statements)
            # statements.append({"empty_label_stmt": {}})
        else:
            # 非空标签语句处理逻辑
            name_node = node.named_children[0]
            shadow_name = self.parse(name_node, statements)
            labeled_statement = {"label_stmt": {"name": shadow_name}}
            # 如果标签语句还有其他子节点（即非空标签语句），继续解析并处理
            if node.named_child_count > 1:
                stmt_node = node.named_children[1]
                self.parse(stmt_node, statements)

            # 添加非空标签语句到语句列表中
            statements.append(labeled_statement)

    def fallthrough_statement(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
    
        #  添加 fallthrough 语句
        statements.append({"fallthrough_stmt": {}})

        # 解析可能存在的其他语句
        if node.named_child_count > 0:
            stmt = node.named_children[0]
            self.parse(stmt, statements)
    
    def break_statement(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
        shadow_name = ""
        if node.named_child_count > 0:
            name = node.named_children[0]
            shadow_name = self.parse(name, statements)

        statements.append({"break_stmt": {"target": shadow_name}})
    
   # def continue_statement(self, node, statements):
    #    print(f"node: {self.read_node_text(node)}")
     #   print(f"node: {node.sexp()}")
      #  shadow_name = ""
       # if node.named_child_count > 0:
        #    name = node.named_children[0]
         #s   shadow_name = self.parse(name, statements)

    def continue_statement(self, node, statements):
        # 打印节点的文本和结构信息，有助于调试和开发
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")

        # 初始化标签名为空字符串
        label_name = ""

        # 检查该节点是否有命名子节点（即标签）
        if node.named_child_count > 0:
            # 提取第一个命名子节点，它应该是标签名
            label_node = node.named_children[0]
            # 解析标签名
            label_name = self.parse(label_node, statements)

            # 添加解析出的标签语句到语句列表中
            statements.append({"type": "continue", "label": label_name})
        else:
            # 如果没有标签，则添加一个无标签的continue语句到列表
            statements.append({"type": "continue", "label": None})

    
    def goto_statement(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
        # 获取标签名
        name = node.named_children[0]
        shadow_name = self.parse(name, statements)

        # 添加到语句列表
        statements.append({"goto_stmt": {"label": shadow_name}})

        # 解析可能存在的其他语句
        if node.named_child_count > 1:
            stmt = node.named_children[1]
            self.parse(stmt, statements)
    
    def empty_statement(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
        
        return
        # 添加空语句
        #statements.append({"empty_stmt": {}})
        
    #def block_statement(self, node, statements):
    #    print(f"node: {self.read_node_text(node)}")
    #    print(f"node: {node.sexp()}")
    #    block_statements = []
    #    for child_node in node.named_children:
    #        self.parse(child_node, block_statements)
    #    # 将 block_statements 添加到 statements 中作为一个语句块
    #    statements.append({"block_stmt": block_statements})
    def block_statement(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")

        # 初始化块内的语句列表
        block_statements = []

        # 处理 block_start (隐式)
        block_statements.append({"block_start": {"stmt_id": id(node), "parent_stmt_id": id(node.parent)}})

        # 遍历块内的命名子节点
        for child_node in node.named_children:
            # 解析每个子节点，并将结果添加到块内的语句列表中
            self.parse(child_node, block_statements)

        # 处理 block_end (隐式)
        block_statements.append({"block_end": {"stmt_id": id(node), "parent_stmt_id": id(node.parent)}})

        # 将完整的块，包括开始和结束，添加到主语句列表
        statements.append({"block": {"body": block_statements}})
    
    def empty_labeled_statement(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
        statements.append({"empty_labeled_stmt": {}})

    def is_statement(self, node):
        # print(node.type)
        # print(dir(node))
        return self.check_statement_handler(node) is not None

    def statement(self, node, statements):
        handler = self.check_statement_handler(node)
        return handler(node, statements)

    def expression_statement(self, node, statements):
        expression = node.named_children[0]
        self.parse(expression, statements)
        return
    
    def send_statement(self, node, statements):
        channel = self.find_child_by_field(node, "channel")
        value = self.find_child_by_field(node, "value")
        shadow_channel = self.parse(channel, statements)
        shadow_value = self.parse(value, statements)
        tmp_variable = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_variable, "operator": '<-', "operand": shadow_channel,
                                           "operand2": shadow_value}})
        return 
    
    def inc_statement(self, node, statements):
        expression = node.named_children[0]
        et=expression.type
        if et=='index_expression':
            array,index=self.parse_array(expression, statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"array_read": {"target": tmp_var, "array": array, "index": index}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '+', "operand": tmp_var,
                                           "operand2": '1'}})
            statements.append({"array_write": {"array": array, "index": index, "source": tmp_var}})
            return
        elif et=='selector_expression':
            target,field=self.parse_field(expression, statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": target, "field": field}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '+', "operand": tmp_var,"operand2": '1'}})
            statements.append({"field_write": {"receiver_object": target, "field": field, "source": tmp_var}})
            return
        elif self.is_star_expression(expression):
            addr=self.parse(expression.child_by_field_name('operand'),statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"mem_read": {"address": addr,"target":tmp_var}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '+', "operand": tmp_var,"operand2": '1'}})
            statements.append({"mem_write": {"address": addr,"source":tmp_var}})
            return
        target=self.parse(expression, statements)
        statements.append({"assign_stmt": {"target": target, "operator": '+', "operand": target,"operand2": '1'}})
        return
    def is_star_expression(self,node):
        return node.type=='unary_expression'  and self.read_node_text(node.child_by_field_name('operator'))=='*'
    def dec_statement(self, node, statements):
        expression = node.named_children[0]
        et=expression.type
        if et=='index_expression':
            array,index=self.parse_array(expression, statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"array_read": {"target": tmp_var, "array": array, "index": index}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '-', "operand": tmp_var,"operand2": '1'}})
            statements.append({"array_write": {"array": array, "index": index, "source": tmp_var}})
            return
        elif et=='selector_expression':
            target,field=self.parse_field(expression, statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"field_read": {"target": tmp_var, "receiver_object": target, "field": field}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '-', "operand": tmp_var,"operand2": '1'}})
            statements.append({"field_write": {"receiver_object": target, "field": field, "source": tmp_var}})
            return
        elif self.is_star_expression(expression):
            addr=self.parse(expression.child_by_field_name('operand'),statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"mem_read": {"address": addr,"target":tmp_var}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '-', "operand": tmp_var,
                                           "operand2": '1'}})
            statements.append({"mem_write": {"address": addr,"source":tmp_var}})
            return
        target=self.parse(expression, statements)
        statements.append({"assign_stmt": {"target": target, "operator": '-', "operand": target,
                                           "operand2": '1'}})
        return

    def assignment_statement(self, node, statements):

        left=self.find_child_by_field(node, "left")#list
        right=self.find_child_by_field(node, "right")
        operator=self.find_child_by_field(node, "operator")
        shadow_operator=self.read_node_text(operator)
        # print("enter assign!")
        if len(shadow_operator)!=1:#complex assignment without expression list size>=2
            cut_operator=shadow_operator[:-1]#remove =
            ex_l=left.named_children[0]
            ex_r=right.named_children[0]
            et=ex_l.type
            if et=='index_expression':
                array,index=self.parse_array(ex_l,statements)
                tmp_var=self.tmp_variable(statements)
                statements.append({"array_read": {"target": tmp_var, "array": array, "index": index}})
                ex_r_v=self.parse(ex_r,statements)
                statements.append({"assign_stmt": {"target": tmp_var, "operator": cut_operator, "operand": tmp_var,
                                           "operand2": ex_r_v}})
                statements.append({"array_write": {"array": array, "index": index, "source": tmp_var}})
                return
            elif et=='selector_expression':
                target,field=self.parse_field(ex_l,statements)
                tmp_var=self.tmp_variable(statements)
                statements.append({"field_read": {"target": tmp_var, "receiver_object": target, "field": field}})
                ex_r_v=self.parse(ex_r,statements)
                statements.append({"assign_stmt": {"target": tmp_var, "operator": cut_operator, "operand": tmp_var,
                                           "operand2": ex_r_v}})
                statements.append({"field_write": {"receiver_object": target, "field": field, "source": tmp_var}})
                return
            elif self.is_star_expression(ex_l):
                addr=self.parse(ex_l.child_by_field_name('operand'),statements)
                tmp_var=self.tmp_variable(statements)
                statements.append({"mem_read": {"address": addr,"target":tmp_var}})
                ex_r_v=self.parse(ex_r,statements)
                statements.append({"assign_stmt": {"target": tmp_var, "operator": cut_operator, "operand": tmp_var,
                                           "operand2": ex_r_v}})
                statements.append({"mem_write": {"address": addr,"source":tmp_var}})
                return
            ex_l_v=self.parse(ex_l,statements)
            # print(ex_r.text)
            ex_r_v=self.parse(ex_r,statements)
            statements.append({"assign_stmt": {"target": ex_l_v, "operator": cut_operator, "operand": ex_l_v,
                                           "operand2": ex_r_v}})
            # print(shadow_operator," 1=1")
        else:#list assign
            left_list=left.named_children#expressions
            right_list=right.named_children#expressions
            # print(len(right_list),right_list[0].type)
            if len(right_list)==1 and right_list[0].type=='call_expression':#expand call return
                ret_arr=self.parse(right_list[0],statements)
                i=0
                for child in left_list:
                    tmp_var=self.tmp_variable(statements)
                    statements.append({"array_read": {"target": tmp_var, "array": ret_arr, "index": str(i)}})
                    i+=1
                    if child.type=='index_expression':
                        array,index=self.parse_array(child,statements)
                        statements.append({"array_write": {"array": array, "index": index, "source": tmp_var}})
                        continue
                    elif child.type=='selector_expression':
                        target,field=self.parse_field(child,statements)
                        statements.append({"field_write": {"receiver_object": target, "field": field, "source": tmp_var}})
                        continue
                    elif self.is_star_expression(child):
                        addr=self.parse(child.child_by_field_name('operand'),statements)
                        statements.append({"mem_write": {"address": addr,"source":tmp_var}})
                        continue
                    shadow_left=self.parse(child,statements)
                    statements.append({"assign_stmt": {"target": shadow_left, "operand":
                                                        tmp_var}})
                return
            #else list assign list,checks the len(left_list)==len(right_list),otherwise error occurs however shouldn't be judged in this procedure?
            if(len(left_list)!=len(right_list)):
                return
            for i in range(len(right_list)):
                left_exp=left_list[i]
                val=self.parse(right_list[i],statements)
                if left_exp.type=='index_expression':
                        array,index=self.parse_array(left_exp,statements)
                        statements.append({"array_write": {"array": array, "index": index, "source": val}})
                        continue
                elif left_exp.type=='selector_expression':
                        target,field=self.parse_field(left_exp,statements)
                        statements.append({"field_write": {"receiver_object": target, "field": field, "source": val}})
                        continue
                elif self.is_star_expression(left_exp):
                        addr=self.parse(left_exp.child_by_field_name('operand'),statements)
                        statements.append({"mem_write": {"address": addr,"source":val}})
                        continue
                shadow_left=self.parse(left_exp,statements)
                statements.append({"assign_stmt": {"target": shadow_left, "operand":
                                                        val}})
            return
        return

    def return_statement(self, node, statements):
        expression_list=self.find_child_by_type(node,'expression_list')
        if expression_list is None:
            statements.append({"return_stmt": {"target": None}})
            return 
        ret_var=self.tmp_variable(statements)
        # list_count=expression_list.named_child_count
        statements.append({"new_array":{"target":ret_var,"attr":None,"data_type":None}})
        index=0
        for child in expression_list.named_children:
            child_val=self.parse(child,statements)
            statements.append({"array_write":{"array":ret_var,"index":str(index),"source":child_val}})
            index+=1
        statements.append({"return_stmt": {"target": ret_var}})
        return 
