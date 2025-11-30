from typing import Literal, Any, Coroutine, TypeVar, overload, Iterable
from pyrogram.enums import MessageEntityType, ParseMode, ChatAction
from pyrogram.raw.types.bot_inline_result import BotInlineResult
from pyrogram.types import Message, User, MessageEntity
from pyrogram import Client, enums, errors
from pyrogram.dispatcher import Dispatcher
from utils.text_to_file import convert as text_to_file
from utils.uploading_file import upload_file
from .my_patches import Client

from html import escape
import datetime
import asyncio
import structlog, logging
import time

import subprocess
import asyncio
import time
import json
import sys
import os


logger = structlog.getLogger(__name__)
LEN_FOR_IMAGE = 1024
MODE = ["file", "image", "both"][0]

type ParseDictValues = Literal["default", "markdown", "html", "disabled"]
parse_dict: dict[ParseDictValues, enums.ParseMode] = {
    "default": enums.ParseMode.DEFAULT,
    "markdown": enums.ParseMode.DEFAULT,
    "html": enums.ParseMode.HTML,
    "disabled": enums.ParseMode.DISABLED,
}

new_code = "</code><code>"
""" "\\</code\\>\\<code\\>" """

T = TypeVar("T")


def code_escape(s):
    """ "\\</code\\>" + string + "\\<code\\>" """
    return f"</code>{s}<code>"


def code_define(s):
    """ "\\</code\\>\\<code\\>" + string + "\\</code\\>\\<code\\>" """
    return new_code + s + new_code


def code_around(s):
    """ "\\<code\\>" + string + "\\</code\\>" """
    return f"<code>{s}</code>"


def blockquote_around(s):
    """return f"\\<blockquote expandable\\>{s}\\</blockquote\\>" """
    return f"<blockquote expandable>{s}</blockquote>"


def get_loop():
    try:
        loop = asyncio.get_running_loop()
    except Exception:
        # print(f"{ex = }, {ex = !r}")
        return None
    else:
        # print(f"{loop = }")
        return loop


async def await_and_send_chat_action(
    coroutine: Coroutine[Any, Any, T],
    client: Client,
    chatId: int,
    action: enums.ChatAction,
) -> T:
    task = asyncio.create_task(coroutine)
    index = 0
    while not task.done():
        if index % 5 == 0:
            await client.send_chat_action(chatId, action)
        await asyncio.sleep(1)
        index += 1
    await client.send_chat_action(chatId, enums.ChatAction.CANCEL)
    return task.result()


# def test_answer(message: Message, text: str):
#     loop = get_loop()
#     if loop is None:
#         return message.reply_text(text)

#     return loop.run_until_complete(message.reply_text(text))


