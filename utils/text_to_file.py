from pyrogram.enums import ParseMode
from pyrogram import Client

import datetime
import asyncio
import pathlib
import hashlib
import os


time_format = "%y-%m-%d %H%M%S"
texts_path = pathlib.Path("data", "output", "temp")
# to_save = str(base_path) + "{os.sep}data{os.sep}output{os.sep}temp{os.sep}"
# to_save = str(texts_path)

files_cache: dict[str, pathlib.Path] = {}
"""some sha256 hash's hexdigest from utf8 text: pathlib.Path"""

is_loaded = False


async def delete_path(path: pathlib.Path, delta_time: int = 600):
    await asyncio.sleep(delta_time)
    files_cache_items = list(files_cache.items())

    path_maybe: list[str] = [i[0] for i in files_cache_items if i[1] == path]
    if not path_maybe:
        return
    need_hash = path_maybe[0]

    if path.is_file():
        os.remove(str(path))
    del files_cache[need_hash]
    return


async def convert(client: Client, text: str):
    if not is_loaded:
        load_texts()
    # text = (await client.parser.parse(text, ParseMode.HTML))['message']
    hashed_text = hashlib.md5(text.encode("utf-8")).hexdigest()
    temp_result = files_cache.get(hashed_text)
    if temp_result is not None:
        return str(temp_result)

    filename = datetime.datetime.now().strftime(time_format)
    path: pathlib.Path = texts_path.joinpath(f"{filename}.txt")
    path.write_text(text, "utf-8")

    asyncio.create_task(delete_path(path, delta_time=600))
    files_cache[text] = path
    return str(path)


def load_texts():
    global is_loaded
    is_loaded = True
    files = list(texts_path.glob("*.txt"))

    temp_dict = {file.read_text("utf-8"): file for file in files}
    files_cache.update(temp_dict)
