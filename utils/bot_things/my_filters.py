from aiogram.types import CallbackQuery, InlineQuery, ChosenInlineResult
from aiogram.filters import Filter
from typing import Union, Any
import structlog
import re


class MyInlineQuery(InlineQuery):
    command: list[str]


class MyChosenInlineResult(ChosenInlineResult):
    command: list[str]


class MyCallbackQuery(CallbackQuery):
    command: list[str]


class ReCommand(Filter):
    command_re = re.compile(r"([\"'])(.*?)(?<!\\)\1|(\S+)")

    def __init__(
        self,
        commands: Union[str, list[str]],
        prefixes: Union[str, list[str], None] = None,
        case_sensitive: bool = False,
    ):
        commands_normalized = commands if isinstance(commands, list) else [commands]
        commands_ = [c if case_sensitive else c.lower() for c in commands_normalized]

        prefixes_normalized = [] if prefixes is None else prefixes
        prefixes_list = (
            prefixes_normalized
            if isinstance(prefixes_normalized, list)
            else [prefixes_normalized]
        )
        prefixes_ = prefixes_list if prefixes_list else [""]

        self.commands = commands_
        self.prefixes = prefixes_
        self.case_sensitive = case_sensitive
        # logger.info(f"initialized {self} with {commands_=}")


class InlineCommand(ReCommand):
    """Filter commands, i.e.: text inline_query starting with "/" or any other custom prefix.

    Parameters:
        commands (``str`` | ``list``):
            The command or list of commands as string the filter should look for.
            Examples: "start", ["start", "help", "settings"]. When a inline_query text containing
            a command arrives, the command itself and its arguments will be stored in the *command*
            field of the :obj:`~pyrogram.types.InlineQuery`.

        prefixes (``str`` | ``list``, *optional*):
            A prefix or a list of prefixes as string the filter should look for.
            Defaults to "/" (slash). Examples: ".", "!", ["/", "!", "."], list(".:!").
            Pass None or "" (empty string) to allow commands with no prefix at all.

        case_sensitive (``bool``, *optional*):
            Pass True if you want your command(s) to be case sensitive. Defaults to False.
            Examples: when True, command="Start" would trigger /Start but not /start.
    """

    async def __call__(
        self,
        event: InlineQuery,
    ) -> Union[bool, dict[str, Any]]:
        assert event.bot, "wtf"
        username = (await event.bot.get_me()).username or ""
        text = event.query
        # setattr(event, "command", list())

        if not text:
            return False

        for prefix in self.prefixes:
            if not text.startswith(prefix):
                continue

            without_prefix = text[len(prefix) :]
            # logger.info(f"{self=}, {without_prefix=}")

            for cmd in self.commands:
                if not re.match(
                    rf"^(?:{cmd}(?:@?{username})?)(?:\s|$)",
                    without_prefix,
                    flags=re.IGNORECASE if not self.case_sensitive else 0,
                ):
                    continue

                without_command = re.sub(
                    rf"{cmd}(?:@?{username})?\s?",
                    "",
                    without_prefix,
                    count=1,
                    flags=re.IGNORECASE if not self.case_sensitive else 0,
                )

                # match.groups are 1-indexed, group(1) is the quote, group(2) is the text
                # between the quotes, group(3) is unquoted, whitespace-split text

                # Remove the escape character from the arguments
                command = [cmd] + [
                    re.sub(r"\\([\"'])", r"\1", m.group(2) or m.group(3) or "")
                    for m in self.command_re.finditer(without_command)
                ]

                return dict(command=command)

        return False


class CallbackCommand(ReCommand):
    """Filter commands, i.e.: text callback_queries starting with "/" or any other custom prefix.

    Parameters:
        commands (``str`` | ``list``):
            The command or list of commands as string the filter should look for.
            Examples: "start", ["start", "help", "settings"]. When a inline_query text containing
            a command arrives, the command itself and its arguments will be stored in the *command*
            field of the :obj:`~pyrogram.types.inline_query`.

        prefixes (``str`` | ``list``, *optional*):
            A prefix or a list of prefixes as string the filter should look for.
            Defaults to "/" (slash). Examples: ".", "!", ["/", "!", "."], list(".:!").
            Pass None or "" (empty string) to allow commands with no prefix at all.

        case_sensitive (``bool``, *optional*):
            Pass True if you want your command(s) to be case sensitive. Defaults to False.
            Examples: when True, command="Start" would trigger /Start but not /start.
    """

    async def __call__(
        self,
        event: CallbackQuery,
    ) -> Union[bool, dict[str, Any]]:
        assert event.bot, "wtf"
        username = (await event.bot.get_me()).username or ""
        text = event.data
        if isinstance(text, bytes):
            return False
        # setattr(event, "command", list())

        if not text:
            return False

        for prefix in self.prefixes:
            if not text.startswith(prefix):
                continue

            without_prefix = text[len(prefix) :]

            for cmd in self.commands:
                if not re.match(
                    rf"^(?:{cmd}(?:@?{username})?)(?:\s|$)",
                    without_prefix,
                    flags=re.IGNORECASE if not self.case_sensitive else 0,
                ):
                    continue

                without_command = re.sub(
                    rf"{cmd}(?:@?{username})?\s?",
                    "",
                    without_prefix,
                    count=1,
                    flags=re.IGNORECASE if not self.case_sensitive else 0,
                )

                # match.groups are 1-indexed, group(1) is the quote, group(2) is the text
                # between the quotes, group(3) is unquoted, whitespace-split text

                # Remove the escape character from the arguments
                command = [cmd] + [
                    re.sub(r"\\([\"'])", r"\1", m.group(2) or m.group(3) or "")
                    for m in self.command_re.finditer(without_command)
                ]

                return dict(command=command)

        return False


