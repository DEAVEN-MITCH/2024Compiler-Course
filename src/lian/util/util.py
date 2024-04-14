#!/usr/bin/env python3
# system modules
import sys
import pandas as pd
import numpy as np
import math

from lian.config import config

def is_empty(element):
    if isna(element):
        return True
    if isinstance(element, (pd.DataFrame, np.ndarray)):
        return element.size == 0
    if not element:
        return True
    return False

def isna(element):
    if element is None:
        return True
    return isinstance(element, float) and math.isnan(element)

def is_none(element):
    return is_empty(element)

def is_available(element):
    return not is_empty(element)

def error_and_quit(*msg):
    sys.stderr.write(f"[ERROR]: {''.join(msg)}\n")
    sys.exit(-1)

def error(*msg):
    sys.stderr.write(f"[ERROR]: {''.join(msg)}\n")

def debug(*msg):
    if config.DEBUG_FLAG:
        output = []
        for m in msg:
            output.append(str(m))
        sys.stdout.write(f"[DEBUG]: {' '.join(output)}\n")

def warn(*msg):
    sys.stderr.write(f"[WARNING]: {''.join(msg)}\n")
        
def log(*msg):
    print(*msg)