# 编译第五次实验实验报告
## 小组成员及分工
- 张佳和:
  stmt_handlers中`analyze_break_stmt`,`analyze_continue_stmt`,`analyze_label_stmt`,以及`analyze_for_stmt`的重写（改变原来不对的地方，并增加break\[label\]、continue\[label\]的处理）,编写continue.go、break.go测试用例来测试以上完成内容，修改test_cfg使得测试程序能测试以上用例。
- 宋岱桉：
    stmt_handlers中`analyze_for_stmt`基础版的书写以及`analyze_forin_stmt`（包含break\[label\]、continue\[label\]的处理）,编写for.go、forin.go测试用例来测试以上完成内容，修改test_cfg使得测试程序能测试以上用例。
- 郑仁哲：
    stmt_handers中`method_decl`和`return`的书写，添加`goto_stmt`的语句分析函数，编写return.go,method_decl.go,goto.go的测试用例，更新对应test_cfg使得测试程序运行。   
## 实验思路及核心代码
1. 张佳和部分：
    1. `analyze_break_stmt`,`analyze_continue_stmt`原本打算直接处理，后来发现很难确定Label的下一句，改为将这两个加到global_special中，由for_stmt或forin_stmt来处理。返回[],-1是因为后面的代码执行不到（经讨论，忽略label+被goto的情况）代码如下：
    ```py
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
    ```
    2. `analyze_label_stmt`部分，由于可能label+loop_stmt结构，为了方便比对当前loop是否在某个label下，创建数据结构`specialBind`作为label_stmt+next_stmt的集合体。label_stmt不仅要构造specialBind存在global_special中，因为顺序执行，还要返回本身使得与下文加边。同时，可能label_stmt可能是前面一个goto_stmt的目标点，需遍历global_special来将这些goto_stmt处理掉。
    ```py
    class specialBind():
        def __init__(self,stmt,next):
            self.stmt=stmt#label_stmt
            self.next_stmt=next
        def match(self,label):#便于比较label匹配
            return self.stmt.name==label
        def label_for(self,for_stmt):#便于比较是否对应当前loop_stmt
            return self.next_stmt.stmt_id==for_stmt.stmt_id
        def __str__(self):#用于debug
            return 'current:'+str(self.stmt.operation)+' next:'+(str(self.next_stmt.operation) if self.next_stmt is not None else '')
        def __repr__(self) -> str:#debug
            return str(self)
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
    ``` 
    3. `analyze_for_stmt`部分。首先编写了一个`link_parent_stmts_to_current_stmt_with_type`函数，用于将parents_stmts中未有明确类型的边以type类型加到current_stmt中，在FOR_CONDITION这种类型时要用。代码如下：
    ```py
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
    ```
    其次，analyze_for_stmt代码如下。思路是首先提取出global_special_stmts中的break和continue，因为这两个肯定是上一级block中传进来的，不能作用于当前loop，为避免纠缠，使用global_special_stmts_without_outer_bc作为当前loop_stmt的special_stmts，其中会有来自子块的break或continue。然后将parent_stmt连接到init,init连到condition_prebody,condition_prebody以CONDITION类型连到for本身，for本身LOOP_TREUE连到body,body连到update，update连到condition;LOOP_FALSE加入previous返回。最后处理global_special_stmts_without_outer_bc中与当前loop对应的continue和break并在加完边后从该列表中删去，把剩下的global_special_stmts_without_outer_bc中global_special_stmts中没有的元素加到global_special_stmts中，即更新global_special_stmts。各种特殊情况均在代码中处理，代码有相应注释。labelBind为与当前for_stmt匹配的label语句集合，用来后面处理continue/break+label的情况。break若匹配到本loop，则作为previous的一员返回，continue则依次尝试连到update、condition、for_stmt。最后boundary由boundary_of_multi_blocks获取，当这些block均为空时boundary为for_stmt本身的_index。返回previous,boundary。
    ```py
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
    ```

2. 宋岱桉部分：
    1. `analyze_for_stmt`
   已在上文中阐述，不再赘述。
    2. `analyze_forin_stmt`部分，与for内容相当，主要区别是处理的块不同。首先，从全局特殊语句列表中抽取“break”和“continue”语句，因为这两个语句可能会影响当前的循环，因此需要单独处理。同时，为了避免外部循环的“break”和“continue”语句影响当前循环，创建一个不包含外部“break”和“continue”的全局特殊语句列表。然后处理循环初始化部分（init），将父语句连接到初始化部分。如果有初始化代码块存在，则将其分析为控制流图，并将其最后的语句与父语句连接起来。将初始化部分与循环条件部分（for-in）连接，使得控制流从初始化到循环条件。处理循环体部分（body），将其分析为控制流图，并将其最后的语句与当前循环语句连接起来。将全局特殊语句列表中与当前循环相关的“break”和“continue”语句进行处理。如果遇到匹配当前循环的“break”语句，则添加到前驱节点列表中；如果遇到匹配当前循环的“continue”语句，则尝试连接到循环的更新部分、条件部分或循环本身。将剩余的全局特殊语句（即不与当前循环相关的语句）添加到全局特殊语句列表中。最后，确定边界，即该循环控制流图的边界。如果初始化和循环体均不存在，则边界为当前循环语句本身的索引。
    ```py
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
        ```
3. 郑仁哲部分：
    1. `analyze_return_stmt`部分，首先，函数通过 link_parent_stmts_to_current_stmt 方法将 return 语句与其父语句连接起来，确保控制流的连续性。随后，通过调用 get_return_value 方法获取 return 语句可能存在的返回值。如果存在返回值，函数将调用 analyze_expression 方法来分析这个返回值表达式，确保任何与返回值相关的依赖或操作都被考虑。此外，函数在控制流图中添加一条特殊的结束边，将 return 语句连接到方法的逻辑结束节点，这通常表示方法的结束。这个结束节点是用一个特殊的 CFG 节点表示的，这里假设为 exit_node。为了支持外部分析，return 语句还会被添加到全局的特殊语句列表 global_special_stmts 中。最后，由于 return 语句表示方法的退出点，函数返回一个空列表和结束标记，表示没有后续的执行路径。这样的处理确保了 return 语句在控制流图中正确表示，同时也支持对方法退出逻辑的精确分析。
       ```python
        def analyze_return_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        # 链接父节点到当前的 return 语句
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        # 处理 return 语句可能携带的返回值
        return_value = current_stmt.get_return_value()  # 假设 get_return_value 方法能获取 return 语句的返回值信息
        if return_value is not None:
            # 分析返回值表达式
            self.analyze_expression(return_value, current_stmt, global_special_stmts)
        # 在 CFG 中添加一个特殊的结束边，将当前 return 语句链接到方法的逻辑结束节点 
        exit_node = CFGNode(-1, ControlFlowKind.NORMAL_EXIT)  # 假设 -1 是方法结束的标准标记
        self.cfg.add_edge(current_stmt, exit_node, ControlFlowKind.NORMAL_EXIT)
        # 将 return 语句添加到 global_special_stmts 以支持外部分析
        global_special_stmts.append(current_stmt)
        # Return 语句执行后不应再有其他执行语句，返回一个空列表和结束标记
        return ([], -1)
       ```
    2. `analyze_method_decl_stmt`部分：首先，该函数通过 link_parent_stmts_to_current_stmt 方法将当前方法声明与其父语句连接起来，以保持执行流的完整性。接着，它将当前的方法声明添加到全局特殊语句列表 global_special_stmts 中，这一步骤对于处理方法内部的跳转语句尤为关键。随后，函数尝试读取并分析方法体内的所有语句。这包括对方法体的逐个语句调用 analyze_block 函数进行深入分析，以构建方法内部的详细控制流图。分析完方法体后，该函数还处理方法结束后的跳转和标签，确保例如 return 或 goto 语句能正确链接到方法声明的控制流中。最终，它会生成一个包含方法体最后语句的列表和方法体之后第一个语句的索引，并将这些信息返回，以供进一步的调用和处理。
    ```python 
   def analyze_method_decl_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        # 链接父语句到当前方法声明语句
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        # 添加当前方法声明到特殊全局语句列表，用于处理内部跳转
        global_special_stmts.append(current_stmt)
        # 方法体的开始点
        method_body_id = current_stmt.body
        method_body = self.read_block(current_block, method_body_id) if not util.isna(method_body_id) else []
        # 初始化方法体内最后的语句列表
        last_stmts_of_method_body = [CFGNode(current_stmt, ControlFlowKind.METHOD_ENTRY)]
        # 分析方法体内的所有语句
        if method_body:
            last_stmts_of_method_body = self.analyze_block(method_body, last_stmts_of_method_body, global_special_stmts)
        # 处理方法结束后的跳转和标签
        if last_stmts_of_method_body:
            for stmt in last_stmts_of_method_body:
                if isinstance(stmt, CFGNode) and stmt.stmt.operation == "return_stmt":
                    self.cfg.add_edge(stmt.stmt, current_stmt, ControlFlowKind.NORMAL_EXIT)
                elif isinstance(stmt, CFGNode) and stmt.stmt.operation == "goto_stmt":
                    if stmt.stmt.target == current_stmt.name:  # 如果goto指向方法的开头
                        self.cfg.add_edge(stmt.stmt, current_stmt, stmt.edge)
        # 方法结束节点，这里认为是方法体之后的第一个语句
        next_index = current_stmt._index + 1
        next_stmt = current_block.access(next_index) if next_index < len(current_block) else None
        newBind = specialBind(current_stmt, next_stmt)
        global_special_stmts.append(newBind)
        # 返回方法体最后的语句和新的索引，以及连接新的绑定
        return (last_stmts_of_method_body, next_index - 1)
    ```
    3. `analyze_goto_stmt`部分，首先，函数通过 link_parent_stmts_to_current_stmt 方法将 goto 语句与其父语句连接起来，以保持控制流的连续性。然后，函数检查全局的特殊语句列表 global_special_stmts 中是否已经存在一个与 goto 语句的目标标签匹配的标签声明。如果找到这样的标签，函数将在控制流图中添加一条边，从 goto 语句指向该标签，表示控制流的跳转。如果在 global_special_stmts 中未找到匹配的标签，这意味着标签可能在后续的代码中定义，因此将 goto 语句添加到 global_special_stmts 中，以便未来处理。这样的处理确保了在当前分析阶段未能解析的 goto 语句可以在后续遇到对应标签时得到正确处理。由于 goto 语句会导致程序跳转到其他位置，函数返回一个空列表和当前 goto 语句的索引。这表示在 goto 语句之后的代码块不应继续执行，因此代码块的分析应该在此处停止。这种处理方式确保 goto 语句在控制流图中的影响被正确表达，并且后续代码的执行逻辑与 goto 的跳转行为一致。
   ```python
   def analyze_goto_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        # 连接当前 goto 语句与其父语句
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)

        # 检查 global_special_stmts 中是否已经存在与 goto 目标相匹配的标签
        target_label = current_stmt.target  # 假设 current_stmt.target 存储了 goto 语句的目标标签名称
        label_found = False
        for stmt in global_special_stmts:
            if isinstance(stmt, specialBind) and stmt.match(target_label):
                # 如果找到匹配的标签，添加边从 goto 到标签
                self.cfg.add_edge(current_stmt, stmt.stmt, ControlFlowKind.GOTO)
                label_found = True
                break

        if not label_found:
            # 如果没有找到标签，将 goto 语句添加到 global_special_stmts 中等待未来处理
            global_special_stmts.append(current_stmt)

        # goto 语句执行后，控制流将跳转到标签，因此后续语句不会执行
        # 返回空列表和当前语句的索引，表明代码块分析应在此处终止
        return ([], current_stmt._index)
   ```
