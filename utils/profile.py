from pyrogram import Client
from pyrogram.types import User
from pyrogram.raw import functions, types
from contextlib import redirect_stdout
from io import StringIO


async def get_full_user(
    client: Client,
    id: int | str | None = None
) -> types.user_full.UserFull:
    me = await client.get_me()
    assert isinstance(me, User), "wth"
    real_id = id or me.id
    result = await client.invoke(
        functions.users.GetFullUser(
            # id=await client.resolve_peer(id or client.me.id),
            id=await client.resolve_peer(real_id)  # type: ignore[arg-type]
        )
    )
    return result


async def get_me(client: Client) -> str:
    me = (await get_full_user(client))
    with StringIO() as buf, redirect_stdout(buf):
        help(me)
        string = buf.getvalue()
    return string


async def change_surname(what: str | None, client: Client) -> str:
    if what is None:
        return ""

    if len(what) > 64:
        what = what[:62] + "…»"

    await client.update_profile(last_name=what)
    return what
