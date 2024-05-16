#!/usr/bin/env python3

import os

command = os.path.realpath("/app/experiment_2/src/lian/lang/main.py") + " --lang=go -debug -print_statements " + os.path.realpath("/app/experiment_2/test/cases/type_declaration.go")

print(command)

os.system(command)