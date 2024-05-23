#!/usr/bin/env python3

import os,sys

from lian.semantic.internal.traversal import InternalTraversal
from lian.util import util


def run(options, apps, module_symbols):
    InternalTraversal(options, apps, module_symbols).run()
    
