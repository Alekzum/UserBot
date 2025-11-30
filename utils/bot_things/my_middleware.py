from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
import structlog


t_d = {0: "секунд", 1: "секунду", 2: "секунды", 5: "секунд"}
t_d.update({3: t_d[2], 4: t_d[2], 6: t_d[5], 7: t_d[5], 8: t_d[5], 9: t_d[5]})
seconds_to_str = t_d.copy()
logger = structlog.getLogger(__name__)


class LogMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        # handler: BaseHandler,
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        logger.debug(f"Invoked {handler} with data {data}")
        return await handler(event, data)
        ...
