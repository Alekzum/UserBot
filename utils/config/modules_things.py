from types import ModuleType
from typing import Literal, Awaitable, Callable, Protocol, Any

import traceback
import structlog
import pathlib
from .my_things import load_raw
from aiogram import Router
from pyrogram.handlers.handler import Handler
from utils.my_patches import Client as Client
from aiogram.dispatcher.event.handler import HandlerObject

from functools import partial
from importlib import reload, import_module
import asyncio


def _wrap_observers(rt: Router):
    def wrap(handler: HandlerObject):
        async def check(
            upd: Any, *args: Any, **kwargs: Any
        ) -> tuple[bool, dict[str, Any]]:
            new_rt: Router = reload(import_module(rt.name)).rt
            # logger.info(f"Reloaded module {rt.name} for filters")
            # logger.info(f"{index=}, {new_rt.observers[update_name].handlers=}")
            if len(new_rt.observers[update_name].handlers) - 1 >= index:
                new_handler = new_rt.observers[update_name].handlers[index]
            else:
                new_handler = handler

            if not new_handler.filters:
                return True, kwargs
            for event_filter in new_handler.filters:
                check = await event_filter.call(upd, *args, **kwargs)
                if not check:
                    return False, kwargs
                if isinstance(check, dict):
                    kwargs.update(check)
            return True, kwargs

        async def call(upd: Any, *args: Any, **kwargs: Any) -> Any:
            callback = handler.callback
            handler.callback = getattr(
                reload(import_module(callback.__module__)), callback.__name__
            )
            logger.debug(f"Reloaded module {callback.__module__} for callback")
            wrapped = partial(
                handler.callback, upd, *args, **handler._prepare_kwargs(kwargs)
            )
            if handler.awaitable:
                return await wrapped()
            return await asyncio.to_thread(wrapped)

        if not getattr(handler, "_wrapped", False):
            # logger.debug(f"rt {rt.name}: wrap {handler.callback.__name__!r}")
            # handler.call
            handler.__dict__["call"] = call
            handler.__dict__["check"] = check
            setattr(handler, "_wrapped", True)
        return handler

    for update_name, observer in rt.observers.items():
        for index, handler in enumerate(observer.handlers):
            observer.handlers[index] = wrap(handler=handler)
    return rt


# class MyAioRouter(Router):
#     # def __new__(cls):

#     def __init__(self, rt: Router):
#         # super().__init__(name=name)
#         self.rt = rt
#         rt._parent_router = None
#         MyAioRouter._wrap_observers(rt)
#         return rt

#     # @classmethod


class BaseModule(Protocol):
    Config: Any


class PyroModule(BaseModule):
    main: Callable
    on_startup: Callable
    on_shutdown: Callable


class AioModule(BaseModule):
    rt: Router


scripts_path = [
    pathlib.Path("scripts"),
    # pathlib.Path("handlers", "userbot")  # use @utils.my_decorators.on_message instead!
]


warned_modules: set[ModuleType] = set()


logger = structlog.getLogger(__name__)


def _get_modules_list() -> list[str]:
    return [
        ".".join(h.parts).removesuffix(h.suffix)
        for directory in scripts_path
        for h in directory.glob("[!_]*.py")
    ]


def get_diffs() -> tuple[list, dict[Literal["added", "removed"], set] | None]:
    """Get difference"""
    old_config = load_raw()["config"]
    handlers = get_active_handlers()
    new_config = load_raw()["config"]

    oc = set(old_config.keys())
    nc = set(new_config.keys())

    added_diff = nc - oc
    removed_diff = oc - nc

    if added_diff or removed_diff:
        logger.info(
            f"""
The difference between the old config and the new one:
    Added to the new one: {", ".join(list(added_diff)) or "nothing"}
    Removed from the old one: {", ".join(list(removed_diff)) or "nothing"}
"""
        )
    else:
        logger.debug(
            "The difference between the old config and the new one is literally nothing"
        )

    if added_diff != set() or removed_diff != set():
        return handlers, {"added": added_diff, "removed": removed_diff}
    else:
        return handlers, None


async def set_handlers(client: Client):
    handlers = get_active_handlers()
    logger.debug("got active handlers", active_handlers=handlers)
    for handler in handlers:
        await client.add_handler(handler)