## 测试用例与结果
1. 张佳和部分
    1. break.go
    ```go
    package main

    import "fmt"

    func main() {
        outerLoop:
        for i := 0; i < 3; i++ {
            fmt.Printf("Outer loop: %d\n", i)
            if gg{
                break;
            }
            for j := 0; j < 3; j++ {
                fmt.Printf("Inner loop: %d\n", j)
                if j == 1 {
                    break outerLoop
                }
                if j>6{
                    break;
                    continue
                }
            }
        }
        eex+1
    }
    func a(){
        for ; ;{

        }
        for ;b ;{

        }
        end();
    }
    ```
    测试结果：
    ```
        ******************** break ********************
    [DEBUG]: Options(recursive=False, input=['/app/experiment_3/tests/resource/control_flow/go/break.go'], workspace='/app/experiment_3/tests/lian_workspace', debug=True, force=True, benchmark=False, print_stmts=True, cores=1, android=False, apps=[], sub_command='run', language=['python', 'go'])
    [WARNING]: With the force mode flag, the workspace is being rewritten: /app/experiment_3/tests/lian_workspace
    [DEBUG]: Lang-Parser: /app/experiment_3/tests/lian_workspace/src/break.go
    [{'package_stmt': {'name': 'main'}},
     {'import_stmt': {'attr': '', 'name': 'fmt'}},
     {'method_decl': {'name': 'main',
                      'type_parameters': [],
                      'parameters': [],
                      'data_type': [],
                      'body': [{'label_stmt': {'name': 'outerLoop'}},
                               {'for_stmt': {'init_body': [{'variable_decl': {'attr': 'short_var',
                                                                              'data_type': '',
                                                                              'name': 'i'}},
                                                           {'assign_stmt': {'target': 'i',
                                                                            'operand': '0'}}],
                                             'condition': '%v0',
                                             'condition_prebody': [{'assign_stmt': {'target': '%v0',
                                                                                    'operator': '<',
                                                                                    'operand': 'i',
                                                                                    'operand2': '3'}}],
                                             'update_body': [{'inc_stmt': {'target': 'i'}}],
                                             'body': [{'field_read': {'target': '%v0',
                                                                      'receiver_object': 'fmt',
                                                                      'field': 'Printf'}},
                                                      {'call_stmt': {'attr': [],
                                                                     'target': '%v1',
                                                                     'name': '%v0',
                                                                     'type_parameters': [],
                                                                     'args': ['"Outer '
                                                                              'loop: '
                                                                              '%d\\n"',
                                                                              'i']}},
                                                      {'if_stmt': {'condition': 'gg',
                                                                   'then_body': [{'break_stmt': {'target': ''}}]}},
                                                      {'for_stmt': {'init_body': [{'variable_decl': {'attr': 'short_var',
                                                                                                     'data_type': '',
                                                                                                     'name': 'j'}},
                                                                                  {'assign_stmt': {'target': 'j',
                                                                                                   'operand': '0'}}],
                                                                    'condition': '%v0',
                                                                    'condition_prebody': [{'assign_stmt': {'target': '%v0',
                                                                                                           'operator': '<',
                                                                                                           'operand': 'j',
                                                                                                           'operand2': '3'}}],
                                                                    'update_body': [{'inc_stmt': {'target': 'j'}}],
                                                                    'body': [{'field_read': {'target': '%v0',
                                                                                             'receiver_object': 'fmt',
                                                                                             'field': 'Printf'}},
                                                                             {'call_stmt': {'attr': [],
                                                                                            'target': '%v1',
                                                                                            'name': '%v0',
                                                                                            'type_parameters': [],
                                                                                            'args': ['"Inner '
                                                                                                     'loop: '
                                                                                                     '%d\\n"',
                                                                                                     'j']}},
                                                                             {'assign_stmt': {'target': '%v2',
                                                                                              'operator': '==',
                                                                                              'operand': 'j',
                                                                                              'operand2': '1'}},
                                                                             {'if_stmt': {'condition': '%v2',
                                                                                          'then_body': [{'break_stmt': {'target': 'outerLoop'}}]}},
                                                                             {'assign_stmt': {'target': '%v3',
                                                                                              'operator': '>',
                                                                                              'operand': 'j',
                                                                                              'operand2': '6'}},
                                                                             {'if_stmt': {'condition': '%v3',
                                                                                          'then_body': [{'break_stmt': {'target': ''}},
                                                                                                        {'continue_stmt': {'target': ''}}]}}]}}]}},
                               {'assign_stmt': {'target': '%v0',
                                                'operator': '+',
                                                'operand': 'eex',
                                                'operand2': '1'}}]}},
     {'method_decl': {'name': 'a',
                      'type_parameters': [],
                      'parameters': [],
                      'data_type': [],
                      'body': [{'for_stmt': {'init_body': [],
                                             'condition': '',
                                             'condition_prebody': [],
                                             'update_body': [],
                                             'body': []}},
                               {'for_stmt': {'init_body': [],
                                             'condition': 'b',
                                             'condition_prebody': [],
                                             'update_body': [],
                                             'body': []}},
                               {'call_stmt': {'attr': [],
                                              'target': '%v0',
                                              'name': 'end',
                                              'type_parameters': [],
                                              'args': []}}]}}]
    [{'operation': 'package_stmt',
      'parent_stmt_id': 0,
      'stmt_id': 10,
      'name': 'main'},
     {'operation': 'import_stmt',
      'parent_stmt_id': 0,
      'stmt_id': 11,
      'attr': '',
      'name': 'fmt'},
     {'operation': 'method_decl',
      'parent_stmt_id': 0,
      'stmt_id': 12,
      'name': 'main',
      'type_parameters': None,
      'parameters': None,
      'data_type': None,
      'body': 13},
     {'operation': 'block_start', 'stmt_id': 13, 'parent_stmt_id': 12},
     {'operation': 'label_stmt',
      'parent_stmt_id': 13,
      'stmt_id': 14,
      'name': 'outerLoop'},
     {'operation': 'for_stmt',
      'parent_stmt_id': 13,
      'stmt_id': 15,
      'init_body': 16,
      'condition': '%v0',
      'condition_prebody': 19,
      'update_body': 21,
      'body': 23},
     {'operation': 'block_start', 'stmt_id': 16, 'parent_stmt_id': 15},
     {'operation': 'variable_decl',
      'parent_stmt_id': 16,
      'stmt_id': 17,
      'attr': 'short_var',
      'data_type': '',
      'name': 'i'},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 16,
      'stmt_id': 18,
      'target': 'i',
      'operand': '0'},
     {'operation': 'block_end', 'stmt_id': 16, 'parent_stmt_id': 15},
     {'operation': 'block_start', 'stmt_id': 19, 'parent_stmt_id': 15},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 19,
      'stmt_id': 20,
      'target': '%v0',
      'operator': '<',
      'operand': 'i',
      'operand2': '3'},
     {'operation': 'block_end', 'stmt_id': 19, 'parent_stmt_id': 15},
     {'operation': 'block_start', 'stmt_id': 21, 'parent_stmt_id': 15},
     {'operation': 'inc_stmt', 'parent_stmt_id': 21, 'stmt_id': 22, 'target': 'i'},
     {'operation': 'block_end', 'stmt_id': 21, 'parent_stmt_id': 15},
     {'operation': 'block_start', 'stmt_id': 23, 'parent_stmt_id': 15},
     {'operation': 'field_read',
      'parent_stmt_id': 23,
      'stmt_id': 24,
      'target': '%v0',
      'receiver_object': 'fmt',
      'field': 'Printf'},
     {'operation': 'call_stmt',
      'parent_stmt_id': 23,
      'stmt_id': 25,
      'attr': None,
      'target': '%v1',
      'name': '%v0',
      'type_parameters': None,
      'args': '[\'"Outer loop: %d\\\\n"\', \'i\']'},
     {'operation': 'if_stmt',
      'parent_stmt_id': 23,
      'stmt_id': 26,
      'condition': 'gg',
      'then_body': 27},
     {'operation': 'block_start', 'stmt_id': 27, 'parent_stmt_id': 26},
     {'operation': 'break_stmt', 'parent_stmt_id': 27, 'stmt_id': 28, 'target': ''},
     {'operation': 'block_end', 'stmt_id': 27, 'parent_stmt_id': 26},
     {'operation': 'for_stmt',
      'parent_stmt_id': 23,
      'stmt_id': 29,
      'init_body': 30,
      'condition': '%v0',
      'condition_prebody': 33,
      'update_body': 35,
      'body': 37},
     {'operation': 'block_start', 'stmt_id': 30, 'parent_stmt_id': 29},
     {'operation': 'variable_decl',
      'parent_stmt_id': 30,
      'stmt_id': 31,
      'attr': 'short_var',
      'data_type': '',
      'name': 'j'},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 30,
      'stmt_id': 32,
      'target': 'j',
      'operand': '0'},
     {'operation': 'block_end', 'stmt_id': 30, 'parent_stmt_id': 29},
     {'operation': 'block_start', 'stmt_id': 33, 'parent_stmt_id': 29},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 33,
      'stmt_id': 34,
      'target': '%v0',
      'operator': '<',
      'operand': 'j',
      'operand2': '3'},
     {'operation': 'block_end', 'stmt_id': 33, 'parent_stmt_id': 29},
     {'operation': 'block_start', 'stmt_id': 35, 'parent_stmt_id': 29},
     {'operation': 'inc_stmt', 'parent_stmt_id': 35, 'stmt_id': 36, 'target': 'j'},
     {'operation': 'block_end', 'stmt_id': 35, 'parent_stmt_id': 29},
     {'operation': 'block_start', 'stmt_id': 37, 'parent_stmt_id': 29},
     {'operation': 'field_read',
      'parent_stmt_id': 37,
      'stmt_id': 38,
      'target': '%v0',
      'receiver_object': 'fmt',
      'field': 'Printf'},
     {'operation': 'call_stmt',
      'parent_stmt_id': 37,
      'stmt_id': 39,
      'attr': None,
      'target': '%v1',
      'name': '%v0',
      'type_parameters': None,
      'args': '[\'"Inner loop: %d\\\\n"\', \'j\']'},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 37,
      'stmt_id': 40,
      'target': '%v2',
      'operator': '==',
      'operand': 'j',
      'operand2': '1'},
     {'operation': 'if_stmt',
      'parent_stmt_id': 37,
      'stmt_id': 41,
      'condition': '%v2',
      'then_body': 42},
     {'operation': 'block_start', 'stmt_id': 42, 'parent_stmt_id': 41},
     {'operation': 'break_stmt',
      'parent_stmt_id': 42,
      'stmt_id': 43,
      'target': 'outerLoop'},
     {'operation': 'block_end', 'stmt_id': 42, 'parent_stmt_id': 41},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 37,
      'stmt_id': 44,
      'target': '%v3',
      'operator': '>',
      'operand': 'j',
      'operand2': '6'},
     {'operation': 'if_stmt',
      'parent_stmt_id': 37,
      'stmt_id': 45,
      'condition': '%v3',
      'then_body': 46},
     {'operation': 'block_start', 'stmt_id': 46, 'parent_stmt_id': 45},
     {'operation': 'break_stmt', 'parent_stmt_id': 46, 'stmt_id': 47, 'target': ''},
     {'operation': 'continue_stmt',
      'parent_stmt_id': 46,
      'stmt_id': 48,
      'target': ''},
     {'operation': 'block_end', 'stmt_id': 46, 'parent_stmt_id': 45},
     {'operation': 'block_end', 'stmt_id': 37, 'parent_stmt_id': 29},
     {'operation': 'block_end', 'stmt_id': 23, 'parent_stmt_id': 15},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 13,
      'stmt_id': 49,
      'target': '%v0',
      'operator': '+',
      'operand': 'eex',
      'operand2': '1'},
     {'operation': 'block_end', 'stmt_id': 13, 'parent_stmt_id': 12},
     {'operation': 'method_decl',
      'parent_stmt_id': 0,
      'stmt_id': 50,
      'name': 'a',
      'type_parameters': None,
      'parameters': None,
      'data_type': None,
      'body': 51},
     {'operation': 'block_start', 'stmt_id': 51, 'parent_stmt_id': 50},
     {'operation': 'for_stmt',
      'parent_stmt_id': 51,
      'stmt_id': 52,
      'init_body': None,
      'condition': '',
      'condition_prebody': None,
      'update_body': None,
      'body': None},
     {'operation': 'for_stmt',
      'parent_stmt_id': 51,
      'stmt_id': 53,
      'init_body': None,
      'condition': 'b',
      'condition_prebody': None,
      'update_body': None,
      'body': None},
     {'operation': 'call_stmt',
      'parent_stmt_id': 51,
      'stmt_id': 54,
      'attr': None,
      'target': '%v0',
      'name': 'end',
      'type_parameters': None,
      'args': None},
     {'operation': 'block_end', 'stmt_id': 51, 'parent_stmt_id': 50}]
    [DEBUG]: analysis_phase name: control_flow index:0
    [DEBUG]: _add_one_edge:14->17, weight=None
    [DEBUG]: _add_one_edge:17->18, weight=None
    [DEBUG]: _add_one_edge:18->20, weight=None
    [DEBUG]: _add_one_edge:20->15, weight=3
    [DEBUG]: _add_one_edge:15->24, weight=4
    [DEBUG]: _add_one_edge:24->25, weight=None
    [DEBUG]: _add_one_edge:25->26, weight=None
    [DEBUG]: _add_one_edge:26->28, weight=1
    [DEBUG]: _add_one_edge:26->31, weight=2
    [DEBUG]: _add_one_edge:31->32, weight=None
    [DEBUG]: _add_one_edge:32->34, weight=None
    [DEBUG]: _add_one_edge:34->29, weight=3
    [DEBUG]: _add_one_edge:29->38, weight=4
    [DEBUG]: _add_one_edge:38->39, weight=None
    [DEBUG]: _add_one_edge:39->40, weight=None
    [DEBUG]: _add_one_edge:40->41, weight=None
    [DEBUG]: _add_one_edge:41->43, weight=1
    [DEBUG]: _add_one_edge:41->44, weight=2
    [DEBUG]: _add_one_edge:44->45, weight=None
    [DEBUG]: _add_one_edge:45->47, weight=1
    [DEBUG]: _add_one_edge:45->36, weight=2
    [DEBUG]: _add_one_edge:36->34, weight=None
    [DEBUG]: _add_one_edge:29->22, weight=5
    [DEBUG]: _add_one_edge:47->22, weight=6
    [DEBUG]: _add_one_edge:22->20, weight=None
    [DEBUG]: _add_one_edge:15->49, weight=5
    [DEBUG]: _add_one_edge:28->49, weight=6
    [DEBUG]: _add_one_edge:43->49, weight=6
    [DEBUG]: _add_one_edge:49->-1, weight=None
    [DEBUG]: analysis_phase name: control_flow index:0
    [DEBUG]: _add_one_edge:52->52, weight=4
    [DEBUG]: _add_one_edge:52->53, weight=5
    [DEBUG]: _add_one_edge:53->53, weight=4
    [DEBUG]: _add_one_edge:53->54, weight=5
    [DEBUG]: _add_one_edge:54->-1, weight=None
    === target file ===
    /app/experiment_3/tests/resource/control_flow/go/break.go
    + reference answer
    [(14, 17, 0),
     (15, 24, 4),
     (15, 49, 5),
     (17, 18, 0),
     (18, 20, 0),
     (20, 15, 3),
     (22, 20, 0),
     (24, 25, 0),
     (25, 26, 0),
     (26, 28, 1),
     (26, 31, 2),
     (28, 49, 6),
     (29, 22, 5),
     (29, 38, 4),
     (31, 32, 0),
     (32, 34, 0),
     (34, 29, 3),
     (36, 34, 0),
     (38, 39, 0),
     (39, 40, 0),
     (40, 41, 0),
     (41, 43, 1),
     (41, 44, 2),
     (43, 49, 6),
     (44, 45, 0),
     (45, 36, 2),
     (45, 47, 1),
     (47, 22, 6),
     (49, -1, 0),
     (52, 52, 4),
     (52, 53, 5),
     (53, 53, 4),
     (53, 54, 5),
     (54, -1, 0)]
    + current result
    [(14, 17, 0),
     (15, 24, 4),
     (15, 49, 5),
     (17, 18, 0),
     (18, 20, 0),
     (20, 15, 3),
     (22, 20, 0),
     (24, 25, 0),
     (25, 26, 0),
     (26, 28, 1),
     (26, 31, 2),
     (28, 49, 6),
     (29, 22, 5),
     (29, 38, 4),
     (31, 32, 0),
     (32, 34, 0),
     (34, 29, 3),
     (36, 34, 0),
     (38, 39, 0),
     (39, 40, 0),
     (40, 41, 0),
     (41, 43, 1),
     (41, 44, 2),
     (43, 49, 6),
     (44, 45, 0),
     (45, 36, 2),
     (45, 47, 1),
     (47, 22, 6),
     (49, -1, 0),
     (52, 52, 4),
     (52, 53, 5),
     (53, 53, 4),
     (53, 54, 5),
     (54, -1, 0)]
    ```




 2. continue.go
     ```go
     package main   

        import "fmt"    

        func function1() {
        	for i := 0; i < 5; i++ {
        		if i == 2 {
        			continue
        		}
        		fmt.Println("Function 1:", i)
        	}
        }   

        func function2() {
        labelh:
        OuterLoop:
        	for i := 0; i < 3; i++ {
        		if gg{
        			break
        		}
        		else if ggagain{
        			continue
        		}
        		readyourself:=1
        		for j := 0; j < 3; j++ {
        			if j == 1 {
        				continue OuterLoop
        			}
        			fmt.Println("Function 2:", i, j)
        		}
        	}
        	flamen:=1
        }   

        func main() {
        	function1()
        	function2()
        } 
    ```

    测试结果：  

    ```
    [DEBUG]: Options(recursive=False, input=['/app/experiment_3/tests/resource/control_flow/go/break.go'], workspace='/app/experiment_3/tests/lian_workspace', debug=True, force=True, benchmark=False, print_stmts=True, cores=1, android=False, apps=[], sub_command='run', language=['python', 'go'])
    [WARNING]: With the force mode flag, the workspace is being rewritten: /app/experiment_3/tests/lian_workspace
    [DEBUG]: Lang-Parser: /app/experiment_3/tests/lian_workspace/src/break.go
    [{'package_stmt': {'name': 'main'}},
     {'import_stmt': {'attr': '', 'name': 'fmt'}},
     {'method_decl': {'name': 'main',
                      'type_parameters': [],
                      'parameters': [],
                      'data_type': [],
                      'body': [{'label_stmt': {'name': 'outerLoop'}},
                               {'for_stmt': {'init_body': [{'variable_decl': {'attr': 'short_var',
                                                                              'data_type': '',
                                                                              'name': 'i'}},
                                                           {'assign_stmt': {'target': 'i',
                                                                            'operand': '0'}}],
                                             'condition': '%v0',
                                             'condition_prebody': [{'assign_stmt': {'target': '%v0',
                                                                                    'operator': '<',
                                                                                    'operand': 'i',
                                                                                    'operand2': '3'}}],
                                             'update_body': [{'inc_stmt': {'target': 'i'}}],
                                             'body': [{'field_read': {'target': '%v0',
                                                                      'receiver_object': 'fmt',
                                                                      'field': 'Printf'}},
                                                      {'call_stmt': {'attr': [],
                                                                     'target': '%v1',
                                                                     'name': '%v0',
                                                                     'type_parameters': [],
                                                                     'args': ['"Outer '
                                                                              'loop: '
                                                                              '%d\\n"',
                                                                              'i']}},
                                                      {'if_stmt': {'condition': 'gg',
                                                                   'then_body': [{'break_stmt': {'target': ''}}]}},
                                                      {'for_stmt': {'init_body': [{'variable_decl': {'attr': 'short_var',
                                                                                                     'data_type': '',
                                                                                                     'name': 'j'}},
                                                                                  {'assign_stmt': {'target': 'j',
                                                                                                   'operand': '0'}}],
                                                                    'condition': '%v0',
                                                                    'condition_prebody': [{'assign_stmt': {'target': '%v0',
                                                                                                           'operator': '<',
                                                                                                           'operand': 'j',
                                                                                                           'operand2': '3'}}],
                                                                    'update_body': [{'inc_stmt': {'target': 'j'}}],
                                                                    'body': [{'field_read': {'target': '%v0',
                                                                                             'receiver_object': 'fmt',
                                                                                             'field': 'Printf'}},
                                                                             {'call_stmt': {'attr': [],
                                                                                            'target': '%v1',
                                                                                            'name': '%v0',
                                                                                            'type_parameters': [],
                                                                                            'args': ['"Inner '
                                                                                                     'loop: '
                                                                                                     '%d\\n"',
                                                                                                     'j']}},
                                                                             {'assign_stmt': {'target': '%v2',
                                                                                              'operator': '==',
                                                                                              'operand': 'j',
                                                                                              'operand2': '1'}},
                                                                             {'if_stmt': {'condition': '%v2',
                                                                                          'then_body': [{'break_stmt': {'target': 'outerLoop'}}]}},
                                                                             {'assign_stmt': {'target': '%v3',
                                                                                              'operator': '>',
                                                                                              'operand': 'j',
                                                                                              'operand2': '6'}},
                                                                             {'if_stmt': {'condition': '%v3',
                                                                                          'then_body': [{'break_stmt': {'target': ''}},
                                                                                                        {'continue_stmt': {'target': ''}}]}}]}}]}},
                               {'assign_stmt': {'target': '%v0',
                                                'operator': '+',
                                                'operand': 'eex',
                                                'operand2': '1'}}]}},
     {'method_decl': {'name': 'a',
                      'type_parameters': [],
                      'parameters': [],
                      'data_type': [],
                      'body': [{'for_stmt': {'init_body': [],
                                             'condition': '',
                                             'condition_prebody': [],
                                             'update_body': [],
                                             'body': []}},
                               {'for_stmt': {'init_body': [],
                                             'condition': 'b',
                                             'condition_prebody': [],
                                             'update_body': [],
                                             'body': []}},
                               {'call_stmt': {'attr': [],
                                              'target': '%v0',
                                              'name': 'end',
                                              'type_parameters': [],
                                              'args': []}}]}}]
    [{'operation': 'package_stmt',
      'parent_stmt_id': 0,
      'stmt_id': 10,
      'name': 'main'},
     {'operation': 'import_stmt',
      'parent_stmt_id': 0,
      'stmt_id': 11,
      'attr': '',
      'name': 'fmt'},
     {'operation': 'method_decl',
      'parent_stmt_id': 0,
      'stmt_id': 12,
      'name': 'main',
      'type_parameters': None,
      'parameters': None,
      'data_type': None,
      'body': 13},
     {'operation': 'block_start', 'stmt_id': 13, 'parent_stmt_id': 12},
     {'operation': 'label_stmt',
      'parent_stmt_id': 13,
      'stmt_id': 14,
      'name': 'outerLoop'},
     {'operation': 'for_stmt',
      'parent_stmt_id': 13,
      'stmt_id': 15,
      'init_body': 16,
      'condition': '%v0',
      'condition_prebody': 19,
      'update_body': 21,
      'body': 23},
     {'operation': 'block_start', 'stmt_id': 16, 'parent_stmt_id': 15},
     {'operation': 'variable_decl',
      'parent_stmt_id': 16,
      'stmt_id': 17,
      'attr': 'short_var',
      'data_type': '',
      'name': 'i'},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 16,
      'stmt_id': 18,
      'target': 'i',
      'operand': '0'},
     {'operation': 'block_end', 'stmt_id': 16, 'parent_stmt_id': 15},
     {'operation': 'block_start', 'stmt_id': 19, 'parent_stmt_id': 15},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 19,
      'stmt_id': 20,
      'target': '%v0',
      'operator': '<',
      'operand': 'i',
      'operand2': '3'},
     {'operation': 'block_end', 'stmt_id': 19, 'parent_stmt_id': 15},
     {'operation': 'block_start', 'stmt_id': 21, 'parent_stmt_id': 15},
     {'operation': 'inc_stmt', 'parent_stmt_id': 21, 'stmt_id': 22, 'target': 'i'},
     {'operation': 'block_end', 'stmt_id': 21, 'parent_stmt_id': 15},
     {'operation': 'block_start', 'stmt_id': 23, 'parent_stmt_id': 15},
     {'operation': 'field_read',
      'parent_stmt_id': 23,
      'stmt_id': 24,
      'target': '%v0',
      'receiver_object': 'fmt',
      'field': 'Printf'},
     {'operation': 'call_stmt',
      'parent_stmt_id': 23,
      'stmt_id': 25,
      'attr': None,
      'target': '%v1',
      'name': '%v0',
      'type_parameters': None,
      'args': '[\'"Outer loop: %d\\\\n"\', \'i\']'},
     {'operation': 'if_stmt',
      'parent_stmt_id': 23,
      'stmt_id': 26,
      'condition': 'gg',
      'then_body': 27},
     {'operation': 'block_start', 'stmt_id': 27, 'parent_stmt_id': 26},
     {'operation': 'break_stmt', 'parent_stmt_id': 27, 'stmt_id': 28, 'target': ''},
     {'operation': 'block_end', 'stmt_id': 27, 'parent_stmt_id': 26},
     {'operation': 'for_stmt',
      'parent_stmt_id': 23,
      'stmt_id': 29,
      'init_body': 30,
      'condition': '%v0',
      'condition_prebody': 33,
      'update_body': 35,
      'body': 37},
     {'operation': 'block_start', 'stmt_id': 30, 'parent_stmt_id': 29},
     {'operation': 'variable_decl',
      'parent_stmt_id': 30,
      'stmt_id': 31,
      'attr': 'short_var',
      'data_type': '',
      'name': 'j'},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 30,
      'stmt_id': 32,
      'target': 'j',
      'operand': '0'},
     {'operation': 'block_end', 'stmt_id': 30, 'parent_stmt_id': 29},
     {'operation': 'block_start', 'stmt_id': 33, 'parent_stmt_id': 29},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 33,
      'stmt_id': 34,
      'target': '%v0',
      'operator': '<',
      'operand': 'j',
      'operand2': '3'},
     {'operation': 'block_end', 'stmt_id': 33, 'parent_stmt_id': 29},
     {'operation': 'block_start', 'stmt_id': 35, 'parent_stmt_id': 29},
     {'operation': 'inc_stmt', 'parent_stmt_id': 35, 'stmt_id': 36, 'target': 'j'},
     {'operation': 'block_end', 'stmt_id': 35, 'parent_stmt_id': 29},
     {'operation': 'block_start', 'stmt_id': 37, 'parent_stmt_id': 29},
     {'operation': 'field_read',
      'parent_stmt_id': 37,
      'stmt_id': 38,
      'target': '%v0',
      'receiver_object': 'fmt',
      'field': 'Printf'},
     {'operation': 'call_stmt',
      'parent_stmt_id': 37,
      'stmt_id': 39,
      'attr': None,
      'target': '%v1',
      'name': '%v0',
      'type_parameters': None,
      'args': '[\'"Inner loop: %d\\\\n"\', \'j\']'},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 37,
      'stmt_id': 40,
      'target': '%v2',
      'operator': '==',
      'operand': 'j',
      'operand2': '1'},
     {'operation': 'if_stmt',
      'parent_stmt_id': 37,
      'stmt_id': 41,
      'condition': '%v2',
      'then_body': 42},
     {'operation': 'block_start', 'stmt_id': 42, 'parent_stmt_id': 41},
     {'operation': 'break_stmt',
      'parent_stmt_id': 42,
      'stmt_id': 43,
      'target': 'outerLoop'},
     {'operation': 'block_end', 'stmt_id': 42, 'parent_stmt_id': 41},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 37,
      'stmt_id': 44,
      'target': '%v3',
      'operator': '>',
      'operand': 'j',
      'operand2': '6'},
     {'operation': 'if_stmt',
      'parent_stmt_id': 37,
      'stmt_id': 45,
      'condition': '%v3',
      'then_body': 46},
     {'operation': 'block_start', 'stmt_id': 46, 'parent_stmt_id': 45},
     {'operation': 'break_stmt', 'parent_stmt_id': 46, 'stmt_id': 47, 'target': ''},
     {'operation': 'continue_stmt',
      'parent_stmt_id': 46,
      'stmt_id': 48,
      'target': ''},
     {'operation': 'block_end', 'stmt_id': 46, 'parent_stmt_id': 45},
     {'operation': 'block_end', 'stmt_id': 37, 'parent_stmt_id': 29},
     {'operation': 'block_end', 'stmt_id': 23, 'parent_stmt_id': 15},
     {'operation': 'assign_stmt',
      'parent_stmt_id': 13,
      'stmt_id': 49,
      'target': '%v0',
      'operator': '+',
      'operand': 'eex',
      'operand2': '1'},
     {'operation': 'block_end', 'stmt_id': 13, 'parent_stmt_id': 12},
     {'operation': 'method_decl',
      'parent_stmt_id': 0,
      'stmt_id': 50,
      'name': 'a',
      'type_parameters': None,
      'parameters': None,
      'data_type': None,
      'body': 51},
     {'operation': 'block_start', 'stmt_id': 51, 'parent_stmt_id': 50},
     {'operation': 'for_stmt',
      'parent_stmt_id': 51,
      'stmt_id': 52,
      'init_body': None,
      'condition': '',
      'condition_prebody': None,
      'update_body': None,
      'body': None},
     {'operation': 'for_stmt',
      'parent_stmt_id': 51,
      'stmt_id': 53,
      'init_body': None,
      'condition': 'b',
      'condition_prebody': None,
      'update_body': None,
      'body': None},
     {'operation': 'call_stmt',
      'parent_stmt_id': 51,
      'stmt_id': 54,
      'attr': None,
      'target': '%v0',
      'name': 'end',
      'type_parameters': None,
      'args': None},
     {'operation': 'block_end', 'stmt_id': 51, 'parent_stmt_id': 50}]
    [DEBUG]: analysis_phase name: control_flow index:0
    [DEBUG]: _add_one_edge:14->17, weight=None
    [DEBUG]: _add_one_edge:17->18, weight=None
    [DEBUG]: _add_one_edge:18->20, weight=None
    [DEBUG]: _add_one_edge:20->15, weight=3
    [DEBUG]: _add_one_edge:15->24, weight=4
    [DEBUG]: _add_one_edge:24->25, weight=None
    [DEBUG]: _add_one_edge:25->26, weight=None
    [DEBUG]: _add_one_edge:26->28, weight=1
    [DEBUG]: _add_one_edge:26->31, weight=2
    [DEBUG]: _add_one_edge:31->32, weight=None
    [DEBUG]: _add_one_edge:32->34, weight=None
    [DEBUG]: _add_one_edge:34->29, weight=3
    [DEBUG]: _add_one_edge:29->38, weight=4
    [DEBUG]: _add_one_edge:38->39, weight=None
    [DEBUG]: _add_one_edge:39->40, weight=None
    [DEBUG]: _add_one_edge:40->41, weight=None
    [DEBUG]: _add_one_edge:41->43, weight=1
    [DEBUG]: _add_one_edge:41->44, weight=2
    [DEBUG]: _add_one_edge:44->45, weight=None
    [DEBUG]: _add_one_edge:45->47, weight=1
    [DEBUG]: _add_one_edge:45->36, weight=2
    [DEBUG]: _add_one_edge:36->34, weight=None
    [DEBUG]: _add_one_edge:29->22, weight=5
    [DEBUG]: _add_one_edge:47->22, weight=6
    [DEBUG]: _add_one_edge:22->20, weight=None
    [DEBUG]: _add_one_edge:15->49, weight=5
    [DEBUG]: _add_one_edge:28->49, weight=6
    [DEBUG]: _add_one_edge:43->49, weight=6
    [DEBUG]: _add_one_edge:49->-1, weight=None
    [DEBUG]: analysis_phase name: control_flow index:0
    [DEBUG]: _add_one_edge:52->52, weight=4
    [DEBUG]: _add_one_edge:52->53, weight=5
    [DEBUG]: _add_one_edge:53->53, weight=4
    [DEBUG]: _add_one_edge:53->54, weight=5
    [DEBUG]: _add_one_edge:54->-1, weight=None
    === target file ===
    /app/experiment_3/tests/resource/control_flow/go/break.go
    + reference answer
    [(14, 17, 0),
     (15, 24, 4),
     (15, 49, 5),
     (17, 18, 0),
     (18, 20, 0),
     (20, 15, 3),
     (22, 20, 0),
     (24, 25, 0),
     (25, 26, 0),
     (26, 28, 1),
     (26, 31, 2),
     (28, 49, 6),
     (29, 22, 5),
     (29, 38, 4),
     (31, 32, 0),
     (32, 34, 0),
     (34, 29, 3),
     (36, 34, 0),
     (38, 39, 0),
     (39, 40, 0),
     (40, 41, 0),
     (41, 43, 1),
     (41, 44, 2),
     (43, 49, 6),
     (44, 45, 0),
     (45, 36, 2),
     (45, 47, 1),
     (47, 22, 6),
     (49, -1, 0),
     (52, 53, 5),
     (53, 54, 5),
     (54, -1, 0)]
    + current result
    [(14, 17, 0),
     (15, 24, 4),
     (15, 49, 5),
     (17, 18, 0),
     (18, 20, 0),
     (20, 15, 3),
     (22, 20, 0),
     (24, 25, 0),
     (25, 26, 0),
     (26, 28, 1),
     (26, 31, 2),
     (28, 49, 6),
     (29, 22, 5),
     (29, 38, 4),
     (31, 32, 0),
     (32, 34, 0),
     (34, 29, 3),
     (36, 34, 0),
     (38, 39, 0),
     (39, 40, 0),
     (40, 41, 0),
     (41, 43, 1),
     (41, 44, 2),
     (43, 49, 6),
     (44, 45, 0),
     (45, 36, 2),
     (45, 47, 1),
     (47, 22, 6),
     (49, -1, 0),
     (52, 52, 4),
     (52, 53, 5),
     (53, 53, 4),
     (53, 54, 5),
     (54, -1, 0)]
     ```
