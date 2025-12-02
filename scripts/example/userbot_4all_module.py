from utils import Client
from utils.config import Config as Cfg
from utils.good_things import answer
from utils.my_decorators import on_message
from utils.my_filters import user_in_global_whitelist, user_in_local_whitelist
from pyrogram.types import Message


Config = Cfg(
    name=__name__,
    desc="some template",
    cmds=["test"],
    other_can_use=True,
    variables=dict(
        delay=10, last_time=0
    ),  # Default cooldown for every user is 10 seconds
)


async def validate(client: Client, message: Message):
    if await user_in_global_whitelist(client, message) or user_in_local_whitelist(
        Config.Metadata.whitelist
    )(client, message):
        return True

    cur_time, delay = message.date.timestamp(), int(Config["delay"])  # type: ignore
    invoked_time = Config["last_time"]

    if cur_time - invoked_time > delay:
        Config["last_time"] = cur_time
        return True

    else:
        return False


@on_message(Config.Metadata.filter)
async def main(client: Client, message: Message):
    if not await validate(client, message):
        return

    args = message.command.copy()  # type: ignore
    result: str | bool | None = None

    match args:
        case [_]:
            result = "Act"

        case _:
            result = Config.Metadata.desc

    if isinstance(result, str) and result:
        await answer(message, result)

    elif isinstance(result, bool):
        pass  # await message.react("👍" if result else "👎")
