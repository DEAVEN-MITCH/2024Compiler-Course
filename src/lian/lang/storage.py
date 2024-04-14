#!/usr/bin/env python3

import os
import pandas as pd
import re
from lian.config import config


def get_output_path(file_unit):
    p = re.sub(re.escape(config.COMMON_INPUT_DIR), "", file_unit, count=1)
    p = p + ".glang"
    output_path = os.path.abspath("/".join([config.OUTPUT_DIR, p]))

    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.system("mkdir -p " + output_dir)

    return output_path

def export(file_unit, flatten_nodes):
    if not flatten_nodes:
        return
    df = pd.DataFrame(flatten_nodes)

    # Write the DataFrame to Feather
    output_path = get_output_path(file_unit)

    if config.DEBUG:
        print("Lang-Parser-Output:", output_path)

    # save the glang statements
    df.to_feather(output_path)