# from utils.modules import get_handlers_status_string
from utils.config import Config as Cfg
from utils.good_things import answer

from pyrogram.types import Message
from utils import Client
from aiogram import Dispatcher, Router
from aiogram.dispatcher.event.handler import HandlerObject as AioHandler

from utils.config.my_types import MyCallable
from pyrogram.handlers.handler import Handler
from pyrogram import filters
from dataclasses import dataclass
from typing import Any, Literal, overload
from types import ModuleType

from importlib import import_module, reload
import pathlib
import os

import traceback
import sys

import datetime
import copy
import json


Config = Cfg(
    name=__name__,
    desc='Control all handlers in userbot. Load/unload/reload? Okay! If forgot commands, use "help"',
    cmds=[
        "module",
        "modules",
        "mhelp",
        "mlist",
        "mcheck",
        # "mreload",
        "munload",
        "mload",
        "minvoke",
    ],
    other_can_use=False,
)

logger = Config.logger

type UB_OR_B = Literal["userbot", "bot"]
type BOOL_OR_STR = Literal["str", "bool"]
await_task = True


@Client.on_message(Config.Metadata.filter)
async def main(client: Client, message: Message):
    # print()
    # logger.info(f"invoked at {datetime.datetime.now()}")
    # _update_dict(client)
    # return

    args = message.command.copy()

    result: str | bool | None = None
    status: bool | None = None

    match args:
        # case ["modules" | "module", "reload", name] | ["mreload" | "reload", name]:
        #     # if not name.startswith("scripts_"): name = "scripts_" + name
        #     result = await reload_handler_by_name(client, name)

        case ["modules" | "module", "check", name, "bool"] | [
            "mcheck",
            name,
            "bool",
        ]:
            result = await handler_is_loaded(client, name, return_type="bool")

        case ["modules" | "module", "check", name] | ["mcheck", name]:
            result = await handler_is_loaded(client, name, return_type="str")

        case ["modules" | "module", "load", name] | ["mload", name]:
            result = await load_handler_by_name(client, name)

        case ["modules" | "module", "unload", name] | ["munload", name]:
            result = await unload_handler_by_name(client, name)

        case ["modules" | "module", "list", *_bot] | ["mlist", *_bot]:
            for_bot = bool(_bot and _bot[0] == "bot")
            bot_type = "bot" if for_bot else "userbot"

            if (
                for_bot
                and (bot := getattr(client, "_other_bot", None)) is not None
            ):
                client_to_check = client
                bot_type_str = "дополнительного бота"

            elif for_bot:
                result = "Дополнительный бот не найден"
                return

            else:
                client_to_check = client
                bot_type_str = "юзербота"

            result = f"Доступные модули {bot_type_str}:\n<blockquote expandable>{await get_handlers_status_string(client_to_check, bot_type)}</blockquote>"

        case ["modules" | "module", "help"] | ["mhelp"]:
            result = "Доступные команды: " + ", ".join(Config.Metadata.cmds)
            result = """Доступные использования:
 • .modules check — проверить состояние модуля (загружен или нет, в краткой форме — реакции лайк/дизлайк)
 • .modules load — загрузить модуль
 • .modules unload — сгрузить модуль
 • .modules list — посмотреть доступные модули
 • .modules list bot — посмотреть доступные модули у бота
 • .modules <модуль> — проверить состояние модуля (да, опять)
"""

        case ["modules" | "module", name]:
            result = await handler_is_loaded(client, name, return_type="str")

        case _:
            result = Config.Metadata.desc

    if isinstance(result, str):
        # print(len(result))
        await answer(message, result, len_for_image=3000)

    elif isinstance(result, bool):
        await message.react("👍" if result else "👎")
        # await asyncio.sleep(5)
        # await message.react()


userbot_scripts_directory = pathlib.Path("scripts")
"""./"""
userbot_handlers_directory = pathlib.Path("handlers", "userbot")
"""./handlers/userbot/"""
bot_handlers_directory = pathlib.Path("handlers", "bot")
"""./handlers/bot/"""


def log(text: str) -> None:
    logger.info(
        f"{str(datetime.datetime.now())[:-3]} - runtime_plaftorm - {text}"
    )


