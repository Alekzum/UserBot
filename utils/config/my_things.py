from __future__ import annotations
from typing import Any, TypeVar, overload

import pathlib
import dpath.exceptions
import dpath

from importlib import import_module
from functools import wraps
import structlog

import json
import time


logger = structlog.getLogger(__name__)
config_path = pathlib.Path("config.json")

_fileBusy = False
_update_time = 0.01

DEFAULT_DICT = dict(config=dict(), prefix=".")

T = TypeVar("T")

module_fields = ["main", "Config", "on_startup", "on_shutdown"]


def wait_unlock():
    global _fileBusy
    while _fileBusy:
        time.sleep(_update_time)


def lock_file():
    global _fileBusy
    _fileBusy = True


def unlock_file():
    global _fileBusy
    _fileBusy = False


def WithLocking(func):
    @wraps(func)
    def inner(*args, **kwargs):
        wait_unlock()
        lock_file()
        result = func(*args, **kwargs)
        unlock_file()
        return result

    return inner


# file things
def get_time() -> str:
    """Return something like 2024-05-22 22:41:51,433"""
    raw = time.time()
    t = time.localtime(raw)
    formation = "{:0>4}-{:0>2}-{:0>2} {:0>2}:{:0>2}:{:0>2},{:0>3}"
    result = formation.format(
        t.tm_year,
        t.tm_mon,
        t.tm_mday,
        t.tm_hour,
        t.tm_min,
        t.tm_sec,
        str(raw - raw // 1)[2:5],
    )
    return result


def get_date(day_offset: int = 0) -> str:
    raw = time.time()
    t = time.localtime(raw + day_offset * 86400)
    formating = "{:0>4}-{:0>2}-{:0>2}"
    result = formating.format(t.tm_year, t.tm_mon, t.tm_mday)
    return result


def get_date_dir(day_offset: int = 0) -> tuple[str, str, str]:
    raw = time.time()
    t = time.localtime(raw + day_offset * 86400)
    return (
        str(t.tm_year).rjust(4, "0"),
        str(t.tm_mon).rjust(2, "0"),
        str(t.tm_mday).rjust(2, "0"),
    )


def mkdir(x: pathlib.Path) -> None:
    for a in reversed(x.parents):
        if not a.exists():
            a.mkdir()


def fix_config() -> None:
    # 2024/11/01_broken.json
    cur_date = get_date_dir()
    for_broken_path = pathlib.Path(*cur_date[:2], f"{cur_date[2]}_broken.json")

    # config is broken, copying it to check errors manually
    cfg_bytes = config_path.read_bytes()
    config_path.parent.joinpath("config_broken.json").write_bytes(cfg_bytes)

    # move broken config to date's directory and rename it
    mkdir(for_broken_path)
    for_broken_path.write_bytes(cfg_bytes)

    # get latest config
    with open(get_backup_filepath(None), encoding="utf-8") as file:
        raw = json.load(file)

    _save_raw(raw)


@WithLocking
def _load_raw() -> str:
    if not config_path.exists():
        _save_raw(DEFAULT_DICT)
    raw_file = config_path.read_text("utf-8")
    # with open("config.json", encoding="utf-8") as file:
    # raw_file = file.read()
    return raw_file


@WithLocking
def _save_raw(raw_dict: dict) -> None:
    string = json.dumps(raw_dict, indent=2, sort_keys=True, ensure_ascii=False)
    config_path.write_text(string, encoding="utf-8")
    # with open("config.json", "w", encoding="utf-8") as file:
    # file.write(string)


def load_raw(fixed=False) -> dict:
    raw_file = _load_raw()
    try:
        raw: dict = json.loads(raw_file)
    except json.JSONDecodeError as ex:
        logger.warning(
            f"JSONDecodeError. Error as position {ex.pos}, aka {ex.lineno}:{ex.colno}, {ex.args=!r}"
        )
        # time.sleep(3)

        if not fixed:
            logger.info("Trying to fix...")
            fix_config()
            return load_raw(fixed=True)

        logger.error("Tried to fix, but nothing happened. Fix by hand!")
        exit(1)

    if isinstance(raw, str):
        raw_dict: dict = json.loads(raw)
        _save_raw(raw_dict)
    else:
        raw_dict = raw

    raw_dict = check_existing_modules(raw_dict)

    if "config" not in raw_dict:
        raw_dict["config"] = {}
        save_raw(raw_dict)

    if fixed:
        logger.info("Config fixed!")
        save_raw(raw_dict)

    return raw_dict


def save_raw(raw_dict: dict):
    old_config_string = _load_raw()
    save_backup(old_config_string)
    _save_raw(raw_dict)
    return


exist_modules_cache: set[str] = set()
not_exist_modules_cache: set[str] = set()


def check_existing_modules(raw_dict: dict | None = None) -> dict:
    """Check modules for existing by using "import <module.name>" """
    if raw_dict is None:
        raw_dict = json.loads(_load_raw()) or DEFAULT_DICT

    if raw_dict is None:
        raise Exception("raw_dict is still None...")

    for moduleName in raw_dict["config"].copy():
        if moduleName in exist_modules_cache:
            continue
        try:
            import_module(moduleName)
        except ModuleNotFoundError:
            if moduleName in not_exist_modules_cache:
                continue
            logger.debug(f"module {moduleName!r} not exists")
            not_exist_modules_cache.add(moduleName)
            del raw_dict["config"][moduleName]
            logger.debug(f"{moduleName in raw_dict['config'] = }")

            continue
        except Exception:
            pass
        exist_modules_cache.add(moduleName)

    _save_raw(raw_dict)
    return raw_dict


def get_backup_filepath(day_offset: int | None = 0) -> pathlib.Path:
    if day_offset is not None:
        return pathlib.Path("backup", *get_date_dir(day_offset), "cfg.json")
    latest_cfg = tuple(
        tuple(
            tuple(tuple(pathlib.Path("backup").glob("*"))[-1].glob("*"))[
                -1
            ].glob("*")
        )[-1].glob("*")
    )[-1]
    logger.info(f"{latest_cfg=}")
    return latest_cfg


def save_backup(raw_string: str):
    filePath = get_backup_filepath()

    for directory in reversed(filePath.parents):
        if not directory.exists():
            directory.mkdir()

    if not filePath.exists():
        filePath.write_text(raw_string, encoding="utf-8")


_DEFAULT = object()


@overload
def get_variable(path: str | list[str], default: T) -> Any | T: ...
@overload
def get_variable(path: str | list[str], default: Any = _DEFAULT) -> Any: ...
def get_variable(path: str | list[str], default: Any | T = _DEFAULT) -> Any | T:
    raw = load_raw()
    if default is _DEFAULT:
        value = dpath.get(dict(**raw), path)
    else:
        value = dpath.get(dict(**raw), path, default=default)
    return value


def set_config(config_path: str | list[str], value: Any) -> int | None:
    path = ["config"] + (
        config_path if isinstance(config_path, list) else [config_path]
    )
    return set_variable(path=path, value=value)


def set_variable(path: str | list[str], value: Any) -> int | None:
    raw = load_raw()

    try:
        x = dpath.set(raw, path, value)

    except dpath.exceptions.PathNotFound:
        return None

    save_raw(raw)
    return x


def delete_variable(path: list[str]) -> int | None:
    raw = load_raw()

    try:
        x = dpath.delete(raw, path)

    except dpath.exceptions.PathNotFound:
        return None

    save_raw(raw)
    return x


def get_prefix() -> str:
    prefix = get_variable("prefix")
    return prefix


logger = structlog.getLogger(__name__)
