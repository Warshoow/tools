import base64, json, os, re, ssl, struct, sys, time, urllib.request

def conf(key):
    if os.environ.get(key):
        return os.environ[key]
    for d in (os.environ.get('GRAB_PROJECT_DIR'), os.getcwd()):
        p = os.path.join(d or '', '.claude', 'settings.local.json')
        if d and os.path.exists(p):
            v = json.load(open(p)).get('env', {}).get(key)
            if v:
                return v
    sys.exit(f'portainer-exec: {key} not set (env or .claude/settings.local.json)')

BASE = f"{conf('PORTAINER_URL').rstrip('/')}/api/endpoints/{conf('PORTAINER_ENDPOINT')}/docker"
TOKEN = conf('PORTAINER_ACCESS_TOKEN')
CTX = ssl._create_unverified_context()

def req(path, body=None, method='GET', timeout=600):
    r = urllib.request.Request(BASE + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'X-API-Key': TOKEN, 'Content-Type': 'application/json'})
    return urllib.request.urlopen(r, context=CTX, timeout=timeout).read()

def demux(b):
    out, i = b'', 0
    while i + 8 <= len(b):
        n = struct.unpack('>I', b[i + 4:i + 8])[0]
        out += b[i + 8:i + 8 + n]
        i += 8 + n
    return out.decode(errors='replace')

def sh(container, cmd, timeout=600):
    e = json.loads(req(f'/containers/{container}/exec',
        {'AttachStdout': True, 'AttachStderr': True, 'Cmd': ['sh', '-c', cmd]}, 'POST'))
    return demux(req(f"/exec/{e['Id']}/start", {'Detach': False, 'Tty': False}, 'POST', timeout))

def b64(path):
    return base64.b64encode(open(path, 'rb').read()).decode()

def check_name(name):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
        sys.exit('portainer-exec: name must be [A-Za-z0-9_-]+')

def poll(container, name):
    return sh(container, f'cat /tmp/pe_{name}.out 2>/dev/null; '
                         f'if [ -f /tmp/pe_{name}.rc ]; then echo "DONE rc=$(cat /tmp/pe_{name}.rc)"; '
                         f'elif [ -f /tmp/pe_{name}.sh ]; then echo RUNNING; else echo "UNKNOWN job {name}"; fi', 60)

def main(a):
    if not a or a[0] in ('-h', '--help', 'help'):
        print(open(os.path.join(os.path.dirname(__file__), 'TOOL.md')).read()); return
    cmd = a[0]
    if cmd == 'ps':
        for c in json.loads(req('/containers/json?all=1')):
            n = c['Names'][0].lstrip('/')
            if len(a) < 2 or a[1] in n:
                print(n, c['State'], c['Status'])
    elif cmd == 'run':
        print(sh(a[1], f'echo {b64(a[2])} | base64 -d > /tmp/pe_run_$$.sh; sh /tmp/pe_run_$$.sh; rc=$?; rm -f /tmp/pe_run_$$.sh; echo "DONE rc=$rc"'))
    elif cmd == 'start':
        check_name(a[3]); n = a[3]
        print(sh(a[1], f'rm -f /tmp/pe_{n}.rc /tmp/pe_{n}.out; echo {b64(a[2])} | base64 -d > /tmp/pe_{n}.sh; '
                       f'(nohup sh /tmp/pe_{n}.sh > /tmp/pe_{n}.out 2>&1; echo $? > /tmp/pe_{n}.rc) > /dev/null 2>&1 & echo "STARTED {n}"', 60))
    elif cmd == 'poll':
        check_name(a[2]); print(poll(a[1], a[2]))
    elif cmd == 'wait':
        check_name(a[2]); deadline = time.time() + 60 * float(a[3] if len(a) > 3 else 30)
        while True:
            try:
                out = poll(a[1], a[2])
            except Exception as e:
                out = f'poll error: {e}\nRUNNING'
            if 'RUNNING' not in out.splitlines()[-1:] or time.time() > deadline:
                print(out if 'RUNNING' not in out.splitlines()[-1:] else out + '\n(wait timed out, job still running)'); return
            time.sleep(30)
    else:
        sys.exit(f'portainer-exec: unknown command {cmd}')

main(sys.argv[1:])