2. 宋岱桉部分
    1. forin.go
    ```go
    func num_sum() {
    numbers := []int{1, 2, 3, 4, 5}
    sum := 0
    count := 0
    for _, num := range numbers {
        sum += num
        count += 1
    }
    fmt.Println("切片中所有元素的总和为:", sum)
    }

    func SimpleBreak() {
        outerLoop:
        for i := range numbers {
            fmt.Printf("Outer loop: %d\n", i)
            if gg{
                break;
            }
            for j := range numbers {
                fmt.Printf("Inner loop: %d\n", j)
                if j == 1 {
                    break outerLoop
                }
                if j>6{
                    break;
                    continue
                }
            }
        }
        eex+1
    }
    func Emp(){
        for range numbers{
        }
    }
    func EmpBreak(){
        for range numbers{
            break
        }
    }
    ```
    测试结果：
    ``` 
    [DEBUG]: Options(recursive=False, input=['/app/experiment_3/tests/resource/control_flow/go/forin.go'], workspace='/app/experiment_3/tests/lian_workspace', debug=True, force=True, benchmark=False, print_stmts=True, cores=1, android=False, apps=[], sub_command='run', language=['python', 'go'])
    [WARNING]: With the force mode flag, the workspace is being rewritten: /app/experiment_3/tests/lian_workspace
    [DEBUG]: Lang-Parser: /app/experiment_3/tests/lian_workspace/src/forin.go
    [{'method_decl': {'name': 'num_sum',
                    'type_parameters': [],
                    'parameters': [],
                    'data_type': [],
                    'body': [{'composite_literal': {'type': ['slice_type',
                                                            {'element': 'int'}],
                                                    'composite_body': [['1'],
                                                                        ['2'],
                                                                        ['3'],
                                                                        ['4'],
                                                                        ['5']]}},
                            {'variable_decl': {'attr': 'short_var',
                                                'data_type': '',
                                                'name': 'numbers'}},
                            {'assign_stmt': {'target': 'numbers',
                                                'operand': '%'}},
                            {'variable_decl': {'attr': 'short_var',
                                                'data_type': '',
                                                'name': 'sum'}},
                            {'assign_stmt': {'target': 'sum', 'operand': '0'}},
                            {'variable_decl': {'attr': 'short_var',
                                                'data_type': '',
                                                'name': 'count'}},
                            {'assign_stmt': {'target': 'count', 'operand': '0'}},
                            {'forin_stmt': {'name': '%v1',
                                            'target': 'numbers',
                                            'array_read': [{'target': '_',
                                                            'array': '%v1',
                                                            'index': 0},
                                                            {'target': 'num',
                                                            'array': '%v1',
                                                            'index': 1}],
                                            'body': [{'assign_stmt': {'target': 'sum',
                                                                        'operator': '+',
                                                                        'operand': 'sum',
                                                                        'operand2': 'num'}},
                                                        {'assign_stmt': {'target': 'count',
                                                                        'operator': '+',
                                                                        'operand': 'count',
                                                                        'operand2': '1'}}]}},
                            {'field_read': {'target': '%v2',
                                            'receiver_object': 'fmt',
                                            'field': 'Println'}},
                            {'call_stmt': {'attr': [],
                                            'target': '%v3',
                                            'name': '%v2',
                                            'type_parameters': [],
                                            'args': ['"切片中所有元素的总和为:"',
                                                    'sum']}}]}},
    {'method_decl': {'name': 'SimpleBreak',
                    'type_parameters': [],
                    'parameters': [],
                    'data_type': [],
                    'body': [{'label_stmt': {'name': 'outerLoop'}},
                            {'forin_stmt': {'name': 'i',
                                            'target': 'numbers',
                                            'body': [{'field_read': {'target': '%v0',
                                                                        'receiver_object': 'fmt',
                                                                        'field': 'Printf'}},
                                                        {'call_stmt': {'attr': [],
                                                                    'target': '%v1',
                                                                    'name': '%v0',
                                                                    'type_parameters': [],
                                                                    'args': ['"Outer '
                                                                                'loop: '
                                                                                '%d\\n"',
                                                                                'i']}},
                                                        {'if_stmt': {'condition': 'gg',
                                                                    'then_body': [{'break_stmt': {'target': ''}}]}},
                                                        {'forin_stmt': {'name': 'j',
                                                                        'target': 'numbers',
                                                                        'body': [{'field_read': {'target': '%v0',
                                                                                                'receiver_object': 'fmt',
                                                                                                'field': 'Printf'}},
                                                                                {'call_stmt': {'attr': [],
                                                                                                'target': '%v1',
                                                                                                'name': '%v0',
                                                                                                'type_parameters': [],
                                                                                                'args': ['"Inner '
                                                                                                        'loop: '
                                                                                                        '%d\\n"',
                                                                                                        'j']}},
                                                                                {'assign_stmt': {'target': '%v2',
                                                                                                'operator': '==',
                                                                                                'operand': 'j',
                                                                                                'operand2': '1'}},
                                                                                {'if_stmt': {'condition': '%v2',
                                                                                            'then_body': [{'break_stmt': {'target': 'outerLoop'}}]}},
                                                                                {'assign_stmt': {'target': '%v3',
                                                                                                'operator': '>',
                                                                                                'operand': 'j',
                                                                                                'operand2': '6'}},
                                                                                {'if_stmt': {'condition': '%v3',
                                                                                            'then_body': [{'break_stmt': {'target': ''}},    
                                                                                                            {'continue_stmt': {'target': ''}}]}}]}}]}},
                            {'assign_stmt': {'target': '%v0',
                                                'operator': '+',
                                                'operand': 'eex',
                                                'operand2': '1'}}]}},
    {'method_decl': {'name': 'Emp',
                    'type_parameters': [],
                    'parameters': [],
                    'data_type': [],
                    'body': [{'forin_stmt': {'name': '%v0',
                                            'target': 'numbers',
                                            'array_read': [],
                                            'body': []}}]}},
    {'method_decl': {'name': 'EmpBreak',
                    'type_parameters': [],
                    'parameters': [],
                    'data_type': [],
                    'body': [{'forin_stmt': {'name': '%v0',
                                            'target': 'numbers',
                                            'array_read': [],
                                            'body': [{'break_stmt': {'target': ''}}]}}]}}]
    [{'operation': 'method_decl',
    'parent_stmt_id': 0,
    'stmt_id': 10,
    'name': 'num_sum',
    'type_parameters': None,
    'parameters': None,
    'data_type': None,
    'body': 11},
    {'operation': 'block_start', 'stmt_id': 11, 'parent_stmt_id': 10},
    {'operation': 'composite_literal',
    'parent_stmt_id': 11,
    'stmt_id': 12,
    'type': "['slice_type', {'element': 'int'}]",
    'composite_body': "[['1'], ['2'], ['3'], ['4'], ['5']]"},
    {'operation': 'variable_decl',
    'parent_stmt_id': 11,
    'stmt_id': 13,
    'attr': 'short_var',
    'data_type': '',
    'name': 'numbers'},
    {'operation': 'assign_stmt',
    'parent_stmt_id': 11,
    'stmt_id': 14,
    'target': 'numbers',
    'operand': '%'},
    {'operation': 'variable_decl',
    'parent_stmt_id': 11,
    'stmt_id': 15,
    'attr': 'short_var',
    'data_type': '',
    'name': 'sum'},
    {'operation': 'assign_stmt',
    'parent_stmt_id': 11,
    'stmt_id': 16,
    'target': 'sum',
    'operand': '0'},
    {'operation': 'variable_decl',
    'parent_stmt_id': 11,
    'stmt_id': 17,
    'attr': 'short_var',
    'data_type': '',
    'name': 'count'},
    {'operation': 'assign_stmt',
    'parent_stmt_id': 11,
    'stmt_id': 18,
    'target': 'count',
    'operand': '0'},
    {'operation': 'forin_stmt',
    'parent_stmt_id': 11,
    'stmt_id': 19,
    'name': '%v1',
    'target': 'numbers',
    'array_read': 20,
    'body': 23},
    {'operation': 'block_start', 'stmt_id': 20, 'parent_stmt_id': 19},
    {'operation': 'target', 'parent_stmt_id': 20, 'stmt_id': 21},
    {'operation': 'target', 'parent_stmt_id': 20, 'stmt_id': 22},
    {'operation': 'block_end', 'stmt_id': 20, 'parent_stmt_id': 19},
    {'operation': 'block_start', 'stmt_id': 23, 'parent_stmt_id': 19},
    {'operation': 'assign_stmt',
    'parent_stmt_id': 23,
    'stmt_id': 24,
    'target': 'sum',
    'operator': '+',
    'operand': 'sum',
    'operand2': 'num'},
    {'operation': 'assign_stmt',
    'parent_stmt_id': 23,
    'stmt_id': 25,
    'target': 'count',
    'operator': '+',
    'operand': 'count',
    'operand2': '1'},
    {'operation': 'block_end', 'stmt_id': 23, 'parent_stmt_id': 19},
    {'operation': 'field_read',
    'parent_stmt_id': 11,
    'stmt_id': 26,
    'target': '%v2',
    'receiver_object': 'fmt',
    'field': 'Println'},
    {'operation': 'call_stmt',
    'parent_stmt_id': 11,
    'stmt_id': 27,
    'attr': None,
    'target': '%v3',
    'name': '%v2',
    'type_parameters': None,
    'args': '[\'"切片中所有元素的总和为:"\', \'sum\']'},
    {'operation': 'block_end', 'stmt_id': 11, 'parent_stmt_id': 10},
    {'operation': 'method_decl',
    'parent_stmt_id': 0,
    'stmt_id': 28,
    'name': 'SimpleBreak',
    'type_parameters': None,
    'parameters': None,
    'data_type': None,
    'body': 29},
    {'operation': 'block_start', 'stmt_id': 29, 'parent_stmt_id': 28},
    {'operation': 'label_stmt',
    'parent_stmt_id': 29,
    'stmt_id': 30,
    'name': 'outerLoop'},
    {'operation': 'forin_stmt',
    'parent_stmt_id': 29,
    'stmt_id': 31,
    'name': 'i',
    'target': 'numbers',
    'body': 32},
    {'operation': 'block_start', 'stmt_id': 32, 'parent_stmt_id': 31},
    {'operation': 'field_read',
    'parent_stmt_id': 32,
    'stmt_id': 33,
    'target': '%v0',
    'receiver_object': 'fmt',
    'field': 'Printf'},
    {'operation': 'call_stmt',
    'parent_stmt_id': 32,
    'stmt_id': 34,
    'attr': None,
    'target': '%v1',
    'name': '%v0',
    'type_parameters': None,
    'args': '[\'"Outer loop: %d\\\\n"\', \'i\']'},
    {'operation': 'if_stmt',
    'parent_stmt_id': 32,
    'stmt_id': 35,
    'condition': 'gg',
    'then_body': 36},
    {'operation': 'block_start', 'stmt_id': 36, 'parent_stmt_id': 35},
    {'operation': 'break_stmt', 'parent_stmt_id': 36, 'stmt_id': 37, 'target': ''},
    {'operation': 'block_end', 'stmt_id': 36, 'parent_stmt_id': 35},
    {'operation': 'forin_stmt',
    'parent_stmt_id': 32,
    'stmt_id': 38,
    'name': 'j',
    'target': 'numbers',
    'body': 39},
    {'operation': 'block_start', 'stmt_id': 39, 'parent_stmt_id': 38},
    {'operation': 'field_read',
    'parent_stmt_id': 39,
    'stmt_id': 40,
    'target': '%v0',
    'receiver_object': 'fmt',
    'field': 'Printf'},
    {'operation': 'call_stmt',
    'parent_stmt_id': 39,
    'stmt_id': 41,
    'attr': None,
    'target': '%v1',
    'name': '%v0',
    'type_parameters': None,
    'args': '[\'"Inner loop: %d\\\\n"\', \'j\']'},
    {'operation': 'assign_stmt',
    'parent_stmt_id': 39,
    'stmt_id': 42,
    'target': '%v2',
    'operator': '==',
    'operand': 'j',
    'operand2': '1'},
    {'operation': 'if_stmt',
    'parent_stmt_id': 39,
    'stmt_id': 43,
    'condition': '%v2',
    'then_body': 44},
    {'operation': 'block_start', 'stmt_id': 44, 'parent_stmt_id': 43},
    {'operation': 'break_stmt',
    'parent_stmt_id': 44,
    'stmt_id': 45,
    'target': 'outerLoop'},
    {'operation': 'block_end', 'stmt_id': 44, 'parent_stmt_id': 43},
    {'operation': 'assign_stmt',
    'parent_stmt_id': 39,
    'stmt_id': 46,
    'target': '%v3',
    'operator': '>',
    'operand': 'j',
    'operand2': '6'},
    {'operation': 'if_stmt',
    'parent_stmt_id': 39,
    'stmt_id': 47,
    'condition': '%v3',
    'then_body': 48},
    {'operation': 'block_start', 'stmt_id': 48, 'parent_stmt_id': 47},
    {'operation': 'break_stmt', 'parent_stmt_id': 48, 'stmt_id': 49, 'target': ''},
    {'operation': 'continue_stmt',
    'parent_stmt_id': 48,
    'stmt_id': 50,
    'target': ''},
    {'operation': 'block_end', 'stmt_id': 48, 'parent_stmt_id': 47},
    {'operation': 'block_end', 'stmt_id': 39, 'parent_stmt_id': 38},
    {'operation': 'block_end', 'stmt_id': 32, 'parent_stmt_id': 31},
    {'operation': 'assign_stmt',
    'parent_stmt_id': 29,
    'stmt_id': 51,
    'target': '%v0',
    'operator': '+',
    'operand': 'eex',
    'operand2': '1'},
    {'operation': 'block_end', 'stmt_id': 29, 'parent_stmt_id': 28},
    {'operation': 'method_decl',
    'parent_stmt_id': 0,
    'stmt_id': 52,
    'name': 'Emp',
    'type_parameters': None,
    'parameters': None,
    'data_type': None,
    'body': 53},
    {'operation': 'block_start', 'stmt_id': 53, 'parent_stmt_id': 52},
    {'operation': 'forin_stmt',
    'parent_stmt_id': 53,
    'stmt_id': 54,
    'name': '%v0',
    'target': 'numbers',
    'array_read': None,
    'body': None},
    {'operation': 'block_end', 'stmt_id': 53, 'parent_stmt_id': 52},
    {'operation': 'method_decl',
    'parent_stmt_id': 0,
    'stmt_id': 55,
    'name': 'EmpBreak',
    'type_parameters': None,
    'parameters': None,
    'data_type': None,
    'body': 56},
    {'operation': 'block_start', 'stmt_id': 56, 'parent_stmt_id': 55},
    {'operation': 'forin_stmt',
    'parent_stmt_id': 56,
    'stmt_id': 57,
    'name': '%v0',
    'target': 'numbers',
    'array_read': None,
    'body': 58},
    {'operation': 'block_start', 'stmt_id': 58, 'parent_stmt_id': 57},
    {'operation': 'break_stmt', 'parent_stmt_id': 58, 'stmt_id': 59, 'target': ''},
    {'operation': 'block_end', 'stmt_id': 58, 'parent_stmt_id': 57},
    {'operation': 'block_end', 'stmt_id': 56, 'parent_stmt_id': 55}]
    [DEBUG]: analysis_phase name: control_flow index:0
    [DEBUG]: _add_one_edge:12->13, weight=None
    [DEBUG]: _add_one_edge:13->14, weight=None
    [DEBUG]: _add_one_edge:14->15, weight=None
    [DEBUG]: _add_one_edge:15->16, weight=None
    [DEBUG]: _add_one_edge:16->17, weight=None
    [DEBUG]: _add_one_edge:17->18, weight=None
    [DEBUG]: _add_one_edge:18->21, weight=None
    [DEBUG]: _add_one_edge:21->22, weight=None
    [DEBUG]: _add_one_edge:22->19, weight=3
    [DEBUG]: _add_one_edge:19->24, weight=4
    [DEBUG]: _add_one_edge:24->25, weight=None
    [DEBUG]: _add_one_edge:25->19, weight=3
    [DEBUG]: _add_one_edge:19->26, weight=5
    [DEBUG]: _add_one_edge:26->27, weight=None
    [DEBUG]: _add_one_edge:27->-1, weight=None
    [DEBUG]: analysis_phase name: control_flow index:0
    [DEBUG]: _add_one_edge:30->31, weight=3
    [DEBUG]: _add_one_edge:31->33, weight=4
    [DEBUG]: _add_one_edge:33->34, weight=None
    [DEBUG]: _add_one_edge:34->35, weight=None
    [DEBUG]: _add_one_edge:35->37, weight=1
    [DEBUG]: _add_one_edge:35->38, weight=2
    [DEBUG]: _add_one_edge:38->40, weight=4
    [DEBUG]: _add_one_edge:40->41, weight=None
    [DEBUG]: _add_one_edge:41->42, weight=None
    [DEBUG]: _add_one_edge:42->43, weight=None
    [DEBUG]: _add_one_edge:43->45, weight=1
    [DEBUG]: _add_one_edge:43->46, weight=2
    [DEBUG]: _add_one_edge:46->47, weight=None
    [DEBUG]: _add_one_edge:47->49, weight=1
    [DEBUG]: _add_one_edge:47->38, weight=2
    [DEBUG]: _add_one_edge:38->31, weight=5
    [DEBUG]: _add_one_edge:49->31, weight=6
    [DEBUG]: _add_one_edge:31->51, weight=5
    [DEBUG]: _add_one_edge:37->51, weight=6
    [DEBUG]: _add_one_edge:45->51, weight=6
    [DEBUG]: _add_one_edge:51->-1, weight=None
    [DEBUG]: analysis_phase name: control_flow index:0
    [DEBUG]: _add_one_edge:54->54, weight=4
    [DEBUG]: _add_one_edge:54->-1, weight=5
    [DEBUG]: analysis_phase name: control_flow index:0
    [DEBUG]: _add_one_edge:57->59, weight=4
    [DEBUG]: _add_one_edge:57->-1, weight=5
    [DEBUG]: _add_one_edge:59->-1, weight=6
    === target file ===
    /app/experiment_3/tests/resource/control_flow/go/forin.go
    + reference answer
    [(12, 13, 0),
    (13, 14, 0),
    (14, 15, 0),
    (15, 16, 0),
    (16, 17, 0),
    (17, 18, 0),
    (18, 21, 0),
    (19, 24, 4),
    (19, 26, 5),
    (21, 22, 0),
    (22, 19, 3),
    (24, 25, 0),
    (25, 19, 3),
    (26, 27, 0),
    (27, -1, 0),
    (30, 31, 3),
    (31, 33, 4),
    (31, 51, 5),
    (33, 34, 0),
    (34, 35, 0),
    (35, 37, 1),
    (35, 38, 2),
    (37, 51, 6),
    (38, 31, 5),
    (38, 40, 4),
    (40, 41, 0),
    (41, 42, 0),
    (42, 43, 0),
    (43, 45, 1),
    (43, 46, 2),
    (45, 51, 6),
    (46, 47, 0),
    (47, 38, 2),
    (47, 49, 1),
    (49, 31, 6),
    (51, -1, 0),
    (54, -1, 5),
    (54, 54, 4),
    (57, -1, 5),
    (57, 59, 4),
    (59, -1, 6)]
    + current result
    [(12, 13, 0),
    (13, 14, 0),
    (14, 15, 0),
    (15, 16, 0),
    (16, 17, 0),
    (17, 18, 0),
    (18, 21, 0),
    (19, 24, 4),
    (19, 26, 5),
    (21, 22, 0),
    (22, 19, 3),
    (24, 25, 0),
    (25, 19, 3),
    (26, 27, 0),
    (27, -1, 0),
    (30, 31, 3),
    (31, 33, 4),
    (31, 51, 5),
    (33, 34, 0),
    (34, 35, 0),
    (35, 37, 1),
    (35, 38, 2),
    (37, 51, 6),
    (38, 31, 5),
    (38, 40, 4),
    (40, 41, 0),
    (41, 42, 0),
    (42, 43, 0),
    (43, 45, 1),
    (43, 46, 2),
    (45, 51, 6),
    (46, 47, 0),
    (47, 38, 2),
    (47, 49, 1),
    (49, 31, 6),
    (51, -1, 0),
    (54, -1, 5),
    (54, 54, 4),
    (57, -1, 5),
    (57, 59, 4),
    (59, -1, 6)]
    ```
