#!/usr/bin/env python3

import os
import tempfile
import unittest
import pandas as pd
import pprint
import numpy as np
from collections import defaultdict
from unittest.mock import patch

import config
from lian.interfaces.command import Lian

class CFGTestCase(unittest.TestCase):
    @classmethod
    def compare_cfg(cls, edge_list, target_file):
        file_name, _ = os.path.splitext(os.path.basename(target_file))
        cfg_results = {
            "forin": [
            ],
            "while": [
            ],
            "if": [
                (12, 13, 0),
                (13, 14, 0),
                (14, 15, 0),
                (15, 16, 0),
                (16, 17, 0),
                (17, 18, 0),
                (18, 19, 0),
                (19, 21, 1),
                (19, 24, 2),
                (21, 22, 0),
                (22, -1, 0),
                (24, 25, 0),
                (25, 27, 1),
                (25, 30, 2),
                (27, 28, 0),
                (28, -1, 0),
                (30, 31, 0),
                (31, -1, 0)
            ],
            "try": [
            ],
            "decl": [
            ],
            "for":[
            ],
            "yield":[
            ],
            "list":[
            ],
            "field":[
            ]

        }
        print("=== target file ===")
        print(target_file)
        result = sorted(cfg_results[file_name])
        edge_list = sorted(edge_list)
        print("+ reference answer")
        pprint.pprint(result)
        print("+ current result")
        pprint.pprint(edge_list)
        assert result == edge_list


    @classmethod
    def setUpClass(cls):
        def get_all_tests(root_dir: str):
            tests = defaultdict(list)
            for dirpath, dirnames, filenames in os.walk(root_dir):
                for file in filenames:
                    tests[os.path.basename(dirpath)].append(os.path.realpath(os.path.join(dirpath, file)))
            return tests

        cls.tests = get_all_tests(os.path.join(config.TEST_CONFIG.config.resource_dir, "control_flow"))
        # cls.out_dir = tempfile.TemporaryDirectory(dir=config.TEST_CONFIG.config.temp_dir, delete=False)
        os.system("mkdir -p " + config.TEST_CONFIG.config.temp_dir)
        cls.out_dir = tempfile.TemporaryDirectory(dir=config.TEST_CONFIG.config.temp_dir)

    @classmethod
    def raw_test(cls):
        Lian().run()

    @classmethod
    def read_cfg(cls, cfg_path):
        cfg = pd.read_feather(cfg_path)
        results = []
        source_nodes = cfg["src_stmt_id"].values
        dst_nodes = cfg["dst_stmt_id"].values
        type_nodes = cfg["control_flow_type"].values
        for index in range(len(cfg)):
            results.append((source_nodes[index], dst_nodes[index], type_nodes[index]))
        return results

    def test_run_all(self):
        os.system('clear')
        for test, files in self.tests.items():
            for target_file in files:
                file_name, _ = os.path.splitext(os.path.basename(target_file))
                print("*"*20, file_name, "*"*20)
                if file_name == "if":
                    patched_testcase = patch(
                        'sys.argv',
                        ["", "run", "-f", "-p", "-d", "-l", "python,java", target_file, "-w", config.TEST_CONFIG.config.output_dir]
                        # ["", "run", "-f", "-l", "python,java", target_file, "-w", config.TEST_CONFIG.config.output_dir]
                    )(
                        self.raw_test
                    )
                    patched_testcase()
                    cfg_path = os.path.join(config.TEST_CONFIG.config.output_dir, "semantic/glang_bundle0.cfg")
                    cfg = self.read_cfg(cfg_path)
                    self.compare_cfg(cfg, target_file)

if __name__ == '__main__':
    unittest.main()
