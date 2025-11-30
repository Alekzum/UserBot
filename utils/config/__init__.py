from . import (
    my_logging,
    my_wraps,
    allowed,
    whitelist,
    my_things,
    my_types,
    modules_things,
)
from .my_types import Metadata, Config

from pyrogram.filters import Filter
from pyrogram.handlers.handler import Handler
import logging
import json


def make_dict(o):
    d = {k: getattr(o, k, None) for k in dir(o)}
    d = {k: v for (k, v) in d.items() if k[0] != "_"}
    d["_"] = str(type(o))
    return d


class ConfigEncoder(json.JSONEncoder):
    def default(self, o):
        # print(f"ConfigEncoder - {o=}")
        if isinstance(o, Config):
            # return make_dict(o)
            lst = [
                "Metadata",
                "vars",
                # "handler",
            ]
            return {k: getattr(o, k, None) for k in lst}
        return MetadataEncoder.default(self, o)


class MetadataEncoder(json.JSONEncoder):
    def default(self, o):
        # print(f"MetadataEncoder - {o=}")
        if isinstance(o, Metadata):
            # return make_dict(o)
            lst = [
                "name",
                "variables",
                "cmds",
                "desc",
                "other_can_use",
                "whitelist",
                "need_vars",
                "can_be_reloaded",
                "filter",
                # "force_filters",
                # "filters",
                "enabled",
                "enabled_logs",
            ]
            return {k: getattr(o, k, None) for k in lst}
        return FilterEncoder.default(self, o)


class FilterEncoder(json.JSONEncoder):
    def default(self, o):
        # print(f"FilterEncoder - {o=}")
        if isinstance(o, Filter):
            return make_dict(o)
            # return {k: getattr(o, k, None) for k in dir(o) if k[0]!="_"} or str(type(o))
        return HandlerEncoder.default(self, o)


class HandlerEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Handler):
            return {"callback": repr(o.callback), "filters": o.filters}
        return TypeEncoder.default(self, o)


class TypeEncoder(json.JSONEncoder):
    def default(self, o):
        # print(f"{o=}")
        if isinstance(o, set):
            return tuple(o)
        elif isinstance(o, (logging.Logger)) or bool(callable(o)):
            return repr(o)
        return json.JSONEncoder.default(self, o)


__all__ = [
    "my_logging",
    "my_wraps",
    "allowed",
    "whitelist",
    "my_things",
    "my_types",
    "modules_things",
    "Metadata",
    "Config",
]