3. 郑仁哲部分
    1. return.go
    ```go
   
    func SimpleReturn() {
    fmt.Println("Executing SimpleReturn")
    return
   }

    func ReturnValue() int {
    return 42
   }


   func ReturnVariable() string {
    message := "Hello, world!"
    return message
   }
   func ReturnExpression(a, b int) int {
    result := a + b
    return result
   }
     func ReturnMultipleValues() (int, string) {
     return 10, "ten"
     }


    func ReturnWithError(value int) (int, error) {
    if value < 0 {
        return 0, errors.New("negative value provided")
    }
    return value, nil
    }


    func ReturnFromIf(value int) string {
    if value > 0 {
        return "positive"
    } else {
        return "non-positive"
    }
    }

    func ReturnFromLoop(numbers []int, target int) bool {
    for _, number := range numbers {
        if number == target {
            return true
        }
    }
    return false
    }
    ```
    2.goto.go
   ```go
   func main() {
    fmt.Println("Start")
    goto Skip
    fmt.Println("This will not be printed")
   Skip:
    fmt.Println("Skipped to here")

    for i := 0; i < 5; i++ {
        if i == 2 {
            goto Found
        }
    }
    fmt.Println("Not found")
   Found:
    fmt.Println("Found at 2")

    if true {
        goto InsideIf
    } else {
        fmt.Println("In the else block")
    }
   InsideIf:
    fmt.Println("Inside if block")

   }
   ```
   3.method_decl.go
   ```go
   type Calculator struct{}

   func (c Calculator) Clear() {
    fmt.Println("Calculator cleared")
   }

   type Rectangle struct {
    width, height float64
   }

   func (r Rectangle) Area() float64 {
    return r.width * r.height
   }

   ```