@dataclass
class MyHandler:
    name: str
    is_loaded: bool
    handler: Handler | AioHandler
    group: int

    def to_dict(self):
        d = vars(self)
        d["_"] = true_repr_name(self)
        return d

    def __bool__(self):
        return self.is_loaded

    def __str__(self):
        return f"<MyHandler {self.name}, is_loaded:{self.is_loaded}>"

    def __repr__(self):
        result = f"MyHandler(name={self.name}, is_loaded={self.is_loaded}, group={self.group}, handler={deparse_handler(self.handler)})"
        return result


def true_repr_name(x: Any) -> str:
    type_ = type(x)
    module = type_.__module__
    qualname = type_.__qualname__
    result = f"{module}.{qualname}"
    return result


def deparse_handler(handler: AioHandler | Handler | Any) -> str:
    """Return some repr(handler)"""
    type_string = true_repr_name(handler)
    callback_string = handler.callback.__module__
    filter_string = repr_filter(handler.filters)
    result = "{}({}, {})".format(type_string, callback_string, filter_string)
    return result


def repr_filter(
    my_obj: filters.Filter | Handler | Any,
    _i=0,
    mode: Literal["json", "python"] = "python",
) -> str:
    """Return some repr(filter)"""
    if not isinstance(my_obj, (filters.Filter, Handler)):
        return repr(my_obj)

    type_string = true_repr_name(my_obj)
    # arguments = {k: v for (k, v) in vars(my_obj) if k[0]!="_" and k!="self"}
    if mode == "json":
        args = (
            json.dumps(
                my_obj,
                sort_keys=True,
                indent=4,
                ensure_ascii=False,
                default=vars,
            )
            .removeprefix("{")
            .removesuffix("}")
        )
    else:
        args = ", ".join([f"{i}={getattr(my_obj, i)}" for i in dir(my_obj)])

    result = f"{type_string}({args})"
    return result


def get_active_handlers(client: Client, bot_type: UB_OR_B | Any):
    if bot_type not in ["userbot", "bot"]:
        raise ValueError(f"Unknown type {bot_type}!")

    elif bot_type == "bot" and (
        other_bot := getattr(client, "_other_bot", None)
    ):
        return get_aio_client_handlers(other_bot[0])

    elif bot_type == "bot":
        raise TypeError("Didn't found additional bot :/")

    else:
        return get_client_handlers(client)


