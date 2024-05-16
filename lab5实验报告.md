# 编译第五次实验实验报告
## 小组成员及分工
- 宋岱桉：declaration中以下部分的解析以及对应测试用例、测试程序的编写
    ```js
        $.method_declaration
        $.import_declaration
        $.if_stmt中init部分关于declaration的补全
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

