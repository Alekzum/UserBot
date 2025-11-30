from typing import (
    TypeVar,
    Any,
    Callable,
    Coroutine,
    Union,
    Optional,
    overload,
    Literal,
)
from types import ModuleType

from pyrogram.handlers.handler import Handler
from pyrogram.handlers.message_handler import MessageHandler
from pyrogram.filters import (
    command as Command,
    me as Me,
    all as All,
    AndFilter,
    OrFilter,
    Filter,
)
from pyrogram.types import Message
from aiogram.types import Message as AioMessage

from .modules_things import load_raw
from .my_things import get_variable, set_variable, get_prefix
from utils.my_patches import Client
from utils.my_filters import (
    user_in_global_whitelist,
    chat_in_allowed,
    user_in_local_whitelist,
)


from dataclasses import dataclass
from importlib import reload, import_module
import traceback
import structlog

from functools import wraps
import asyncio


__slots__ = ["Config", "Metadata", "MyAioRouter"]

T = TypeVar("T")
_DEFAULT = object()
logger = structlog.getLogger(__name__)


def setup_logger(name: str):
    temp_logger = structlog.getLogger(name)
    return temp_logger


def generate_exception_tree(exception: Exception):
    return traceback.format_exception(exception)


def parse_exception(ex: Exception, need_log=True) -> str:
    import traceback

    error = "".join(traceback.format_exception(ex))
    result = (
        f"Возникла ошибка {ex!r}\n<blockquote expandable>{error}</blockquote>"
    )
    if need_log:
        print(result)
    return result


class MyCallable:
    """Just function with handlers"""

    handlers: list[tuple[Handler, int]]
    __name__: str


class UsualModule(ModuleType):
    Config: "Config"


class ModuleWithMain(UsualModule):
    main: Callable[[Client, Message], Coroutine]


class ModuleWithStartup(UsualModule):
    on_startup: Callable[[Client], Coroutine]


class ModuleWithShutdown(UsualModule):
    on_shutdown: Callable[[Client], Coroutine]


@dataclass
class Metadata:
    """
    Attributes:
        name (str): Config's name in logging. Please use __name__
        variables (dict[str, Any], optional): What need to be added in Config's variables. You can use these variables by using Config as dict. Defaults to {}.
        cmds (str | list[str], optional): Commands to invoke this module. If empty, then module invoked on all messages. Defaults to [].
        desc (str, optional): Module's description. Used in .help <Module's name>. Defaults to "".
        other_can_use (bool, optional): Can users (exclude userbot's "host") use this module or only he. Defaults to False.
        whitelist (list[str], optional): Who can use this module with other (Why i add this?). Defaults to [].
        need_vars (list[str], optional): What need to add when use func main(). Defaults to [].
        can_be_reloaded (bool, optional): Module can be reloaded every invoke or need to reload this module for updated code?
        filters (Filter, optional): Set for this module some custom filter, parameter "cmds" need to be skipped. If skipped, all messages will be catch
        force_filters (bool): Only custom filter will be used. Defaults to False
        enabled (bool, optional): Is module enabled with startup or it need to be turn on after startup?
        enabled_logs (bool, optional): Do you need logging when this module is activated? Defaults to True
    """

    name: str
    variables: dict[str, Any]
    cmds: list[str]
    desc: str
    other_can_use: bool
    whitelist: list[Union[int, str]]
    need_vars: list[str]
    can_be_reloaded: bool
    filters: Optional[Filter]
    force_filters: bool
    enabled: bool
    enabled_logs: bool

    @property
    def filter(
        self, mode: Literal["message", "callback", "inline", "cir"] = "message"
    ) -> Filter | None:
        if self.force_filters and self.filters:
            return self.filters
        elif not self.force_filters and self.filters:
            logger.warning(
                f"{self.name} - Filters are provided, but force_filters=False"
            )

        elif self.force_filters and not self.filters:
            logger.warning(
                f"{self.name} - Filters aren't provided, but force_filters=True"
            )
            return self.filters

        cmds = self.cmds
        _other_can_use = self.other_can_use
        whitelist = self.whitelist

        _CanUseDangerModules = OrFilter(Me, user_in_global_whitelist)
        _OtherCanUse = OrFilter(
            chat_in_allowed, user_in_local_whitelist(whitelist)
        )
        _UserInvoke = (
            OrFilter(_CanUseDangerModules, _OtherCanUse)
            if _other_can_use
            else _CanUseDangerModules
        )
        """is command from me or chat/user which allowed to use command?"""
        _IsInvoked = Command(cmds, get_prefix()) if cmds else All
        """is module invoked?"""
        result = (
            self.filters
            if self.force_filters
            else AndFilter(_UserInvoke, _IsInvoked)
        )
        return result