def get_module_handlers(_name: str) -> list[MyHandler]:
    name, bot_type = get_module_type(_name)
    if bot_type is None:
        raise TypeError("unknown type none")

    handlers = get_default_handlers(bot_type)
    handlers_names = list()
    for h in handlers:
        if h.name != name:
            continue
        # logger.info(h.name)
        handlers_names.append(h.name.rsplit(".", maxsplit=1)[0])

    return handlers


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
    name, bot_type = get_module_type(_name)
    if bot_type is None or name is None:
        return False if is_bool else f"Не найден модуль {_name} ({name})"

    handlers = get_active_handlers(client, bot_type)
    handlers_names = [h.name.rsplit(".", maxsplit=1)[0] for h in handlers]

    if name not in sys.modules and name in handlers_names:
        await unload_handler_by_name(client, _name)
        handlers = get_active_handlers(client, bot_type)
        handlers_names = [h.name.rsplit(".", maxsplit=1)[0] for h in handlers]

    if name not in sys.modules or name not in handlers_names:
        result = f"Модуль {_name} ({name}) не загружен"
        # print(result)
        return False if is_bool else f"Модуль {name} не загружен"

    result = f"Модуль {_name} ({name}) загружен"
    # print(result)
    handler_index = handlers_names.index(name)
    handler = handlers[handler_index]

    if is_bool:
        return handler.is_loaded

    return result


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
    is_bool = return_type == "bool"
    name, bot_type = get_module_type(_name)
    if bot_type is None or name is None:
        # print(f"{_name}: {name}, {bot_type}")
        return False if is_bool else f"Не найден модуль {_name} ({name})"

    if (
        bot_type == "bot"
        and hasattr(client, "_other_bot")
        and isinstance(client._other_bot, Client)
    ):
        client_to_change: Client = client._other_bot

    elif bot_type == "bot":
        raise TypeError("Didn't found additional bot :/")

    elif bot_type == "userbot" and name is not None:
        client_to_change = client

    else:
        raise TypeError(f"Didn't understood args ({name, bot_type}) :/")

    default_handlers, with_errors = get_default_handlers(
        bot_type, save_errors=True
    )
    default_handlers_names = [
        h.name.rsplit(".", 1)[0] for h in default_handlers
    ]
    errors_names = [i[0].replace(".", "/") + ".py" for i in with_errors]
    print([i.name.rsplit(".", 1)[0] for i in default_handlers], name)

    handlers = get_active_handlers(client, bot_type)
    handlers_names = [h.name.rsplit(".", 1)[0] for h in handlers]
    if name in errors_names:
        index = errors_names.index(name)
        errored = with_errors[index]
        return (
            False
            if is_bool
            else f"Модуль {name} не загружен, потому что произошла ошибка {errored[1]!r}"
        )
    if name not in default_handlers_names:
        # logger.info(f"! module {name} didn't found")
        return False if is_bool else f"Не найден модуль {name} ({_name}) :/"

    is_already_loaded = name in handlers_names
    if is_already_loaded:
        # logger.info(f"! module {name} already loaded")
        return True if is_bool else "Модуль уже загружен"

    # logger.info(f"! module {name} is loading...")
    while name in default_handlers_names:
        handler_index = default_handlers_names.index(name)
        handler = default_handlers[handler_index]
        # logger.info(f"  handler with {handler.handler.callback} is loading...")
        client_to_change.add_handler(handler.handler, handler.group)

        # logger.info(f"  handler with {handler.handler.callback} is loaded")
        del default_handlers[handler_index]
        del default_handlers_names[handler_index]

    # logger.info(f"load {name}")
    if is_bool:
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
    name, bot_type = get_module_type(_name)
    if bot_type is None or name is None:
        raise ValueError(f"Didn't found module {_name} :/")

    if bot_type == "bot" and (other_bot := getattr(client, "_other_bot", None)):
        client_to_change: Client = other_bot

    elif bot_type == "bot":
        raise TypeError("Didn't found additional bot :/")

    else:
        client_to_change = client

    handlers = get_active_handlers(client, bot_type)
    handlers_names = [h.name.rsplit(".", 1)[0] for h in handlers]
    # logger.info(name, f"{handlers_names}")
    is_already_unloaded = name not in sys.modules
    if is_already_unloaded:
        # logger.info(f"! module {name} already unloaded")
        return True if is_bool else "Модуль уже разгружен"

    while name in handlers_names:
        handler_index = handlers_names.index(name)
        handler = handlers[handler_index]
        client_to_change.remove_handler(handler.handler, handler.group)

        del handlers[handler_index]
        del handlers_names[handler_index]
    del sys.modules[name]

    # logger.info(f"unload {name}")
    if is_bool:
        return True
    return f"Разгружен модуль {name}"


def convert_my_module(name: str) -> list[MyCallable]:
    """Convert my module type to list with typical pyrogram's functions (@Client.on_message... but result of it)"""
    module = try_import_module(name)
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


def try_import_module(name: str) -> ModuleType | None:
    try:
        module = import_module(name)
        return module
    except Exception as ex:
        logger.warning(f"skip importing {name} bc {ex}")
        return None


def get_aio_client_handlers(router: Router) -> list[MyHandler]:
    s = os.sep
    # modules: list[UsualModule] = list()
    results: list[MyHandler] = []

    for router in router.sub_routers:
        for observer in router.observers.values():
            for handler in observer.handlers:
                callback = handler.callback
                module_name = callback.__module__
                is_enabled = import_module(module_name).Config.Metadata.enabled
                handler = MyHandler(
                    f"{callback.__module__}.{callback.__name__}",
                    is_enabled,
                    handler,
                    0,
                )
                results.append(handler)
        for x in router.sub_routers:
            results.extend(get_aio_client_handlers(x))

    return results


def get_client_handlers(client: Client) -> list[MyHandler]:
    s = os.sep
    # modules: list[UsualModule] = list()
    results: list[MyHandler] = []

    real_handlers: dict[int, list[Handler]] = client.dispatcher.groups
    for real_handler_group in real_handlers:
        for real_handler in real_handlers[real_handler_group]:
            callback = real_handler.callback
            # print(callback.__module__)
            _r: tuple[ModuleType] | None
            module_name = (
                (_r := real_handler.callback.__defaults__) and _r[0].__name__
            ) or callback.__module__
            is_enabled = import_module(module_name).Config.Metadata.enabled
            handler = MyHandler(
                f"{callback.__module__}.{callback.__name__}",
                is_enabled,
                real_handler,
                real_handler_group,
            )
            results.append(handler)

    return results


only_actual_files_pattern = "[!_]*.py"


