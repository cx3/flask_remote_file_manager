#! Python38
import os
import base64
import platform
import datetime

# third party imports
from flask import Flask, request, render_template, Response, send_from_directory
from werkzeug.utils import secure_filename


# local imports
from configs import config
import utils


# let's code!
app = Flask(__name__)
pg = utils.pg
sep = utils.sep
login_required = utils.login_required


@app.route('/ip', **pg)
def get_ip_route():
    return request.remote_addr


setattr(utils, 'get_ip_route', get_ip_route)


@app.route('/login', **pg)
def login_route():
    if utils.is_admin(request.remote_addr):
        return utils.js_redirect('/main')

    if request.method == 'GET':
        return render_template('login.html')

    if request.method == 'POST':
        args = dict(request.form)
        for item in ['user', 'pass']:
            if item not in args:
                args[item] = ''

        if args['user'] == config['admin_login'] and args['pass'] == config['admin_pass']:
            config['logged_users'][request.remote_addr] = True
            if 'next' in args:
                return utils.js_redirect(args['next'])
            return utils.js_redirect('/main')
        else:
            render_template("login.html", **{'user': args['user'], 'pass': args['pass']})
    return render_template('/login')


@app.route('/logout')
def logout_route():
    if request.remote_addr in config['logged_users']:
        del config['logged_users'][request.remote_addr]
    return utils.js_redirect('/main')


@app.route('/', **pg)
@app.route('/main', **pg)
@login_required
def main_route():
    return utils.js_redirect('/ls?f=' + utils.path_to_web(config['this_dir']))


@app.route('/os_name')
@login_required
def os_info_route():
    return f"{platform.system()} {platform.release()}"


@app.route('/ls', **pg)
@login_required
def ls_route():
    args = dict(request.args)
    src = '/'
    if 'dir' in args:
        try:
            src = utils.web_to_path(args['dir'], os_slashes=True)
        except FileNotFoundError:
            pass

    dirs, files = [], []

    for item in os.listdir(src):
        full_path = utils.os_path(src + '/' + item)
        info = utils.get_file_info(full_path)
        if 'dir' in info['type']:
            dirs.append(info)
        else:
            files.append(info)

    return render_template('dir_content2.html', ls=src, dirs=dirs, files=files)


@app.route('/find', **pg)
@login_required
def find_files_route():
    if request.method in ['GET', 'POST']:
        args = dict(request.args)

        if 'src_dir' not in args:
            args['src_dir'] = '/'
        if 'partial_file_name' not in args:
            args['partial_file_name'] = '*'
        if 'found_limit' not in args:
            args['found_limit'] = 1000
        if 'sort' in args:
            args['sort'] = args['sort'].lower()
            if args['sort'] in ['1', 'true', 'y', 'yes']:
                args['sort'] = True
        else:
            args['sort'] = False

        return "<br>".join(utils.find_files(**args))


@app.route('/ace', **pg)
@login_required
def ace_edit_route():
    if request.method == 'GET':
        args = dict(request.args)
        if 'f' in args:
            fp = args['f']
        elif 'file' in args:
            fp = args['file']
        else:
            if not os.path.exists('./new_ace_file.txt'):
                open('new_ace_file.txt', 'w').close()
            return utils.js_redirect(
                f"/ace?f=" + utils.path_to_web(f"{config['this_dir']}{sep}new_ace_file.txt") + '&encoding=ascii'
            )

        data = bytes('Empty file'.encode('ascii'))
        old_fp = fp
        fp = utils.web_to_path(fp, os_slashes=True)

        if os.path.isfile(fp):
            try:
                data = bytes(open(fp, 'r').read())
            except (UnicodeError, UnicodeDecodeError, Exception):
                data = bytes(open(fp, 'rb').read())

        data = base64.b64encode(data)
        dirs, files = [], []

        for item in os.listdir(utils.get_dir_of_file(fp)):
            if os.path.isdir(fp + sep + item):
                dirs.append(item)
            else:
                files.append(item)

        return render_template(
            "ace_editor.html",
            data=str(data)[2:-1],
            dirs=dirs,
            files=files,
            action='/ace?f=' + old_fp,
            encoding=utils.predict_encoding(data),
            full_path=fp,
            file_name=fp.split(sep)[-1]
        )

    if request.method == 'POST':
        args = dict(request.args)

        def resp(msg_when_fail='Error', succes=True):
            return Response(
                response='{"success": "true"}' if succes else msg_when_fail,
                status=200 if succes else 500,
                content_type='application/json'
            )

        if 'f' in args and 'content' in args and 'encoding' in args:
            fp = utils.web_to_path(args['f'], os_slashes=True)
            enc = args['encoding']
            data = base64.b64decode(args['content'])
            data = data.decode(enc)

            if os.path.isfile(fp):
                fp = 'encoding_test.py'
                try:
                    open(fp, 'w', encoding=enc).write(data)
                    return resp()
                except UnicodeDecodeError:
                    open(fp, 'wb').write(data)
                    return resp()
                except (OSError, Exception) as e:
                    return resp(f"OSERROR: {type(e)}: {e}", succes=False)
            if os.path.isdir(fp):
                return resp(f"OSERROR: Cannot save string/binary content as directory", succes=False)
        else:
            return resp(f"Invalid parameters", succes=False)