_valid_get_modes = ["load_raw", "get_variable"]
_get_mode: Literal["load_raw", "get_variable"] = "get_variable"
_save_after_every_action: bool = True


class Config:
    _main_func = "main"
    _startup_func = "on_startup"
    _shutdown_func = "on_shutdown"
    _handler: Handler | None = None
    _not_be_saved = ["Metadata", "logger", "handler", "filter", "__all__"]

    def __init__(
        self,
        name: str,
        variables: dict[str, Any] | None = None,
        cmds: str | list[str] | None = None,
        desc: str = "",
        other_can_use: bool = False,
        whitelist: list[Union[int, str]] | None = None,
        need_vars: list[str] | None = None,
        can_be_reloaded=True,
        filters: Optional[Filter] = None,
        force_filters: bool = False,
        enabled: bool = True,
        enabled_logs: bool = True,
        _main_func: str = _main_func,
        _startup_func: str = _startup_func,
        _shutdown_func: str = _shutdown_func,
    ):
        """Just create config

        Args:
            name (str): Config's name in logging. Please use __name__
            variables (dict[str, Any], optional): What need to be added in Config's variables. You can use these variables by using Config as dict. Defaults to {}.
            cmds (str | list[str], optional): Commands to invoke this module. If empty, then module invoked on all messages. Defaults to [].
            desc (str, optional): Module's description. Used in .help <Module's name>. Defaults to "".
            other_can_use (bool, optional): Can users (exclude userbot's "host") use this module or only he. Defaults to False.
            whitelist (list[str], optional): Who can use this module with other (Why i add this?). Defaults to [].
            need_vars (list[str], optional): What need to add when use func main(). Defaults to [].
            can_be_reloaded (bool, optional): Module can be reloaded every invoke or need to reload this module for updated code?
            filters (Filter, optional): Set for this module some custom filter, parameter "cmds" need to be skipped. If skipped, all messages will be catch
            force_filters (bool): Only custom filter will be used. Defaults to False
            enabled (bool, optional): Is module enabled with startup or it need to be turn on after startup?
            enabled_logs (bool, optional): Do you need logging when this module is activated? Defaults to True
        """
        self._directory_path = ["data", "scripts", name]

        _cmds = (
            [] if cmds is None else [cmds] if isinstance(cmds, str) else cmds
        )
        _variables = variables or {}
        _whitelist = whitelist or []
        _need_vars = need_vars or []

        self.logger = setup_logger(name)
        self.Metadata = Metadata(
            name=name,
            desc=desc,
            cmds=_cmds,
            other_can_use=other_can_use,
            variables=_variables,
            whitelist=_whitelist,
            need_vars=_need_vars,
            can_be_reloaded=can_be_reloaded,
            filters=filters,
            force_filters=force_filters,
            enabled=enabled,
            enabled_logs=enabled_logs,
        )

        self._filter = self.Metadata.filter

        self.vars = self.Metadata.variables
        self.load_config()

    def __getitem__(self, key: str, /):
        return self.get(key)

    def __delitem__(self, key: str, /):
        return self.delete(key)

    def __setitem__(self, key: str, value: Any, /):
        return self.set(key, value)

    def __contains__(self, key: str, /):
        return key in self.vars

    def update(self, values: dict):
        if not isinstance(values, dict):
            raise TypeError(f"Value must be dict, not {type(values)}!")

        self.vars.update(values)
        if _save_after_every_action:
            self.save_config()

    @property
    def handler(self) -> Handler:
        module: ModuleType | ModuleWithMain = import_module(self.Metadata.name)

        callback = getattr(module, self._main_func)
        my_filter = self.Metadata.filter or All

        @wraps(callback)
        async def custom_callback(
            c: Client,
            m: Message,
            _module=module,
            _callback_name=self._main_func,
        ) -> None:
            if self.Metadata.can_be_reloaded:
                callback = getattr(reload(_module), _callback_name)
            else:
                callback = getattr(_module, _callback_name)

            try:
                await callback(c, m)
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                temp_result = " * ".join(generate_exception_tree(ex))
                logger.error(f"{self.Metadata.name} - {temp_result}\n * {ex!s}")

            self._log_about_invoke_by_message(m, after=True)
            m.continue_propagation()

        result = MessageHandler(callback=custom_callback, filters=my_filter)
        return result

    def _log_about_invoke_by_message(
        self, message: Message | AioMessage, after: bool = False
    ):
        def onlyLetters(string: str):
            return "".join([n for n in string if ord(n) < 128506])

        def shrink(string: str, length: int):
            return string if len(string) < length else string[:length] + "…"

        if isinstance(message, AioMessage):
            chat_display_name = shrink(onlyLetters(message.chat.full_name), 12)
            invoker = (
                message.sender_chat
                or message.from_user
                or message.sender_business_bot
            )
            invoker_display_name = invoker and invoker.full_name

            aboutChat = f"{chat_display_name!r}/{message.chat.id}, #{message.message_id}"
            if self.Metadata.enabled_logs:
                verb = "Invoking" if not after else "Invoked"
                logger.info(
                    f"{verb} AIOGRAM MODULE {self.Metadata.name} by {invoker_display_name} in chat {aboutChat}"
                )
            return

        chat_display_name = shrink(
            onlyLetters(message.chat and message.chat.full_name or "*unknown*"),
            12,
        )

        invoker = message.sender_chat or message.from_user
        invoker_display_name = ascii(
            invoker and invoker.full_name or "*unknown*"
        )

        aboutChat = f"{chat_display_name!r}/{message.chat and message.chat.id or 'id???'}, #{message.id} ({message.link})"
        if self.Metadata.enabled_logs:
            logger.info(
                f"Invoked PYROGRAM MODULE {self.Metadata.name} by {invoker_display_name} in chat {aboutChat}"
            )

    def load_config(self) -> None:
        """Just load config for this module"""
        default_cfg = self.vars
        real_cfg = default_cfg.copy()

        if _get_mode == "load_raw":
            raw = load_raw()
            loaded_cfg = raw["config"].get(self.Metadata.name, None)
            is_new = loaded_cfg is None
            loaded_cfg = loaded_cfg or dict()

        elif _get_mode == "get_variable":
            path = ["config", self.Metadata.name]
            loaded_cfg = get_variable(path, None)
            is_new = loaded_cfg is None
            loaded_cfg = loaded_cfg or dict()

        else:
            raise ValueError(
                f"Excepted {', '.join(_valid_get_modes)}, not {_get_mode!r}!"
            )

        if isinstance(loaded_cfg, dict):
            real_cfg.update(loaded_cfg)
        else:
            logger.warning(
                f"{self.Metadata.name} - Loaded config is not dict, it is {type(loaded_cfg)}!"
            )

        self.vars = real_cfg
        for key, item in real_cfg.items():
            if item is None:
                continue

        if is_new:
            self.save_config()

    def save_config(self):
        """Just save config for this module."""
        x = set_variable(["config", self.Metadata.name], self.vars)
        if x is None:
            logger.error(f"{x=}, {self.Metadata.name=}, {self.vars=}")
            return
        logger.debug(f"{x=}, {self.Metadata.name=}, {self.vars=}")

    def delete(self, key: str):
        """Delete Config.key.
        It is also be deleted from config.json"""
        del self.vars[key]
        if _save_after_every_action:
            self.save_config()

    def set(self, key: str, value: object):
        """Set Config.key to value *value*.
        It is also be setted in config.json"""
        self.vars[key] = value
        if _save_after_every_action:
            self.save_config()

    @overload
    def get(self, key: str) -> Any: ...
    @overload
    def get[T](self, key: str, default: T) -> Any | T: ...
    def get[T](self, key: str, default: T | object = _DEFAULT) -> Any | T:
        """Get actual Config.*key*.
        It is be get from config.json"""
        if default is _DEFAULT:
            return self.vars[key]
        else:
            return self.vars.get(key, default)