async def answer(
    message: Message,
    text: str,
    reply: bool = True,
    edit: bool = True,
    image: bool = False,
    parse_mode: ParseDictValues = "default",
    len_for_image: int | None = None,
    chat_action: ChatAction | None = None,
    **kwargs,
) -> Message:
    """Answer to message in some formats

    Args:
        message (Message): Message which will be used in answer
        text (str): Answer's text
        reply (bool, optional): Reply will contain this message? Defaults to True.
        edit (bool, optional): Answer will edit message from author or reply? Defaults to False.
        image (bool, optional): Answer will be always image or if this answer is too long? Defaults to False.
        lem_for_image (int, optional): How long can be text before turning it to image? Defaults to None, maximum is 4095.
        parse_mode (Literal[0, 1, 2, &#39;markdown&#39;, &#39;html&#39;, &#39;default&#39;, &#39;disabled&#39;], optional): Which parse mode need . Defaults to 'default'.
        chat_action (bool, optional): Send ChatAction in chat? Defaults to False.

    Returns:
        Message: Message which contains answer to previous message
    """
    if kwargs:
        logger.warning(f"{kwargs = }!")
    client: Client = message._client  # type: ignore

    async def custom_await_and_send_chat_action[T](
        coroutine: Coroutine[Any, Any, T],
        chatId: int = message.chat.id,
        chatAction: ChatAction | None = None,
    ) -> T:
        if chatAction is None:
            return await coroutine

        return await await_and_send_chat_action(
            coroutine, client, chatId, chatAction
        )

    chosen_parse_mode = parse_dict[parse_mode]
    result = text

    caption: str = ""
    file_path: str = ""
    _len_for_image = (
        min(4095, (len_for_image or LEN_FOR_IMAGE)) or LEN_FOR_IMAGE
    )
    raw_text = (await client.parser.parse(text, ParseMode.HTML))["message"]

    if not (image or len(raw_text) > _len_for_image):
        if message.from_user and message.from_user.is_self:
            return await message.edit_text(result, parse_mode=chosen_parse_mode)
        return await message.reply_text(
            result, quote=reply, parse_mode=chosen_parse_mode
        )

    # In case that text to send is too long
    # if MODE == 'file':
    file_path = await text_to_file(client, raw_text)

    send_url = False
    try:
        file_url = await upload_file(file_path)
        caption = f"URL to file with output: {file_url}"
        send_url = True

    except Exception:
        file_url = None
        caption = None

    # text_in_image = await text_to_file(client, raw_text)

    try:
        # if path is not None:
        msg = await message.reply_document(
            file_path,
            quote=reply,
            force_document=True,
            parse_mode=chosen_parse_mode,
            caption=caption,
        )
        # else:
        #     msg = await message.reply_text(caption, quote=reply, parse_mode=chosen_parse_mode)
    except errors.SlowmodeWait:
        maybe_msg = await client.send_document(
            message.from_user.id,
            file_path,
            force_document=True,
            parse_mode=chosen_parse_mode,
            caption=caption,
        )
        if not isinstance(maybe_msg, Message):
            raise ConnectionError("Sending file is canceled")
        msg = maybe_msg
    return msg


# def parse_args_for_await_answer(m_i, i) -> tuple[Client, Message, int]:
#     if isinstance(m_i, Message) and (i is None or isinstance(i, int)):  # just await_asnwer(msg)
#         temp_c: Client = m_i._client
#         temp_m: Message = m_i
#         temp_i: int = i or 1
#         client, message, index = temp_c, temp_m, temp_i
#     else:
#         raise TypeError('args cannot be ({}, {})'.format(type(m_i), type(i)))
#     assert isinstance(client, Client) and isinstance(message, Message) and isinstance(index, int), "Something wrong with parses:  ({}, {}, {})".format(type(client), type(message), type(index))
#     return client, message, index


async def await_answer(
    message: Message,
    index: int = 1,
    timeout: int = 30,
    await_from_user_id: int | None = None,
    delta_time: float = 0.5,
    need_to_wait: bool = True,
) -> Message | None:
    client, message, index = parse_args_for_await_answer(message, index)
    chat_id = message.chat.id
    response_id = message.id + index

    need_user_id = await_from_user_id or (
        message.chat.id if message.chat.type is enums.ChatType.PRIVATE else None
    )

    start_time = time.time()
    response_index = 0
    response: Message | None = None

    while (
        is_not_timeout := (time.time() - start_time < timeout)
    ) and response_index != index:
        if need_to_wait:
            await asyncio.sleep(delta_time)

        response = await client.get_messages(chat_id, response_id, replies=0)  # type: ignore

        if response and response.empty:
            continue

        if (
            response and response.chat.id != chat_id
        ):  # because private messages exists -_-
            response_id += 1
            continue

        if (
            response
            and (sender := response.from_user or response.sender_chat)
            and (sender.id == need_user_id or sender.username == need_user_id)
            or need_user_id is None
        ):
            response_index += 1
        else:
            response_id += 1

    result = response if is_not_timeout else None
    return result


