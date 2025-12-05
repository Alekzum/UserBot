# from utils.modules import get_handlers_status_string
from utils.config import Config as Cfg
from utils.good_things import answer

from pyrogram.types import Message
from utils import Client

from utils.config.my_types import MyCallable
from pyrogram.handlers.handler import Handler
from pyrogram import filters

# from dataclasses import dataclass
from pydantic import BaseModel, ConfigDict
from typing import Any, Literal, overload
from types import ModuleType

from importlib import import_module, reload
import pathlib

import traceback
import sys

import copy

import time
from functools import lru_cache


Config = Cfg(
    name=__name__,
    desc='Control all handlers in userbot. Load/unload/reload? Okay! If forgot commands, use "mhelp"',
    cmds=[
        "mhelp",
        "mlist",
        "mcheck",
        "mreload",
        "munload",
        "mload",
        "minvoke",
    ],
    other_can_use=False,
)

logger = Config.logger

type UB_OR_B = Literal["userbot", "bot"]
type BOOL_OR_STR = Literal["str", "bool"]
userbot_scripts_directory = pathlib.Path("scripts")
"""./"""
userbot_handlers_directory = pathlib.Path("handlers", "userbot")
"""./handlers/userbot/"""
bot_handlers_directory = pathlib.Path("handlers", "bot")
"""./handlers/bot/"""


def log(text: str) -> None:
    pass


@lru_cache
def to_dict(obj, depth=-1):
    def loop(obj, depth=depth):
        d = try_get_dict(obj=obj)
        if not isinstance(d, dict):
            return d

        if (obj_module := getattr(obj, "__module__", None)) is not None:
            d["_"] = obj_module

        if (
            obj_name := getattr(obj, "__name__", None)
            or getattr(obj, "__qualname__", None)
        ) is not None:
            d["_"] = f"{x}.{obj_name}" if (x := d.get("_", "")) else obj_name

        for k, i1 in d.items():
            if depth > 0:
                d[k] = loop(obj=i1, depth=depth - 1)
            elif depth == -1:
                d[k] = loop(obj=i1, depth=-1)
            else:
                d[k] = try_get_dict(obj=i1)
        return d

    def try_get_dict(obj, return_empty_dict=False):
        if obj_d := getattr(obj, "__dict__", {}):
            return obj_d.copy()
        elif return_empty_dict:
            return dict()
        return obj

    started_at = time.perf_counter()
    d = loop(obj)
    ended_at = time.perf_counter()

    logger.debug(
        "parsed object",
        started_at=started_at,
        ended_at=ended_at,
        time_elapsed=ended_at - started_at,
        obj=obj,
        result=d,
    )

    return d


class MyHandler(BaseModel):
    name: str
    is_loaded: bool
    handler: Handler
    group: int

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self, depth=-1):
        return globals()["to_dict"](obj=self, depth=-1)

    def __bool__(self):
        return self.is_loaded

    def __str__(self):
        return f"<MyHandler {self.name}, is_loaded:{self.is_loaded}>"
    
    def __hash__(self):
        return hash(repr(self.__dict__))
    # def __repr__(self):
    #     result = f"MyHandler(name={self.name}, is_loaded={self.is_loaded}, group={self.group}, handler={deparse_handler(self.handler)})"
    #     return result


def true_repr(x: Any) -> str:
    type_ = type(x)
    module = type_.__module__
    qualname = type_.__qualname__
    result = f"{module}.{qualname}"
    return result


# def deparse_handler(handler: Handler | Any) -> str:
#     """Return some repr(handler)"""
#     module = import_module(handler.callback.__module__)
#     if module.__package__ != "scripts":
#         m = module
#     else:
#         m = handler.callback.__defaults__[0]  # type: ignore[index]
#     name = m.__name__.split(".")[1]
#     callback_string = "scripts.{}.main".format(name)
#     filter_string = repr_filter(handler.filters)
#     type_string = true_repr(handler)
#     result = "{}({}, {})".format(type_string, callback_string, filter_string)
#     return result


def repr_filter(my_obj: filters.Filter | Handler | Any) -> str:
    """Return some repr(filter)"""
    if not isinstance(my_obj, (filters.Filter, Handler)):
        return str(my_obj)

    type_string = true_repr(my_obj)
    arguments = [n for n in dir(my_obj) if n[0] != "_" and n != "self"]

    args = ", ".join(
        [f"{i}={repr_filter(getattr(my_obj, i))}" for i in arguments]
    )

    result = f"{type_string}({args})"
    return result


