from flask import Blueprint, render_template

import utils


current_dir = utils.os_path(utils.get_dir_of_file(__file__))
if current_dir[-1] != utils.sep:
    current_dir += utils.sep


bp = Blueprint('xterm', __name__)
bp.template_folder = current_dir + 'templates'


@bp.route('/', defaults={'path': 'index.html'})
@bp.route('/xterm/<path:path>')
@utils.login_required
def serve_xterm_route(path):
    # https://stackoverflow.com/questions/45777770/catch-all-routes-for-flask
    if '.html' in path:
        template = path
        if '/' in path:
            template = path.split('/')[-1]
        return render_template(template)

    found = utils.find_files(current_dir, utils.os_path(path), 1)
    if not found:
        return 'xterm/serve_xterm_route: Could not find resource for ' + path
    return open(found[0], 'rb').read()
