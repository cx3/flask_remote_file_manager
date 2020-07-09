path = 'http://192.168.56.1/download?f=C:\\proj\\py\\flask_remote_desktop\\server2.py'

from requests import get as g

open('downloaded_file.py', 'wb').write(g(path).content)
