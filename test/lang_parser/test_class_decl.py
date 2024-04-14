#!/usr/bin/env python3

import os

command = os.path.realpath("/app/experiment_2/src/lian/lang/main.py") + " --lang=java -debug -print_statements " + os.path.realpath("/app/experiment_2/test/cases/class_decl.java")

print(command)

os.system(command)