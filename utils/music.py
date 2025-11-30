from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSession as Session,
)
from .good_things import timedelta_to_string
from pydantic import BaseModel

# from dataclasses import dataclass
from typing import Optional
from datetime import timedelta
import structlog, logging
import asyncio


logger = structlog.getLogger(__name__)


class MusicInfo(BaseModel):
    status: bool
    """Is music play"""
    artist: Optional[str] = None
    title: Optional[str] = None
    # time: Optional[str] = None
    current_time: Optional[timedelta] = None
    end_time: Optional[timedelta] = None
    """ "03:25 / 05:45" """
    _variables = ["status", "artist", "title", "time"]

    async def update_info(self) -> "MusicInfo":
        _session = await get_session()
        if _session is None:
            return MusicInfo(status=False)
        artist, title = await get_music_info(_session)
        current_time = end_time = None
        if pair := await get_time(_session):
            current_time, end_time = pair
        return MusicInfo(
            status=True,
            artist=artist,
            title=title,
            current_time=current_time,
            end_time=end_time,
        )

    @property
    def time(self) -> None | str:
        return (
            timedelta_to_string(self.end_time - self.current_time)
            if self.end_time and self.current_time
            else None
        )

    @property
    def song(self) -> None | str:
        return " - ".join([n for n in [self.artist, self.title] if n])

    @property
    def song_info(self) -> None | str:
        return self.song and f"{self.song} ({self.time})"

    @property
    def humanity(self) -> None | str:
        return self.song_info

    # def __str__(self):
    #     status_str = "enabled" if self.status else "not enabled"
    #     song_info = self.song_info
    #     other_args = ", " + ", ".join([song_info])
    #     return f"<Music {status_str}{other_args}>"

    # def __repr__(self):
    #     attrs = [f"{n}={getattr(self, n)!r}" for n in self._variables]
    #     return f'MusicInfo({",".join(attrs)})'


async def get_session() -> Session | None:
    sessions = await MediaManager.request_async()
    # This source_app_user_model_id check and if statement is optional
    # Use it if you want to only get a certain player/program's media
    # (e.g. only chrome.exe's media not any other program's).
    #
    # To get the ID, use a breakpoint() to run sessions.get_current_session()
    # while the media you want to get is playing.
    # Then set TARGET_ID to the string this call returns.
    cur_ses: Session | None = sessions.get_current_session()
    return cur_ses


async def play_pause(_session: Optional[Session] = None) -> bool:
    """Trying change player's play/pause status"""
    session = _session or await get_session()
    return bool(session and await session.try_toggle_play_pause_async())


async def next(_session: Optional[Session] = None) -> bool:
    """Trying skip current song to next"""
    session = _session or await get_session()
    return bool(session and await session.try_skip_next_async())


async def prev(_session: Optional[Session] = None) -> bool:
    """Trying skip current song to previous"""
    session = _session or await get_session()
    return bool(session and await session.try_skip_previous_async())


async def get_time(
    _session: Optional[Session] = None,
) -> tuple[timedelta, timedelta] | None:
    """Return something like `30:09/55:37`"""
    session = _session or await get_session()
    if session is None:
        return None

    timeline = session.get_timeline_properties()
    if timeline is None:
        return None

    cur, end = timeline.position, timeline.end_time
    return cur, end


async def get_time_str(_session: Optional[Session] = None) -> str | None:
    """Return something like `30:09/55:37`"""
    session = _session or await get_session()
    if session is None:
        return None

    timeline = session.get_timeline_properties()
    if timeline is None:
        return None

    if not (pair := await get_time(session)):
        return None
    cur, end = pair

    cur_string = timedelta_to_string(cur)
    end_string = timedelta_to_string(end)

    result = f"""{cur_string} / {end_string}"""
    return result


async def get_media_info(_session: Optional[Session] = None) -> dict | None:
    """Get dict with current song info, like title/artist/album…"""
    session = _session or await get_session()
    if session is None:
        return None

    info = await session.try_get_media_properties_async()

    # song_attr[0] != '_' ignores system attributes
    info_dict = {
        song_attr: info.__getattribute__(song_attr)
        for song_attr in dir(info)
        if song_attr[0] != "_"
    }

    # converts winrt vector to list
    info_dict["genres"] = list(info_dict["genres"])

    return info_dict


def _format(a, b=None):
    return f"«{' — '.join([n for n in [a, b] if n])}»"


async def get_music_info(
    _session: Optional[Session] = None,
) -> tuple[str | None, str | None]:
    "returns artist and title"
    session = _session or await get_session()
    raw = await get_media_info(session)
    # time = await get_time(session)
    if not raw:
        return None, None

    artist, title = raw.get("artist"), raw.get("title")
    return (artist, title)


async def get_music_string(_session: Optional[Session] = None) -> str | None:
    if not (pair := await get_music_info(_session)):
        return None
    artist, title = pair
    if artist and title:
        return _format(artist, title)

    elif artist:
        return _format(artist)
    elif title:
        return _format(title)

    else:
        return None


async def get_music_with_time(session: Optional[Session]) -> str | None:
    if session is None:
        return None

    music = await get_music_string(session)
    if music is None:
        return None
    
    time = await get_time_str(session)
    if time is None:
        return None

    result = f"{music} ({time})"
    return result


async def current_music(session: Optional[Session] = None) -> MusicInfo:
    session = session or await get_session()
    if session is None:
        return MusicInfo(status=False)

    artist, title = await get_music_info(session)
    cur_time, end_time = pair if (pair:=await get_time(session)) else (None, None)

    result = MusicInfo(status=True, artist=artist, title=title, current_time=cur_time, end_time=end_time)
    return result


async def main() -> None:
    session = await get_session()
    music = await current_music(session)
    result = "Играет в данный момент: " + (music.song_info or "ничего")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
