#!/usr/bin/env python3

from . import common_parser


class Parser(common_parser.Parser):
    def __init__(self):
        pass

    def is_literal(self, node):
        return node.endswith("literal")
