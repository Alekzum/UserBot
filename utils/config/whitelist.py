from typing import Literal, overload, Protocol
import time
import json
import os


file_name = os.sep.join(["data", "config", "whitelist.json"])
default_list = [1325079151, 5625978754]



_fileBusy = False
_update_time = 0.01


class User(Protocol):
    id: int


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
        json.dump({'whitelist': default_list}, f)


@WithLocking
def get_raw():
    with open(file_name, encoding='utf-8') as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError:
            raw = {'whitelist': default_list}
            save_raw({'whitelist': default_list})
    return raw


@WithLocking
def save_raw(raw):
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(raw, f)
    return True


def get_whitelist() -> list[int]:
    """Get whitelist users"""
    return get_raw().get('whitelist', default_list)


def add_to_whitelist(user: int|User) -> bool:
    """Try add user to whitelist users"""
    if hasattr(user, "id") and isinstance(user.id, int):
        return add_to_whitelist(user.id)
    
    if in_whitelist(user):
        return False
    
    raw = get_raw()
    raw['whitelist'].append(user)
    raw['whitelist'] = list(set(raw['whitelist']))
    save_raw(raw)
    return True


def delete_from_whitelist(user: int|User) -> list | Literal[False]:
    """Delete user from whitelist users. Return new whitelist users or False if already removed"""
    if hasattr(user, "id") and isinstance(user.id, int):
        return delete_from_whitelist(user.id)
    
    if not in_whitelist(user):
        return False
    raw = get_raw()
    raw['whitelist'].remove(user)
    raw['whitelist'] = list(set(raw['whitelist']))
    save_raw(raw)
    return raw['whitelist']


def in_whitelist(user: int|User) -> bool:
    """Check what user in whitelist users"""
    if hasattr(user, "id") and isinstance(user.id, int):
        return in_whitelist(user.id)
    return user in get_raw()['whitelist']
