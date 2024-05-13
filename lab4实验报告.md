# 编译第四次实验实验报告
## 小组成员及分工
- 张佳和：_statement中以下部分的解析以及对应测试用例、测试程序的编写
    ```js
        $._declaration,
        $._simple_statement,
        $.return_statement,
    ```
    其中_declaration中type_declaration留作下次完成，解析了以下部分
    ```js
        $.const_declaration,
        $.var_declaration,
    ```
    其中_simple_statement包括以下部分
    ```js
        $.expression_statement,
        $.send_statement,
        $.inc_statement,
        $.dec_statement,
        $.assignment_statement,
        $.short_var_declaration,
    ```
    此外补充了`$.composite_literal`的解析
- 郑仁哲：_statement中以下部分的解析以及对应测试用例、测试程序的编写
    ```js
        $.labeled_statement,
        $.fallthrough_statement,
        $.break_statement,
        $.continue_statement,
        $.goto_statement,
        $.block,
        $.empty_statement,
    ```
- 宋岱桉：_statement中以下部分的解析以及对应测试用例、测试程序的编写
    ```js
        $.go_statement,
        $.defer_statement,
        $.if_statement,
        $.for_statement,
        $.expression_switch_statement,
        $.type_switch_statement,
        $.select_statement,
    ```