# async def reload_handler_by_name(client: Client, _name: str) -> str | bool:
#     name, bot_type = _get_type(_name)
#     if bot_type is None or name is None:
#         return False

#     args: tuple[Client, str, Literal["bool"]] = (client, name, "bool")
#     is_unloaded = True

#     if not await handler_is_loaded(*args):
#         return f"Модуль {name} нельзя перезагрузить, он разгружен"

#     is_unloaded = await unload_handler_by_name(*args)

#     is_loaded = await load_handler_by_name(*args)
#     return is_unloaded and is_loaded


def get_active_handlers(client: Client, bot_type: UB_OR_B | Any):
    if bot_type not in ["userbot", "bot"]:
        raise ValueError(f"Unknown type {bot_type}!")

    elif bot_type == "bot" and (
        other_bot := getattr(client, "_other_bot", None)
    ):
        return _get_client_handlers(other_bot)

    elif bot_type == "bot":
        raise TypeError("Didn't found additional bot :/")

    else:
        return _get_client_handlers(client)


# def get_module_handlers(_name: str) -> list[MyHandler]:
#     name, bot_type = _get_type(_name)
#     if bot_type is None:
#         raise TypeError("unknown type none")

#     handlers = get_default_handlers(bot_type)
#     handlers_names = list()
#     for h in handlers:
#         if h.name != name:
#             continue
#         handlers_names.append(h.name.rsplit(".", maxsplit=1)[0])

#     return handlers


@overload
async def handler_is_loaded(
    client: Client, _name: str, return_type: Literal["str"] = "str"
) -> str: ...
@overload
async def handler_is_loaded(
    client: Client, _name: str, return_type: Literal["bool"]
) -> bool: ...
async def handler_is_loaded(
    client: Client, _name: str, return_type: BOOL_OR_STR = "str"
) -> str | bool:
    is_bool = return_type == "bool"
    name, bot_type = _get_type(_name)
    if bot_type is None:
        raise ValueError(f"Didn't found module {name} ({_name}) :/")

    handlers = get_active_handlers(client, bot_type)
    handlers_names = [h.name.rsplit(".", maxsplit=1)[0] for h in handlers]

    if name not in sys.modules and name in handlers_names:
        await unload_handler_by_name(client, _name)
        handlers = get_active_handlers(client, bot_type)
        handlers_names = [h.name.rsplit(".", maxsplit=1)[0] for h in handlers]

    if name not in sys.modules or name not in handlers_names:
        return False if is_bool else f"Модуль {name} не загружен"

    handler_index = handlers_names.index(name)
    handler = handlers[handler_index]

    if is_bool:
        return handler.is_loaded

    formatter = "{}: {}"
    handlers_info = "\n * ".join(
        [""]
        + [
            formatter.format(
                h.handler.callback.__name__, repr_filter(h.handler.filters)
            )
            for h in handlers
            if name in h.name
        ]
    )
    return f"Модуль {_name} ({name}) {'' if handler.is_loaded else 'не'} загружен. {handlers_info}"


@overload
async def load_handler_by_name(
    client: Client, _name: str, return_type: Literal["str"] = "str"
) -> str: ...
@overload
async def load_handler_by_name(
    client: Client, _name: str, return_type: Literal["bool"]
) -> bool: ...
async def load_handler_by_name(
    client: Client, _name: str, return_type: BOOL_OR_STR = "str"
) -> str | bool:
    return_bool = return_type == "bool"
    name, bot_type = _get_type(_name)
    if bot_type is None:
        logger.warning(
            "Unknown module type",
            in_name=_name,
            module_name=name,
            bot_type=bot_type,
        )
        return f"Didn't found module {_name} :/"

    if name is None:
        logger.warning(
            "Unknown module name",
            in_name=_name,
            module_name=name,
            bot_type=bot_type,
        )
        return f"Didn't found module {_name} :/"

    if bot_type == "bot":
        return "эээм... я пока хз как это делать"
        raise TypeError("Didn't found additional bot :/")

    else:
        client_to_change = client

    default_handlers = get_default_handlers(bot_type)
    default_handlers_names = [
        h.name.rsplit(".", 1)[0] for h in default_handlers
    ]

    handlers = get_active_handlers(client, bot_type)
    handlers_names = [h.name.rsplit(".", 1)[0] for h in handlers]
    if name not in default_handlers_names:
        logger.debug(
            "Not found module_name in default handlers",
            default_handlers_names=default_handlers_names,
            module_name=name,
        )
        return False if return_bool else f"Не найден модуль ('{name}') :/"

    is_already_loaded = name in handlers_names
    if is_already_loaded:
        return True if return_bool else "Модуль уже загружен"

    while name in default_handlers_names:
        handler_index = default_handlers_names.index(name)
        handler = default_handlers[handler_index]
        await client_to_change.add_handler(handler.handler, handler.group)

        del default_handlers[handler_index]
        del default_handlers_names[handler_index]

    if return_bool:
        return True
    return f"Загружен модуль {name}"


