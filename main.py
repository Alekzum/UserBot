from utils.config.my_wraps import wrap_loggers
from utils.config.modules_things import (
    set_handlers_get_diffs,
    execute_on_startup,
    execute_on_shutdown,
    get_bot_routers,
)
import pyrogram
import traceback
import asyncio
import structlog
import logging
import dotenv
import os

from contextlib import contextmanager, suppress

from requests.exceptions import ConnectionError, Timeout
from httpx import NetworkError, TimeoutException

import aiogram
from aiogram.client.default import DefaultBotProperties

# from utils.my_patches import Dispatcher, Client
from utils.my_patches import Client
from utils.bot_things.my_middleware import LogMiddleware

dotenv.load_dotenv()


logger = structlog.getLogger(__name__)
pyro_client_logger = logging.getLogger("pyrogram.client")
bot_turn_on = True

tasks: set[asyncio.Task] = set()

TIMEOUT_EXCEPTIONS = (Timeout, ConnectionError, NetworkError, TimeoutException)


@contextmanager
def mute_pyrogram():
    logger.debug("pyrogram.client now WARN ;)")
    pyro_client_logger.setLevel(logging.WARNING)
    yield
    pyro_client_logger.setLevel(logging.INFO)
    logger.debug("pyrogram.client now INFO ;)")


async def stop_app(app: Client) -> bool:
    if not app.is_connected:
        logger.warning("Client is already stopped!")
        return True
    await execute_on_shutdown(app)

    logger.info("Stopping bots...")
    # async for i in app.get_dialogs():
    # pass

    try:
        logger.debug("Clearing last name...")
        await app.update_profile(last_name="")
        logger.debug("Cleared last name.")
    except Exception as ex:
        ex_str = "".join(traceback.format_exception(ex))
        logger.warning(f"Captured exception {ex!s}: \n{ex_str}")
        pass
    # except KeyboardInterrupt:
    # pass

    if bot_turn_on and app._other_bot:
        dp, bot = app._other_bot
        logger.debug("Stopping additional bot")

        for task in tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

        try:
            await dp.emit_shutdown(bot=bot)
            await bot.session.close()
        except TIMEOUT_EXCEPTIONS:
            logger.warning("Timeout at additional bot.")
        # await dp.stop_polling()
        logger.info("Stopped additional bot")
        delattr(app, "_other_bot")

    logger.debug("Stopping main app...")
    # await app.storage.save()
    try:
        await app.stop()
    except TIMEOUT_EXCEPTIONS:
        logger.warning("Timeout at main app.")
    logger.info("Stopped main app")
    return True


async def start_app(app: Client) -> bool:
    additional_info: list[str] = []

    if app.is_connected:
        logger.warning("Client is already started!")
        return True

    diffs = await set_handlers_get_diffs(app)

    logger.debug(
        f"Start bot{'s' if bot_turn_on else ''} (aka connect to Telegram)"
    )

    with mute_pyrogram():
        await app.start()

    if bot_turn_on and app._other_bot:
        pair = app._other_bot
        dp, bot = pair
        # aiogram_taskh mute_pyrogram():
        # await dp.emit_startup(bot=bot)
        # tasks.add(asyncio.create_task(dp.start_polling(bot)))
        # await asyncio.sleep(5)
        tasks.add(asyncio.create_task(dp.start_polling(bot)))
        # await dp._polling(bot)
        # tasks.add(asyncio.create_task(dp._polling(bot)))
        bot_username = (await bot.get_me()).username
        additional_info.append(f"(bot's username is @{bot_username})")

    await execute_on_startup(app, diffs)

    result_string = " ".join(["Userbot pyrogram.idle"] + additional_info)
    logger.info(result_string)
    return True


async def main():
    # app = PyroClient(
    app = Client(
        "Kurigram_UserBot",
        api_id=os.environ["ID"],
        api_hash=os.environ["HASH"],
        system_version="SDK 31",
        device_model="Samsung SM-G998B",
        client_platform=pyrogram.enums.ClientPlatform.ANDROID,
        phone_number=os.environ["PHONE"],
        password=os.environ["PASSWORD"],
        plugins=dict(root="handlers.userbot"),
        workdir="my_sessions",
        lang_pack="jabka",
        lang_code="ru",
        system_lang_code="ru",
        sleep_threshold=120,
    )
    # app.storage = AIOSQLiteStorage(client=app)
    setattr(app, "_other_bot", None)

    if bot_turn_on:
        # bot = PyroClient(
        bot = aiogram.Bot(
            # "Kurigram_Bot",
            token=os.environ["BOT_TOKEN"],
            default=DefaultBotProperties(parse_mode="html"),
            # plugins=dict(root="handlers.bot"),
            # workdir="my_sessions",
            # api_id=os.environ["ID"],
            # api_hash=os.environ["HASH"],
            # lang_pack="jabka",
            # lang_code="ru",
            # system_lang_code="ru",
            # sleep_threshold=120,
            # system_version="SDK 31",
            # client_platform=pyrogram.enums.ClientPlatform.ANDROID,
            # device_model="Samsung SM-G998B",
        )
        dp = aiogram.Dispatcher(disable_fsm=True)
        dp.update.middleware(LogMiddleware())
        dp.include_routers(*get_bot_routers())
        # bot.storage = AIOSQLiteStorage(client=bot)
        setattr(app, "_other_bot", (dp, bot))
        # bot = patch_app(bot)

    # app = patch_app(app)
    await start_app(app)
    await pyrogram.idle()  # pyright: ignore[reportPrivateImportUsage]
    await stop_app(app)


if __name__ == "__main__":
    logger.debug("Invoking main() somehow")
    wrap_loggers()
    logger.info("Starting...\n")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Userbot is stopped")
        exit(-1)

    logger.info("Userbot is stopped")
    exit()
