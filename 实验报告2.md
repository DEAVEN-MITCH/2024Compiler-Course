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