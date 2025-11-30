from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineQuery,
    ChosenInlineResult,
    Update,
    User,
    Chat,
)
from pyrogram.filters import create, Filter
from utils.my_patches import Client
from utils.config.whitelist import in_whitelist as _in_whitelist
from utils.config.allowed import in_allowed as _in_allowed
from functools import wraps
import structlog, logging


logger = structlog.getLogger(__name__)


type UserMessage = Update | Message
type UserInline = Update | CallbackQuery | InlineQuery | ChosenInlineResult
type UserUpdate = UserMessage | UserInline


class _UserInLocalWhitelistFilter(Filter):
    whitelist: list[str | int]


def _get_invoker(obj: UserUpdate) -> User | Chat | None:
    if (x:=getattr(obj, "from_user", None)) and isinstance(x, User):
        return x
    
    elif (x:=getattr(obj, "from_user", None)):
        logger.warning(f"{type(obj)}, {type(x) = }")

    elif (x:=getattr(obj, "sender_chat", None)) and isinstance(x, Chat):
        return x

    elif (x:=getattr(obj, "sender_chat", None)):
        logger.warning(f"{type(obj)}, {type(x) = }")

    logger.warning(f"{type(obj)}, {obj = }")
    return None


def user_in_local_whitelist(whitelist: list[str | int]):
    """Check is some user in some list (aka in local whitelist)"""

    @wraps(user_in_local_whitelist)
    async def _user_in_local_whitelist(
        flt: _UserInLocalWhitelistFilter, client: Client, upd: UserUpdate
    ):
        def invoker_is_valid(user: User | Chat):
            return user.id in flt.whitelist or user.username in flt.whitelist

        user_is_exists = _get_invoker(upd)
        return user_is_exists and invoker_is_valid(user_is_exists)

    return create(_user_in_local_whitelist, whitelist=whitelist)


# def user_in_global_whitelist_func(flt, client: Client, upd: UserUpdate):
#     """Check if someone can use module"""
#     user_is_exists = hasattr(upd, "from_user") and upd.from_user
#     return user_is_exists and _in_whitelist(user_is_exists)

#     # async def user_in_global_whitelist_func(flt, client: Client, upd: UserUpdate):
#     #     user_is_exists = hasattr(upd, "from_user") and upd.from_user
#     #     return user_is_exists and _in_whitelist(user_is_exists)

# user_in_global_whitelist = create(user_in_global_whitelist_func, "UserInGlobalList")


# def _chat_in_allowed(flt, client: Client, upd: UserUpdate):
#     """Check if some chat can use module"""
#     return hasattr(upd, "chat") and bool(upd.chat) and _in_allowed(upd.chat.id)

#     # async def chat_in_allowed_func(flt, client: Client, upd: Update | Message):
#     #     return hasattr(upd, "chat") and bool(upd.chat) and _in_allowed(upd.chat.id)

#     # return create(chat_in_allowed_func)

# chat_in_allowed = create(_chat_in_allowed)


async def user_in_global_whitelist_func(flt, client: Client, upd: UserUpdate):
    user_is_exists = hasattr(upd, "from_user") and upd.from_user
    return user_is_exists and _in_whitelist(user_is_exists)


user_in_global_whitelist: Filter = create(
    user_in_global_whitelist_func, "UserInGlobalList"
)


async def _chat_in_allowed(flt, client: Client, upd: UserUpdate):
    """Check if some chat can use module"""
    return hasattr(upd, "chat") and bool(upd.chat) and _in_allowed(upd.chat.id)


chat_in_allowed: Filter = create(_chat_in_allowed, "ChatInAllowed")
