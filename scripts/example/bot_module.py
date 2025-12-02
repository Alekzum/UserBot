from utils import Client
from utils.config import Config as Cfg
from pyrogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from utils.bot_things.my_filters import InlineCommand  # , CallbackCommand
from utils.config.allowed import in_allowed
from utils.config.whitelist import in_whitelist
from aiogram import Router, F, Bot


Config = Cfg(name=__name__, desc="some template", cmds=["test"])
rt = Router(name=__name__)


@rt.inline_query(
    F.func(lambda x: in_allowed(x.from_user.id))
    | F.func(lambda x: in_whitelist(x.from_user.id)),
    InlineCommand(commands="text", prefixes=""),
)
async def say_hello(bot: Bot, inline_query: InlineQuery):
    match inline_query.query.split(" "):
        case [_, "hi"]:
            msg_text = "hello!"

        case _:
            msg_text = "I understand only these commands: hi"

    msg = InputTextMessageContent(message_text=msg_text)

    article = InlineQueryResultArticle(
        f"Module {__name__}",
        description="Write avaiable commands for this inline request",
        input_message_content=msg,
    )
    await inline_query.answer([article])
    ...


async def on_startup(client: Client, *args, **kwargs):
    pass


async def on_shutdown(client: Client):
    pass


# async def main(client: Client, message: Message):
#     args = message.command.copy()
#     result: str | bool | None = None

#     match args:
#         case [_]:
#             result = "Act"

#         case _:
#             result = Config.Metadata.desc

#     if isinstance(result, str) and result:
#         await answer(message, result)

#     elif isinstance(result, bool):
#         pass # await message.react("👍" if result else "👎")