def get_handler_by_name(name: str) -> Handler:
    module = import_module(f"scripts.{name}")
    # module = reload(module)
    handler = module.Config.handler
    return handler


def import_modules(names: list[str]) -> list[ModuleType]:
    result = []
    skipped_modules: list[tuple[str, Exception]] = []
    for name in names:
        try:
            module = import_module(name)
        except Exception as ex:
            skipped_modules.append((name, ex))
            continue

        try:
            _ = module.Config
        except AttributeError as ex:
            if module in warned_modules:
                continue
            warned_modules.add(module)
            logger.warning(
                "Module didn't have a config. Is it not needed? Add prefix _ to filename :shrug:",
                module_name=name,
                exception=ex, exc_info=True
            )

        result.append(module)

    for skipped_module, exc in skipped_modules:
        logger.warning(
            "Module raised an exceptions", module_name=skipped_module, exception=exc, exc_info=exc
        )
    return result


def _get_modules() -> list[ModuleType]:
    modules_names = _get_modules_list()
    modules = import_modules(modules_names)
    return modules


def get_active_handlers() -> list[Handler]:
    modules = _get_modules()
    handlers = [
        module.Config.handler
        for module in modules
        if hasattr(module, "main")
        and hasattr(module, "Config")
        and module.Config.Metadata.enabled
    ]
    return handlers


# on_EVENT things


def get_modules_with_func(func_name: str):
    have_func = function_in_module(func_name)
    return [module for module in _get_modules() if have_func(module)]


async def execute_on_startup(client: Client, diffs):
    startup_modules = get_modules_with_func("on_startup")

    # logger.info(f"{startup_modules=}")
    for module in startup_modules:
        await run_startup_module_async(module.__name__, client, diffs=diffs)


async def execute_on_shutdown(client: Client):
    shutdown_modules = get_modules_with_func("on_shutdown")

    # logger.info(f"{shutdown_modules=}")
    for module in shutdown_modules:
        await run_shutdown_module_async(module.__name__, client)


# startup things
async def run_startup_module_async(name: str, client: Client, *args, **kwargs):
    temp_module = import_module(name)
    on_startup: Callable[[Client], Awaitable] | None
    if (on_startup := getattr(temp_module, "on_startup", None)) is None:
        logger.warning(
            f"Module {temp_module.__name__} don't have function \"on_startup\" but it's selected as startup!"
        )
        return

    try:
        await on_startup(client, *args, **kwargs)
    except Exception as ex:
        ex_str = "\n" + "".join(traceback.format_exception(ex))
        logger.warning(f"Error with {name=}: {ex_str}")


# shutdown things
async def run_shutdown_module_async(name: str, client: Client):
    temp_module = import_module(name)
    on_shutdown: Callable[[Client], Awaitable] | None
    if (on_shutdown := getattr(temp_module, "on_shutdown", None)) is None:
        logger.warning(
            f"Module {temp_module.__name__} don't have function \"on_shutdown\" but it's selected as shutdown!"
        )
        return

    try:
        await on_shutdown(client)
    except Exception as ex:
        ex_str = "\n" + "".join(traceback.format_exception(ex))
        logger.warning(f"Error with {name=}: {ex_str}")


def function_in_module(func_name: str):
    def inner(module: ModuleType):
        return (func := getattr(module, func_name, None)) is not None and bool(
            callable(func)
        )

    return inner


def get_bot_routers() -> list[Router]:
    # def get_bot_routers() -> list[aiogram.Router]:
    modules = import_modules(
        list(
            set(
                f.as_posix().replace("/", ".").removesuffix(".py")
                for f in list(pathlib.Path("handlers", "bot").glob("[!_]*.py"))
                + list(pathlib.Path("handlers", "bot").glob("[!_]*.py"))
                + list(pathlib.Path("scripts").glob("[!_]*.py"))
            )
        )
    )
    routers = list(
        set(
            (_wrap_observers(rt) if rt.name.startswith("scripts.") else rt)
            # rt
            for module in modules
            if (rt := getattr(module, "rt", None))
            # and (getattr(rt, "parent_router", None) is None)
        )
    )
    return routers
