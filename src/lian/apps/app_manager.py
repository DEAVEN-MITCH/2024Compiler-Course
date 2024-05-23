#!/usr/bin/env python3

import os,sys

from lian.util import util
from lian.config import config
from lian.config.constants import EventKind


class AppTemplate:
    def __init__(self):
        self.name = "app"
        self.description = "app template"
        self.events = []
        self.priority = 0       # 0-99
        self.app_path = __file__

    def run(self, event, input_data):
        pass


class AppManager:
    def __init__(self, options):
        self.glang_apps = []
        self.control_flow_apps = []
        self.state_flow_apps = []
        self.method_summary_apps = []
        self.entry_point_apps = []
        self.taint_analysis_apps = []

        self.event_handlers = {
            EventKind.GLANGIR: self.glang_apps,
            EventKind.CONTROL_FLOW: self.control_flow_apps,
            EventKind.STATE_FLOW: self.state_flow_apps,
            EventKind.METHOD_SUMMARY: self.method_summary_apps,
            EventKind.ENTRY_POINT: self.entry_point_apps,
            EventKind.TAINT_ANALYSIS: self.taint_analysis_apps,
        }

        for app in options.apps:
            self.register_app(app)

    def notify(self, event, data):
        handlers = self.event_handlers.get(event)
        for h in handlers:
            h.run(event, data)

    def insert_by_priority(self, apps, new_app):
        pos = -1
        for current_index, current_app in enumerate(apps):
            if current_app.priority < new_app.priority:
                pos = current_index
                break

        if pos >= 0:
            apps.insert(pos, new_app)
        else:
            apps.append(new_app)

    def register_app(self, app):
        app.priority = app.priority % config.MAX_PRIORITY
        for event in app.events:
            handlers = self.event_handlers.get(event)
            if handlers is not None:
                self.insert_by_priority(handlers, app)

    def print_apps(self, name, apps):
        util.debug(name)
        for a in apps:
            util.debug(f"\t({a.priority}){a.app_path}")
        
    def list_installed_apps(self):
        self.print_apps("EventKind.GLANG", self.glang_apps)
        self.print_apps("EventKind.CONTROL_FLOW", self.control_flow_apps)
        self.print_apps("EventKind.STATE_FLOW", self.state_flow_apps)
        self.print_apps("EventKind.METHOD_SUMMARY", self.method_summary_apps)
        self.print_apps("EventKind.TAINT_ANALYSIS", self.taint_analysis_apps)
