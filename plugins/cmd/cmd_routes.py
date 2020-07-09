import time
import copy
import shlex
import base64
import threading
import subprocess
from queue import Queue


from flask import Blueprint, render_template, request, jsonify

import utils


current_dir = utils.os_path(utils.get_dir_of_file(__file__))
if current_dir[-1] != utils.sep:
    current_dir += utils.sep


bp = Blueprint('cmd', __name__)
bp.template_folder = current_dir + 'templates'


def run_command(command: str, caller_obj) -> tuple:
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline()
        if output == b'' and process.poll() is not None:
            break
        if output:
            if str(output) != b'':
                caller_obj.out.put(output.strip())
    rc = process.poll()
    caller_obj.status = 'finished'
    return rc, caller_obj.status


class CmdTask:
    def __init__(self, ip_addr, cmd):
        self.out = Queue()
        self.last_out = None
        self.ip_addr = ip_addr
        self.cmd = cmd
        self.status = 'running'
        self.thread = threading.Thread(target=run_command, args=(cmd, self))
        self.thread.start()

    def __call__(self, clear=False) -> list:
        result = list(copy.copy(self.out.queue))
        if result != self.last_out:
            self.last_out = result
        """if clear:
            self.clear()"""
        return result

    def clear(self):
        self.out = Queue()


c = CmdTask("127.0.0.1", "tracert wp.pl")
out = c()
while c.status != 'finished':
    new = c()
    print('>', "\n".join(str(_)[2:-1] for _ in new))
    if new != out:
        out = new[len(out):]
        print("\n".join(str(_)[2:-1] for _ in out))
        time.sleep(1)

exit()


class Tasks(object):
    __tasks__ = dict()

    def __init__(self):
        self.tasks = Tasks.__tasks__


@bp.route('/', defaults={'path': 'index.html'}, methods=['GET'])
@bp.route('/cmd/<path:path>', methods=['GET'])
@utils.login_required
def serve_cmd_route(path):
    if request.method == 'GET':
        if '.html' in path:
            template = path
            if '/' in path:
                template = path.split('/')[-1]
            return open(current_dir + "templates" + utils.sep + template, 'rb').read()

        found = utils.find_files(current_dir, utils.os_path(path), 1)
        if not found:
            return 'cmd/serve_cmd_route: Could not find resource for ' + path
        return open(found[0], 'rb').read()


@bp.route('/q', methods=['POST', 'GET'])
@utils.login_required
def command_route():
    print('cmd_route.py q route')
    if request.method == 'GET':
        return 'GET, OK'
    if request.method == 'POST':
        print("args:", request.args)
        if 'cmd' in request.args:
            cmd = str(base64.b64decode(request.args['cmd']))[2:-1]
            return jsonify({'status': 200, 'data': cmd})
        return 'POST, OK'
