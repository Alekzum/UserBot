from utils.config import Config as Cfg
from utils.good_things import answer
from utils.my_patches import Client as Client
from pyrogram.types import Message
from dataclasses import dataclass
from typing import Optional, Callable, Any, Coroutine
from types import ModuleType
import pathlib
import json
import os


Config = Cfg(
    name=__name__,
    desc="Get help for commands",
    cmds=["help"],
    other_can_use=True,
    variables={},
)


@dataclass
class ModuleInfo:
    # __slots__ = ['desc', "cmds", "other_can_use"]
    desc: str
    cmds: list[str] | str
    other_can_use: bool


class ModuleInfoEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o,  ModuleInfo):
            return o.__dict__
        return json.JSONEncoder.default(self, o)


class Module:
    Config: Cfg
    main: Optional[Callable[[Client, Message], Coroutine[Any, Any, Any]]]
    on_startup: Optional[Callable[[Client], Any]]

    def __init__(self, raw: ModuleType):
        self.Config = raw.Config
        self.main = getattr(raw, "main", None)
        self.on_startup: Optional[Callable[[Client], Any]] = getattr(
            raw, "on_startup", None
        )


def parse_module(raw) -> ModuleInfo:
    module = Module(raw)
    desc = module.Config.Metadata.desc
    cmds = module.Config.Metadata.cmds
    other_can_use = module.Config.Metadata.other_can_use

    return ModuleInfo(desc=desc, cmds=cmds, other_can_use=other_can_use)


def get_helps() -> dict[str, ModuleInfo]:
    directories: list[str] = ["scripts", "handlers/userbot"]
    list_of_files = [
        f for d in directories for f in pathlib.Path(d).glob("[!_]*.py")
    ]

    helps = {}
    for file in list_of_files:
        module = str(file).removesuffix(file.suffix).replace(os.sep, ".")
        file_module = __import__(module, fromlist=("Config"))

        if not (hasattr(file_module, "Config")):
            continue

        parsed = parse_module(Module(file_module))
        file_info = ModuleInfo(
            desc=parsed.desc,
            cmds=parsed.cmds,
            other_can_use=parsed.other_can_use,
        )
        helps.update({module: file_info})

    return helps


def search(command_or_module_name, is_owner: bool):
    helps = get_helps()
    meanings: dict[str, str] = {}
    descs = {}
    for name in helps:
        values = helps[name]

        desc = values.desc
        cmds = values.cmds or []
        other_can_use = values.other_can_use

        if not is_owner and not other_can_use:
            continue

        descs[name] = "\n".join(
            [
                f"Description: «{desc}»",
                f"Commands: {', '.join(cmds)}",
                f"Other can use: {other_can_use}",
            ]
        )

        meanings.update((cmd, name) for cmd in cmds)
    # print(json.dumps(meanings, indent=4, ensure_ascii=False, cls=ModuleInfoEncoder))

    module_name = meanings.get(command_or_module_name)
    if module_name:
        result = descs.get(module_name)
    else:
        result = "Module not found."

    return result


def get_list() -> str:
    _result = []
    helps = get_helps()
    for name in sorted(
        helps, key=lambda name: helps[name].other_can_use, reverse=True
    ):
        value = helps[name]
        name = name.split(".")[1]
        cmds = value.cmds or []
        if not cmds:
            continue
        # print(cmds)

        permissions_str = "**" if value.other_can_use else "* "
        cmds_str = ", ".join(cmds)

        to_append_temp = " ".join(
            [
                permissions_str,
                name,
                "(Commands: {})".format(cmds_str.replace("\n", "\\n")),
                "\n    " + value.desc or "*без описания*",
            ]
        )
        _result.append(to_append_temp)
    _result = sorted(_result, key=lambda x: x[0])
    result = "\n\n".join(_result)
    return result


def get_help(is_for_owner=False, only_one_category=False) -> str:
    result = []
    helps = get_helps()

    if is_for_owner:
        modules_list = helps
    elif only_one_category:
        modules_list = {
            n: helps[n] for n in helps if helps[n].other_can_use == is_for_owner
        }
    else:
        modules_list = {n: helps[n] for n in helps if helps[n].other_can_use}

    for name in sorted(
        modules_list, key=lambda n: f"{1 - (helps[n].other_can_use)}{n}"
    ):
        # for name in sorted(helps, key=lambda name: helps[name].get("other_can_use"), reverse=True):
        value = helps[name]
        name = name.split(".")[1]
        cmds = value.cmds or []
        if not cmds:
            continue
        # print(cmds)

        for_all = value.other_can_use
        permissions_str = "Для всех" if for_all else "Для меня"
        cmds_str = ", ".join(cmds)
        to_append = "\n".join(
            [
                f"✨ Модуль «{name}» ({permissions_str})",
                f"🕹️ Команды: {cmds_str}",
                f"📜 Описание: {value.desc or 'без описания'}",
                "",
            ]
        )

        if for_all or is_for_owner:
            result.append(to_append)

    helps_list = list(sorted(result, key=lambda x: x[0]))
    _helps = "\n".join(helps_list)
    _result = f"Доступные модули:\n</code><blockquote expandable>{_helps}</blockquote></code>"
    return _result


async def main(client: Client, message: Message):
    if message.from_user is None:
        return
    isOwner = message.from_user.id == (await client.get_me()).id
    args = message.command.copy()
    result: str | None = None

    match args:
        case [_, "for_all" | "all"]:
            result = get_help(False)

        # case [_, 'short' | '-short' | 'list' | '-list']:
        # result = get_list()

        case [_, "me"]:
            result = get_help(isOwner, False)

        case [_, "only", "me"]:
            result = get_help(isOwner, True)

        # case [_] if not isOwner:
        #     result = get_help(isOwner)

        case [_, command_or_module_name]:
            result = search(command_or_module_name, isOwner)

        case [_]:
            result = """Доступные использования:
  • .help for_all — посмотреть модули, которые доступны для всех
  • .help me — посмотреть модули, которые доступны для владельца бота
  • .help squotes — найти модуль по его названию и посмотреть информацию о нём
  • .help sq — найти модуль по его команде и посмотреть информацию о нём
  • .help — посмотреть 'доступные использования'
  """

    if isinstance(result, str):
        await answer(message, result)