2.测试结果依次为：
（1）                  'type_parameters': [],
                  'parameters': [],
                  'data_type': [],
                  'body': [{'field_read': {'target': '%v0',
                                           'receiver_object': 'fmt',
                                           'field': 'Println'}},
                           {'call_stmt': {'attr': [],
                                          'target': '%v1',
                                          'name': '%v0',
                                          'type_parameters': [],
                                          'args': ['"Executing '
                                                   'SimpleReturn"']}},
                           {'return': {'target': ''}}]}},
 {'method_decl': {'name': 'ReturnValue',
                  'type_parameters': [],
                  'parameters': [],
                  'data_type': 'int',
                  'body': [{'return': {'target': '42'}}]}},
 {'method_decl': {'name': 'ReturnVariable',
                  'type_parameters': [],
                  'parameters': [],
                  'data_type': 'string',
                  'body': [{'variable_decl': {'attr': 'short_var',
                                              'data_type': '',
                                              'name': 'message'}},
                           {'assign_stmt': {'target': 'message',
                                            'operand': '"'}},
                           {'return': {'target': 'message'}}]}},
 {'method_decl': {'name': 'ReturnExpression',
                  'type_parameters': [],
                  'parameters': [[{'parameter_decl': {'name': 'a',
                                                      'data_type': 'int'}},
                                  {'parameter_decl': {'name': 'b',
                                                      'data_type': 'int'}}]],
                  'data_type': 'int',
                  'body': [{'assign_stmt': {'target': '%v0',
                                            'operator': '+',
                                            'operand': 'a',
                                            'operand2': 'b'}},
                           {'variable_decl': {'attr': 'short_var',
                                              'data_type': '',
                                              'name': 'result'}},
                           {'assign_stmt': {'target': 'result',
                                            'operand': '%'}},
                           {'return': {'target': 'result'}}]}},
 {'method_decl': {'name': 'ReturnMultipleValues',
                  'type_parameters': [],
                  'parameters': [],
                  'data_type': [[{'parameter_decl': {'data_type': 'int'}},
                                 {'parameter_decl': {'data_type': 'string'}}]],
                  'body': [{'return': {'target': ['10', '"ten"']}}]}},
 {'method_decl': {'name': 'ReturnWithError',
                  'type_parameters': [],
                  'parameters': [[{'parameter_decl': {'name': 'value',
                                                      'data_type': 'int'}}]],
                  'data_type': [[{'parameter_decl': {'data_type': 'int'}},
                                 {'parameter_decl': {'data_type': 'error'}}]],
                  'body': [{'assign_stmt': {'target': '%v0',
                                            'operator': '<',
                                            'operand': 'value',
                                            'operand2': '0'}},
                           {'if_stmt': {'condition': '%v0',
                                        'then_body': [{'field_read': {'target': '%v0',    
                                                                      'receiver_object': 'errors',
                                                                      'field': 'New'}},   
                                                      {'call_stmt': {'attr': [],
                                                                     'target': '%v1',     
                                                                     'name': '%v0',       
                                                                     'type_parameters': [],
                                                                     'args': ['"negative '
                                                                              'value '    
                                                                              'provided"']}},
                                                      {'return': {'target': ['0',
                                                                             '%v1']}}]}}, 
                           {'return': {'target': ['value', 'nil']}}]}},
 {'method_decl': {'name': 'ReturnFromIf',
                  'type_parameters': [],
                  'parameters': [[{'parameter_decl': {'name': 'value',
                                                      'data_type': 'int'}}]],
                  'data_type': 'string',
                  'body': [{'assign_stmt': {'target': '%v0',
                                            'operator': '>',
                                            'operand': 'value',
                                            'operand2': '0'}},
                           {'if_stmt': {'condition': '%v0',
                                        'then_body': [{'return': {'target': '"positive"'}}],
                                        'else_body': [{'return': {'target': '"non-positive"'}}]}}]}},
 {'method_decl': {'name': 'ReturnFromLoop',
                  'type_parameters': [],
                  'parameters': [[{'parameter_decl': {'name': 'numbers',
                                                      'data_type': ['slice_type',
                                                                    {'element': 'int'}]}},
                                  {'parameter_decl': {'name': 'target',
                                                      'data_type': 'int'}}]],
                  'data_type': 'bool',
                  'body': [{'forin_stmt': {'name': '%v0',
                                           'target': 'numbers',
                                           'array_read': [{'target': '_',
                                                           'array': '%v0',
                                                           'index': 0},
                                                          {'target': 'number',
                                                           'array': '%v0',
                                                           'index': 1}],
                                           'body': [{'assign_stmt': {'target': '%v0',     
                                                                     'operator': '==',    
                                                                     'operand': 'number', 
                                                                     'operand2': 'target'}},
                                                    {'if_stmt': {'condition': '%v0',      
                                                                 'then_body': [{'return': {'target': 'true'}}]}}]}},
                           {'return': {'target': 'false'}}]}}]
