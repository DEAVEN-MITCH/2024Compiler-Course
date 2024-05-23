#!/usr/bin/env python3

import builtins
try:
    builtins.profile
except AttributeError:
    # No line profiler, provide a pass-through version
    def profile(func): return func
    builtins.profile = profile

import argparse
import dataclasses
from os import path

import pandas as pd

pd.set_option('display.max_columns', None)  # or 1000
pd.set_option('display.max_rows', None)  # or 1000
pd.set_option('display.max_colwidth', None)  # or 199

import sys,os
root_path = os.path.realpath(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
src_path = os.path.join(root_path, "src")
# sys.path.append(root_path)
sys.path.append(src_path)

TEST_DIR = path.realpath(path.dirname(__file__))
TEMP_DIR = path.realpath(path.join(TEST_DIR, './temp'))
RESOURCE_DIR = path.realpath(path.join(TEST_DIR, './resource'))
OUTPUT_DIR = path.realpath(path.join(TEST_DIR, './lian_workspace'))

@dataclasses.dataclass
class Config:
	debug: bool = True
	test_dir: str = TEST_DIR
	temp_dir: str = TEMP_DIR
	resource_dir: str = RESOURCE_DIR
	output_dir: str = OUTPUT_DIR


class TestParser:
	def __init__(self):
		self.parser = argparse.ArgumentParser(description='Distiller')
		self.parser.add_argument('-d', '--debug', action='store_true')
		self.parser.add_argument('--temp_dir', type=str, default=TEMP_DIR)
		self.parser.add_argument('--test_dir', type=str, default=TEST_DIR)
		self.parser.add_argument('--resource_dir', type=str, default=RESOURCE_DIR)

	def parse_args(self, args=None) -> Config:
		if args:
			args = self.parser.parse_args(args)
		else:
			args = self.parser.parse_args()
		return Config(**vars(args))

	def __repr__(self):
		return self.__str__()

	def __str__(self):
		return self.parser.__str__()


class TestConfig:
	def __init__(self):
		self.config = Config()
		self.parser = TestParser()

	def set_config(self, config: Config = None, args=None):
		if config:
			self.config = config
		else:
			self.config = self.parser.parse_args(args=args)

	def reset_config(self):
		self.config = Config()

	def __repr__(self):
		return self.__str__()

	def __str__(self):
		return self.config.__str__() + "\n" + self.parser.__str__()


TEST_CONFIG = TestConfig()

if __name__ == "__main__":
	print(TEST_CONFIG)
	TEST_CONFIG.set_config()
	print(TEST_CONFIG)
