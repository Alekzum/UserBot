from utils import Client
from utils.config import Config as Cfg
from utils.good_things import answer
from utils.my_decorators import on_message
from pyrogram.types import Message


Config = Cfg(
    name=__name__,
    desc="some template",
    cmds=["test"]
)


async def on_startup(client: Client, *args, **kwargs):
    pass


async def on_shutdown(client: Client):
    pass


@on_message(Config.Metadata.filter)
async def main(client: Client, message: Message):
    result: str | bool | None = None

    match message.command:
        case [_]:
            result = "Act"

        case _:
            result = Config.Metadata.desc

    if isinstance(result, str) and result:
        await answer(message, result)

    elif isinstance(result, bool):
        pass # await message.react("👍" if result else "👎")