[{'operation': 'method_decl',
  'parent_stmt_id': 0,
  'stmt_id': 10,
  'name': 'SimpleReturn',
  'type_parameters': None,
  'parameters': None,
  'data_type': None,
  'body': 11},
 {'operation': 'block_start', 'stmt_id': 11, 'parent_stmt_id': 10},
 {'operation': 'field_read',
  'parent_stmt_id': 11,
  'stmt_id': 12,
  'target': '%v0',
  'receiver_object': 'fmt',
  'field': 'Println'},
 {'operation': 'call_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 13,
  'attr': None,
  'target': '%v1',
  'name': '%v0',
  'type_parameters': None,
  'args': '[\'"Executing SimpleReturn"\']'},
 {'operation': 'return', 'parent_stmt_id': 11, 'stmt_id': 14, 'target': ''},
 {'operation': 'block_end', 'stmt_id': 11, 'parent_stmt_id': 10},
 {'operation': 'method_decl',
  'parent_stmt_id': 0,
  'stmt_id': 15,
  'name': 'ReturnValue',
  'type_parameters': None,
  'parameters': None,
  'data_type': 'int',
  'body': 16},
 {'operation': 'block_start', 'stmt_id': 16, 'parent_stmt_id': 15},
 {'operation': 'return', 'parent_stmt_id': 16, 'stmt_id': 17, 'target': '42'},
 {'operation': 'block_end', 'stmt_id': 16, 'parent_stmt_id': 15},
 {'operation': 'method_decl',
  'parent_stmt_id': 0,
  'stmt_id': 18,
  'name': 'ReturnVariable',
  'type_parameters': None,
  'parameters': None,
  'data_type': 'string',
  'body': 19},
 {'operation': 'block_start', 'stmt_id': 19, 'parent_stmt_id': 18},
 {'operation': 'variable_decl',
  'parent_stmt_id': 19,
  'stmt_id': 20,
  'attr': 'short_var',
  'data_type': '',
  'name': 'message'},
 {'operation': 'assign_stmt',
  'parent_stmt_id': 19,
  'stmt_id': 21,
  'target': 'message',
  'operand': '"'},
 {'operation': 'return',
  'parent_stmt_id': 19,
  'stmt_id': 22,
  'target': 'message'},
 {'operation': 'block_end', 'stmt_id': 19, 'parent_stmt_id': 18},
 {'operation': 'method_decl',
  'parent_stmt_id': 0,
  'stmt_id': 23,
  'name': 'ReturnExpression',
  'type_parameters': None,
  'parameters': "[[{'parameter_decl': {'name': 'a', 'data_type': 'int'}}, "
                "{'parameter_decl': {'name': 'b', 'data_type': 'int'}}]]",
  'data_type': 'int',
  'body': 24},
 {'operation': 'block_start', 'stmt_id': 24, 'parent_stmt_id': 23},
 {'operation': 'assign_stmt',
  'parent_stmt_id': 24,
  'stmt_id': 25,
  'target': '%v0',
  'operator': '+',
  'operand': 'a',
  'operand2': 'b'},
 {'operation': 'variable_decl',
  'parent_stmt_id': 24,
  'stmt_id': 26,
  'attr': 'short_var',
  'data_type': '',
  'name': 'result'},
 {'operation': 'assign_stmt',
  'parent_stmt_id': 24,
  'stmt_id': 27,
  'target': 'result',
  'operand': '%'},
 {'operation': 'return',
  'parent_stmt_id': 24,
  'stmt_id': 28,
  'target': 'result'},
 {'operation': 'block_end', 'stmt_id': 24, 'parent_stmt_id': 23},
 {'operation': 'method_decl',
  'parent_stmt_id': 0,
  'stmt_id': 29,
  'name': 'ReturnMultipleValues',
  'type_parameters': None,
  'parameters': None,
  'data_type': "[[{'parameter_decl': {'data_type': 'int'}}, {'parameter_decl': "
               "{'data_type': 'string'}}]]",
  'body': 30},
 {'operation': 'block_start', 'stmt_id': 30, 'parent_stmt_id': 29},
 {'operation': 'return',
  'parent_stmt_id': 30,
  'stmt_id': 31,
  'target': '[\'10\', \'"ten"\']'},
 {'operation': 'block_end', 'stmt_id': 30, 'parent_stmt_id': 29},
 {'operation': 'method_decl',
  'parent_stmt_id': 0,
  'stmt_id': 32,
  'name': 'ReturnWithError',
  'type_parameters': None,
  'parameters': "[[{'parameter_decl': {'name': 'value', 'data_type': 'int'}}]]",
  'data_type': "[[{'parameter_decl': {'data_type': 'int'}}, {'parameter_decl': "
               "{'data_type': 'error'}}]]",
  'body': 33},
 {'operation': 'block_start', 'stmt_id': 33, 'parent_stmt_id': 32},
 {'operation': 'assign_stmt',
  'parent_stmt_id': 33,
  'stmt_id': 34,
  'target': '%v0',
  'operator': '<',
  'operand': 'value',
  'operand2': '0'},
 {'operation': 'if_stmt',
  'parent_stmt_id': 33,
  'stmt_id': 35,
  'condition': '%v0',
  'then_body': 36},
 {'operation': 'block_start', 'stmt_id': 36, 'parent_stmt_id': 35},
 {'operation': 'field_read',
  'parent_stmt_id': 36,
  'stmt_id': 37,
  'target': '%v0',
  'receiver_object': 'errors',
  'field': 'New'},
 {'operation': 'call_stmt',
  'parent_stmt_id': 36,
  'stmt_id': 38,
  'attr': None,
  'target': '%v1',
  'name': '%v0',
  'type_parameters': None,
  'args': '[\'"negative value provided"\']'},
 {'operation': 'return',
  'parent_stmt_id': 36,
  'stmt_id': 39,
  'target': "['0', '%v1']"},
 {'operation': 'block_end', 'stmt_id': 36, 'parent_stmt_id': 35},
 {'operation': 'return',
  'parent_stmt_id': 33,
  'stmt_id': 40,
  'target': "['value', 'nil']"},
 {'operation': 'block_end', 'stmt_id': 33, 'parent_stmt_id': 32},
 {'operation': 'method_decl',
  'parent_stmt_id': 0,
  'stmt_id': 41,
  'name': 'ReturnFromIf',
  'type_parameters': None,
  'parameters': "[[{'parameter_decl': {'name': 'value', 'data_type': 'int'}}]]",
  'data_type': 'string',
  'body': 42},
 {'operation': 'block_start', 'stmt_id': 42, 'parent_stmt_id': 41},
 {'operation': 'assign_stmt',
  'parent_stmt_id': 42,
  'stmt_id': 43,
  'target': '%v0',
  'operator': '>',
  'operand': 'value',
  'operand2': '0'},
 {'operation': 'if_stmt',
  'parent_stmt_id': 42,
  'stmt_id': 44,
  'condition': '%v0',
  'then_body': 45,
  'else_body': 47},
 {'operation': 'block_start', 'stmt_id': 45, 'parent_stmt_id': 44},
 {'operation': 'return',
  'parent_stmt_id': 45,
  'stmt_id': 46,
  'target': '"positive"'},
 {'operation': 'block_end', 'stmt_id': 45, 'parent_stmt_id': 44},
 {'operation': 'block_start', 'stmt_id': 47, 'parent_stmt_id': 44},
 {'operation': 'return',
  'parent_stmt_id': 47,
  'stmt_id': 48,
  'target': '"non-positive"'},
 {'operation': 'block_end', 'stmt_id': 47, 'parent_stmt_id': 44},
 {'operation': 'block_end', 'stmt_id': 42, 'parent_stmt_id': 41},
 {'operation': 'method_decl',
  'parent_stmt_id': 0,
  'stmt_id': 49,
  'name': 'ReturnFromLoop',
  'type_parameters': None,
  'parameters': "[[{'parameter_decl': {'name': 'numbers', 'data_type': "
                "['slice_type', {'element': 'int'}]}}, {'parameter_decl': "
                "{'name': 'target', 'data_type': 'int'}}]]",
  'data_type': 'bool',
  'body': 50},
 {'operation': 'block_start', 'stmt_id': 50, 'parent_stmt_id': 49},
 {'operation': 'forin_stmt',
  'parent_stmt_id': 50,
  'stmt_id': 51,
  'name': '%v0',
  'target': 'numbers',
  'array_read': 52,
  'body': 55},
 {'operation': 'block_start', 'stmt_id': 52, 'parent_stmt_id': 51},
 {'operation': 'target', 'parent_stmt_id': 52, 'stmt_id': 53},
 {'operation': 'target', 'parent_stmt_id': 52, 'stmt_id': 54},
 {'operation': 'block_end', 'stmt_id': 52, 'parent_stmt_id': 51},
 {'operation': 'block_start', 'stmt_id': 55, 'parent_stmt_id': 51},
 {'operation': 'assign_stmt',
  'parent_stmt_id': 55,
  'stmt_id': 56,
  'target': '%v0',
  'operator': '==',
  'operand': 'number',
  'operand2': 'target'},
 {'operation': 'if_stmt',
  'parent_stmt_id': 55,
  'stmt_id': 57,
  'condition': '%v0',
  'then_body': 58},
 {'operation': 'block_start', 'stmt_id': 58, 'parent_stmt_id': 57},
 {'operation': 'return', 'parent_stmt_id': 58, 'stmt_id': 59, 'target': 'true'},
 {'operation': 'block_end', 'stmt_id': 58, 'parent_stmt_id': 57},
 {'operation': 'block_end', 'stmt_id': 55, 'parent_stmt_id': 51},
 {'operation': 'return',
  'parent_stmt_id': 50,
  'stmt_id': 60,
  'target': 'false'},
 {'operation': 'block_end', 'stmt_id': 50, 'parent_stmt_id': 49}]