class ChosenInlineResultCommand(ReCommand):
    """Filter commands, i.e.: text chosen_inline_result starting with "/" or any other custom prefix.

    Parameters:
        commands (``str`` | ``list``):
            The command or list of commands as string the filter should look for.
            Examples: "start", ["start", "help", "settings"]. When a inline_query text containing
            a command arrives, the command itself and its arguments will be stored in the *command*
            field of the :obj:`~pyrogram.types.inline_query`.

        prefixes (``str`` | ``list``, *optional*):
            A prefix or a list of prefixes as string the filter should look for.
            Defaults to "/" (slash). Examples: ".", "!", ["/", "!", "."], list(".:!").
            Pass None or "" (empty string) to allow commands with no prefix at all.

        case_sensitive (``bool``, *optional*):
            Pass True if you want your command(s) to be case sensitive. Defaults to False.
            Examples: when True, command="Start" would trigger /Start but not /start.
    """

    async def __call__(
        self,
        event: ChosenInlineResult,
    ) -> Union[bool, dict[str, Any]]:
        assert event.bot, "wtf"
        username = (await event.bot.get_me()).username or ""
        text = event.inline_message_id
        # setattr(event, "command", list())

        if not text:
            return False

        for prefix in self.prefixes:
            if not text.startswith(prefix):
                continue

            without_prefix = text[len(prefix) :]

            for cmd in self.commands:
                if not re.match(
                    rf"^(?:{cmd}(?:@?{username})?)(?:\s|$)",
                    without_prefix,
                    flags=re.IGNORECASE if not self.case_sensitive else 0,
                ):
                    continue

                without_command = re.sub(
                    rf"{cmd}(?:@?{username})?\s?",
                    "",
                    without_prefix,
                    count=1,
                    flags=re.IGNORECASE if not self.case_sensitive else 0,
                )

                # match.groups are 1-indexed, group(1) is the quote, group(2) is the text
                # between the quotes, group(3) is unquoted, whitespace-split text

                # Remove the escape character from the arguments
                command = [cmd] + [
                    re.sub(r"\\([\"'])", r"\1", m.group(2) or m.group(3) or "")
                    for m in self.command_re.finditer(without_command)
                ]

                return dict(command=command)

        return False


def inline_command(
    commands: Union[str, list[str]],
    prefixes: Union[str, list[str]] = "",
    case_sensitive: bool = False,
):
    """Filter commands, i.e.: text inline_query starting with "/" or any other custom prefix.

    Parameters:
        commands (``str`` | ``list``):
            The command or list of commands as string the filter should look for.
            Examples: "start", ["start", "help", "settings"]. When a inline_query text containing
            a command arrives, the command itself and its arguments will be stored in the *command*
            field of the :obj:`~pyrogram.types.InlineQuery`.

        prefixes (``str`` | ``list``, *optional*):
            A prefix or a list of prefixes as string the filter should look for.
            Defaults to "/" (slash). Examples: ".", "!", ["/", "!", "."], list(".:!").
            Pass None or "" (empty string) to allow commands with no prefix at all.

        case_sensitive (``bool``, *optional*):
            Pass True if you want your command(s) to be case sensitive. Defaults to False.
            Examples: when True, command="Start" would trigger /Start but not /start.
    """
    return InlineCommand(
        commands=commands, prefixes=prefixes, case_sensitive=case_sensitive
    )


def callback_command(
    commands: Union[str, list[str]],
    prefixes: Union[str, list[str]] = "",
    case_sensitive: bool = False,
):
    """Filter commands, i.e.: text callback_queries starting with "/" or any other custom prefix.

    Parameters:
        commands (``str`` | ``list``):
            The command or list of commands as string the filter should look for.
            Examples: "start", ["start", "help", "settings"]. When a inline_query text containing
            a command arrives, the command itself and its arguments will be stored in the *command*
            field of the :obj:`~pyrogram.types.inline_query`.

        prefixes (``str`` | ``list``, *optional*):
            A prefix or a list of prefixes as string the filter should look for.
            Defaults to "/" (slash). Examples: ".", "!", ["/", "!", "."], list(".:!").
            Pass None or "" (empty string) to allow commands with no prefix at all.

        case_sensitive (``bool``, *optional*):
            Pass True if you want your command(s) to be case sensitive. Defaults to False.
            Examples: when True, command="Start" would trigger /Start but not /start.
    """
    return CallbackCommand(
        commands=commands, prefixes=prefixes, case_sensitive=case_sensitive
    )


def cir_command(
    commands: Union[str, list[str]],
    prefixes: Union[str, list[str]] = "",
    case_sensitive: bool = False,
):
    """Filter commands, i.e.: text chosen_inline_result starting with "/" or any other custom prefix.

    Parameters:
        commands (``str`` | ``list``):
            The command or list of commands as string the filter should look for.
            Examples: "start", ["start", "help", "settings"]. When a inline_query text containing
            a command arrives, the command itself and its arguments will be stored in the *command*
            field of the :obj:`~pyrogram.types.inline_query`.

        prefixes (``str`` | ``list``, *optional*):
            A prefix or a list of prefixes as string the filter should look for.
            Defaults to "/" (slash). Examples: ".", "!", ["/", "!", "."], list(".:!").
            Pass None or "" (empty string) to allow commands with no prefix at all.

        case_sensitive (``bool``, *optional*):
            Pass True if you want your command(s) to be case sensitive. Defaults to False.
            Examples: when True, command="Start" would trigger /Start but not /start.
    """

    return ChosenInlineResultCommand(
        commands=commands, prefixes=prefixes, case_sensitive=case_sensitive
    )


logger = structlog.getLogger(__name__)
