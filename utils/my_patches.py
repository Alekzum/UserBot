from pyrogram.types import Message
from pyrogram.handlers.start_handler import StartHandler
from pyrogram.handlers.stop_handler import StopHandler
from pyrogram.handlers.connect_handler import ConnectHandler
from pyrogram.handlers.disconnect_handler import DisconnectHandler
from pyrogram.handlers.handler import Handler
from typing_extensions import OrderedDict, override
import pyrogram.client
import pyrogram.dispatcher
import aiogram
import structlog


class PatchedClient(pyrogram.client.Client):  # type: ignore
    _other_bot: tuple[aiogram.Dispatcher, aiogram.Bot] | None
    dispatcher: "PatchedDispatcher"

    @override
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatcher = PatchedDispatcher(self)  # type: ignore

    async def require_inline_bot(
        self, message: Message, query: str
    ) -> Message | None:
        from utils.good_things import require_inline_my_bot

        return await require_inline_my_bot(
            client=self, message=message, query=query
        )

    @override
    def add_handler(self: "PatchedClient", handler: "Handler", group: int = 0):  # type: ignore

        async def inner():
            if isinstance(handler, StartHandler):
                self.start_handler = handler.callback
            elif isinstance(handler, StopHandler):
                self.stop_handler = handler.callback
            elif isinstance(handler, ConnectHandler):
                self.connect_handler = handler.callback
            elif isinstance(handler, DisconnectHandler):
                self.disconnect_handler = handler.callback
            else:
                await self.dispatcher.add_handler(handler, group)

            return handler, group

        return self.loop.create_task(inner())

    @override
    def remove_handler(
        self: "PatchedClient", handler: "Handler", group: int = 0
    ):  # type: ignore
        async def inner():
            if isinstance(handler, DisconnectHandler):
                self.disconnect_handler = None
            else:
                self.dispatcher.remove_handler(handler, group)

        return self.loop.create_task(inner())


class PatchedDispatcher(pyrogram.dispatcher.Dispatcher):
    def __init__(self, app: "PatchedClient"):
        super().__init__(app)

    @override
    def add_handler(self, handler: "Handler", group: int):  # type: ignore
        logger.debug("Adding handler", func=handler.callback, func_module=handler.callback.__module__)
        async def fn():
            for lock in self.locks_list:
                await lock.acquire()

            try:
                if group not in self.groups:
                    self.groups[group] = []
                    self.groups = OrderedDict(sorted(self.groups.items()))

                self.groups[group].append(handler)
            finally:
                for lock in self.locks_list:
                    lock.release()

        return self.client.loop.create_task(fn())

    @override
    def remove_handler(self, handler: "Handler", group: int):  # type: ignore
        logger.debug("Removing handler", func=handler.callback, func_module=handler.callback.__module__)
        async def fn():
            for lock in self.locks_list:
                await lock.acquire()

            try:
                if group not in self.groups:
                    raise ValueError(
                        f"Group {group} does not exist. Handler was not removed."
                    )

                self.groups[group].remove(handler)
            finally:
                for lock in self.locks_list:
                    lock.release()

        return self.client.loop.create_task(fn())


Client = PatchedClient
Dispatcher = PatchedDispatcher


logger = structlog.getLogger(__name__)


__all__ = ["Client", "Dispatcher", "PatchedClient", "PatchedDispatcher"]