[DEBUG]: analysis_phase name: control_flow index:0
[DEBUG]: _add_one_edge:12->13, weight=None
[DEBUG]: _add_one_edge:13->14, weight=None
[DEBUG]: _add_one_edge:14->-1, weight=None
[DEBUG]: analysis_phase name: control_flow index:0
[DEBUG]: _add_one_edge:17->-1, weight=None
[DEBUG]: analysis_phase name: control_flow index:0
[DEBUG]: _add_one_edge:20->21, weight=None
[DEBUG]: _add_one_edge:21->22, weight=None
[DEBUG]: _add_one_edge:22->-1, weight=None
/app/experiment_3/src/lian/util/dataframe_operation.py:271: FutureWarning: elementwise comparison failed; returning scalar instead, but in the future will perform elementwise comparison
  query = (self.stmt_id.values == block_id)
<__array_function__ internals>:200: DeprecationWarning: Calling nonzero on 0d arrays is deprecated, as it behaves surprisingly. Use `atleast_1d(cond).nonzero()` if the old behavior was intended. If the context of this warning is of the form `arr[nonzero(cond)]`, just use `arr[cond]`.
[DEBUG]: analysis_phase name: control_flow index:0
[DEBUG]: _add_one_edge:25->26, weight=None
[DEBUG]: _add_one_edge:26->27, weight=None
[DEBUG]: _add_one_edge:27->28, weight=None
[DEBUG]: _add_one_edge:28->-1, weight=None
[DEBUG]: analysis_phase name: control_flow index:0
[DEBUG]: _add_one_edge:31->-1, weight=None
[DEBUG]: analysis_phase name: control_flow index:0
[DEBUG]: _add_one_edge:34->35, weight=None
[DEBUG]: _add_one_edge:35->37, weight=1
[DEBUG]: _add_one_edge:37->38, weight=None
[DEBUG]: _add_one_edge:38->39, weight=None
[DEBUG]: _add_one_edge:39->40, weight=None
[DEBUG]: _add_one_edge:35->40, weight=2
[DEBUG]: _add_one_edge:40->-1, weight=None
[DEBUG]: analysis_phase name: control_flow index:0
[DEBUG]: _add_one_edge:43->44, weight=None
[DEBUG]: _add_one_edge:44->46, weight=1
[DEBUG]: _add_one_edge:44->48, weight=2
[DEBUG]: _add_one_edge:46->-1, weight=None
[DEBUG]: _add_one_edge:48->-1, weight=None
[DEBUG]: analysis_phase name: control_flow index:0
[DEBUG]: _add_one_edge:53->54, weight=None
[DEBUG]: _add_one_edge:54->51, weight=3
[DEBUG]: _add_one_edge:51->56, weight=4
[DEBUG]: _add_one_edge:56->57, weight=None
[DEBUG]: _add_one_edge:57->59, weight=1
[DEBUG]: _add_one_edge:59->51, weight=3
[DEBUG]: _add_one_edge:57->51, weight=2
[DEBUG]: _add_one_edge:51->60, weight=5
[DEBUG]: _add_one_edge:60->-1, weight=None
=== target file ===
/app/experiment_3/tests/resource/control_flow/go/return.go
+ reference answer
[(12, 13, 0),
 (13, 14, 0),
 (14, -1, 0),
 (17, -1, 0),
 (20, 21, 0),
 (21, 22, 0),
 (22, -1, 0),
 (25, 26, 0),
 (26, 27, 0),
 (27, 28, 0),
 (28, -1, 0),
 (31, -1, 0),
 (34, 35, 0),
 (35, 37, 1),
 (35, 40, 2),
 (37, 38, 0),
 (38, 39, 0),
 (39, 40, 0),
 (40, -1, 0),
 (43, 44, 0),
 (44, 46, 1),
 (44, 48, 2),
 (46, -1, 0),
 (48, -1, 0),
 (51, 56, 4),
 (51, 60, 5),
 (53, 54, 0),
 (54, 51, 3),
 (56, 57, 0),
 (57, 51, 2),
 (57, 59, 1),
 (59, 51, 3),
 (60, -1, 0)]
+ current result
[(12, 13, 0),
 (13, 14, 0),
 (14, -1, 0),
 (17, -1, 0),
 (20, 21, 0),
 (21, 22, 0),
 (22, -1, 0),
 (25, 26, 0),
 (26, 27, 0),
 (27, 28, 0),
 (28, -1, 0),
 (31, -1, 0),
 (34, 35, 0),
 (35, 37, 1),
 (35, 40, 2),
 (37, 38, 0),
 (38, 39, 0),
 (39, 40, 0),
 (40, -1, 0),
 (43, 44, 0),
 (44, 46, 1),
 (44, 48, 2),
 (46, -1, 0),
 (48, -1, 0),
 (51, 56, 4),
 (51, 60, 5),
 (53, 54, 0),
 (54, 51, 3),
 (56, 57, 0),
 (57, 51, 2),
 (57, 59, 1),
 (59, 51, 3),
 (60, -1, 0)]
（2）  [{'method_decl': {'name': 'main',
                  'type_parameters': [],
                  'parameters': [],
                  'data_type': [],
                  'body': [{'field_read': {'target': '%v0',
                                           'receiver_object': 'fmt',
                                           'field': 'Println'}},
                           {'call_stmt': {'attr': [],
                                          'target': '%v1',
                                          'name': '%v0',
                                          'type_parameters': [],
                                          'args': ['"Start"']}},
                           {'goto_stmt': {'target': 'Skip'}},
                           {'field_read': {'target': '%v2',
                                           'receiver_object': 'fmt',
                                           'field': 'Println'}},
                           {'call_stmt': {'attr': [],
                                          'target': '%v3',
                                          'name': '%v2',
                                          'type_parameters': [],
                                          'args': ['"This will not be '
                                                   'printed"']}},
                           {'label_stmt': {'name': 'Skip'}},
                           {'field_read': {'target': '%v4',
                                           'receiver_object': 'fmt',
                                           'field': 'Println'}},
                           {'call_stmt': {'attr': [],
                                          'target': '%v5',
                                          'name': '%v4',
                                          'type_parameters': [],
                                          'args': ['"Skipped to here"']}},
                           {'for_stmt': {'init_body': [{'variable_decl': {'attr': 'short_var',
                                                                          'data_type': '',
                                                                          'name': 'i'}},  
                                                       {'assign_stmt': {'target': 'i',    
                                                                        'operand': '0'}}],
                                         'condition': '%v0',
                                         'condition_prebody': [{'assign_stmt': {'target': '%v0',
                                                                                'operator': '<',
                                                                                'operand': 'i',
                                                                                'operand2': '5'}}],
                                         'update_body': [{'inc_stmt': {'target': 'i'}}],  
                                         'body': [{'assign_stmt': {'target': '%v0',       
                                                                   'operator': '==',      
                                                                   'operand': 'i',        
                                                                   'operand2': '2'}},     
                                                  {'if_stmt': {'condition': '%v0',        
                                                               'then_body': [{'goto_stmt': {'target': 'Found'}}]}}]}},
                           {'field_read': {'target': '%v6',
                                           'receiver_object': 'fmt',
                                           'field': 'Println'}},
                           {'call_stmt': {'attr': [],
                                          'target': '%v7',
                                          'name': '%v6',
                                          'type_parameters': [],
                                          'args': ['"Not found"']}},
                           {'label_stmt': {'name': 'Found'}},
                           {'field_read': {'target': '%v8',
                                           'receiver_object': 'fmt',
                                           'field': 'Println'}},
                           {'call_stmt': {'attr': [],
                                          'target': '%v9',
                                          'name': '%v8',
                                          'type_parameters': [],
                                          'args': ['"Found at 2"']}},
                           {'if_stmt': {'condition': 'true',
                                        'then_body': [{'goto_stmt': {'target': 'InsideIf'}}],
                                        'else_body': [{'field_read': {'target': '%v0',    
                                                                      'receiver_object': 'fmt',
                                                                      'field': 'Println'}},
                                                      {'call_stmt': {'attr': [],
                                                                     'target': '%v1',     
                                                                     'name': '%v0',       
                                                                     'type_parameters': [],
                                                                     'args': ['"In '      
                                                                              'the '      
                                                                              'else '     
                                                                              'block"']}}]}},
                           {'label_stmt': {'name': 'InsideIf'}},
                           {'field_read': {'target': '%v10',
                                           'receiver_object': 'fmt',
                                           'field': 'Println'}},
                           {'call_stmt': {'attr': [],
                                          'target': '%v11',
                                          'name': '%v10',
                                          'type_parameters': [],
                                          'args': ['"Inside if block"']}}]}}]
