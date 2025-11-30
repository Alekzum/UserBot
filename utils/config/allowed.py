from typing import Literal
import time
import json
import os


file_name = os.sep.join(["data", "config", "allowed.json"])

_fileBusy = False
_update_time = 0.01


def wait_unlock():
    global _fileBusy
    while _fileBusy:
        time.sleep(_update_time)


def lock_file():
    global _fileBusy
    _fileBusy = True


def unlock_file():
    global _fileBusy
    _fileBusy = False


def WithLocking(func):
    def inner(*args, **kwargs):
        wait_unlock()
        lock_file()
        result = func(*args, **kwargs)
        unlock_file()
        return result
    return inner


if not os.path.isfile(file_name):
    with open(file_name, 'w') as f: 
        json.dump({'allowed': []}, f)


@WithLocking
def get_raw():
    with open(file_name, encoding='utf-8') as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError:
            raw = {'allowed': []}
            save_raw({'allowed': []})
    return raw


@WithLocking
def save_raw(raw):
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(raw, f)
    return True


def get_allowed() -> list:
    """Get allowed groups"""
    return get_raw().get('allowed', [])


def add_allowed(group: int|str) -> list | Literal[False]:
    """Add group to allowed groups. Return new allowed groups or False if already in"""
    if in_allowed(group):
        return False
    raw = get_raw()
    raw['allowed'].append(group)
    raw['allowed'] = list(set(raw['allowed']))
    save_raw(raw)
    return raw['allowed']


def delete_allowed(group: int|str) -> list | Literal[False]:
    """Delete group from allowed groups. Return new allowed groups or False if already removed"""
    if not in_allowed(group):
        return False
    raw = get_raw()
    raw['allowed'].remove(group)
    raw['allowed'] = list(set(raw['allowed']))
    save_raw(raw)
    return raw['allowed']


def in_allowed(group: int|str) -> bool:
    """Check what group in allowed groups"""
    return group in get_raw()['allowed']
