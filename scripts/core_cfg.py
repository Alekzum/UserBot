from utils.config import Config as Cfg
from utils.config.modules_things import load_raw
from utils.config.my_things import set_variable, get_variable
from utils.good_things import answer
from pyrogram.types import Message
from pyrogram import Client
from typing import Union, Any, Sequence
import asyncio
import ast


Config = Cfg(
    name=__name__,
    desc="Edit config!",
    cmds=["cfg", "config"],
    other_can_use=False,
    variables={"edit_enabled": False, "debug": False},
)


def str_to_type(string: str) -> Union[str, int, bool, None]:
    """
    convert string to some type (like string, boolean, integer, dict and list!)
    :param string:
    :type string:
    """
    assert isinstance(string, str), f"{type(string)=}! ({string!r})"
    match list(string):
        case ["{", *_, "}"] | ["[", *_, "]"]:
            return ast.literal_eval(string)

        case [*_] if string in ["False", "True", "None"]:
            if string == "False":
                return False

            elif string == "True":
                return True

            elif string == "None":
                return None

            raise ValueError

        case _ if string.isdigit():
            return int(string)

        case _:  # it's literally string... or something else idk
            return string


def stringify(something: dict | list | str | int) -> str:
    debug = Config["debug"]
    match something:
        case dict():
            if debug:
                Config.logger.info("LOG - dict")
            result = "\n".join(
                [f"{name}: {something[name].__class__.__name__}" for name in something]
            )

        case list():
            if debug:
                Config.logger.info("LOG - list")
            result = repr(something)

        case str() | int() | bool() | float() | None:
            if debug:
                Config.logger.info("LOG - some string")
            result = str(something)

        case _:
            if debug:
                Config.logger.info("LOG - error")
            raise Exception(
                f"Invalid type for convert into text! Didn't excepted {type(something)}"
            )
    result = result.replace("__", "¯¯")
    return result


def path_to_raw_path(path: list[str]) -> str:
    if path.startswith("."):
        path = f"config/scripts{path}"
    return path


def get(path: list[str]) -> str:
    if not path:
        return stringify(load_raw())

    path = path_to_raw_path(path)

    try:
        return stringify(get_variable(path))
    except KeyError:
        return f"Ошибка: Неизвестный путь {path}."
    except Exception as ex:
        return f"Ошибка: {ex}"

    raise


def set(path: str, value: Any) -> str:
    raw_path = path_to_raw_path(path)
    thing1: Any = get(raw_path)
    thing2: Any = str_to_type(value)

    if thing1 is None:
        return "Неизвестный путь."
    edited = set_variable(raw_path, thing2)
    edited_str = "Изменено" if edited else "Не изменено"
    result = (
        f"{edited_str} значение по пути '{raw_path!s}' с '{thing1!s}' на '{thing2!s}'"
    )
    Config.logger.info(result)
    return result



def parse(something) -> str:
    result = stringify(something)
    if not result:
        result = "Неизвестный путь."
    return result


def test_path(path: Sequence[str]) -> bool:
    raw_path = path_to_raw_path(path)
    thing1: Any = get(raw_path)
    return thing1 is not None
    pass


async def main(client: Client, message: Message):
    edit_enabled = Config["edit_enabled"]

    args = message.text.split()
    match args:
        case [_, path, "set", *new_thing] if test_path(path):
            result = set(path, " ".join(new_thing))

        case [_, path] if test_path(path):
            result = get(path)

        case _:
            result = "бу!"

    if isinstance(result, str):
        await answer(message, "<code>" + message.text.html + "</code>\n" + result)