[{'operation': 'method_decl',
  'parent_stmt_id': 0,
  'stmt_id': 10,
  'name': 'main',
  'type_parameters': None,
  'parameters': None,
  'data_type': None,
  'body': 11},
 {'operation': 'block_start', 'stmt_id': 11, 'parent_stmt_id': 10},
 {'operation': 'field_read',
  'parent_stmt_id': 11,
  'stmt_id': 12,
  'target': '%v0',
  'receiver_object': 'fmt',
  'field': 'Println'},
 {'operation': 'call_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 13,
  'attr': None,
  'target': '%v1',
  'name': '%v0',
  'type_parameters': None,
  'args': '[\'"Start"\']'},
 {'operation': 'goto_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 14,
  'target': 'Skip'},
 {'operation': 'field_read',
  'parent_stmt_id': 11,
  'stmt_id': 15,
  'target': '%v2',
  'receiver_object': 'fmt',
  'field': 'Println'},
 {'operation': 'call_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 16,
  'attr': None,
  'target': '%v3',
  'name': '%v2',
  'type_parameters': None,
  'args': '[\'"This will not be printed"\']'},
 {'operation': 'label_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 17,
  'name': 'Skip'},
 {'operation': 'field_read',
  'parent_stmt_id': 11,
  'stmt_id': 18,
  'target': '%v4',
  'receiver_object': 'fmt',
  'field': 'Println'},
 {'operation': 'call_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 19,
  'attr': None,
  'target': '%v5',
  'name': '%v4',
  'type_parameters': None,
  'args': '[\'"Skipped to here"\']'},
 {'operation': 'for_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 20,
  'init_body': 21,
  'condition': '%v0',
  'condition_prebody': 24,
  'update_body': 26,
  'body': 28},
 {'operation': 'block_start', 'stmt_id': 21, 'parent_stmt_id': 20},
 {'operation': 'variable_decl',
  'parent_stmt_id': 21,
  'stmt_id': 22,
  'attr': 'short_var',
  'data_type': '',
  'name': 'i'},
 {'operation': 'assign_stmt',
  'parent_stmt_id': 21,
  'stmt_id': 23,
  'target': 'i',
  'operand': '0'},
 {'operation': 'block_end', 'stmt_id': 21, 'parent_stmt_id': 20},
 {'operation': 'block_start', 'stmt_id': 24, 'parent_stmt_id': 20},
 {'operation': 'assign_stmt',
  'parent_stmt_id': 24,
  'stmt_id': 25,
  'target': '%v0',
  'operator': '<',
  'operand': 'i',
  'operand2': '5'},
 {'operation': 'block_end', 'stmt_id': 24, 'parent_stmt_id': 20},
 {'operation': 'block_start', 'stmt_id': 26, 'parent_stmt_id': 20},
 {'operation': 'inc_stmt', 'parent_stmt_id': 26, 'stmt_id': 27, 'target': 'i'},
 {'operation': 'block_end', 'stmt_id': 26, 'parent_stmt_id': 20},
 {'operation': 'block_start', 'stmt_id': 28, 'parent_stmt_id': 20},
 {'operation': 'assign_stmt',
  'parent_stmt_id': 28,
  'stmt_id': 29,
  'target': '%v0',
  'operator': '==',
  'operand': 'i',
  'operand2': '2'},
 {'operation': 'if_stmt',
  'parent_stmt_id': 28,
  'stmt_id': 30,
  'condition': '%v0',
  'then_body': 31},
 {'operation': 'block_start', 'stmt_id': 31, 'parent_stmt_id': 30},
 {'operation': 'goto_stmt',
  'parent_stmt_id': 31,
  'stmt_id': 32,
  'target': 'Found'},
 {'operation': 'block_end', 'stmt_id': 31, 'parent_stmt_id': 30},
 {'operation': 'block_end', 'stmt_id': 28, 'parent_stmt_id': 20},
 {'operation': 'field_read',
  'parent_stmt_id': 11,
  'stmt_id': 33,
  'target': '%v6',
  'receiver_object': 'fmt',
  'field': 'Println'},
 {'operation': 'call_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 34,
  'attr': None,
  'target': '%v7',
  'name': '%v6',
  'type_parameters': None,
  'args': '[\'"Not found"\']'},
 {'operation': 'label_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 35,
  'name': 'Found'},
 {'operation': 'field_read',
  'parent_stmt_id': 11,
  'stmt_id': 36,
  'target': '%v8',
  'receiver_object': 'fmt',
  'field': 'Println'},
 {'operation': 'call_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 37,
  'attr': None,
  'target': '%v9',
  'name': '%v8',
  'type_parameters': None,
  'args': '[\'"Found at 2"\']'},
 {'operation': 'if_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 38,
  'condition': 'true',
  'then_body': 39,
  'else_body': 41},
 {'operation': 'block_start', 'stmt_id': 39, 'parent_stmt_id': 38},
 {'operation': 'goto_stmt',
  'parent_stmt_id': 39,
  'stmt_id': 40,
  'target': 'InsideIf'},
 {'operation': 'block_end', 'stmt_id': 39, 'parent_stmt_id': 38},
 {'operation': 'block_start', 'stmt_id': 41, 'parent_stmt_id': 38},
 {'operation': 'field_read',
  'parent_stmt_id': 41,
  'stmt_id': 42,
  'target': '%v0',
  'receiver_object': 'fmt',
  'field': 'Println'},
 {'operation': 'call_stmt',
  'parent_stmt_id': 41,
  'stmt_id': 43,
  'attr': None,
  'target': '%v1',
  'name': '%v0',
  'type_parameters': None,
  'args': '[\'"In the else block"\']'},
 {'operation': 'block_end', 'stmt_id': 41, 'parent_stmt_id': 38},
 {'operation': 'label_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 44,
  'name': 'InsideIf'},
 {'operation': 'field_read',
  'parent_stmt_id': 11,
  'stmt_id': 45,
  'target': '%v10',
  'receiver_object': 'fmt',
  'field': 'Println'},
 {'operation': 'call_stmt',
  'parent_stmt_id': 11,
  'stmt_id': 46,
  'attr': None,
  'target': '%v11',
  'name': '%v10',
  'type_parameters': None,
  'args': '[\'"Inside if block"\']'},
 {'operation': 'block_end', 'stmt_id': 11, 'parent_stmt_id': 10}]
[DEBUG]: analysis_phase name: control_flow index:0
[DEBUG]: _add_one_edge:12->13, weight=None
[DEBUG]: _add_one_edge:13->14, weight=None
[DEBUG]: _add_one_edge:15->16, weight=None
[DEBUG]: _add_one_edge:16->17, weight=None
[DEBUG]: _add_one_edge:14->17, weight=None
[DEBUG]: _add_one_edge:17->18, weight=None
[DEBUG]: _add_one_edge:18->19, weight=None
[DEBUG]: _add_one_edge:19->22, weight=None
[DEBUG]: _add_one_edge:22->23, weight=None
[DEBUG]: _add_one_edge:23->25, weight=None
[DEBUG]: _add_one_edge:25->20, weight=3
[DEBUG]: _add_one_edge:20->29, weight=4
[DEBUG]: _add_one_edge:29->30, weight=None
[DEBUG]: _add_one_edge:30->32, weight=1
[DEBUG]: _add_one_edge:30->27, weight=2
[DEBUG]: _add_one_edge:27->25, weight=None
[DEBUG]: _add_one_edge:20->33, weight=5
[DEBUG]: _add_one_edge:33->34, weight=None
[DEBUG]: _add_one_edge:34->35, weight=None
[DEBUG]: _add_one_edge:32->35, weight=None
[DEBUG]: _add_one_edge:35->36, weight=None
[DEBUG]: _add_one_edge:36->37, weight=None
[DEBUG]: _add_one_edge:37->38, weight=None
[DEBUG]: _add_one_edge:38->40, weight=1
[DEBUG]: _add_one_edge:38->42, weight=2
[DEBUG]: _add_one_edge:42->43, weight=None
[DEBUG]: _add_one_edge:43->44, weight=None
[DEBUG]: _add_one_edge:40->44, weight=None
[DEBUG]: _add_one_edge:44->45, weight=None
[DEBUG]: _add_one_edge:45->46, weight=None
[DEBUG]: _add_one_edge:46->-1, weight=None
=== target file ===
/app/experiment_3/tests/resource/control_flow/go/goto.go
+ reference answer
[(12, 13, 0),
 (13, 14, 0),
 (14, 17, 0),
 (15, 16, 0),
 (16, 17, 0),
 (17, 18, 0),
 (18, 19, 0),
 (19, 22, 0),
 (20, 29, 4),
 (20, 33, 5),
 (22, 23, 0),
 (23, 25, 0),
 (25, 20, 3),
 (27, 25, 0),
 (29, 30, 0),
 (30, 27, 2),
 (30, 32, 1),
 (32, 35, 0),
 (33, 34, 0),
 (34, 35, 0),
 (35, 36, 0),
 (36, 37, 0),
 (37, 38, 0),
 (38, 40, 1),
 (38, 42, 2),
 (40, 44, 0),
 (42, 43, 0),
 (43, 44, 0),
 (44, 45, 0),
 (45, 46, 0),
 (46, -1, 0)]
+ current result
[(12, 13, 0),
 (13, 14, 0),
 (14, 17, 0),
 (15, 16, 0),
 (16, 17, 0),
 (17, 18, 0),
 (18, 19, 0),
 (19, 22, 0),
 (20, 29, 4),
 (20, 33, 5),
 (22, 23, 0),
 (23, 25, 0),
 (25, 20, 3),
 (27, 25, 0),
 (29, 30, 0),
 (30, 27, 2),
 (30, 32, 1),
 (32, 35, 0),
 (33, 34, 0),
 (34, 35, 0),
 (35, 36, 0),
 (36, 37, 0),
 (37, 38, 0),
 (38, 40, 1),
 (38, 42, 2),
 (40, 44, 0),
 (42, 43, 0),
 (43, 44, 0),
 (44, 45, 0),
 (45, 46, 0),
 (46, -1, 0)]
  （3）
  [DEBUG]: Lang-Parser: /app/experiment_3/tests/lian_workspace/src/method_decl.go
[{'type_decl': {'attr': 'type',
                'name': 'Calculator',
                'type_parameters': '',
                'type': ['struct_type']}},
 {'method_decl': {'attr': [[{'parameter_decl': {'name': 'c',
                                                'data_type': 'Calculator'}}]],
                  'name': 'Clear',
                  'parameters': [],
                  'data_type': [],
                  'body': [{'field_read': {'target': '%v0',
                                           'receiver_object': 'fmt',
                                           'field': 'Println'}},
                           {'call_stmt': {'attr': [],
                                          'target': '%v1',
                                          'name': '%v0',
                                          'type_parameters': [],
                                          'args': ['"Calculator cleared"']}}]}},
 {'type_decl': {'attr': 'type',
                'name': 'Rectangle',
                'type_parameters': '',
                'type': ['struct_type',
                         {'name': 'height', 'type': 'float64', 'tag': []}]}},
 {'method_decl': {'attr': [[{'parameter_decl': {'name': 'r',
                                                'data_type': 'Rectangle'}}]],
                  'name': 'Area',
                  'parameters': [],
                  'data_type': 'float64',
                  'body': [{'field_read': {'target': '%v0',
                                           'receiver_object': 'r',
                                           'field': 'width'}},
                           {'field_read': {'target': '%v1',
                                           'receiver_object': 'r',
                                           'field': 'height'}},
                           {'assign_stmt': {'target': '%v2',
                                            'operator': '*',
                                            'operand': '%v0',
                                            'operand2': '%v1'}},
                           {'return': {'target': '%v2'}}]}}]
[{'operation': 'type_decl',
  'parent_stmt_id': 0,
  'stmt_id': 10,
  'attr': 'type',
  'name': 'Calculator',
  'type_parameters': '',
  'type': "['struct_type']"},
 {'operation': 'method_decl',
  'parent_stmt_id': 0,
  'stmt_id': 11,
  'attr': "[[{'parameter_decl': {'name': 'c', 'data_type': 'Calculator'}}]]",
  'name': 'Clear',
  'parameters': None,
  'data_type': None,
  'body': 12},
 {'operation': 'block_start', 'stmt_id': 12, 'parent_stmt_id': 11},
 {'operation': 'field_read',
  'parent_stmt_id': 12,
  'stmt_id': 13,
  'target': '%v0',
  'receiver_object': 'fmt',
  'field': 'Println'},
 {'operation': 'call_stmt',
  'parent_stmt_id': 12,
  'stmt_id': 14,
  'attr': None,
  'target': '%v1',
  'name': '%v0',
  'type_parameters': None,
  'args': '[\'"Calculator cleared"\']'},
 {'operation': 'block_end', 'stmt_id': 12, 'parent_stmt_id': 11},
 {'operation': 'type_decl',
  'parent_stmt_id': 0,
  'stmt_id': 15,
  'attr': 'type',
  'name': 'Rectangle',
  'type_parameters': '',
  'type': "['struct_type', {'name': 'height', 'type': 'float64', 'tag': []}]"},
 {'operation': 'method_decl',
  'parent_stmt_id': 0,
  'stmt_id': 16,
  'attr': "[[{'parameter_decl': {'name': 'r', 'data_type': 'Rectangle'}}]]",
  'name': 'Area',
  'parameters': None,
  'data_type': 'float64',
  'body': 17},
 {'operation': 'block_start', 'stmt_id': 17, 'parent_stmt_id': 16},
 {'operation': 'field_read',
  'parent_stmt_id': 17,
  'stmt_id': 18,
  'target': '%v0',
  'receiver_object': 'r',
  'field': 'width'},
 {'operation': 'field_read',
  'parent_stmt_id': 17,
  'stmt_id': 19,
  'target': '%v1',
  'receiver_object': 'r',
  'field': 'height'},
 {'operation': 'assign_stmt',
  'parent_stmt_id': 17,
  'stmt_id': 20,
  'target': '%v2',
  'operator': '*',
  'operand': '%v0',
  'operand2': '%v1'},
 {'operation': 'return', 'parent_stmt_id': 17, 'stmt_id': 21, 'target': '%v2'},
 {'operation': 'block_end', 'stmt_id': 17, 'parent_stmt_id': 16}]
[DEBUG]: analysis_phase name: control_flow index:0
[DEBUG]: _add_one_edge:13->14, weight=None
[DEBUG]: _add_one_edge:14->-1, weight=None
[DEBUG]: analysis_phase name: control_flow index:0
[DEBUG]: _add_one_edge:18->19, weight=None
[DEBUG]: _add_one_edge:19->20, weight=None
[DEBUG]: _add_one_edge:20->21, weight=None
[DEBUG]: _add_one_edge:21->-1, weight=None
=== target file ===
/app/experiment_3/tests/resource/control_flow/go/method_decl.go
+ reference answer
[(13, 14, 0), (14, -1, 0), (18, 19, 0), (19, 20, 0), (20, 21, 0), (21, -1, 0)]
+ current result
[(13, 14, 0), (14, -1, 0), (18, 19, 0), (19, 20, 0), (20, 21, 0), (21, -1, 0)]