def parse_args_for_await_answer(m_i, i) -> tuple[Client, Message, int]:
    if isinstance(m_i, Message) and (
        i is None or isinstance(i, int)
    ):  # just await_asnwer(msg)
        temp_c: Client = m_i._client  # type: ignore
        temp_m: Message = m_i
        temp_i: int = i or 1
        client, message, index = temp_c, temp_m, temp_i
    else:
        raise TypeError("args cannot be ({}, {})".format(type(m_i), type(i)))

    assert (
        isinstance(client, Client)
        and isinstance(message, Message)
        and isinstance(index, int)
    ), (
        f"Something wrong with parses: ({type(client)}, {type(message)}, {type(index)})"
    )
    return client, message, index


# def await_answer_sync(
#     message: Message,
#     index: int = 1,
#     timeout: int = 30,
#     await_from_user_id: int | None = None,
#     delta_time: float = 0.5,
#     need_to_wait: bool = True,
# ) -> Message | None:
#     client, message, index = parse_args_for_await_answer(message, index)
#     chat_id = message.chat.id
#     response_id = message.id + index

#     need_user_id = await_from_user_id or (
#         message.chat.id if message.chat.type is enums.ChatType.PRIVATE else None
#     )

#     start_time = time.time()

#     response_index = 0
#     response: Message | None = None

#     while (
#         is_not_timeout := (time.time() - start_time < timeout)
#     ) and response_index != index:
#         if need_to_wait:
#             time.sleep(delta_time)

#         response = client.get_messages(chat_id, response_id, replies=0)  # type: ignore

#         if response and response.empty:
#             continue

#         if response and response.chat.id != chat_id:  # because private messages exists -_-
#             response_id += 1
#             continue

#         if (
#             response and (sender := response.from_user or response.sender_chat)
#             and (sender.id == need_user_id or sender.username == need_user_id)
#             or need_user_id is None
#         ):
#             response_index += 1
#         else:
#             response_id += 1

#     result = response if is_not_timeout else None
#     return result


async def wait_until_update(message: Message, timeout=60) -> Message:
    if timeout < 0:
        raise ValueError("Timeout ca")
    client = message._client
    actual_message = await client.get_messages(message.chat.id, message.id)
    start_time = time.time()
    while time.time() - start_time < timeout:
        actual_message = await client.get_messages(message.chat.id, message.id)
        assert isinstance(actual_message, Message)
        if actual_message != message:
            return actual_message
        await asyncio.sleep(1)
    assert isinstance(actual_message, Message)
    return actual_message


def user_to_text(something_with_user: object | User) -> str:
    """From variable get User and make display_name"""
    if isinstance(something_with_user, User):
        user: User = something_with_user

    elif hasattr(something_with_user, "from_user"):
        user = getattr(something_with_user, "from_user")

    elif hasattr(something_with_user, "me"):
        user = getattr(something_with_user, "me")

    elif hasattr(something_with_user, "user"):
        user = getattr(something_with_user, "user")

    else:
        raise KeyError("This thing doesn't have user...")

    display_name = f"""{user.username or user.full_name} ({user.id})"""
    return display_name


def get_display_name(something_with_user: object | User) -> str:
    """From variable get User and make display_name"""
    return user_to_text(something_with_user)


async def run_in_sequence(*coroutines, ignore=False):
    result = []
    for coroutine in coroutines:
        try:
            temp = await coroutine
        except Exception as ex:
            if ignore:
                temp = ex
            else:
                raise (ex)
        result.append(temp)
    return result


def unix_time_to_string(unix: float) -> str:
    """Return something like "01h 30m 45s" or "45s" """
    delta = datetime.timedelta(seconds=unix)
    string = timedelta_to_string_cool(delta)
    return string


def timedelta_to_string_cool(
    delta: datetime.timedelta, add_minutes_zeros: bool = True
) -> str:
    """Return something like "01h 30m 45s" or "45s" """
    total = delta.total_seconds()
    d, h, m, s = (
        (total % 31_536_000) // 86400,
        (total % 86400) // 3600,
        (total % 3600) // 60,
        (total % 60) // 1,
    )
    result = " ".join(
        [
            f"{int(v)}{n}"
            for (v, n) in zip([d, h, m, s], ["d", "h", "m", "s"])
            if v > 0
        ]
    )

    return result


