from PIL import ImageFont, Image, ImageDraw
from io import BytesIO
import aiofiles
import datetime
import asyncio
import structlog, logging
import pathlib
import os


logger = structlog.getLogger(__name__)
time_format = "%y-%m-%d %H%M%S%d"
font_size = 16
font_file = str(pathlib.Path(__file__).parent.joinpath("consola.ttf"))
# to_save = pathlib.Path().joinpath("data", "temp", "images")
to_save = pathlib.Path().joinpath("data", "temp")
padding = _pad = 8
max_len_line = 64

results_cache: dict[str, str] = {}
"""Dict with text and path to image with same text"""


async def delete_path(_path: str, delta_time=600):
    await asyncio.sleep(delta_time)
    text = [
        temp_text
        for (temp_text, temp_path) in results_cache.items()
        if temp_path == _path
    ][0]
    del results_cache[text]
    if os.path.isfile(_path):
        os.remove(_path)
    return


async def save_image(_path: str, _image: bytes) -> None:
    async with aiofiles.open(_path, "wb") as _file:
        await _file.write(_image)


async def split_text(source_text: str, len_for_line: int = max_len_line) -> str:
    lines = source_text.splitlines()
    maximum_line_len = max([len(line) for line in lines] + [len_for_line])
    if maximum_line_len == len_for_line:
        return source_text

    temp_result = []
    for line in lines:
        line_words: list[str] = line.split(" ")
        temp_line: list[str] = list()
        for index, word in enumerate(line_words):
            # logger.debug(f"{index=}, {line=}, {len(temp_line)=}")
            maybe_final_line = " ".join(temp_line + [word])

            if len(maybe_final_line) > max_len_line:
                temp_result.append(" ".join(temp_line))
                temp_line.clear()
                temp_line.append(word)
                logger.debug(f"too long temp line - clear temp_line at {word=}")
            else:
                temp_line.append(word)
                # continue

            if index + 1 == len(line_words):
                # temp_line.append(line)
                temp_result.append(" ".join(temp_line))
                temp_line.clear()
                logger.debug(f"last word - clear temp_line at {word=}")

            await asyncio.sleep(0)
        await asyncio.sleep(0)

    result = "\n".join(temp_result)
    return result


async def convert(text: str, max_line_len: int = max_len_line, auto_delete: bool = True):
    """Returns path to image"""
    # text = (await client.parser.parse(text, ParseMode.HTML))['message']
    temp_result = results_cache.get(text)
    if temp_result is not None:
        return temp_result

    text = await split_text(text, len_for_line=max_line_len)
    logger.debug("writing to image")
    # seguivar.ttf consola.ttf

    font = ImageFont.truetype(font_file, font_size)

    with Image.new("RGBA", size=(1, 1), color=(0, 0, 0)) as img:
        # size = font.getbbox(text)
        draw = ImageDraw.ImageDraw(img)
        size = draw.multiline_textbbox((0, 0), text, font, font_size=font_size)

        w, h = round(size[2] - size[0]) + _pad * 2, round(size[3] - size[1]) + _pad * 2
        img = img.resize((w, h))
        draw = ImageDraw.ImageDraw(img)
        draw.text((_pad, _pad), text, (0xDF, 0xDF, 0xDF), font)

        size = draw.multiline_textbbox((0, 0), text, font, font_size=font_size)
        w, h = round(size[2] - size[0]) + _pad * 2, round(size[3] - size[1]) + _pad * 2
        draw.line(
            [(0, 0), (0, h), (w, h), (w, 0), (0, 0)], fill=(0xFF, 0x80, 0, 128), width=8
        )

    filename = datetime.datetime.now().strftime(time_format)
    path = str(to_save.joinpath(filename + ".png"))

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img.close()
    result_bytes = bytes(buffer.getbuffer())

    await save_image(path, result_bytes)
    if auto_delete:
        asyncio.create_task(delete_path(path, 600))
        results_cache[text] = path
    return path


if __name__ == "__main__":

    async def main():
        import json
        import os

        test = """📸📸📸 чел 📸📸📸
📸📸📸 ты 📸📸📸
📸📸📸 сфоткан 📸📸📸


Мьюинг (англ. "mewing") - это техника правильного положения языка и челюстно-лицевых мышц. 
Этот термин происходит от имени британского ортодонтиста Джона Мьюа (John Mew), который разработал эту методику в 1980-х годах. Мьюинг заключается в правильном расположении языка во рту, при котором оно прижато к поднебесной дуге и держится в этом положении естественным образом, без усилий. Мьюинг предлагает, что это положение языка может стимулировать правильный рост и развитие лица, а также повлиять на позицию зубов и дыхательную систему. Приверженцы этой методики считают, что мьюинг может помочь снизить риск различных проблем со здоровьем, связанных с дыханием, образованием рта и лица. Однако, мнения врачей по поводу эффективности мьюинга разделяются, и некоторые из них считают, что более качественные исследования требуются для подтверждения его эффективности.
{
    "a": {
        "b": {
            "c": 3
        }, 
        "d": [
            1, 
            2, 
            {
                "a": "mogus"
            }
        ]
    }
}
"""
        # test += json.dumps(
        #     ,
        #     indent=4,
        #     sort_keys=True,
        #     ensure_ascii=False,
        # )
        test += "\n1234567890" * 100

        logging.basicConfig(level=logging.DEBUG)
        logger.debug("start convert")
        result = await convert(test)
        logger.debug(result)
        os.system(f'code "{result}"')
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            pass
        os.remove(result)

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        pass

__all__ = ["convert"]
