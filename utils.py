import os
import socket
import base64
import datetime
import requests
import chardet

from functools import wraps
from pathlib import Path

from configs import config
# from server import get_ip_route


sep = os.path.sep
this_ip = socket.gethostbyname(socket.gethostname())
pg = {'methods': ['POST', 'GET']}

get_ip_route: callable = lambda: "error"  # server.py: setattr(utils, 'get_ip_route, get_ip_route)


def js_redirect(link: str) -> str:
    link = link if link[0] == '/' else '/' + link
    return f"<script>window.location='{link}';</script>"


def is_admin(client_ip: str) -> bool:
    if client_ip == '127.0.0.1' or client_ip == this_ip:
        return True

    for ip, _bool in config['logged_users'].items():
        if client_ip == ip:
            if _bool is True:
                return True
    return False


def os_path(path: str) -> str:
    if os.name == 'nt':
        path = path.replace('/', '\\')
        while '\\\\' in path:
            path = path.replace('\\\\', '\\')
    else:
        path = path.replace('\\', '/')
        while '//' in path:
            path = path.replace('//', '/')
    return path


def get_drives():
    if os.name == 'nt':
        import string
        from ctypes import windll
        drives = []
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(letter)
            bitmask >>= 1

        return drives
    return ['-']


def path_to_web(local_path: str, encoding='utf8', os_slashes=False, check_exists=False) -> str or FileNotFoundError:
    if os_slashes:
        local_path = os_path(local_path)
    if check_exists:
        if not os.path.exists(local_path):
            raise FileNotFoundError(f'file: {local_path}')
    return str(base64.b64encode(local_path.encode(encoding)))[2:-1]


def web_to_path(encoded_local_path: str, os_slashes=False, check_exists=False) -> str or FileNotFoundError:
    if ':' in encoded_local_path or '/' in encoded_local_path or '\\' in encoded_local_path:
        result = encoded_local_path
    else:
        result = str(base64.b64decode(encoded_local_path))[2:-1]  # remove staring b' and ending '
    if os_slashes:
        result = os_path(result)
    if check_exists:
        if not os.path.exists(result):
            raise FileNotFoundError(f'file: {result}')
    return result


def dir_sep():
    return '\\' if os.name == 'nt' else '/'


def from_time_stamp(time_attr, stamp_format="%d-%m-%Y, %H:%M") -> str:
    return datetime.datetime.fromtimestamp(time_attr).strftime(stamp_format)


def get_file_info(full_path):
    ptw = path_to_web(local_path=full_path, os_slashes=True, check_exists=True)

    parent = get_dir_of_file(full_path)
    name = parent if parent == sep else os_path(full_path).split(sep)[-1]

    # print(f'get_file_info full_path "{full_path}", ptw "{ptw}"  ')

    result = {
        'name': name,
        'access': from_time_stamp(os.path.getatime(full_path)),
        'modified': from_time_stamp(os.path.getmtime(full_path)),
        'changed': from_time_stamp(os.path.getctime(full_path)),  # 'changed': time.ctime(os.path.getctime(full_path)),
        'size': os.path.getsize(full_path),
    }

    if os.path.isdir(full_path):
        result['type'] = 'directory'
        try:
            result['files inside'] = len(os.listdir(full_path))
        except (PermissionError, Exception):
            result['files inside'] = '0 - Access Denied'
    else:
        result['type'] = 'file'

    result['link'] = ptw
    return result


def get_all_files_and_dirs(root_dir, sort=False):
    result = []
    for path in Path(root_dir).rglob('*.*'):
        result.append(str(path))
    if not sort:
        return result
    return sorted(result, key=lambda x: os_path(x).split(sep)[-1])


def find_files(src_dir, partial_file_name, found_limit=0, sort=False):
    result = []

    if not isinstance(found_limit, int):
        if str(found_limit).isdigit():
            try:
                found_limit = int(found_limit)
            except ValueError:
                found_limit = 0

    if found_limit <= 0:
        for path in Path(src_dir).rglob('*.*'):
            path = str(path)
            if partial_file_name in path:
                result.append(path)
    else:
        for path in Path(src_dir).rglob('*.*'):
            path = str(path)
            if partial_file_name in path:
                result.append(path)
                if len(result) > found_limit:
                    break
    if sort:
        return sorted(result, key=lambda x: os_path(x).split('/\\')[-1])
    return result


def get_dir_of_file(full_path) -> str:
    full_path = os_path(full_path)
    if full_path.count(sep) == 0:
        return '/'
    return sep.join(full_path.split(sep)[:-1])


def predict_file_encoding(file_path, n_lines=20) -> str:
    with open(file_path, 'rb') as f:
        data = b''.join([f.readline() for _ in range(n_lines)])
        return chardet.detect(data)['encoding']


def predict_encoding(raw_data: bytearray or bytes) -> str:
    return chardet.detect(raw_data)['encoding']


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # if is_admin(get_ip_route()):
        if is_admin(get_ip_route()):
            return f(*args, **kwargs)
        return js_redirect('/login?next=/main')
    return decorated_function
