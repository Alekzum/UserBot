from utils.config import Config as Cfg, allowed
from utils.good_things import answer
from utils.my_patches import Client
from pyrogram.types import Message


Config = Cfg(
    name=__name__,
    desc="Control allowed groups. Avaliable commands: all/remove/add/check",
    cmds=["allowed"],
    other_can_use=False,
    variables={},
)


async def main(client: Client, message: Message):
    args = message.command.copy()
    cid = message.chat.id
    match args:
        case [_, "get" | "all"]:
            chats = [str(x) for x in allowed.get_allowed()]
            result = f"Список разрешённых чатов: {', '.join(chats) if chats else 'пусто'}."

        case [_, "remove" | "-", chat_id] if chat_id[
            chat_id.startswith("-") :
        ].isdigit():
            res = allowed.delete_allowed(int(chat_id))
            result = (
                "Этот чат удалён из списка разрешённых."
                if not res
                else "Этот чат уже удалён из списка разрешённых."
            )

        case [_, "add" | "+", chat_id] if chat_id[
            chat_id.startswith("-") :
        ].isdigit():
            res = allowed.add_allowed(int(chat_id))
            result = (
                "Этот чат добавлен в список разрешённых."
                if not res
                else "Этот чат уже в списке разрешённых."
            )

        case [_, "check" | "?", chat_id] if chat_id[
            chat_id.startswith("-") :
        ].isdigit():
            already = not allowed.in_allowed(int(chat_id))
            result = "Это чат " + "не " * already + "в списке разрешённых."

        case [_, "remove" | "-"]:
            res = allowed.delete_allowed(cid)
            result = (
                "Этот чат удалён из списка разрешённых."
                if not res
                else "Этот чат уже удалён из списка разрешённых."
            )

        case [_, "add" | "+"]:
            res = allowed.add_allowed(cid)
            result = (
                "Этот чат добавлен в список разрешённых."
                if not res
                else "Этот чат уже в списке разрешённых."
            )

        case [_, "check" | "?"]:
            already = not allowed.in_allowed(cid)
            result = "Это чат " + "не " * already + "в списке разрешённых."

        case _:
            result = Config.Metadata.desc

    if result:
        await answer(message, result)
