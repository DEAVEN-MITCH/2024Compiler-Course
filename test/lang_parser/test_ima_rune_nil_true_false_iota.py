#!/usr/bin/env python3

import os

command = os.path.realpath("/app/experiment_2/src/lian/lang/main.py") + " --lang=java -debug -print_statements " + os.path.realpath("/app/experiment_2/test/cases/ima_rune_nil_true_false_iota.go")

print(command)

os.system(command)
