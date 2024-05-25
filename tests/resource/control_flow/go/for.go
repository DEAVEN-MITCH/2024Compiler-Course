func print() {
    for i := 1; i <= 5; i++ {
        fmt.Println(i)
    }
	c=0
}

/*  序号标注，方便对照
[10{'method_decl': {'name': 'print',
                  'type_parameters': [],
                  'parameters': [],
                  'data_type': [],
                  11'body': [{12'for_stmt': {13'init_body': [{'14variable_decl': {'attr': 'short_var',
                                                                          'data_type': '',
                                                                          'name': 'i'}},
                                                       {15'assign_stmt': {'target': 'i',
                                                                        'operand': '1'}}],
                                         'condition': '%v0',
                                         'condition_prebody': [17{'assign_stmt': {'target': '%v0',
                                                                                'operator': '<=',
                                                                                'operand': 'i',
                                                                                'operand2': '5'}}],
                                         'update_body': [19{'inc_stmt': {'target': 'i'}}],
                                         'body': [21{'field_read': {'target': '%v0',
                                                                  'receiver_object': 'fmt',
                                                                  'field': 'Println'}},
                                                  22{'call_stmt': {'attr': [],
                                                                 'target': '%v1',
                                                                 'name': '%v0',
                                                                 'type_parameters': [],
                                                                 'args': ['i']}}]}}]}}]
23 c=0
*/