@overload
async def unload_handler_by_name(
    client: Client, _name: str, return_type: Literal["str"] = "str"
) -> str: ...
@overload
async def unload_handler_by_name(
    client: Client, _name: str, return_type: Literal["bool"]
) -> bool: ...
async def unload_handler_by_name(
    client: Client, _name: str, return_type: BOOL_OR_STR = "str"
) -> str | bool:
    is_bool = return_type == "bool"
    name, bot_type = _get_type(_name)
    if bot_type is None or name is None:
        raise ValueError(f"Didn't found module {_name} :/")

    if bot_type == "bot":
        return "эээм... я пока хз как это делать"
        raise TypeError("Didn't found additional bot :/")

    else:
        client_to_change = client

    handlers = get_active_handlers(client, bot_type)
    handlers_names = [h.name.rsplit(".", 1)[0] for h in handlers]
    is_already_unloaded = name not in sys.modules
    if is_already_unloaded:
        return True if is_bool else "Модуль уже разгружен"

    while name in handlers_names:
        handler_index = handlers_names.index(name)
        handler = handlers[handler_index]
        await client_to_change.remove_handler(handler.handler, handler.group)

        del handlers[handler_index]
        del handlers_names[handler_index]
    del sys.modules[name]

    if is_bool:
        return True
    return f"Разгружен модуль {name}"


def _convert_my_module(name: str) -> list[MyCallable]:
    """Convert my module type to list with typical pyrogram's functions (@Client.on_message... but result of it)"""
    module = _try_import_module(name)
    if module is None:
        raise NameError(f"Didn't found module {name}!")

    if not hasattr(module, "Config"):
        raise ValueError(f'Userbot\'s module {name} need to have "Config"')

    cfg: Cfg = module.Config
    if not hasattr(module, cfg._main_func):
        raise ValueError(
            f'Userbot\'s module {name} need to have function "{cfg._main_func}"!'
        )

    callback: MyCallable = copy.deepcopy(getattr(module, cfg._main_func))
    handler_tuple = cfg.handler, 0
    callback.handlers = []
    callback.handlers.append(handler_tuple)
    return [callback]


def _try_import_module(name: str) -> ModuleType | None:
    try:
        module = import_module(name)
        return module
    except Exception as ex:
        logger.warning(f"skip importing {name} bc {ex}")
        return None


def _get_client_handlers(client: Client) -> list[MyHandler]:
    results: list[MyHandler] = []

    real_handlers: dict[int, list[Handler]] = client.dispatcher.groups
    for real_handler_group in real_handlers:
        for real_handler in real_handlers[real_handler_group]:
            callback = real_handler.callback
            handler = MyHandler(
                name=f"{callback.__module__}.{callback.__name__}",
                is_loaded=True,
                handler=real_handler,
                group=real_handler_group,
            )
            results.append(handler)

    return results


only_actual_files_pattern = "[!_]*.py"


def get_default_handlers(type: UB_OR_B) -> list[MyHandler]:
    default_handlers: list[MyHandler] = list()
    scripts: list[pathlib.Path] = []
    if type == "userbot":
        directories = [userbot_handlers_directory, userbot_scripts_directory]

    elif type == "bot":
        directories = [bot_handlers_directory]

    else:
        raise ValueError(f'Excepted "userbot" or "bot", not {type!r}!')

    for directory in directories:
        scripts.extend(directory.glob(only_actual_files_pattern))

    for script in scripts:
        module_name = script.as_posix().replace("/", ".").removesuffix(".py")
        loaded_before_import = module_name in sys.modules
        try:
            module = import_module(module_name)
        except Exception as ex:
            ex_str = " * ".join(traceback.format_exception(ex))
            logger.error(f"Skipped {script} because {ex}: \n{ex_str}")
            if loaded_before_import:
                del sys.modules[module_name]
            continue

        if hasattr(module, "main") and callable(module.main):
            callbacks_with_handlers = _convert_my_module(module.__name__)
        else:
            callbacks_with_handlers = [
                var_value
                for var_value in module.__dict__.values()
                if hasattr(var_value, "handlers")
                and bool(callable(var_value))
                and isinstance(var_value.handlers, list)
            ]

        for callback in callbacks_with_handlers:
            for handler_tuple in callback.handlers:
                handler = MyHandler(
                    name=f"{callback.__module__}.{callback.__name__}",
                    is_loaded=False,
                    handler=handler_tuple[0],
                    group=handler_tuple[1],
                )
                default_handlers.append(handler)
    return default_handlers