@app.route('/b64/<string:b64_or_path>', **pg)
def b64_or_path_route(b64_or_path=None):
    # path = utils.web_to_path(request.path.split('/')[1])
    try:
        path = utils.web_to_path(b64_or_path, check_exists=True)
    except (FileNotFoundError, Exception):
        return 'File/directory not found'

    if request.method == 'GET':
        if os.path.isdir(path):
            return 'directory'
        return 'file'
    if request.method == 'POST':
        return str(NotImplemented)


@app.route('/upload', **pg)
def upload_route():

    upload_dir = config['this_dir'] + sep + 'upload'

    if request.method == 'GET':
        args = dict(request.args)
        dest_dir = upload_dir if 'dir' not in args else args['dir']

        if 'modal' in args:
            if args['modal'].lower() in ['1', 'y', 't', 'true']:
                return render_template('upload_form_modal.html', dest_dir=dest_dir)
        return render_template('upload_form.html', dest_dir=dest_dir)

    if request.method == 'POST':
        args = dict(request.args)
        dest_dir = upload_dir if 'dir' not in args else args['dir']

        if not os.path.exists(dest_dir) or not os.path.isdir(dest_dir):
            dest_dir = upload_dir

        dest_dir = utils.os_path(dest_dir)
        if dest_dir[-1] != sep:
            dest_dir += sep

        saved_files = []

        for item in request.files.items():
            fn: str = secure_filename(request.files[item[0]].filename)
            if os.path.exists(dest_dir + fn):
                ext = ''
                if '.' in fn:
                    ext = fn.split('.')[-1]
                    fn = fn[:-(len(ext) + 1)]
                fn = fn + '__' + datetime.datetime.now().strftime("%Y_%m_%d__@__%H_%M_%S") + '.' + ext
            fn = dest_dir + fn
            item[1].save(fn)
            saved_files.append(fn)
        return str(saved_files)


@app.route('/download', methods=['GET'])
def download_route():
    fp = '' if 'f' not in request.args else request.args['f']
    fp = utils.web_to_path(fp)

    if not os.path.exists(fp):
        return f'File {fp} not exists on server'

    if os.path.isdir(fp):
        return 'Cannot download whole directory this way'

    return send_from_directory(utils.get_dir_of_file(fp), fp.split(sep)[-1], as_attachment=True)


@app.errorhandler(404)
@login_required
def serve_static_file(*args, **kwargs):

    if '/' in request.path:
        name = request.path.split('/')[-1]
    else:
        name = request.path

    print(f'404 handling for "{request.path}"')

    for next_file in config['ace_files']:
        if name in next_file:
            print('e> ', name, ' => ', next_file)
            return open(next_file, 'rb').read()
    return f'FILE "{name}" NOT FOUND.  args={args}, kwargs={kwargs}'


def test():
    import subprocess, sys

    cmd = 'p38 c:\\proj\\py\\flask_fm\\infinite_loop.py'
    p = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE)

    while True:
        out = p.stderr.read(1)
        if out == '' and p.poll() is not None:
            break
        if out != '' and str(out) != "b''":
            try:
                sys.stdout.write(out)
                sys.stdout.flush()
            except TypeError:
                print('broken at:' + str(out))
                break
        else:
            break




@app.route('/map', **pg)
@app.route('/site_map', **pg)
@app.route('/site-map', **pg)
@login_required
def site_map_route():
    html = ""
    for i in app.url_map.iter_rules():
        # ['_argument_weights', '_converters', '_regex', '_static_weights', '_trace', 'alias', 'arguments',
        # 'bind', 'build', 'build_compare_key', 'build_only', 'compile', 'defaults', 'empty', 'endpoint',
        # 'get_converter', 'get_empty_kwargs', 'get_rules', 'host', 'is_leaf', 'map', 'match',
        # 'match_compare_key', 'methods', 'provide_automatic_options', 'provides_defaults_for', 'redirect_to',
        # 'refresh', 'rule', 'strict_slashes', 'subdomain', 'suitable_for']

        # print(f'{i.rule} -> {i.endpoint}, mets:{i.methods} args:{i.arguments}')

        if i.rule in ['/site_map', '/site-map']:
            continue

        html += f"""<a href="{i.rule}">{i.rule}</a><br>"""
    return html


import plugins.xterm
import plugins.cmd
app.register_blueprint(plugins.xterm.xterm_routes.bp, url_prefix='/xterm')
app.register_blueprint(plugins.cmd.cmd_routes.bp, url_prefix='/cmd')


if __name__ == "__main__":
    config['this_dir'] = utils.os_path(utils.get_dir_of_file(__file__))
    config['ace_files'] = utils.get_all_files_and_dirs(config['this_dir'] + sep + 'ace-master', sort=True)

    app.run(host=config['host'], port=config['port'], debug=config['debug'])
