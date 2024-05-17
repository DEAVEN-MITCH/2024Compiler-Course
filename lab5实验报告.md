# 编译第五次实验实验报告
## 小组成员及分工
- 宋岱桉：declaration中以下部分的解析以及对应测试用例、测试程序的编写
    ```js
        $.method_declaration
        $.import_declaration
        $.if_stmt中init部分关于declaration的补全
    ```
- 张佳和：type_declaration的编写和测试用例、程序的编写，并修改了composite_literal。编写parser_type函数处理各种类型（匿名结构体、接口等）
- 郑仁哲：以下部分的解析以及对应测试用例、测试程序的编写
    ```js
        $.package_clause
        $.function_declaration
    ```
## 实验思路及核心代码
1. 宋岱桉部分：
   1. method_declaration,使用method_decl，将结构体作为对象的第一个参数，并在attr中标记为'interface_method'.
   在解析参数列表时，使用了先前编写好的self.parse_parameters
   ```py
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
    ```
    2. import_declaration，用分支语句直接区分import一个spec还是一个spec列表，同时根据是否起了别名判断使用import_stmt还是import_as_stmt，代码如下：
   ```py
       def import_declaration(self, node, statements):
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
2. 张佳和部分：
   1. type_declaration部分，包括type_spec和type_alias两种情况，type_alias用type_alias_stmt解决，其中type部分需要用parser_type处理一下。type_spec分三个部分，name,type_parameters，和type。由于有type_parameters部分，后面的type可能是泛型类，于是均用decl而不是alias来简化处理逻辑。type先把括号递归去除，然后分三种情况处理，struct_type、interface_type和其它类型。struct_type和parser_type函数中处理匿名结构体方法类似，根据field_declaration的类型：有名域就增加对应的field,内嵌结构体就在nested_type中增加相应parse完后的type，并作为class_decl的attr记录下来。interface_type和parser_type函数中处理匿名接口方法类似，分别处理method_spec、struct_elem和constraint_elem，由于constraint_elem和struct_elem在glang中没有对应语句，直接用字符串表示存在nested_type和nested_constraints这两个列表中,并进一步保存在interface_decl的attr中;method_spec用method_decl处理记录在methods列表中。代码如下
   ```py
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
   ```
   2. type_parser部分，处理匿名类型，首先把可能的parenthesized_type的括号去除掉。得到_simple_type，再按实际类型分别处理。这边分为了struct、interface、pointer、array、slice、implicit_length_array、map、channel、function、union、negated、generic和其它类型分别处理，大体思路是把内嵌的表达式或类型递归parse，再按照对应格式返回类型的字符串。struct和interface用临时变量作为匿名的名称，其它的没有decl。代码如下
   ```py
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
    ```
   3. composite_literal部分的修改。原来嵌套的literal_value仅作了一层处理，更深层次没有处理直接字符串解析，这次编写了parse_literal_value函数用以递归处理它。由于没有类型检查机制，composite_literal中嵌套的literal_value无法确定类型，统一使用field_write来初始化父结构。parse_literal_value主要处理和原来composite_literal中第一层的literal_value处理过程类似，只是初始化语句统一使用field_write并且new_instance的data_type=None。parse_literal_value代码如下。composite_literal中有literal_value的地方均按需递归优化处理，太长就不放出来了,和parse_literal_value这里可以类比得到。
   ```py
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
   ```
3. 郑仁哲部分：
   1. 'package_clause' 函数主要用于解析 Go 语言的 package 声明节点，提取并验证包名，然后将其记录并输出。首先打印节点文本和结构以辅助调试。
   ```py
      def package_clause(self, node, statements):
        print(f"node: {self.read_node_text(node)}")
        print(f"node: {node.sexp()}")
        name = self.read_node_text(node.named_children[0])
        if name:
            statements.append({"package_stmt": {"name": name}})
   ```
   2.'function_declaration'方法，用于解析和处理 Go 语言中的函数声明。此方法首先打印节点的文本内容和结构，以帮助调试。然后，它按顺序提取函数名、类型参数、参数列表、返回类型和函数体：
   函数名：通过节点的 child_by_field_name('name') 获取，如果未找到则使用默认值 "UnnamedFunction"。
   类型参数：从 type_parameters 子节点中提取，如果存在。
   参数列表：通过调用 parameter_declaration 方法逐个解析 parameters 子节点中的每个参数。
   返回类型：从 result 子节点中提取文本作为返回类型，如果存在。 
   函数体：解析 body 子节点中的每条语句，使用 parse_statement 方法处理。
   最后，将所有这些信息聚合成一个字典，并将其添加到 statements 列表中。这个字典包括函数的名称、类型参数、参数列表、返回类型和函数体。函数结束时打印一条消息确认函数已被声明。
   ```py
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
   ```
## 测试用例与结果
1. 宋岱桉部分
   1. method_declaration
   测试代码：
   ```go
   func (a int) Add(b int, c int) int {
        return a + b + c
    }
    ```
   测试结果：
   [{'method_decl': {'attr': 'interface_method',
                    'data_type': 'int',
                  'name': 'Add',
                  'parameters': [{'parameter_decl': {'name': 'a',
                                                     'data_type': 'int',
                                                     'modifiers': []}},
                                 {'parameter_decl': {'name': 'b',
                                                     'data_type': 'int',
                                                     'modifiers': []}},
                                 {'parameter_decl': {'name': 'c',
                                                     'data_type': 'int',
                                                     'modifiers': []}}],
                  'body': [{'new_array': {'target': '%v0',
                                          'attr': None,
                                          'data_type': None}},
                           {'assign_stmt': {'target': '%v1',
                                            'operator': '+',
                                            'operand': 'a',
                                            'operand2': 'b'}},
                           {'assign_stmt': {'target': '%v2',
                                            'operator': '+',
                                            'operand': '%v1',
                                            'operand2': 'c'}},
                           {'array_write': {'array': '%v0',
                                            'index': '0',
                                            'source': '%v2'}},
                           {'return_stmt': {'target': '%v0'}}]}}]
    2. import_declaration
   测试代码：
   ```go
    import "fmt1"
    import myfmt "fmt2"
    import (
        "fmt3"
        "math"
    )
    import (
        "fmt4"
        m "math"
    )
    import . "fmt5"
    import _ "github.com/example/package"
    ```
    测试结果：
    {'import_stmt': {'name': '"fmt1"'}},
    {'import_as_stmt': {'name': '"fmt2"', 'alias': 'myfmt'}},
    {'import_stmt': {'name': '"fmt3"'}}, {'import_stmt': {'name': '"math"'}},
    {'import_stmt': {'name': '"fmt4"'}},
    {'import_as_stmt': {'name': '"math"', 'alias': 'm'}},
    {'import_as_stmt': {'name': '"fmt5"', 'alias': '.'}},
    {'import_as_stmt': {'name': '"github.com/example/package"', 'alias': '_'}}
2. 张佳和部分
    type_declaration.go用以type_declaration和composite_literal的递归解析。
    测试代码如下：
    ```go
    type MyInt int
    type MyFloat float64
    type MyString string
    type IntAlias = int
    type StringAlias = string
    type FloatAlias = float64
    type Person struct {
        Name string
        Age  int
    }

    type Address struct {
        Street string
        City   string
        State  string
        Zip    string
    }
    type Reader interface {
        Read(p []byte) (n int, err error)
    }

    type Writer interface {
        Write(p []byte) (n int, err error)
    }
    type IntArray [10]int
    type StringSlice []string
    type StringMap map[string]string
    type IntMap map[int]int
    type IntChannel chan int
    type StringChannel chan string
    type (
        MyInt int
        MyFloat float64
        MyString string
        Person struct {
            Name string
            Age  int
        }
        Address struct {
            Street string
            City   string
            State  string
            Zip    string
        }
        Reader interface {
            Read(p []byte) (n int, err error)
        }
        Writer interface {
            Write(p []byte) (n int, err error)
        }
        IntArray [10]int
        StringSlice []string
        StringMap map[string]string
        IntMap map[int]int
        IntChannel chan int
        StringChannel chan string
    )
    type Container[T any] struct {
        value T
    }
    type Number interface {
        ~int | ~float64
    }

    type Container[T Number] struct {
        value T
    }
    type Pair[K any, V any] struct {
        Key   K
        Value V
    }
    nestedSlice := [][]int{
    	{1, 2, 3},
    	{4, 5, 6},
    	{7, 8, 9},
    }
    nestedMap := map[string]map[string]int{
    	"A": {"X": 10, "Y": 20},
    	"B": {"X": 30, "Y": 40},
    }
    type Contact struct {
        Email    string
        Phone    string
    }

    type Person struct {
        Name     string
        Age      int
        Contacts []Contact
    }
    person := Person{
    	Name: "Alice",
    	Age: 30,
    	Contacts: []Contact{
    		{Email: "alice@example.com", Phone: "123-456"},
    		{Email: "bob@example.com", Phone: "789-012"},
    	},
    }
    type Pair[T any, U any] struct {
        First  T
        Second U
    }
    pair1 := Pair[int, string]{First: 1, Second: "one"}
    type Person struct {
        Name string `json:"name" xml:"name"`
        Age  int    `json:"age,omitempty"`
        Address *Address "af"
    }
    type Person struct {
        Name    string
        Age     int
        *Address // 嵌入指针类型
    }

    type ExampleInterface interface {
        Method1() string
        Method2(int) bool
        Method3(x int, y int) (int, error)
    }

    ```
    测试结果如下：
    ```
    [{'class_decl': {'name': 'MyInt',
                     'attr': ["{'nested_type': ['int']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'MyFloat',
                     'attr': ["{'nested_type': ['float64']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'MyString',
                     'attr': ["{'nested_type': ['string']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'type_alias_stmt': {'target': 'IntAlias', 'source': 'int'}},
     {'type_alias_stmt': {'target': 'StringAlias', 'source': 'string'}},
     {'type_alias_stmt': {'target': 'FloatAlias', 'source': 'float64'}},
     {'class_decl': {'name': 'Person',
                     'attr': ["{'nested_type': []}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'Name',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'Age',
                                                   'data_type': 'int',
                                                   'attr': ["{'tag': None}"]}}],
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'Address',
                     'attr': ["{'nested_type': []}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'Street',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'City',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'State',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'Zip',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}}],
                     'methods': None,
                     'nested': []}},
     {'interface_decl': {'name': 'Reader',
                         'attr': ["{'nested_type': [], 'nested_constraints': []}"],
                         'supers': None,
                         'type_parameters': [],
                         'static_init': None,
                         'init': None,
                         'fields': None,
                         'methods': [{'method_decl': {'name': 'Read',
                                                      'parameters': [{'parameter_decl': {'name': 'p',
                                                                                         'data_type': '[]byte',
                                                                                         'modifiers': []}}],
                                                      'data_type': '(n int, err '
                                                                   'error)',
                                                      'attr': [],
                                                      'init': None,
                                                      'body': None}}],
                         'nested': []}},
     {'interface_decl': {'name': 'Writer',
                         'attr': ["{'nested_type': [], 'nested_constraints': []}"],
                         'supers': None,
                         'type_parameters': [],
                         'static_init': None,
                         'init': None,
                         'fields': None,
                         'methods': [{'method_decl': {'name': 'Write',
                                                      'parameters': [{'parameter_decl': {'name': 'p',
                                                                                         'data_type': '[]byte',
                                                                                         'modifiers': []}}],
                                                      'data_type': '(n int, err '
                                                                   'error)',
                                                      'attr': [],
                                                      'init': None,
                                                      'body': None}}],
                         'nested': []}},
     {'class_decl': {'name': 'IntArray',
                     'attr': ["{'nested_type': ['[10]int']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'StringSlice',
                     'attr': ["{'nested_type': ['[]string']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'StringMap',
                     'attr': ["{'nested_type': ['map[string]string']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'IntMap',
                     'attr': ["{'nested_type': ['map[int]int']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'IntChannel',
                     'attr': ["{'nested_type': ['chan int']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'StringChannel',
                     'attr': ["{'nested_type': ['chan string']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'MyInt',
                     'attr': ["{'nested_type': ['int']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'MyFloat',
                     'attr': ["{'nested_type': ['float64']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'MyString',
                     'attr': ["{'nested_type': ['string']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'Person',
                     'attr': ["{'nested_type': []}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'Name',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'Age',
                                                   'data_type': 'int',
                                                   'attr': ["{'tag': None}"]}}],
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'Address',
                     'attr': ["{'nested_type': []}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'Street',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'City',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'State',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'Zip',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}}],
                     'methods': None,
                     'nested': []}},
     {'interface_decl': {'name': 'Reader',
                         'attr': ["{'nested_type': [], 'nested_constraints': []}"],
                         'supers': None,
                         'type_parameters': [],
                         'static_init': None,
                         'init': None,
                         'fields': None,
                         'methods': [{'method_decl': {'name': 'Read',
                                                      'parameters': [{'parameter_decl': {'name': 'p',
                                                                                         'data_type': '[]byte',
                                                                                         'modifiers': []}}],
                                                      'data_type': '(n int, err '
                                                                   'error)',
                                                      'attr': [],
                                                      'init': None,
                                                      'body': None}}],
                         'nested': []}},
     {'interface_decl': {'name': 'Writer',
                         'attr': ["{'nested_type': [], 'nested_constraints': []}"],
                         'supers': None,
                         'type_parameters': [],
                         'static_init': None,
                         'init': None,
                         'fields': None,
                         'methods': [{'method_decl': {'name': 'Write',
                                                      'parameters': [{'parameter_decl': {'name': 'p',
                                                                                         'data_type': '[]byte',
                                                                                         'modifiers': []}}],
                                                      'data_type': '(n int, err '
                                                                   'error)',
                                                      'attr': [],
                                                      'init': None,
                                                      'body': None}}],
                         'nested': []}},
     {'class_decl': {'name': 'IntArray',
                     'attr': ["{'nested_type': ['[10]int']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'StringSlice',
                     'attr': ["{'nested_type': ['[]string']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'StringMap',
                     'attr': ["{'nested_type': ['map[string]string']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'IntMap',
                     'attr': ["{'nested_type': ['map[int]int']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'IntChannel',
                     'attr': ["{'nested_type': ['chan int']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'StringChannel',
                     'attr': ["{'nested_type': ['chan string']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': None,
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'Container',
                     'attr': ["{'nested_type': []}"],
                     'supers': None,
                     'type_parameters': ['T'],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'value',
                                                   'data_type': 'T',
                                                   'attr': ["{'tag': None}"]}}],
                     'methods': None,
                     'nested': []}},
     {'interface_decl': {'name': 'Number',
                         'attr': ["{'nested_type': [], 'nested_constraints': "
                                  "['~int | ~float64']}"],
                         'supers': None,
                         'type_parameters': [],
                         'static_init': None,
                         'init': None,
                         'fields': None,
                         'methods': [],
                         'nested': []}},
     {'class_decl': {'name': 'Container',
                     'attr': ["{'nested_type': []}"],
                     'supers': None,
                     'type_parameters': ['T'],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'value',
                                                   'data_type': 'T',
                                                   'attr': ["{'tag': None}"]}}],
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'Pair',
                     'attr': ["{'nested_type': []}"],
                     'supers': None,
                     'type_parameters': ['K', 'V'],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'Key',
                                                   'data_type': 'K',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'Value',
                                                   'data_type': 'V',
                                                   'attr': ["{'tag': None}"]}}],
                     'methods': None,
                     'nested': []}},
     {'variable_decl': {'name': 'nestedSlice', 'data_type': None, 'attr': ['var']}},
     {'new_instance': {'target': '%v0',
                       'type_parameters': [],
                       'data_type': '[][]int',
                       'args': ['%v0', '%v1', '%v2'],
                       'init': [{'new_instance': {'target': '%v0',
                                                  'type_parameters': [],
                                                  'data_type': None,
                                                  'args': ['1', '2', '3'],
                                                  'init': [],
                                                  'fields': [],
                                                  'methods': [],
                                                  'nested': []}},
                                {'new_instance': {'target': '%v1',
                                                  'type_parameters': [],
                                                  'data_type': None,
                                                  'args': ['4', '5', '6'],
                                                  'init': [],
                                                  'fields': [],
                                                  'methods': [],
                                                  'nested': []}},
                                {'new_instance': {'target': '%v2',
                                                  'type_parameters': [],
                                                  'data_type': None,
                                                  'args': ['7', '8', '9'],
                                                  'init': [],
                                                  'fields': [],
                                                  'methods': [],
                                                  'nested': []}}],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'nestedSlice', 'operand': '%v0'}},
     {'variable_decl': {'name': 'nestedMap', 'data_type': None, 'attr': ['var']}},
     {'new_instance': {'target': '%v1',
                       'type_parameters': [],
                       'data_type': 'map[string]map[string]int',
                       'args': [],
                       'init': [{'new_instance': {'target': '%v0',
                                                  'type_parameters': [],
                                                  'data_type': None,
                                                  'args': [],
                                                  'init': [{'field_write': {'receiver_object': '@this',
                                                                            'field': '"X"',
                                                                            'source': '10'}},
                                                           {'field_write': {'receiver_object': '@this',
                                                                            'field': '"Y"',
                                                                            'source': '20'}}],
                                                  'fields': [],
                                                  'methods': [],
                                                  'nested': []}},
                                {'map_write': {'target': '@this',
                                               'key': '"A"',
                                               'value': '%v0'}},
                                {'new_instance': {'target': '%v1',
                                                  'type_parameters': [],
                                                  'data_type': None,
                                                  'args': [],
                                                  'init': [{'field_write': {'receiver_object': '@this',
                                                                            'field': '"X"',
                                                                            'source': '30'}},
                                                           {'field_write': {'receiver_object': '@this',
                                                                            'field': '"Y"',
                                                                            'source': '40'}}],
                                                  'fields': [],
                                                  'methods': [],
                                                  'nested': []}},
                                {'map_write': {'target': '@this',
                                               'key': '"B"',
                                               'value': '%v1'}}],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'nestedMap', 'operand': '%v1'}},
     {'class_decl': {'name': 'Contact',
                     'attr': ["{'nested_type': []}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'Email',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'Phone',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}}],
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'Person',
                     'attr': ["{'nested_type': []}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'Name',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'Age',
                                                   'data_type': 'int',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'Contacts',
                                                   'data_type': '[]Contact',
                                                   'attr': ["{'tag': None}"]}}],
                     'methods': None,
                     'nested': []}},
     {'variable_decl': {'name': 'person', 'data_type': None, 'attr': ['var']}},
     {'new_instance': {'target': '%v2',
                       'type_parameters': [],
                       'data_type': 'Person',
                       'args': [],
                       'init': [{'field_write': {'receiver_object': '@this',
                                                 'field': 'Name',
                                                 'source': '"Alice"'}},
                                {'field_write': {'receiver_object': '@this',
                                                 'field': 'Age',
                                                 'source': '30'}},
                                {'new_instance': {'target': '%v0',
                                                  'type_parameters': [],
                                                  'data_type': '[]Contact',
                                                  'args': ['%v0', '%v1'],
                                                  'init': [{'new_instance': {'target': '%v0',
                                                                             'type_parameters': [],
                                                                             'data_type': None,
                                                                             'args': [],
                                                                             'init': [{'field_write': {'receiver_object': '@this',
                                                                                                       'field': 'Email',
                                                                                                       'source': '"alice@example.com"'}},
                                                                                      {'field_write': {'receiver_object': '@this',
                                                                                                       'field': 'Phone',
                                                                                                       'source': '"123-456"'}}],
                                                                             'fields': [],
                                                                             'methods': [],
                                                                             'nested': []}},
                                                           {'new_instance': {'target': '%v1',
                                                                             'type_parameters': [],
                                                                             'data_type': None,
                                                                             'args': [],
                                                                             'init': [{'field_write': {'receiver_object': '@this',
                                                                                                       'field': 'Email',
                                                                                                       'source': '"bob@example.com"'}},
                                                                                      {'field_write': {'receiver_object': '@this',
                                                                                                       'field': 'Phone',
                                                                                                       'source': '"789-012"'}}],
                                                                             'fields': [],
                                                                             'methods': [],
                                                                             'nested': []}}],
                                                  'fields': [],
                                                  'methods': [],
                                                  'nested': []}},
                                {'field_write': {'receiver_object': '@this',
                                                 'field': 'Contacts',
                                                 'source': '%v0'}}],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'person', 'operand': '%v2'}},
     {'class_decl': {'name': 'Pair',
                     'attr': ["{'nested_type': []}"],
                     'supers': None,
                     'type_parameters': ['T', 'U'],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'First',
                                                   'data_type': 'T',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'Second',
                                                   'data_type': 'U',
                                                   'attr': ["{'tag': None}"]}}],
                     'methods': None,
                     'nested': []}},
     {'variable_decl': {'name': 'pair1', 'data_type': None, 'attr': ['var']}},
     {'new_instance': {'target': '%v3',
                       'type_parameters': ['int', 'string'],
                       'data_type': 'Pair',
                       'args': [],
                       'init': [{'field_write': {'receiver_object': '@this',
                                                 'field': 'First',
                                                 'source': '1'}},
                                {'field_write': {'receiver_object': '@this',
                                                 'field': 'Second',
                                                 'source': '"one"'}}],
                       'fields': [],
                       'methods': [],
                       'nested': []}},
     {'assign_stmt': {'target': 'pair1', 'operand': '%v3'}},
     {'class_decl': {'name': 'Person',
                     'attr': ["{'nested_type': []}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'Name',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': "
                                                            '\'"json:"name" '
                                                            'xml:"name""\'}']}},
                                {'variable_decl': {'name': 'Age',
                                                   'data_type': 'int',
                                                   'attr': ["{'tag': "
                                                            '\'"json:"age,omitempty""\'}']}},
                                {'variable_decl': {'name': 'Address',
                                                   'data_type': '*Address',
                                                   'attr': ["{'tag': "
                                                            '\'"af"\'}']}}],
                     'methods': None,
                     'nested': []}},
     {'class_decl': {'name': 'Person',
                     'attr': ["{'nested_type': ['*Address']}"],
                     'supers': None,
                     'type_parameters': [],
                     'static_init': None,
                     'init': None,
                     'fields': [{'variable_decl': {'name': 'Name',
                                                   'data_type': 'string',
                                                   'attr': ["{'tag': None}"]}},
                                {'variable_decl': {'name': 'Age',
                                                   'data_type': 'int',
                                                   'attr': ["{'tag': None}"]}}],
                     'methods': None,
                     'nested': []}},
     {'interface_decl': {'name': 'ExampleInterface',
                         'attr': ["{'nested_type': [], 'nested_constraints': []}"],
                         'supers': None,
                         'type_parameters': [],
                         'static_init': None,
                         'init': None,
                         'fields': None,
                         'methods': [{'method_decl': {'name': 'Method1',
                                                      'parameters': [],
                                                      'data_type': 'string',
                                                      'attr': [],
                                                      'init': None,
                                                      'body': None}},
                                     {'method_decl': {'name': 'Method2',
                                                      'parameters': [],
                                                      'data_type': 'bool',
                                                      'attr': [],
                                                      'init': None,
                                                      'body': None}},
                                     {'method_decl': {'name': 'Method3',
                                                      'parameters': [{'parameter_decl': {'name': 'x',
                                                                                         'data_type': 'int',
                                                                                         'modifiers': []}},
                                                                     {'parameter_decl': {'name': 'y',
                                                                                         'data_type': 'int',
                                                                                         'modifiers': []}}],
                                                      'data_type': '(int, error)',
                                                      'attr': [],
                                                      'init': None,
                                                      'body': None}}],
                         'nested': []}}]
    ```
3.郑仁哲部分
  测试样例：
  ```
// main.go
package main

import (
    "fmt"
    "math"
)

// Simple function with no parameters and no return value
func printHello() {
    fmt.Println("Hello, world!")
}

// Function with two parameters and a return value
func add(x int, y int) int {
    return x + y
}

// Function demonstrating named return value
func divide(dividend float64, divisor float64) (result float64, err error) {
    if divisor == 0.0 {
        err = fmt.Errorf("cannot divide by zero")
        return
    }
    result = dividend / divisor
    return result, nil
}

// Function with variadic parameters
func sum(numbers ...int) int {
    total := 0
    for _, number := range numbers {
        total += number
    }
    return total
}

// Main function calls other functions
func main() {
    printHello()
    result := add(5, 7)
    fmt.Println("Result of add: ", result)

    quotient, err := divide(5.4, 2.0)
    if err != nil {
        fmt.Println("Error:", err)
    } else {
        fmt.Println("Result of divide:", quotient)
    }

    total := sum(1, 2, 3, 4, 5)
    fmt.Println("Result of sum:", total)
}
  ```
测试结果：
   ```
  [{'package_stmt': {'name': 'main'}}, {'import_stmt': {'name': '"fmt"'}},
 {'import_stmt': {'name': '"math"'}},
 {'function_decl': {'name': b'printHello',
                    'type_parameters': [],
                    'parameters': [],
                    'result_type': None,
                    'body': [{'type': 'expression_statement',
                              'content': b'fmt.Println("Hello, world!")'}]}},
 {'function_decl': {'name': b'add',
                    'type_parameters': [],
                    'parameters': [{'parameter_decl': {'name': b'x',
                                                       'data_type': None}},
                                   {'parameter_decl': {'name': b'y',
                                                       'data_type': None}}],
                    'result_type': b'int',
                    'body': [{'type': 'return_statement',
                              'content': b'return x + y'}]}},
 {'function_decl': {'name': b'divide',
                    'type_parameters': [],
                    'parameters': [{'parameter_decl': {'name': b'dividend',
                                                       'data_type': None}},
                                   {'parameter_decl': {'name': b'divisor',
                                                       'data_type': None}}],
                    'result_type': b'(result float64, err error)',
                    'body': [{'type': 'if_statement',
                              'content': b'if divisor == 0.0 {\n        err '
                                         b'= fmt.Errorf("cannot divide by zero"'
                                         b')\n        return\n    }'},
                             {'type': 'assignment_statement',
                              'content': b'result = dividend / divisor'},
                             {'type': 'return_statement',
                              'content': b'return result, nil'}]}},
 {'function_decl': {'name': b'sum',
                    'type_parameters': [],
                    'parameters': [{'parameter_decl': {'name': b'numbers',
                                                       'data_type': None}}],
                    'result_type': b'int',
                    'body': [{'type': 'short_var_declaration',
                              'content': b'total := 0'},
                             {'type': 'for_statement',
                              'content': b'for _, number := range numbers {'
                                         b'\n        total += number\n    }'},
                             {'type': 'return_statement',
                              'content': b'return total'}]}},
 {'function_decl': {'name': b'main',
                    'type_parameters': [],
                    'parameters': [],
                    'result_type': None,
                    'body': [{'type': 'expression_statement',
                              'content': b'printHello()'},
                             {'type': 'short_var_declaration',
                              'content': b'result := add(5, 7)'},
                             {'type': 'expression_statement',
                              'content': b'fmt.Println("Result of add: ", resul'
                                         b't)'},
                             {'type': 'short_var_declaration',
                              'content': b'quotient, err := divide(5.4, 2.0)'},
                             {'type': 'if_statement',
                              'content': b'if err != nil {\n        fmt.Prin'
                                         b'tln("Error:", err)\n    } else {\n'
                                         b'        fmt.Println("Result of divid'
                                         b'e:", quotient)\n    }'},
                             {'type': 'short_var_declaration',
                              'content': b'total := sum(1, 2, 3, 4, 5)'},
                             {'type': 'expression_statement',
                              'content': b'fmt.Println("Result of sum:", total)'}]}}]
[{'operation': 'package_stmt', 'stmt_id': 1, 'name': 'main'},
 {'operation': 'import_stmt', 'stmt_id': 2, 'name': '"fmt"'},
 {'operation': 'import_stmt', 'stmt_id': 3, 'name': '"math"'},
 {'operation': 'function_decl',
  'stmt_id': 4,
  'name': b'printHello',
  'type_parameters': None,
  'parameters': None,
  'result_type': None,
  'body': 5},
 {'operation': 'block_start', 'stmt_id': 5, 'parent_stmt_id': 4},
 {'operation': 'type', 'stmt_id': 6},
 {'operation': 'block_end', 'stmt_id': 5, 'parent_stmt_id': 4},
 {'operation': 'function_decl',
  'stmt_id': 7,
  'name': b'add',
  'type_parameters': None,
  'parameters': 8,
  'result_type': b'int',
  'body': 11},
 {'operation': 'block_start', 'stmt_id': 8, 'parent_stmt_id': 7},
 {'operation': 'parameter_decl', 'stmt_id': 9, 'name': b'x', 'data_type': None},
 {'operation': 'parameter_decl',
  'stmt_id': 10,
  'name': b'y',
  'data_type': None},
 {'operation': 'block_end', 'stmt_id': 8, 'parent_stmt_id': 7},
 {'operation': 'block_start', 'stmt_id': 11, 'parent_stmt_id': 7},
 {'operation': 'type', 'stmt_id': 12},
 {'operation': 'block_end', 'stmt_id': 11, 'parent_stmt_id': 7},
 {'operation': 'function_decl',
  'stmt_id': 13,
  'name': b'divide',
  'type_parameters': None,
  'parameters': 14,
  'result_type': b'(result float64, err error)',
  'body': 17},
 {'operation': 'block_start', 'stmt_id': 14, 'parent_stmt_id': 13},
 {'operation': 'parameter_decl',
  'stmt_id': 15,
  'name': b'dividend',
  'data_type': None},
 {'operation': 'parameter_decl',
  'stmt_id': 16,
  'name': b'divisor',
  'data_type': None},
 {'operation': 'block_end', 'stmt_id': 14, 'parent_stmt_id': 13},
 {'operation': 'block_start', 'stmt_id': 17, 'parent_stmt_id': 13},
 {'operation': 'type', 'stmt_id': 18}, {'operation': 'type', 'stmt_id': 19},
 {'operation': 'type', 'stmt_id': 20},
 {'operation': 'block_end', 'stmt_id': 17, 'parent_stmt_id': 13},
 {'operation': 'function_decl',
  'stmt_id': 21,
  'name': b'sum',
  'type_parameters': None,
  'parameters': 22,
  'result_type': b'int',
  'body': 24},
 {'operation': 'block_start', 'stmt_id': 22, 'parent_stmt_id': 21},
 {'operation': 'parameter_decl',
  'stmt_id': 23,
  'name': b'numbers',
  'data_type': None},
 {'operation': 'block_end', 'stmt_id': 22, 'parent_stmt_id': 21},
 {'operation': 'block_start', 'stmt_id': 24, 'parent_stmt_id': 21},
 {'operation': 'type', 'stmt_id': 25}, {'operation': 'type', 'stmt_id': 26},
 {'operation': 'type', 'stmt_id': 27},
 {'operation': 'block_end', 'stmt_id': 24, 'parent_stmt_id': 21},
 {'operation': 'function_decl',
  'stmt_id': 28,
  'name': b'main',
  'type_parameters': None,
  'parameters': None,
  'result_type': None,
  'body': 29},
 {'operation': 'block_start', 'stmt_id': 29, 'parent_stmt_id': 28},
 {'operation': 'type', 'stmt_id': 30}, {'operation': 'type', 'stmt_id': 31},
 {'operation': 'type', 'stmt_id': 32}, {'operation': 'type', 'stmt_id': 33},
 {'operation': 'type', 'stmt_id': 34}, {'operation': 'type', 'stmt_id': 35},
 {'operation': 'type', 'stmt_id': 36},
 {'operation': 'block_end', 'stmt_id': 29, 'parent_stmt_id': 28}]
   ```