def get_handlers_status_string(
    client: Client, type: UB_OR_B = "userbot"
) -> str:
    default_handlers = get_default_handlers(type=type)
    handlers = _get_client_handlers(client)

    combined_handlers = {h.name: h for h in default_handlers}
    combined_handlers.update({h.name: h for h in handlers})

    logger.debug(
        "Got handlers",
        default_handlers=[h.to_dict() for h in default_handlers],
        handlers=[h.to_dict() for h in handlers],
        combined_handlers={
            i[0]: i[1].to_dict() for i in combined_handlers.items()
        },
    )

    results: list[str] = []

    for handler in combined_handlers.values():
        # if handler.name in sys.modules:
        # real_handler = handlers_names[handler.name]
        # loaded = real_handler.is_loaded
        # else:
        loaded = handler.is_loaded
        results.append(f"{'✅' if loaded else '🚫'} {handler.name}")

    result = "\n".join(results)
    return result


def _get_type(name: str) -> tuple[str, UB_OR_B] | tuple[None, None]:
    if name.startswith("handlers.userbot."):
        return name, "userbot"

    elif name.startswith("handlers.bot."):
        return name, "bot"

    elif name.startswith("scripts."):
        return name, "userbot"

    elif name.startswith("bot."):
        return f"handlers.{name}", "bot"

    elif name.startswith("userbot."):
        return f"handlers.{name}", "userbot"

    else:
        return None, None


def reload_module_by_name(name: str) -> bool:
    try:
        module = import_module(name)
        module = reload(module)
        return True
    except Exception:
        return False


def _main():
    import handlers.userbot.my_music as custom_module  # type: ignore

    callback = custom_module.music_cmd  # noqa: F841


if __name__ == "__main__":
    _main()


async def main(client: Client, message: Message):
    return await core_modules_cmd(client, message)


@Client.on_message(Config.Metadata.filter)
async def core_modules_cmd(client: Client, message: Message):
    # print()

    args = (message.command or []).copy()

    result: str | bool | None = None

    match args:
        # case [
        #     "mreload" | "reload",
        #     name,
        # ]:
        #     result = await reload_handler_by_name(client, name)

        case [
            "mcheck",
            name,
            "bool",
        ] | ["mcheck", name]:
            result = await handler_is_loaded(client, name, return_type="bool")

        case ["mcheck", name, "str"]:
            result = await handler_is_loaded(client, name, return_type="str")

        case ["mload", name]:
            result = await load_handler_by_name(client, name)

        case ["munload", name]:
            result = await unload_handler_by_name(client, name)

        case ["mlist"]:
            result = f"Here is the modules:\n<blockquote expandable>{get_handlers_status_string(client)}</blockquote>"

        case ["mlist", "bot"]:
            other_bot: Client | None
            if other_bot := getattr(client, "_other_bot", None):
                result = f"Доступные модули бота:\n<blockquote expandable>{get_handlers_status_string(other_bot, type='bot')}</blockquote>"
            else:
                result = "Дополнительный бот не найден :/"

        case ["mhelp"]:
            result = "Доступные команды: " + ", ".join(Config.Metadata.cmds)
            result = """Доступные использования:
 • .modules check — проверить состояние модуля (загружен ли (краткой формой) – реакция лайк/дизлайк)
 • .modules load — загрузить модуль
 • .modules unload — сгрузить модуль
 • .modules list — посмотреть доступные модули
 • .modules list bot — посмотреть доступные модули у бота
 • .modules <модуль> — проверить состояние модуля (да, опять)
"""

        case _:
            result = Config.Metadata.desc

    if isinstance(result, str):
        await answer(message, result, len_for_image=4095, edit=False)

    elif isinstance(result, bool):
        await message.react("👍" if result else "👎")
