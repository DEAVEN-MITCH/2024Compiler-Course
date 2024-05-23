import os
import pprint
import sys

from lian.apps.app_manager import AppTemplate
from lian.config.constants import EventKind


class CustomedApp(AppTemplate):
    def __init__(self):
        super().__init__()
        self.events = [EventKind.GLANGIR]

    def run(self, event, input_data):
        for stmt in input_data:
            self.process_variable(stmt)
        return super().run(event, input_data)

    def process_variable(self, stmt):
        variable_lsit = []
        to_be_del = []
        for key, value in stmt.items():
            if key == "class_decl" or key == "method_decl":
                self.process_variable(value)
            if key == "body":
                for index, body_stmt in enumerate(value):
                    if list(body_stmt.keys())[0] == "variable_decl":
                        content = body_stmt["variable_decl"]
                        for varib_key, varib_value in content.items():
                            if varib_key == "name":
                                if varib_value in variable_lsit:
                                    to_be_del.append(index)
                                else:
                                    variable_lsit.append(varib_value)
                for index in to_be_del:
                    value.pop(index)
