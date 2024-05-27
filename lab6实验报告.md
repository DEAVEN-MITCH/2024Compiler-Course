# 编译第五次实验实验报告
## 小组成员及分工
- 张佳和:
  stmt_handlers中`analyze_break_stmt`,`analyze_continue_stmt`,`analyze_label_stmt`,以及`analyze_for_stmt`的重写（改变原来不对的地方，并增加break\[label\]、continue\[label\]的处理）,编写continue.go、break.go测试用例来测试以上完成内容，修改test_cfg使得测试程序能测试以上用例。
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