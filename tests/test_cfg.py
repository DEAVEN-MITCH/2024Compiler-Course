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
            "goto":[(12, 13, 0),
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
 (46, -1, 0)],
            "return":[  (12, 13, 0),
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
 (60, -1, 0)],
            "method_decl": [(13, 14, 0), (14, -1, 0), (18, 19, 0), (19, 20, 0), (20, 21, 0), (21, -1, 0)
            ],
            "forin": [(12, 13, 0),
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
 (59, -1, 6)],
            "while": [
            ],
            "if": [
            ],
            "try": [
            ],
            "decl": [
            ],
            "for":[(12, 15, 0),
 (13, 22, 4),
 (13, 24, 5),
 (15, 16, 0),
 (16, 18, 0),
 (18, 13, 3),
 (20, 18, 0),
 (22, 23, 0),
 (23, 20, 0),
 (24, 27, 0),
 (25, -1, 5),
 (25, 31, 4),
 (27, 25, 3),
 (29, 27, 0),
 (31, 32, 0),
 (32, 33, 0),
 (33, 34, 0),
 (34, 29, 0),
 (37, 40, 0),
 (38, 47, 4),
 (38, 72, 5),
 (40, 41, 0),
 (41, 43, 0),
 (43, 38, 3),
 (45, 43, 0),
 (47, 48, 0),
 (48, 49, 0),
 (49, 51, 1),
 (49, 54, 2),
 (51, 72, 6),
 (52, 45, 5),
 (52, 61, 4),
 (54, 55, 0),
 (55, 57, 0),
 (57, 52, 3),
 (59, 57, 0),
 (61, 62, 0),
 (62, 63, 0),
 (63, 64, 0),
 (64, 66, 1),
 (64, 67, 2),
 (66, 72, 6),
 (67, 68, 0),
 (68, 59, 2),
 (68, 70, 1),
 (70, 45, 6),
 (72, -1, 0),
 (75, 75, 4),
 (75, 76, 5),
 (76, 76, 4),
 (76, 77, 5),
 (77, -1, 0)],
            "yield":[
            ],
            "list":[
            ],
            "field":[
            ],
            "break":[(14, 17, 0),
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
 (54, -1, 0)],
            "continue":[(14, -1, 5),
 (14, 23, 4),
 (16, 17, 0),
 (17, 19, 0),
 (19, 14, 3),
 (21, 19, 0),
 (23, 24, 0),
 (24, 26, 1),
 (24, 27, 2),
 (26, 21, 7),
 (27, 28, 0),
 (28, 21, 0),
 (31, 32, 0),
 (32, 35, 0),
 (33, 42, 4),
 (33, 65, 5),
 (35, 36, 0),
 (36, 38, 0),
 (38, 33, 3),
 (40, 38, 0),
 (42, 44, 1),
 (42, 45, 2),
 (44, 65, 6),
 (45, 47, 1),
 (45, 48, 2),
 (47, 40, 7),
 (48, 49, 0),
 (49, 52, 0),
 (50, 40, 5),
 (50, 59, 4),
 (52, 53, 0),
 (53, 55, 0),
 (55, 50, 3),
 (57, 55, 0),
 (59, 60, 0),
 (60, 62, 1),
 (60, 63, 2),
 (62, 40, 7),
 (63, 64, 0),
 (64, 57, 0),
 (65, 66, 0),
 (66, -1, 0),
 (69, 70, 0),
 (70, -1, 0)],

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
                # print(file_name)
                # print(target_file)
                if file_name in ["if",'break','for','continue','method_decl','return','goto']:
                #if file_name in ['goto']:
                    patched_testcase = patch(
                        'sys.argv',
                        ["", "run", "-f", "-p", "-d", "-l", "python,go", target_file, "-w", config.TEST_CONFIG.config.output_dir]
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
