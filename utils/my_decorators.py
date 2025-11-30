from .my_patches import Client as Client
from pyrogram.types import Message
from pyrogram.filters import Filter, all as All
from pyrogram.methods.decorators.on_message import OnMessage
from pyrogram.methods.decorators.on_inline_query import OnInlineQuery
from pyrogram.methods.decorators.on_callback_query import OnCallbackQuery
from pyrogram.handlers.message_handler import MessageHandler
from pyrogram.handlers.inline_query_handler import InlineQueryHandler
from pyrogram.handlers.callback_query_handler import CallbackQueryHandler
from typing import Callable, Union, Optional, cast
from functools import wraps
from importlib import import_module
import structlog
from .config.my_types import Config


logger = structlog.getLogger(__name__)


def wrap_func(thing, func):
    @wraps(func)
    async def inner(client: Client, m: Message):
        cfg: Config = import_module(func.__module__).Config
        cfg._log_about_invoke_by_message(m)
        return await func(client, m)

    return inner


def _maker_handler(
    self: Union[
        "OnInlineQuery", "OnCallbackQuery", "OnMessage", Filter, None
    ] = None,
    filters: Optional[Filter] = None,
    group: int = 0,
    handler_type: Union[
        type[InlineQueryHandler],
        type[CallbackQueryHandler],
        type[MessageHandler],
        None,
    ] = None,
) -> Callable[[Callable], Callable]:
    if handler_type is None:
        raise ValueError(
            "Handler type is must be one of "
            "these handlers: InlineQueryHandler, "
            "CallbackQueryHandler, MessageHandler, not None!"
        )
    thing = filters or self or All
    logger.debug(f"invoked with {thing}")

    def decorator(func) -> Callable:
        nonlocal filters
        nonlocal self
        func = wrap_func(thing, func)

        if isinstance(self, Client):
            filters = cast(Filter, filters)
            self.add_handler(handler_type(func, filters), group)
        elif isinstance(self, Filter) or self is None:
            self = self or All
            if not hasattr(func, "handlers"):
                setattr(func, "handlers", [])

            getattr(func, "handlers").append(
                (
                    handler_type(func, self),
                    group if filters is None else filters,
                )
            )
        return func

    return decorator


def on_message(
    self: Union["OnMessage", Filter, None] = None,
    filters: Optional[Filter] = None,
    group: int = 0,
) -> Callable:
    """Decorator for handling new messages.

    This does the same thing as :meth:`~Client.add_handler` using the
    :obj:`~pyrogram.handlers.MessageHandler`.

    Parameters:
        filters (:obj:`~pyrogram.filters`, *optional*):
            Pass one or more filters to allow only a subset of messages to be passed
            in your function.

        group (``int``, *optional*):
            The group identifier, defaults to 0.
    """

    return _maker_handler(
        self, filters, group=group, handler_type=MessageHandler
    )


def on_inline_query(
    self: Union["OnInlineQuery", Filter, None] = None,
    filters: Optional[Filter] = None,
    group: int = 0,
) -> Callable:
    """Decorator for handling inline queries.

    This does the same thing as :meth:`~Client.add_handler` using the
    :obj:`~pyrogram.handlers.InlineQueryHandler`.

    Parameters:
        filters (:obj:`~pyrogram.filters`, *optional*):
            Pass one or more filters to allow only a subset of inline queries to be passed
            in your function.

        group (``int``, *optional*):
            The group identifier, defaults to 0.
    """

    return _maker_handler(
        self, filters, group=group, handler_type=InlineQueryHandler
    )


def on_callback_query(
    self: Union["OnCallbackQuery", Filter, None] = None,
    filters: Optional[Filter] = None,
    group: int = 0,
) -> Callable:
    """Decorator for handling callback queries.

    This does the same thing as :meth:`~Client.add_handler` using the
    :obj:`~pyrogram.handlers.CallbackQueryHandler`.

    Parameters:
        filters (:obj:`~pyrogram.filters`, *optional*):
            Pass one or more filters to allow only a subset of callback queries to be passed
            in your function.

        group (``int``, *optional*):
            The group identifier, defaults to 0.
    """
    return _maker_handler(
        self, filters, group=group, handler_type=CallbackQueryHandler
    )
