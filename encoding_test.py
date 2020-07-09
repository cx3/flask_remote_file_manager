import os


def os_path(path: str) -> str:
    if os.name == 'nt':
        path = path.replace('/', '\\')
        while '\\\\' in path:
            path = path.replace('\\\\', '\\')
    else:
        path = path.replace('\\', '/')
        while '//' in path:
            path = path.replace('//', '/')
    return path  #test