def timedelta_to_string(delta: datetime.timedelta) -> str:
    """Return something like 01:30:45 or 00:45"""
    total = delta.total_seconds()
    d, h, m, s = (
        (total % 31_536_000) // 86400,
        (total % 86400) // 3600,
        (total % 3600) // 60,
        (total % 60) // 1,
    )
    result = ":".join([f"{int(n):0>2}" for n in [d, h, m, s]])
    result = result.replace("00:", "")
    result = f"00:{result:0>2}" if len(result) in [0, 1, 2] else result
    return result


def message_from_user_to_text(
    message: Message,
    text: str,
    user_mention: bool = True,
    blacklist_strings: Iterable[str] = (
        "/",
        "@",
    ),
    whitelist_strings: Iterable[str] = ("</",),
    need_to_escape=True,
) -> str:
    temp = text
    for i, whitelist_string in enumerate(whitelist_strings):
        temp = temp.replace(whitelist_string, f"\\w{i}\\")

    for i, blacklist_string in enumerate(blacklist_strings):
        temp = temp.replace(blacklist_string, f"\\b{i}\\")

    for i, whitelist_string in enumerate(whitelist_strings):
        temp = temp.replace(f"\\w{i}\\", whitelist_string)
    # temp_blacklist = dict((v, f"•◘{i}") for (i, v) in enumerate(blacklist_strings))
    # for (i, v) in temp_blacklist.items():
    #     f = lambda s: str.replace(s, v, f"•◘{i}")
    #     temp = f(temp)
    # temp_whitelist = f(temp_whitelist)

    result = text.replace("/", "•").replace("@", "◘").replace("<•", "</")
    result = escape(result) if need_to_escape else result
    mention = (
        message.from_user
        and (
            message.from_user.mention(str(message.from_user.id))
            if user_mention
            else message.from_user.id
        )
        or (message.sender_chat and message.sender_chat.username)
        or "*unknown sender*"
    )
    result = "\n".join(
        [
            result,
            "From: {}".format(mention),
            f"Line: «{message.text}»",
        ]
    )
    # result = f"{result}\nFrom: {code_escape(message.from_user.mention(str(message.from_user.id)))}\nLine: «{message.text}»"
    return result


def resolve_entity(
    text: str, tag: str, entity_type: MessageEntityType, **kwargs
) -> tuple[MessageEntity, str]:
    open_tag = tag
    close_tag = tag.replace("<", "</")
    before_start_tag, start_tag, after_start_tag = text.partition(open_tag)
    offset = len(before_start_tag)

    before_close_tag, tab, after_close_tag = after_start_tag.partition(
        close_tag
    )
    length = len(before_close_tag)

    text = before_start_tag + before_close_tag + after_close_tag
    entity = MessageEntity(
        type=entity_type, offset=offset, length=length, **kwargs
    )
    return entity, text


def resolve_entities(
    text: str, _entities=None
) -> tuple[list[MessageEntity], str]:
    tag_list: dict[str, dict[str, MessageEntityType | bool]] = {
        "<blockquote>": dict(
            entity_type=MessageEntityType.BLOCKQUOTE, expandable=True
        ),
        "<code>": dict(entity_type=MessageEntityType.CODE),
    }
    result = _entities or []

    offsets = [
        text.find(tagName) for tagName in tag_list if text.find(tagName) != -1
    ]
    minOffset = min(offsets) if offsets else None

    if minOffset is None:
        return result, text

    minTag = list(tag_list.keys())[offsets.index(minOffset)]
    entity_dict: dict = tag_list[minTag]
    entity, text = resolve_entity(
        text, minTag, entity_type=entity_dict.pop("entity_type"), **entity_dict
    )
    result.append(entity)

    return resolve_entities(text, result)
    # return result, text