@overload
def get_default_handlers(type: UB_OR_B) -> list[MyHandler]: ...
@overload
def get_default_handlers(
    type: UB_OR_B, save_errors: Literal[False]
) -> list[MyHandler]: ...
@overload
def get_default_handlers(
    type: UB_OR_B, save_errors: Literal[True]
) -> tuple[list[MyHandler], list[tuple[str, Exception]]]: ...
def get_default_handlers(
    type: UB_OR_B, save_errors: bool = False
) -> list[MyHandler] | tuple[list[MyHandler], list[tuple[str, Exception]]]:
    default_handlers: list[MyHandler] = list()
    scripts: list[pathlib.Path] = []

    with_errors = []

    if type == "userbot":
        directories = [userbot_handlers_directory, userbot_scripts_directory]

    elif type == "bot":
        directories = [bot_handlers_directory, userbot_scripts_directory]

    else:
        raise ValueError(f'Excepted "userbot" or "bot", not {type!r}!')

    for directory in directories:
        scripts.extend(directory.glob(only_actual_files_pattern))

    for script in scripts:
        module_name = script.as_posix().replace("/", ".").removesuffix(".py")
        try:
            module = import_module(module_name)
        except Exception as ex:
            ex_str = " * ".join(traceback.format_exception(ex))
            logger.error(f"Skipped {script} because {ex}: \n{ex_str}")
            if save_errors:
                with_errors.append((module_name, ex))
            continue

        # for script like scripts.boo
        if type == "userbot":
            if hasattr(module, "main") and callable(module.main):
                callbacks_with_handlers = convert_my_module(module.__name__)
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
                        f"{callback.__module__}.{callback.__name__}",
                        False,
                        handler_tuple[0],
                        handler_tuple[1],
                    )
                    default_handlers.append(handler)
        else:
            rt: Router | None = getattr(module, "rt", None)
            if rt is None:
                continue
            for observer in rt.observers.values():
                for handler in observer.handlers:
                    callback = handler.callback
                    my_handler = MyHandler(
                        f"{callback.__module__}.{callback.__name__}",
                        True,
                        handler,
                        0,
                    )
                    default_handlers.append(my_handler)
    if save_errors:
        return default_handlers, with_errors
    return default_handlers


async def get_handlers_status_string(
    client: Client, type: UB_OR_B = "userbot"
) -> str:
    default_handlers = get_default_handlers(type=type)
    if type == "userbot":
        # assert isinstance(client, Client)
        handlers = get_client_handlers(client)
    else:
        # assert isinstance(client, )
        dp: Dispatcher = getattr(client, "_other_bot")[0]
        handlers = get_aio_client_handlers(dp)

    # default_names: dict[str, MyHandler] = {hand.name: hand for hand in default_handlers}
    handlers_names: dict[str, MyHandler] = {
        hand.name: hand for hand in handlers
    }

    results: list[str] = []

    # print([h.name for h in default_handlers])
    # print([h.name for h in handlers])
    for handler in default_handlers:
        module_name = handler.name.rsplit(".", 1)[0]
        loaded = await handler_is_loaded(client, module_name, "bool")

        # if handler.name in handlers_names:
        #     real_handler = handlers_names[handler.name]
        #     loaded = real_handler.is_loaded
        # else:
        #     real_handler = None
        #     loaded = handler.is_loaded

        results.append(f"{'✅' if loaded else '🚫'} {handler.name}")

    result = "\n".join(results)
    return result


def get_module_type(name: str) -> tuple[str, UB_OR_B] | tuple[None, None]:
    fields: dict[str, tuple[str, UB_OR_B]] = {
        "handlers.userbot.": ("{}", "userbot"),
        "handlers.bot.": ("{}", "bot"),
        "userbot.": ("handlers.{}", "userbot"),
        "bot.": ("handlers.{}", "bot"),
        "scripts.": ("{}", "userbot"),
    }

    for prefix, (formatter, result) in fields.items():
        if (
            name.startswith(prefix)
            and pathlib.Path(
                (_name := formatter.format(name)).replace(".", "/") + ".py"
            ).exists()
        ):
            return _name, result
    else:
        if pathlib.Path(
            (_name := f"scripts.{name}").replace(".", "/") + ".py"
        ).exists():
            print(_name)
            return _name, "userbot"
        return None, None

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
    except:
        return False


def _main():
    import handlers.userbot.my_music as custom_module

    callback = custom_module.music_cmd
    logger.info(callback.handlers)
    logger.info(dir(callback))


if __name__ == "__main__":
    _main()
