#!/usr/bin/env python3

import os
import shutil

from lian.util import util
from lian.config import constants, config

LANG_EXTENSIONS = constants.LANG_EXTENSIONS
EXTENSIONS_LANG = constants.EXTENSIONS_LANG

def manage_directory(options, path):
    if not os.path.exists(path):
        os.makedirs(path)
        if config.DEBUG_FLAG:
            util.debug(f"Directory created at: {path}")
        return

    if not options.force:
        util.error_and_quit(f"The target directory already exists: {path}")
    
    if config.DEBUG_FLAG:                    
        util.warn(f"With the force mode flag, the workspace is being rewritten: {path}")
    
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            util.error_and_quit(f"Failed to delete {file_path}. Reason: {e}")
                

def build_workspace(options):
    workspace_path = options.workspace
    manage_directory(options, workspace_path)
    
    subdirs = [config.SRC_DIR, config.GLANG_DIR, config.SEMANTIC_DIR]
    for subdir in subdirs:
        subdir_path = os.path.join(workspace_path, subdir)
        os.makedirs(subdir_path, exist_ok=True)

    src_dir_path = os.path.join(workspace_path, 'src')
    for package_path in options.input:
        dest_path = os.path.join(src_dir_path, os.path.basename(package_path))
        
        if os.path.exists(package_path):
            if os.path.isfile(package_path):
                ext = os.path.splitext(package_path)[1]
                if ext in options.language_extensions:
                    shutil.copy(package_path, src_dir_path)
            elif os.path.isdir(package_path):
                try:
                    shutil.copytree(package_path, dest_path, ignore=shutil.ignore_patterns('.git', '*.git*', '.*'), dirs_exist_ok=True)
                except shutil.Error as e:
                    util.error(f"Fail to copy directory {package_path} to {dest_path}: {e}")
        else:
            util.debug(f"Package not found: {package_path}")

def setup(options):
    build_workspace(options)