async def require_inline_my_bot(
    client: Client | Client, message: Message, query: str
) -> Message | None:
    pair: tuple[Dispatcher, Client] | None = getattr(client, "_other_bot", None)
    if pair is None:
        logger.warning(f'Didn\'t found "_other_bot" at client')
        return None

    dp, other_bot = pair
    inline_requests = await client.get_inline_bot_results(
        (await other_bot.get_me()).id, query
    )

    need_result = inline_requests.results[0]

    if not isinstance(need_result, BotInlineResult):
        logger.warning(
            f'need_result is type {type(need_result)}, not "raw" BotInlineResult'
        )
        return None

    await message.reply_inline_bot_result(
        query_id=inline_requests.query_id, result_id=need_result.id
    )

    # print(upd)
    msg: Message | None = await await_answer(
        message,
        await_from_user_id=(await client.get_me()).id,
        need_to_wait=False,
    )
    return msg


def print_diffs(old_str: str, new_str: str) -> None:
    to_write = new_str.replace(old_str, "")
    sys.stdout.write(to_write)


@overload
def my_decode(text: bytes) -> str: ...
@overload
def my_decode(text: bytes, return_none_if_failture: Literal[False]) -> str: ...
@overload
def my_decode(
    text: bytes, return_none_if_failture: Literal[True]
) -> str | None: ...
def my_decode(text: bytes, return_none_if_failture: bool = False):
    encodings: list[str] = ["utf-8", "cp866", "cp1251", "cp1252"]
    for encoding in encodings:
        try:
            return text.decode(encoding)
        except:
            continue
    raise Exception(f"No one of encodings {encodings} didn't decode {text=!r}")
    # try: return text.decode("utf-8")
    # except UnicodeDecodeError:
    # try: return text.decode("cp866")
    # except UnicodeDecodeError:
    # try: return text.decode("cp1261")


# async def run_process(*cmd: str, timeout: int = 300) -> tuple[subprocess.Popen, bytes, bytes]:
async def run_process(*cmd: str, timeout: int = 300):
    delta_time = 0.5
    proc = subprocess.Popen(
        cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=False
    )
    stderr: bytes = b""
    stdout: bytes = b""
    temp_stderr: bytes = b""
    temp_stdout: bytes = b""
    start_time = time.perf_counter()
    while (
        proc.returncode is None
        and (time.perf_counter() - start_time) <= timeout
    ):
        try:
            temp_stdout, temp_stderr = proc.communicate(timeout=0)
        except subprocess.TimeoutExpired:
            pass

        stdout += temp_stdout
        stderr += temp_stderr

        # if proc.stderr:
        #     temp_stderr = proc.stderr.read() or b""
        #     if not proc.stderr.closed:
        #         proc.stderr.close()

        # if proc.stdout:
        #     temp_stdout = proc.stdout.read() or b""
        #     if not proc.stdout.closed:
        #         proc.stdout.close()

        # stdout += temp_stdout
        # stderr += temp_stderr

        sys.stdout.write(my_decode(temp_stdout))
        sys.stderr.write(my_decode(temp_stderr))

        # try:
        # temp_stdout, temp_stderr = proc.communicate(timeout=0.5)
        # except (subprocess.TimeoutExpired, TimeoutError):
        # pass
        # else:
        # print_diffs(stderr, temp_stderr)
        # print_diffs(stdout, temp_stdout)
        # stderr, stdout = temp_stderr, temp_stdout
        await asyncio.sleep(delta_time)

    return (proc, stdout, stderr)


def try_call(obj):
    try:
        return [obj, obj()]
    except BaseException as ex:
        return [obj, ex]


def cool_print(obj):
    d = {x: try_call(getattr(obj, x)) for x in dir(obj)}
    d["_"] = getattr(
        obj, "__qualname__", getattr(obj, "__name__", "unknown_object")
    )
    string = json.dumps(
        d,
        default=lambda x: str(x),
        sort_keys=True,
        ensure_ascii=False,
        indent=2,
    )
    print(string)


def main():
    args = ["py", "-m", "pip", "-V"]
    print(asyncio.run(run_process(*args)))
    # delta_time = 98465312.124341
    # result = unix_time_to_string(delta_time)
    # print(result)


if __name__ == "__main__":
    main()