## 实验思路及核心代码
1. 分工
2. 有过上次实验的经验，这次解析起来得心应手，有疑点的话就与其他组讨论或咨询助教、老师。
3. 张佳和部分
   1. `return_statement`注册在statement_handler下，调用对应名称函数进行parse。基本处理是没有expression_list子节点时返回一个空target，有expression_list子节点时将其中每个expression解析后的值加到一个新建的数组返回值中。即new_array、array_write和return_stmt结合。代码如下
   ```py
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
            statements.append({"array_write":{"array":ret_var,"index":index,"source":child_val}})
            index+=1
        statements.append({"return_stmt": {"target": ret_var}})
        return 
    ```
    2. `expression_statement`也注册在expression_statement中，调用对应名称函数进行parse。这个比较简单，就是把子节点expression解析掉就行。代码如下
    ```py
        def expression_statement(self, node, statements):
        expression = node.named_children[0]
        self.parse(expression, statements)
        return
    ```
    3. `send_statement`注册在expression_statement中，调用对应名称函数进行parse。把子节点channel和field域分别解析后，利用assign_stmt的灵活的operator实现<-操作符的解析。代码如下
    ```py
        def send_statement(self, node, statements):
        channel = self.find_child_by_field(node, "channel")
        value = self.find_child_by_field(node, "value")
        shadow_channel = self.parse(channel, statements)
        shadow_value = self.parse(value, statements)
        tmp_variable = self.tmp_variable(statements)
        statements.append({"assign_stmt": {"target": tmp_variable, "operator": '<-', "operand": shadow_channel,
                                           "operand2": shadow_value}})
        return 
    ```
    4. `inc_statement`和`dec_statement`类似，注册在`expression_statement`中，调用对应名称函数进行parse。以`inc_statement`为例（`dec_statement`十分雷同，就不介绍了），首先inc_statement节点只有一个有名节点expression，取出来。分别对expression的type进行分类处理：1.为index_expression，即array/map类型，统一使用parse_array得到array与index,隐式parse了这两个节点，如何用array_read读出array[index]的值赋给临时变量tmp_var，再用assign_stmt给tmp_var自增1，最后用array_write将tmp_var写回到array[index]中；2.为selector_expression,即域表达式，与上面类似，不同的是用field_read读，用field_write写回；3.为unary_expression中的*表达式，即指针解引用读写，专门写了一个`is_star_expression`函数协助判断，与上面过程类似，不同的是调用mem_read和mem_write进行读写；4.其他情况，直接assign_stmt target=target+1即可。代码如下，包括辅助函数`is_star_expression`:
    ```py
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
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '+', "operand": tmp_var,
                                           "operand2": '1'}})
            statements.append({"field_write": {"receiver_object": target, "field": field, "source": tmp_var}})
            return
        elif self.is_star_expression(expression):
            addr=self.parse(expression.child_by_field_name('operand'),statements)
            tmp_var=self.tmp_variable(statements)
            statements.append({"mem_read": {"address": addr,"target":tmp_var}})
            statements.append({"assign_stmt": {"target": tmp_var, "operator": '+', "operand": tmp_var,
                                           "operand2": '1'}})
            statements.append({"mem_write": {"address": addr,"source":tmp_var}})
            return
        target=self.parse(expression, statements)
        statements.append({"assign_stmt": {"target": target, "operator": '+', "operand": target,
                                           "operand2": '1'}})
        return
    def is_star_expression(self,node):
        return node.type=='unary_expression'  and self.read_node_text(node.child_by_field_name('operator'))=='*'
    ```
    5. `assignment_statement`注册在`expression_statement`中，调用对应名称函数进行parse。首先分两种情况讨论，即复合赋值还是简单赋值。复合赋值operator长度>2，此时go语言左右边只能有一个被赋值的变量，根据左边表达式类型为`index_expression`还是`selector_expression`还是解引用或其他来分类讨论，如何parse右边表达式，用复合赋值运算符去除`=`号后进行assign_stmt,当然，前三种情况需要额外用对应read、write语句和临时变量协助，和`inc_statement`类似，不再赘述。简单赋值同样要考虑两种子情况：右边表达式是一个函数调用的解包还是表达式列表，解包的话把右边函数调用先解析得到返回值，返回值作为数组read后按四种情况assign/write给左边；表达式列表则按对应顺序一一按四种情况把右边assign/write给左边对应表达式。代码十分长，就不放出来了。
    6. `short_var_declaration`、`const_declaration`和`var_declaration`注册在declaration_handler中，处理过程类似，不同处如attr不同，分别为[]、['const']、['var]；初始化与类型声明的要求不同，如short_var_declaration就不需要类型声明，而const、var对初始化的要求也有细微差别，但总体处理是类似的。以下以`const_declaration`为例说明。首先`const_declaration`可能包含多个`const_spec`即变量声明语句，就获取所有const_spec，遍历处理。对每个const_spec,尝试获取其下name、type、value域对应的节点，用解析好的shadow_type和shadow_names进行变量声明variable_decl，如果有value结点则分别用array_read分解包或assign_stmt分解表达式列表进行初始化赋值。代码如下：
    ```py
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
    ```
    7.`composite_literal`部分利用new_instance进行声明，首先对于type分泛型类和其他类处理，泛型类分出泛型参数列表和基类。然后字面量右边的值分为literal_elements和keyed_elements进行处理，前者parse完作为args一部分赋给new_instance语句，后者根据type类型选择用field_write、map_write、array_write来进行处理。其中匿名类的处理暂时跳过。代码如下：
    ```py
     def composite_literal(self,node,statements,replacement):
        type_node=node.child_by_field_name('type')
        shadow_type=self.read_node_text(type_node)
        nt=type_node.type
        body_node=node.child_by_field_name('body')#literal_value
        literal_elements=self.find_children_by_type(body_node,'literal_element')
        keyed_elments=self.find_children_by_type(body_node,'keyed_element')
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
            shadow_type=self.read_node_text(bt)
            tp=type_node.child_by_field_name('type_arguments').named_children
            for child in tp:
                if child.type==',':
                    continue
                type_parameters.append(self.read_node_text(child))
        for child in literal_elements:
            n=child.named_children[0]#ex or literal
            v=self.parse(n,statements)
            args.append(v)
        for child in keyed_elments:
            key=child.named_children[0]#literal_element
            value=child.named_children[1]
            keyv=key.named_children[0]#ex or lit
            valuev=value.named_children[0]
            t_key=self.parse(keyv,init)
            t_value=self.parse(valuev,init)
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
    ```
4. 郑仁哲部分
    1. `label_statement`此方法处理带标签的语句。首先打印节点的文本和结构信息以便于调试。接着，根据是否有子节点来确定处理方式：如果没有子节点，则调用self.empty_labeled_statement方法处理空标签语句；如果有子节点，解析第一个子节点作为标签名，并将结果存储在labeled_statement字典中。如果有更多子节点，表示标签后面跟着具体的语句，继续调用self.parse解析这些语句。最终，将包含标签名的字典加入到statements列表。
    ```py
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
    ```
    2. `fallthrough_statement`在Go中，fallthrough用于switch语句中，以指示继续执行下一个case的代码。
    ```py
    def fallthrough_statement(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
    
        #  添加 fallthrough 语句
        statements.append({"fallthrough_stmt": {}})

        # 解析可能存在的其他语句
        if node.named_child_count > 0:
            stmt = node.named_children[0]
            self.parse(stmt, statements)
    ```
    3. `break_statement`处理break语句，可能会指定一个跳出的目标标签。如果存在命名子节点，则解析这些子节点以获取目标标签，并将其作为break_stmt的一部分添加到statements。这里需要注意的是shadow_name的定义在所有相关分支中均有效。
    ```py
    def break_statement(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
        shadow_name = ""
        if node.named_child_count > 0:
            name = node.named_children[0]
            shadow_name = self.parse(name, statements)

        statements.append({"break_stmt": {"target": shadow_name}})
    ```
    4. `continue_statement`类似于break语句的处理方式，这里解析continue语句，可能带有一个标签。打印节点信息后，检查是否有子节点。如果有，解析这些节点获取标签名，并添加到statements。
    ```py
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
    ```
    5. `goto_statement`处理goto语句，必须解析后面跟随的标签名。首先打印节点信息，然后解析标签名并添加到statements。如果还有更多子节点，继续解析这些节点。这种方法确保了goto语句后的所有相关逻辑都被正确处理。
    ```py
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
    ```  
    6. `empty_statement`空语句处理十分直接，只需将一个代表空语句的字典添加到statements。在Go语言中，空语句主要用于占位，不执行任何操作。
    ```py
    def empty_statement(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
        # 添加空语句
        #statements.append({"empty_stmt": {}})
    ```
    7.`block`处理由花括号定义的代码块。首先打印节点信息，然后遍历所有子节点，解析这些节点并收集结果到一个临时列表block_statements，最后将这个列表作为一个整体添加到statements。这种处理方式支持嵌套的代码块。
    ```py
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
    
    ```
    8.另外处理空标签情况
5. 宋岱桉部分
   1. go_statement从给定节点对象中找到调用表达式，解析调用表达式中的函数名，并将其存储在变量 shadow_name 中。然后解析调用表达式中的类型参数（type_arguments），如果有的话，并将其存储在变量 type_text 中，再解析调用表达式中的参数，并将每个参数的值存储在列表 args_list 中。go存在attr中。
   ```py
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
    ```
    2. 处理 defer 语句,首先从给定的节点对象中查找调用表达式（call_expression）。然后，解析调用表达式中的函数名，并将其存储在变量 shadow_name 中。接着，如果调用表达式中存在类型参数（type_arguments），则将其解析并存储在变量 type_text 中。之后，解析调用表达式中的参数，并将每个参数的值存储在列表 args_list 中。同时，还生成一个临时变量名，用于存储 defer 语句的返回值，并将其存储在变量 tmp_return 中。
    3. if 语句。首先查找节点对象中的条件部分，然后解析条件部分的内容，并将其存储在变量 shadow_condition 中。然后查找节点对象中的真实部分（即条件成立时执行的部分），并将其解析为一个语句列表 true_body。将另一部分解析为另一个语句列表 false_body。最后，根据条件是否有假设部分，将一个包含 if 语句信息的字典添加到语句列表中。
    4. for 循环语句。首先查找节点对象中的条件部分，然后根据条件部分的类型分别处理不同的情况。
       - 如果存在 for_clause，则表示使用的是经典的 for 循环形式。在这种情况下，解析初始化器（initializer）、条件（condition）和更新（update）部分，然后将它们存储在相应的变量中，并解析循环体（body），最后将一个包含 for 循环信息的字典添加到语句列表中。
       - 如果存在 range_clause，则表示使用的是 range 形式的 for 循环。在这种情况下，解析 range 子句的左值（left）和右值（right），然后将左值解析为循环变量名（name），右值解析为遍历的数据源（target），最后将一个包含 for-in 循环信息的字典添加到语句列表中。
       - 如果以上两种情况都不存在，则表示使用的是基于表达式的 for 循环形式。在这种情况下，解析条件表达式，并将其存储在变量中，并解析循环体，最后将一个包含 for 循环信息的字典添加到语句列表中。
    5. 处理表达式 switch 语句。首先查找节点对象中的初始化器（initializer）和条件部分（value），然后解析它们的内容。接着，遍历所有的表达式 case 和默认 case，对每一个 case 进行解析，并将解析结果存储在一个列表中。
        1. 解析初始化器并将其存储在变量 init_m 中。
        2. 解析条件部分，并将其存储在变量 shadow_condition2 中。
        3. 遍历所有的表达式 case：
            - 对于每个 case，解析其条件部分，并将解析结果存储在变量 shadow_condition 中。
            - 如果该 case 不是最后一个条件部分，将其条件部分添加到 switch_stmt_list 中作为一个单独的 case。
            - 如果该 case 后面有语句块，则解析其语句块，并将解析结果存储在变量 new_body 中，然后将条件部分和语句块一起添加到 switch_stmt_list 中。
        4. 遍历所有的默认 case：
            - 对于每个默认 case，解析其中的语句块，并将解析结果存储在变量 new_body 中，然后将其添加到 switch_stmt_list 中作为一个默认 case。
        5. 最后，将一个包含 switch 语句信息的字典添加到语句列表中，该字典包括初始化器、条件部分和所有 case 的信息。
    6. 处理type_switch 语句的函数。
        1. 首先查找节点对象中的初始化器（initializer）、条件部分（value）和类型别名（alias），然后解析它们的内容。
        2. 构建两个列表：gettype_stmt 和 switch_stmt_list。
           - gettype_stmt 用于存储获取类型的语句
           - switch_stmt_list 则用于存储类型 case 和默认 case 的信息。
        3. 对于类型别名部分，遍历所有的别名，将每个别名解析为相应的变量，并将其添加到 ali_m 列表中作为赋值语句。同时，将获取类型的语句添加到 gettype_stmt 列表中。
        4. 遍历所有的类型 case 和默认 case：对于每个类型 case，解析其类型条件和语句块，并将其添加到 switch_stmt_list 中。对于默认 case，解析其中的语句块，并将其添加到 switch_stmt_list 中。
        5. 将一个包含 switch 语句信息的字典添加到语句列表中，该字典包括初始化器、获取类型的语句和所有 case 的信息。
     7. 处理select 语句。遍历节点对象中的所有通信 case 和默认 case，并将它们解析为相应的字典形式，然后将这些字典添加到 switch_stmt_list 中。具体来说：对于每个通信 case，解析通信操作（communication），并将其存储在变量 comm 中。然后解析该 case 的语句块，并将其存储在变量 case_body 中。最后，将包含通信操作和语句块的字典添加到 switch_stmt_list 中。对于默认 case，解析其中的语句块，并将其存储在变量 default_body 中。然后，将包含默认 case 语句块的字典添加到 switch_stmt_list 中。最后，将一个包含 select 语句信息的字典添加到语句列表中，该字典包括空的条件列表和所有 case 的信息。
## 测试用例与结果
1. 张佳和部分
    1. 针对return语句，测试用例为return.go,如下
    ```go
    func (a ,b int)int,int{
	return a,b
    }(1,2)
    ```
    测试结果如下
    ```
    [{'method_decl': {'attr': [],
                  'data_type': 'int',
                  'name': '%m0',
                  'parameters': [{'parameter_decl': {'name': 'b',
                                                     'data_type': 'int',
                                                     'modifiers': []}},
                                 {'parameter_decl': {'name': 'a',
                                                     'data_type': 'int',
                                                     'modifiers': []}}],
                  'body': [{'new_array': {'target': '%v0',
                                          'attr': None,
                                          'data_type': None}},
                           {'array_write': {'array': '%v0',
                                            'index': '0',
                                            'source': 'a'}},
                           {'array_write': {'array': '%v0',
                                            'index': '1',
                                            'source': 'b'}},
                           {'return_stmt': {'target': '%v0'}}],
                  'init': [],
                  'type_parameters': []}},
    {'call_stmt': {'target': '%v0',
                'name': '%m0',
                'type_parameters': '',
                'args': ['1', '2']}}]
    ```
    2. 针对所有_simple_statement,编写simple_statements.go，如下：
    ```go
        a+b+c-123.2
        a++
        c<-144
        vv--
        v+=v
        l%=g+fs
        bzfb^=a+b*c
        a,b,c=1,2,3
        a1,a2,a3[2]=f(v,b,z)
        ag[1],as.vz,*bh=ks()
        agb:=ma["ghafh"]
        aba[gdhs]--
        *b++ 
    ```
    测试结果如下：
    ```
    [{'assign_stmt': {'target': '%v0',
                      'operator': '+',
                      'operand': 'a',
                      'operand2': 'b'}},
     {'assign_stmt': {'target': '%v1',
                      'operator': '+',
                      'operand': '%v0',
                      'operand2': 'c'}},
     {'assign_stmt': {'target': '%v2',
                      'operator': '-',
                      'operand': '%v1',
                      'operand2': '123.2'}},
     {'assign_stmt': {'target': 'a',
                      'operator': '+',
                      'operand': 'a',
                      'operand2': '1'}},
     {'assign_stmt': {'target': '%v3',
                      'operator': '<-',
                      'operand': 'c',
                      'operand2': '144'}},
     {'assign_stmt': {'target': 'vv',
                      'operator': '-',
                      'operand': 'vv',
                      'operand2': '1'}},
     {'assign_stmt': {'target': 'v',
                      'operator': '+',
                      'operand': 'v',
                      'operand2': 'v'}},
     {'assign_stmt': {'target': '%v4',
                      'operator': '+',
                      'operand': 'g',
                      'operand2': 'fs'}},
     {'assign_stmt': {'target': 'l',
                      'operator': '%',
                      'operand': 'l',
                      'operand2': '%v4'}},
     {'assign_stmt': {'target': '%v5',
                      'operator': '*',
                      'operand': 'b',
                      'operand2': 'c'}},
     {'assign_stmt': {'target': '%v6',
                      'operator': '+',
                      'operand': 'a',
                      'operand2': '%v5'}},
     {'assign_stmt': {'target': 'bzfb',
                      'operator': '^',
                      'operand': 'bzfb',
                      'operand2': '%v6'}},
     {'assign_stmt': {'target': 'a', 'operand': '1'}},
     {'assign_stmt': {'target': 'b', 'operand': '2'}},
     {'assign_stmt': {'target': 'c', 'operand': '3'}},
     {'call_stmt': {'target': '%v7',
                    'name': 'f',
                    'type_parameters': '',
                    'args': ['v', 'b', 'z']}},
     {'array_read': {'target': '%v8', 'array': '%v7', 'index': '0'}},
     {'assign_stmt': {'target': 'a1', 'operand': '%v8'}},
     {'array_read': {'target': '%v9', 'array': '%v7', 'index': '1'}},
     {'assign_stmt': {'target': 'a2', 'operand': '%v9'}},
     {'array_read': {'target': '%v10', 'array': '%v7', 'index': '2'}},
     {'array_write': {'array': 'a3', 'index': '2', 'source': '%v10'}},
     {'call_stmt': {'target': '%v11',
                    'name': 'ks',
                    'type_parameters': '',
                    'args': []}},
     {'array_read': {'target': '%v12', 'array': '%v11', 'index': '0'}},
     {'array_write': {'array': 'ag', 'index': '1', 'source': '%v12'}},
     {'array_read': {'target': '%v13', 'array': '%v11', 'index': '1'}},
     {'field_write': {'receiver_object': 'as', 'field': 'vz', 'source': '%v13'}},
     {'array_read': {'target': '%v14', 'array': '%v11', 'index': '2'}},
     {'mem_write': {'address': 'bh', 'source': '%v14'}},
     {'variable_decl': {'name': 'agb', 'data_type': None, 'attr': ['var']}},
     {'array_read': {'target': '%v15', 'array': 'ma', 'index': '"ghafh"'}},
     {'assign_stmt': {'target': 'agb', 'operand': '%v15'}},
     {'array_read': {'target': '%v16', 'array': 'aba', 'index': 'gdhs'}},
     {'assign_stmt': {'target': '%v16',
                      'operator': '-',
                      'operand': '%v16',
                      'operand2': '1'}},
     {'array_write': {'array': 'aba', 'index': 'gdhs', 'source': '%v16'}},
     {'mem_read': {'address': 'b', 'target': '%v17'}},
     {'assign_stmt': {'target': '%v17',
                      'operator': '+',
                      'operand': '%v17',
                      'operand2': '1'}},
     {'mem_write': {'address': 'b', 'source': '%v17'}}]
    ```    
    3. 针对三种declaration和composite_literal,编写cv_declaration.go，如下：
    ```go
    const Pi = 3.14159
    const MaxUint = ^uint(0)
    const MinInt = -1 << 31	
    // 变量声明
    var name string = "John"
    var age int = 30
    var isAdult bool = true

    // 多变量声明
    var x, y, z int
    var a, b, c string

    // 复杂类型声明
    var point Point = Point{X: 10, Y: 20}
    var person Person = Person{Name: "John", Age: 30}
    var student Student = Student{Person: Person{Name: "John", Age: 30}, Grade: 90}

    // 复杂类型初始化
    var point = Point{X: 10, Y: 20}
    var person = Person{Name: "John", Age: 30}
    var student = Student{Person: Person{Name: "John", Age: 30}, Grade: 90}
    // 1. 直接赋值
    var name string = "John"
    var age int = 30
    var isAdult bool = true

    // 2. 使用关键字 `new`
    var point *Point = new(Point)
    var person *Person = new(Person)

    // 3. 使用类型推断
    var x = 10
    var y = 3.14
    var z = "Hello"

    // 4. 使用匿名结构体
    // var point = struct {
    //   X int
    //   Y int
    // }{X: 10, Y: 20}

    // 5. 使用匿名函数
    var f = func(x int) int {
      return x * x
    }
    var arr [10]int // 声明一个长度为 10 的整型数组
    var arr2 [5]string // 声明一个长度为 5 的字符串数组
    arr := [3]int{1, 2, 3} // 初始化一个长度为 3 的整型数组，元素为 1, 2, 3
    arr3 := [...]int{4, 5, 6, 7, 8} // 初始化一个长度为 5 的整型数组，元素为 4, 5, 6, 7, 8
    var slice []int // 声明一个空的整型切片
    var slice2 []string // 声明一个空的字符串切片
    slice := []int{1, 2, 3} // 初始化一个长度为 3 的整型切片，元素为 1, 2, 3
    slice3 := make([]string, 5) // 初始化一个长度为 5 的字符串切片，元素为 ""
    var m map[string]int // 声明一个字符串到整型的映射
    var m2 map[int]string // 声明一个整型到字符串的映射
    m := map[string]int{"a": 1, "b": 2} // 初始化一个字符串到整型的映射，键值对为 {"a": 1, "b": 2}
    m3 := make(map[int]string) // 初始化一个整型到字符串的映射，为空
    var ch chan int // 声明一个无缓冲的整型通道
    var ch2 chan string // 声明一个无缓冲的字符串通道
    ch := make(chan int) // 初始化一个无缓冲的整型通道
    ch3 := make(chan string, 10) // 初始化一个缓冲为 10 的字符串通道
    ```
    测试结果如下：
    ```
    [{'variable_decl': {'name': 'Pi', 'data_type': None, 'attr': ['const']}},
     {'assign_stmt': {'target': 'Pi', 'operand': '3.14159'}},
     {'variable_decl': {'name': 'MaxUint', 'data_type': None, 'attr': ['const']}},
     {'call_stmt': {'target': '%v0',
                    'name': 'uint',
                    'type_parameters': '',
                    'args': ['0']}},
     {'assign_stmt': {'target': '%v1', 'operator': '^', 'operand': '%v0'}},
     {'assign_stmt': {'target': 'MaxUint', 'operand': '%v1'}},
     {'variable_decl': {'name': 'MinInt', 'data_type': None, 'attr': ['const']}},
     {'assign_stmt': {'target': '%v2', 'operator': '-', 'operand': '1'}},
     {'assign_stmt': {'target': '%v3',
                      'operator': '<<',
                      'operand': '%v2',
                      'operand2': '31'}},
     {'assign_stmt': {'target': 'MinInt', 'operand': '%v3'}},
     {'variable_decl': {'name': 'name', 'data_type': 'string', 'attr': ['var']}},
     {'assign_stmt': {'target': 'name', 'operand': '"John"'}},
     {'variable_decl': {'name': 'age', 'data_type': 'int', 'attr': ['var']}},
     {'assign_stmt': {'target': 'age', 'operand': '30'}},
     {'variable_decl': {'name': 'isAdult', 'data_type': 'bool', 'attr': ['var']}},
     {'assign_stmt': {'target': 'isAdult', 'operand': 'true'}},
     {'variable_decl': {'name': 'x', 'data_type': 'int', 'attr': ['var']}},
     {'variable_decl': {'name': 'y', 'data_type': 'int', 'attr': ['var']}},
     {'variable_decl': {'name': 'z', 'data_type': 'int', 'attr': ['var']}},
     {'variable_decl': {'name': 'a', 'data_type': 'string', 'attr': ['var']}},
     {'variable_decl': {'name': 'b', 'data_type': 'string', 'attr': ['var']}},
     {'variable_decl': {'name': 'c', 'data_type': 'string', 'attr': ['var']}},
     {'variable_decl': {'name': 'point', 'data_type': 'Point', 'attr': ['var']}},
     {'new_instance': {'target': '%v4',
                       'type_parameters': [],
                       'data_type': 'Point',
                       'args': [],
                       'init': [{'field_write': {'receiver_object': '@this',
                                                 'field': 'X',
                                                 'source': '10'}},
                                {'field_write': {'receiver_object': '@this',
                                                 'field': 'Y',
                                                 'source': '20'}}],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'point', 'operand': '%v4'}},
     {'variable_decl': {'name': 'person', 'data_type': 'Person', 'attr': ['var']}},
     {'new_instance': {'target': '%v5',
                       'type_parameters': [],
                       'data_type': 'Person',
                       'args': [],
                       'init': [{'field_write': {'receiver_object': '@this',
                                                 'field': 'Name',
                                                 'source': '"John"'}},
                                {'field_write': {'receiver_object': '@this',
                                                 'field': 'Age',
                                                 'source': '30'}}],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'person', 'operand': '%v5'}},
     {'variable_decl': {'name': 'student',
                        'data_type': 'Student',
                        'attr': ['var']}},
     {'new_instance': {'target': '%v6',
                       'type_parameters': [],
                       'data_type': 'Student',
                       'args': [],
                       'init': [{'new_instance': {'target': '%v0',
                                                  'type_parameters': [],
                                                  'data_type': 'Person',
                                                  'args': [],
                                                  'init': [{'field_write': {'receiver_object': '@this',
                                                                            'field': 'Name',
                                                                            'source': '"John"'}},
                                                           {'field_write': {'receiver_object': '@this',
                                                                            'field': 'Age',
                                                                            'source': '30'}}],
                                                  'fields': [],
                                                  'methods': [],
                                                  'nested': []}},
                                {'field_write': {'receiver_object': '@this',
                                                 'field': 'Person',
                                                 'source': '%v0'}},
                                {'field_write': {'receiver_object': '@this',
                                                 'field': 'Grade',
                                                 'source': '90'}}],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'student', 'operand': '%v6'}},
     {'variable_decl': {'name': 'point', 'data_type': None, 'attr': ['var']}},
     {'new_instance': {'target': '%v7',
                       'type_parameters': [],
                       'data_type': 'Point',
                       'args': [],
                       'init': [{'field_write': {'receiver_object': '@this',
                                                 'field': 'X',
                                                 'source': '10'}},
                                {'field_write': {'receiver_object': '@this',
                                                 'field': 'Y',
                                                 'source': '20'}}],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'point', 'operand': '%v7'}},
     {'variable_decl': {'name': 'person', 'data_type': None, 'attr': ['var']}},
     {'new_instance': {'target': '%v8',
                       'type_parameters': [],
                       'data_type': 'Person',
                       'args': [],
                       'init': [{'field_write': {'receiver_object': '@this',
                                                 'field': 'Name',
                                                 'source': '"John"'}},
                                {'field_write': {'receiver_object': '@this',
                                                 'field': 'Age',
                                                 'source': '30'}}],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'person', 'operand': '%v8'}},
     {'variable_decl': {'name': 'student', 'data_type': None, 'attr': ['var']}},
     {'new_instance': {'target': '%v9',
                       'type_parameters': [],
                       'data_type': 'Student',
                       'args': [],
                       'init': [{'new_instance': {'target': '%v0',
                                                  'type_parameters': [],
                                                  'data_type': 'Person',
                                                  'args': [],
                                                  'init': [{'field_write': {'receiver_object': '@this',
                                                                            'field': 'Name',
                                                                            'source': '"John"'}},
                                                           {'field_write': {'receiver_object': '@this',
                                                                            'field': 'Age',
                                                                            'source': '30'}}],
                                                  'fields': [],
                                                  'methods': [],
                                                  'nested': []}},
                                {'field_write': {'receiver_object': '@this',
                                                 'field': 'Person',
                                                 'source': '%v0'}},
                                {'field_write': {'receiver_object': '@this',
                                                 'field': 'Grade',
                                                 'source': '90'}}],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'student', 'operand': '%v9'}},
     {'variable_decl': {'name': 'name', 'data_type': 'string', 'attr': ['var']}},
     {'assign_stmt': {'target': 'name', 'operand': '"John"'}},
     {'variable_decl': {'name': 'age', 'data_type': 'int', 'attr': ['var']}},
     {'assign_stmt': {'target': 'age', 'operand': '30'}},
     {'variable_decl': {'name': 'isAdult', 'data_type': 'bool', 'attr': ['var']}},
     {'assign_stmt': {'target': 'isAdult', 'operand': 'true'}},
     {'variable_decl': {'name': 'point', 'data_type': '*Point', 'attr': ['var']}},
     {'call_stmt': {'target': '%v10',
                    'name': 'new',
                    'type_parameters': '',
                    'args': []}},
     {'array_read': {'target': 'point', 'array': '%v10', 'index': '0'}},
     {'variable_decl': {'name': 'person', 'data_type': '*Person', 'attr': ['var']}},
     {'call_stmt': {'target': '%v11',
                    'name': 'new',
                    'type_parameters': '',
                    'args': []}},
     {'array_read': {'target': 'person', 'array': '%v11', 'index': '0'}},
     {'variable_decl': {'name': 'x', 'data_type': None, 'attr': ['var']}},
     {'assign_stmt': {'target': 'x', 'operand': '10'}},
     {'variable_decl': {'name': 'y', 'data_type': None, 'attr': ['var']}},
     {'assign_stmt': {'target': 'y', 'operand': '3.14'}},
     {'variable_decl': {'name': 'z', 'data_type': None, 'attr': ['var']}},
     {'assign_stmt': {'target': 'z', 'operand': '"Hello"'}},
     {'variable_decl': {'name': 'f', 'data_type': None, 'attr': ['var']}},
     {'method_decl': {'attr': [],
                      'data_type': 'int',
                      'name': '%m0',
                      'parameters': [{'parameter_decl': {'name': 'x',
                                                         'data_type': 'int',
                                                         'modifiers': []}}],
                      'body': [{'new_array': {'target': '%v0',
                                              'attr': None,
                                              'data_type': None}},
                               {'assign_stmt': {'target': '%v1',
                                                'operator': '*',
                                                'operand': 'x',
                                                'operand2': 'x'}},
                               {'array_write': {'array': '%v0',
                                                'index': '0',
                                                'source': '%v1'}},
                               {'return_stmt': {'target': '%v0'}}],
                      'init': [],
                      'type_parameters': []}},
     {'assign_stmt': {'target': 'f', 'operand': '%m0'}},
     {'variable_decl': {'name': 'arr', 'data_type': '[10]int', 'attr': ['var']}},
     {'variable_decl': {'name': 'arr2', 'data_type': '[5]string', 'attr': ['var']}},
     {'variable_decl': {'name': 'arr', 'data_type': None, 'attr': ['var']}},
     {'new_instance': {'target': '%v12',
                       'type_parameters': [],
                       'data_type': '[3]int',
                       'args': ['1', '2', '3'],
                       'init': [],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'arr', 'operand': '%v12'}},
     {'variable_decl': {'name': 'arr3', 'data_type': None, 'attr': ['var']}},
     {'new_instance': {'target': '%v13',
                       'type_parameters': [],
                       'data_type': '[...]int',
                       'args': ['4', '5', '6', '7', '8'],
                       'init': [],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'arr3', 'operand': '%v13'}},
     {'variable_decl': {'name': 'slice', 'data_type': '[]int', 'attr': ['var']}},
     {'variable_decl': {'name': 'slice2',
                        'data_type': '[]string',
                        'attr': ['var']}},
     {'variable_decl': {'name': 'slice', 'data_type': None, 'attr': ['var']}},
     {'new_instance': {'target': '%v14',
                       'type_parameters': [],
                       'data_type': '[]int',
                       'args': ['1', '2', '3'],
                       'init': [],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'slice', 'operand': '%v14'}},
     {'call_stmt': {'target': '%v15',
                    'name': 'make',
                    'type_parameters': '',
                    'args': ['5']}},
     {'variable_decl': {'name': 'slice3', 'data_type': None, 'attr': ['var']}},
     {'array_read': {'target': 'slice3', 'array': '%v15', 'index': '0'}},
     {'variable_decl': {'name': 'm',
                        'data_type': 'map[string]int',
                        'attr': ['var']}},
     {'variable_decl': {'name': 'm2',
                        'data_type': 'map[int]string',
                        'attr': ['var']}},
     {'variable_decl': {'name': 'm', 'data_type': None, 'attr': ['var']}},
     {'new_instance': {'target': '%v16',
                       'type_parameters': [],
                       'data_type': 'map[string]int',
                       'args': [],
                       'init': [{'map_write': {'target': '@this',
                                               'key': '"a"',
                                               'value': '1'}},
                                {'map_write': {'target': '@this',
                                               'key': '"b"',
                                               'value': '2'}}],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'm', 'operand': '%v16'}},
     {'call_stmt': {'target': '%v17',
                    'name': 'make',
                    'type_parameters': '',
                    'args': []}},
     {'variable_decl': {'name': 'm3', 'data_type': None, 'attr': ['var']}},
     {'array_read': {'target': 'm3', 'array': '%v17', 'index': '0'}},
     {'variable_decl': {'name': 'ch', 'data_type': 'chan int', 'attr': ['var']}},
     {'variable_decl': {'name': 'ch2',
                        'data_type': 'chan string',
                        'attr': ['var']}},
     {'call_stmt': {'target': '%v18',
                    'name': 'make',
                    'type_parameters': '',
                    'args': []}},
     {'variable_decl': {'name': 'ch', 'data_type': None, 'attr': ['var']}},
     {'array_read': {'target': 'ch', 'array': '%v18', 'index': '0'}},
     {'call_stmt': {'target': '%v19',
                    'name': 'make',
                    'type_parameters': '',
                    'args': ['10']}},
     {'variable_decl': {'name': 'ch3', 'data_type': None, 'attr': ['var']}},
     {'array_read': {'target': 'ch3', 'array': '%v19', 'index': '0'}}]
     ```
2. 郑仁哲部分
    1. 针对break和fallthrough语句，测试用例如下：
    ```go
      switch i := 2; i {
    case 2:
        fmt.Println("Two")
        fallthrough
    case 3:
        fmt.Println("Three")
        break
      }
   for i := 0; i < 10; i++ {
        if i > 5 {
            break
        }
        fmt.Println(i)
   }
    ```
    测试结果：
    ```
   [{'variable_decl': {'name': 'i', 'data_type': None, 'attr': ['var']}},
   {'assign_stmt': {'target': 'i', 'operand': '2'}},
   {'field_read': {'target': '%v0',
                 'receiver_object': 'fmt',
                 'field': 'Println'}},
   {'call_stmt': {'target': '%v1',
                'name': '%v0',
                'type_parameters': '',
                'args': ['"Two"']}},
   {'fallthrough_stmt': {}},
   {'field_read': {'target': '%v2',
                 'receiver_object': 'fmt',
                 'field': 'Println'}},
   {'call_stmt': {'target': '%v3',
                'name': '%v2',
                'type_parameters': '',
                'args': ['"Three"']}},
   {'break_stmt': {'target': ''}},
   {'variable_decl': {'name': 'i', 'data_type': None, 'attr': ['var']}},
   {'assign_stmt': {'target': 'i', 'operand': '0'}},
   {'assign_stmt': {'target': '%v4',
                  'operator': '<',
                  'operand': 'i',
                  'operand2': '10'}},
   {'assign_stmt': {'target': 'i',
                  'operator': '+',
                  'operand': 'i',
                  'operand2': '1'}},
   {'block': {'body': [{'block_start': {'stmt_id': 140395298227056,
                                      'parent_stmt_id': 140395298227568}},
                     {'assign_stmt': {'target': '%v0',
                                      'operator': '>',
                                      'operand': 'i',
                                      'operand2': '5'}},
                     {'if_stmt': {'condition': '%v0',
                                  'then_body': [{'block': {'body': [{'block_start': {'stmt_id': 140395298229296,
                                                                                     'parent_stmt_id': 140395298229488}},
                                                                    {'break_stmt': {'target': ''}},
                                                                    {'block_end': {'stmt_id': 140395298229296,
                                                                                   'parent_stmt_id': 140395298230448}}]}}]}},
                     {'field_read': {'target': '%v1',
                                     'receiver_object': 'fmt',
                                     'field': 'Println'}},
                     {'call_stmt': {'target': '%v2',
                                    'name': '%v1',
                                    'type_parameters': '',
                                    'args': ['i']}},
                     {'block_end': {'stmt_id': 140395298227056,
                                    'parent_stmt_id': 140395298229360}}]}}]
   [{'operation': 'variable_decl',
   'stmt_id': 1,
   'name': 'i',
   'data_type': None,
   'attr': "['var']"},
   {'operation': 'assign_stmt', 'stmt_id': 2, 'target': 'i', 'operand': '2'},
   {'operation': 'field_read',
   'stmt_id': 3,
   'target': '%v0',
   'receiver_object': 'fmt',
   'field': 'Println'},
   {'operation': 'call_stmt',
   'stmt_id': 4,
   'target': '%v1',
   'name': '%v0',
   'type_parameters': '',
   'args': '[\'"Two"\']'},
   { 'operation': 'fallthrough_stmt', 'stmt_id': 5},
   {'operation': 'field_read',
   'stmt_id': 6,
   'target': '%v2',
   'receiver_object': 'fmt',
   'field': 'Println'},
   {'operation': 'call_stmt',
   'stmt_id': 7,
   'target': '%v3',
   'name': '%v2',
   'type_parameters': '',
   'args': '[\'"Three"\']'},
   {'operation': 'break_stmt', 'stmt_id': 8, 'target': ''},
   {'operation': 'variable_decl',
    'stmt_id': 9,
   'name': 'i',
   'data_type': None,
   'attr': "['var']"},
   {'operation': 'assign_stmt', 'stmt_id': 10, 'target': 'i', 'operand': '0'},
   {'operation': 'assign_stmt',
   'stmt_id': 11,
   'target': '%v4',
   'operator': '<',
   'operand': 'i',
   'operand2': '10'},
   {'operation': 'assign_stmt',
   'stmt_id': 12,
   'target': 'i',
   'operator': '+',
   'operand': 'i',
   'operand2': '1'},
   {'operation': 'block', 'stmt_id': 13, 'body': 14},
   {'operation': 'block_start', 'stmt_id': 14, 'parent_stmt_id': 13},
   {'operation': 'block_start',
   'stmt_id': 140395298227056,
   'parent_stmt_id': 140395298227568},
   {'operation': 'assign_stmt',
   'stmt_id': 16,
   'target': '%v0',
   'operator': '>',
   'operand': 'i',
   'operand2': '5'},
   {'operation': 'if_stmt', 'stmt_id': 17, 'condition': '%v0', 'then_body': 18},
   {'operation': 'block_start', 'stmt_id': 18, 'parent_stmt_id': 17},
   {'operation': 'block', 'stmt_id': 19, 'body': 20},
   {'operation': 'block_start', 'stmt_id': 20, 'parent_stmt_id': 19},
   {'operation': 'block_start',
   'stmt_id': 140395298229296,
   'parent_stmt_id': 140395298229488},
   {'operation': 'break_stmt', 'stmt_id': 22, 'target': ''},
   {'operation': 'block_end',
   'stmt_id': 140395298229296,
   'parent_stmt_id': 140395298230448},
   { 'operation': 'block_end', 'stmt_id': 20, 'parent_stmt_id': 19},
   {'operation': 'block_end', 'stmt_id': 18, 'parent_stmt_id': 17},
   {'operation': 'field_read',
   'stmt_id': 24,
   'target': '%v1',
   'receiver_object': 'fmt',
   'field': 'Println'},
   {'operation': 'call_stmt',
   'stmt_id': 25,
   'target': '%v2',
   'name': '%v1',
   'type_parameters': '',
   'args': "['i']"},
   {'operation': 'block_end',
   'stmt_id': 140395298227056,
   'parent_stmt_id': 140395298229360},
   {'operation': 'block_end', 'stmt_id': 14, 'parent_stmt_id': 13}]
    ```
    2.针对continue/labeled/goto/block/empty的测试样例如下：
    ```go
        OuterLoop:
    for i := 0; i < 5; i++ {
        for j := 0; j < 5; j++ {
            if j == 2 {
                continue OuterLoop 
            }
            fmt.Printf("i = %d, j = %d\n", i, j)
        }
    }

    
    {
        fmt.Println("This is a block statement")
    }

    
    ; 

    
    fmt.Println("Before goto")
    goto Skip
    fmt.Println("This will not be executed")
    Skip:
    fmt.Println("After goto")

    BlockLabel:
    {
        fmt.Println("This is a labeled block")
        goto BlockLabel 
    }

    ```
    测试结果：
    ```
   [{'variable_decl': {'name': 'i', 'data_type': None, 'attr': ['var']}},
   {'assign_stmt': {'target': 'i', 'operand': '0'}},
   {'assign_stmt': {'target': '%v0',
                  'operator': '<',
                  'operand': 'i',
                  'operand2': '5'}},
   {'assign_stmt': {'target': 'i',
                  'operator': '+',
                  'operand': 'i',
                  'operand2': '1'}},
   {'block': {'body': [{'block_start': {'stmt_id': 140456256330352,
                                      'parent_stmt_id': 140456256344432}},
                     {'variable_decl': {'name': 'j',
                                        'data_type': None,
                                        'attr': ['var']}},
                     {'assign_stmt': {'target': 'j', 'operand': '0'}},
                     {'assign_stmt': {'target': '%v0',
                                      'operator': '<',
                                      'operand': 'j',
                                      'operand2': '5'}},
                     {'assign_stmt': {'target': 'j',
                                      'operator': '+',
                                      'operand': 'j',
                                      'operand2': '1'}},
                     {'block': {'body': [{'block_start': {'stmt_id': 140456256345072,
                                                          'parent_stmt_id': 140456256345712}},
                                         {'assign_stmt': {'target': '%v0',
                                                          'operator': '==',
                                                          'operand': 'j',
                                                          'operand2': '2'}},
                                         {'if_stmt': {'condition': '%v0',
                                                      'then_body': [{'block': {'body': [{'block_start': {'stmt_id': 140456256347568,
                                                                                                         'parent_stmt_id': 140456256347760}},       
                                                                                        {'type': 'continue',
                                                                                         'label': None},
                                                                                        {'block_end': {'stmt_id': 140456256347568,
                                                                                                       'parent_stmt_id': 140456256361392}}]}}]}},   
                                         {'field_read': {'target': '%v1',
                                                         'receiver_object': 'fmt',
                                                         'field': 'Printf'}},
                                         {'call_stmt': {'target': '%v2',
                                                        'name': '%v1',
                                                        'type_parameters': '',
                                                        'args': ['"i = %d, j = '
                                                                 '%d\\n"',
                                                                 'i', 'j']}},
                                         {'block_end': {'stmt_id': 140456256345072,
                                                        'parent_stmt_id': 140456256347696}}]}},
                     {'block_end': {'stmt_id': 140456256330352,
                                    'parent_stmt_id': 140456256361520}}]}},
   {'label_stmt': {'name': None}},
   {'block': {'body': [{'block_start': {'stmt_id': 140456256328944,
                                       'parent_stmt_id': 140456256362224}},
                     {'field_read': {'target': '%v0',
                                     'receiver_object': 'fmt',
                                     'field': 'Println'}},
                     {'call_stmt': {'target': '%v1',
                                    'name': '%v0',
                                    'type_parameters': '',
                                    'args': ['"This is a block statement"']}},
                     {'block_end': {'stmt_id': 140456256328944,
                                    'parent_stmt_id': 140456256363376}}]}},
   {'field_read': {'target': '%v1',
                 'receiver_object': 'fmt',
                 'field': 'Println'}},
   {'call_stmt': {'target': '%v2',
                'name': '%v1',
                'type_parameters': '',
                'args': ['"Before goto"']}},
   {'goto_stmt': {'label': None}},
   {'field_read': {'target': '%v3',
                 'receiver_object': 'fmt',
                 'field': 'Println'}},
   {'call_stmt': {'target': '%v4',
                'name': '%v3',
                'type_parameters': '',
                'args': ['"This will not be executed"']}},
   {'field_read': {'target': '%v5',
                 'receiver_object': 'fmt',
                 'field': 'Println'}},
   {'call_stmt': {'target': '%v6',
                'name': '%v5',
                'type_parameters': '',
                'args': ['"After goto"']}},
   {'label_stmt': {'name': None}},
   {'block': {'body': [{'block_start': {'stmt_id': 140456256374704,
                                      'parent_stmt_id': 140456256374832}},
                     {'field_read': {'target': '%v0',
                                     'receiver_object': 'fmt',
                                     'field': 'Println'}},
                     {'call_stmt': {'target': '%v1',
                                    'name': '%v0',
                                    'type_parameters': '',
                                    'args': ['"This is a labeled block"']}},
                     {'goto_stmt': {'label': None}},
                     {'block_end': {'stmt_id': 140456256374704,
                                    'parent_stmt_id': 140456256378096}}]}},
   {'label_stmt': {'name': None}}]
   [{'operation': 'variable_decl',
   'stmt_id': 1,
   'name': 'i',
   'data_type': None,
   'attr': "['var']"},
   {'operation': 'assign_stmt', 'stmt_id': 2, 'target': 'i', 'operand': '0'},
   {'operation': 'assign_stmt',
   'stmt_id': 3,
   'target': '%v0',
   'operator': '<',
   'operand': 'i',
   'operand2': '5'},
   {'operation': 'assign_stmt',
   'stmt_id': 4,
   'target': 'i',
   'operator': '+',
   'operand': 'i',
   'operand2': '1'},
   {'operation': 'block', 'stmt_id': 5, 'body': 6},
   {'operation': 'block_start', 'stmt_id': 6, 'parent_stmt_id': 5},
   {'operation': 'block_start',
   'stmt_id': 140456256330352,
   'parent_stmt_id': 140456256344432},
    { 'operation': 'variable_decl',
   'stmt_id': 8,
   'name': 'j',
   'data_type': None,
   'attr': "['var']"},
   {'operation': 'assign_stmt', 'stmt_id': 9, 'target': 'j', 'operand': '0'},
   {'operation': 'assign_stmt',
   'stmt_id': 10,
   'target': '%v0',
   'operator': '<',
   'operand': 'j',
   'operand2': '5'},
   {'operation': 'assign_stmt',
   'stmt_id': 11,
   'target': 'j',
   'operator': '+',
   'operand': 'j',
   'operand2': '1'},
   {'operation': 'block', 'stmt_id': 12, 'body': 13},
   {'operation': 'block_start', 'stmt_id': 13, 'parent_stmt_id': 12},
   {'operation': 'block_start',
    'stmt_id': 140456256345072,
   'parent_stmt_id': 140456256345712},
   { 'operation': 'assign_stmt',
   'stmt_id': 15,
   'target': '%v0',
   'operator': '==',
   'operand': 'j',
   ' operand2': '2'},
   {'operation': 'if_stmt', 'stmt_id': 16, 'condition': '%v0', 'then_body': 17},
   {'operation': 'block_start', 'stmt_id': 17, 'parent_stmt_id': 16},
   {'operation': 'block', 'stmt_id': 18, 'body': 19},
   {'operation': 'block_start', 'stmt_id': 19, 'parent_stmt_id': 18},
   {'operation': 'block_start',
    'stmt_id': 140456256347568,
    'parent_stmt_id': 140456256347760},
   {'operation': 'type', 'stmt_id': 21},
   {'operation': 'block_end',
    'stmt_id': 140456256347568,
     'parent_stmt_id': 140456256361392},
    {'operation': 'block_end', 'stmt_id': 19, 'parent_stmt_id': 18},
   {'operation': 'block_end', 'stmt_id': 17, 'parent_stmt_id': 16},
   {'operation': 'field_read',
   'stmt_id': 23,
   'target': '%v1',
   'receiver_object': 'fmt',
   'field': 'Printf'},
   {'operation': 'call_stmt',
   'stmt_id': 24,
   'target': '%v2',
   'name': '%v1',
   'type_parameters': '',
   'args': '[\'"i = %d, j = %d\\\\n"\', \'i\', \'j\']'},
   {'operation': 'block_end',
   'stmt_id': 140456256345072,
   'parent_stmt_id': 140456256347696},
   {'operation': 'block_end', 'stmt_id': 13, 'parent_stmt_id': 12},
   {'operation': 'block_end',
   'stmt_id': 140456256330352,
   'parent_stmt_id': 140456256361520},
   {'operation': 'block_end', 'stmt_id': 6, 'parent_stmt_id': 5},
   {'operation': 'label_stmt', 'stmt_id': 27, 'name': None},
   {'operation': 'block', 'stmt_id': 28, 'body': 29},
   {'operation': 'block_start', 'stmt_id': 29, 'parent_stmt_id': 28},
   {'operation': 'block_start',
   'stmt_id': 140456256328944,
   'parent_stmt_id': 140456256362224},
   {'operation': 'field_read',
   'stmt_id': 31,
   'target': '%v0',
   'receiver_object': 'fmt',
   'field': 'Println'},
   {'operation': 'call_stmt',
   'stmt_id': 32,
   'target': '%v1',
   'name': '%v0',
   'type_parameters': '',
   'args': '[\'"This is a block statement"\']'},
   {'operation': 'block_end',
   'stmt_id': 140456256328944,
   'parent_stmt_id': 140456256363376},
   {'operation': 'block_end', 'stmt_id': 29, 'parent_stmt_id': 28},
   {'operation': 'field_read',
   'stmt_id': 34,
   'target': '%v1',
   'receiver_object': 'fmt',
    'field': 'Println'},
   {'operation': 'call_stmt',
   'stmt_id': 35,
   'target': '%v2',
   'name': '%v1',
   'type_parameters': '',
   'args': '[\'"Before goto"\']'},
   {'operation': 'goto_stmt', 'stmt_id': 36, 'label': None},
   {'operation': 'field_read',
   'stmt_id': 37,
   'target': '%v3',
   'receiver_object': 'fmt',
   'field': 'Println'},
   {'operation': 'call_stmt',
   'stmt_id': 38,
   'target': '%v4',
   'name': '%v3',
   'type_parameters': '',
   'args': '[\'"This will not be executed"\']'},
   {'operation': 'field_read',
   'stmt_id': 39,
   'target': '%v5',
   'receiver_object': 'fmt',
   'field': 'Println'},
   {'operation': 'call_stmt',
   'stmt_id': 40,
   'target': '%v6',
   'name': '%v5',
   'type_parameters': '',
   'args': '[\'"After goto"\']'},
   {'operation': 'label_stmt', 'stmt_id': 41, 'name': None},
   {'operation': 'block', 'stmt_id': 42, 'body': 43},
   {'operation': 'block_start', 'stmt_id': 43, 'parent_stmt_id': 42},
   {'operation': 'block_start',
   'stmt_id': 140456256374704,
   'parent_stmt_id': 140456256374832},
   {'operation': 'field_read',
   'stmt_id': 45,
   'target': '%v0',
   'receiver_object': 'fmt',
   'field': 'Println'},
   {'operation': 'call_stmt',
   'stmt_id': 46,
   'target': '%v1',
   'name': '%v0',
   'type_parameters': '',
   'args': '[\'"This is a labeled block"\']'},
   {'operation': 'goto_stmt', 'stmt_id': 47, 'label': None},
   {'operation': 'block_end',
   'stmt_id': 140456256374704,
    'parent_stmt_id': 140456256378096},
   {'operation': 'block_end', 'stmt_id': 43, 'parent_stmt_id': 42},
   {'operation': 'label_stmt', 'stmt_id': 49, 'name': None}]
    ```
3. 宋岱桉部分：
   1. go:
   ```go
        go myFunction(a)
    ```
        {'call_stmt': {'attr': 'go',
                'target': '%v0',
                'name': 'myFunction',
                'type_parameters': '',
                'args': ['a']}}
   2. defer:
   ```go
        defer cleanup()
    ```
        {'call_stmt': {'attr': 'defer',
                'target': '%v1',
                'name': 'cleanup',
                'type_parameters': '',
                'args': []}},
   3. if:
   ```go
        if x > 10 {
            fmt.Println("x is greater than 10")
        } else {
            fmt.Println("x is less than or equal to 10")
        }
    ```
        {'assign_stmt': {'target': '%v2',
                  'operator': '>',
                  'operand': 'x',
                  'operand2': '10'}},
        {'if_stmt': {'condition': '%v2',
              'then_body': [{'field_read': {'target': '%v0',
                                            'receiver_object': 'fmt',
                                            'field': 'Println'}},
                            {'call_stmt': {'target': '%v1',
                                           'name': '%v0',
                                           'type_parameters': '',
                                           'args': ['"x is greater than '
                                                    '10"']}}],
              'else_body': [{'field_read': {'target': '%v0',
                                            'receiver_object': 'fmt',
                                            'field': 'Println'}},
                            {'call_stmt': {'target': '%v1',
                                           'name': '%v0',
                                           'type_parameters': '',
                                           'args': ['"x is less than or equal '
                                                    'to 10"']}}]}},
   4. for:
   ```go
        for i := 0; i < 5; i++ { fmt.Println(i) }
        for i < 5 {
            fmt.Println(i)
            i++
        }
        for value := range numbers {
            fmt.Printf(value)
        }
    ```
        {'for_stmt': {'init_body': [{'variable_decl': {'name': 'i',
                                                'data_type': None,
                                                'attr': ['var']}},
                             {'assign_stmt': {'target': 'i', 'operand': '0'}}],
               'condition': '%v0',
               'condition_prebody': [{'assign_stmt': {'target': '%v0',
                                                      'operator': '<',
                                                      'operand': 'i',
                                                      'operand2': '5'}}],
               'update_body': [{'assign_stmt': {'target': 'i',
                                                'operator': '+',
                                                'operand': 'i',
                                                'operand2': '1'}}],
               'body': [{'field_read': {'target': '%v0',
                                        'receiver_object': 'fmt',
                                        'field': 'Println'}},
                        {'call_stmt': {'target': '%v1',
                                       'name': '%v0',
                                       'type_parameters': '',
                                       'args': ['i']}}]}},
        {'for_stmt': {'condition': '%v0',
               'condition_prebody': [{'assign_stmt': {'target': '%v0',
                                                      'operator': '<',
                                                      'operand': 'i',
                                                      'operand2': '5'}}],
               'body': [{'field_read': {'target': '%v0',
                                        'receiver_object': 'fmt',
                                        'field': 'Println'}},
                        {'call_stmt': {'target': '%v1',
                                       'name': '%v0',
                                       'type_parameters': '',
                                       'args': ['i']}},
                        {'assign_stmt': {'target': 'i',
                                         'operator': '+',
                                         'operand': 'i',
                                         'operand2': '1'}}]}},
        {'forin_stmt': {'attr': None,
                 'data_type': None,
                 'name': 'value',
                 'target': 'numbers',
                 'body': [{'field_read': {'target': '%v0',
                                          'receiver_object': 'fmt',
                                          'field': 'Printf'}},
                          {'call_stmt': {'target': '%v1',
                                         'name': '%v0',
                                         'type_parameters': '',
                                         'args': ['value']}}]}},


    5. switch:
   ```go
        switch x := 2;x {
        case 1:
            a=1
            break
        case 2:
            a=2
        default:
            a=3
            a=4
        }
    ```
        {'switch_stmt': {'init_body': [{'variable_decl': {'name': 'x',
                                                   'data_type': None,
                                                   'attr': ['var']}},
                                {'assign_stmt': {'target': 'x',
                                                 'operand': '2'}}],
                  'condition': 'x',
                  'body': [{'case_stmt': {'condition': '1',
                                          'body': [{'assign_stmt': {'target': 'a',
                                                                    'operand': '1'}}]}},
                           {'case_stmt': {'condition': '2',
                                          'body': [{'assign_stmt': {'target': 'a',
                                                                    'operand': '2'}}]}},
                           {'default_stmt': {'body': [{'assign_stmt': {'target': 'a',
                                                                       'operand': '3'}},
                                                      {'assign_stmt': {'target': 'a',
                                                                       'operand': '4'}}]}}]}}
    6. type_switch
   ```go
   switch i:=1;x:=i.(type) {
    case int:
        a=1
    case string:
        a=2
    default:
        a=3
    }
    ```
    [{'switch_stmt': {'init_body': ["[{'assign_stmt': {'target': 'x'}}]",
                                {'variable_decl': {'name': 'i',
                                                   'data_type': None,
                                                   'attr': ['var']}},
                                {'assign_stmt': {'target': 'i',
                                                 'operand': '1'}}],
                  'condition': ["[{'gettype_stmt': {'target': 'i'}}]"],
                  'body': [{'case_stmt': {'condition': 'int',
                                          'body': [{'assign_stmt': {'target': 'a',
                                                                    'operand': '1'}}]}},
                           {'case_stmt': {'condition': 'string',
                                          'body': [{'assign_stmt': {'target': 'a',
                                                                    'operand': '2'}}]}},
                           {'default_stmt': {'body': [{'assign_stmt': {'target': 'a',
                                                                       'operand': '3'}}]}}]}}]
    7. select
   ```go
   select {
    case msg1 := <-channel1:
        a=1
    case msg2 := <-channel2:
        a=2
    default:
        a=3
    }
    ```
        [{'switch_stmt': {'condition': [],
                  'body': [{'case_stmt': {'condition': [{'assign_stmt': {'target': '%v0',
                                                                         'operator': '<-',
                                                                         'operand': 'channel1'}}],
                                          'body': [{'assign_stmt': {'target': 'a',
                                                                    'operand': '1'}}]}},
                           {'case_stmt': {'condition': [{'assign_stmt': {'target': '%v0',
                                                                         'operator': '<-',
                                                                         'operand': 'channel2'}}],
                                          'body': [{'assign_stmt': {'target': 'a',
                                                                    'operand': '2'}}]}},
                           {'default_stmt': {'body': [{'assign_stmt': {'target': 'a',
                                                                       'operand': '3'}}]}}]}}]