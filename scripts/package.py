from pathlib import Path
import json
import os
import pty
import select
import signal
import subprocess
import time
import xml.etree.ElementTree as XML
import zipfile
from font_assets import write_widget_archive

ROOT = Path(__file__).resolve().parents[1]

DEFAULTS = {'signingProfile': 'FrameHome', 'sdkDir': '.local/tizen-sdk'}


def load_config():
    config = dict(DEFAULTS)
    path = ROOT / '.local/packaging.json'
    if not path.exists():
        return config
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        raise SystemExit('Cannot parse .local/packaging.json: invalid JSON at line %s, column %s.' % (error.lineno, error.colno))
    if not isinstance(raw, dict):
        raise SystemExit('Cannot use .local/packaging.json: expected an object with keys: sdkDir, signingProfile.')
    for key in raw:
        if key not in DEFAULTS:
            raise SystemExit("Unknown key '%s' in .local/packaging.json. Supported keys: sdkDir, signingProfile." % key)
    for key, value in raw.items():
        if not isinstance(value, str) or not value:
            raise SystemExit("Invalid value for '%s' in .local/packaging.json: expected a non-empty string." % key)
    config.update(raw)
    return config


def resolve_sdk_dir(value, root=ROOT):
    """Resolve an sdkDir value against root.

    Relative values resolve from the repository root; absolute values
    are used as given. A leading ~ is not expanded.
    """
    path = Path(value)
    if path.is_absolute():
        return path
    return root / value


def find_cli(sdk):
    cli = sdk / 'tools/ide/bin/tizen'
    if not cli.exists():
        raise SystemExit('Tizen CLI not found at %s. Install the SDK or set the sdkDir key in .local/packaging.json.' % cli)
    if not os.access(cli, os.X_OK):
        raise SystemExit('Tizen CLI at %s is not executable. Run: chmod +x %s' % (cli, cli))
    return cli


def check_inputs(root=ROOT):
    config = load_config()
    signing_profile = config['signingProfile']
    sdk = resolve_sdk_dir(config['sdkDir'], root)
    if not sdk.exists():
        raise SystemExit('Tizen SDK not found at %s. Install the SDK there or set the sdkDir key in .local/packaging.json. See docs/development.md.' % sdk)
    cli = find_cli(sdk)
    private = root / '.local/certificates/private'
    password_file = private / 'certificate-password.txt'
    if not password_file.exists():
        raise SystemExit('Signing password file missing at %s. See docs/development.md.' % password_file)
    password = password_file.read_bytes().strip()
    if not password:
        raise SystemExit('Signing password is empty at %s.' % password_file)
    profile = private / 'profiles.xml'
    if not profile.exists():
        raise SystemExit('Signing profiles file missing at %s. See docs/development.md.' % profile)
    try:
        tree = XML.parse(profile)
    except XML.ParseError:
        raise SystemExit('Cannot parse signing profiles file at %s. Recreate it with the Tizen Certificate Manager.' % profile)
    names = set()
    for element in tree.getroot().iter():
        if element.tag in ('profile', 'profileitem'):
            name = element.get('name')
            if name:
                names.add(name)
    if signing_profile not in names:
        raise SystemExit("Signing profile '%s' (key signingProfile in .local/packaging.json) not found in %s." % (signing_profile, profile))
    data = sdk / 'data'
    planned = 'TIZEN_SDK_INSTALLED_PATH=' + str(sdk) + '\nTIZEN_SDK_DATA_PATH=' + str(data) + '\nJDK_PATH=' + str(sdk / 'jdk') + '\n'
    info = sdk / 'sdk.info'
    if sdk.resolve().is_relative_to((root / '.local').resolve()):
        planned_sdk_info = planned
    elif not info.exists():
        planned_sdk_info = planned
    elif info.read_text() == planned:
        planned_sdk_info = None
    else:
        raise SystemExit('Will not rewrite differing sdk.info at %s. Tizen tools read sdk.info to find the data directory, so rewriting it would retarget other work that shares this SDK. Use a dedicated copy under .local/tizen-sdk (key sdkDir in .local/packaging.json). See docs/development.md.' % info.resolve())
    return {
        'root': root,
        'sdk': sdk,
        'cli': cli,
        'signing_profile': signing_profile,
        'password': password,
        'profile': profile,
        'profiles_tree': tree,
        'planned_sdk_info': planned_sdk_info,
    }


def prepare(inputs):
    root = inputs['root']
    sdk = inputs['sdk']
    dist = root / 'dist'
    dist.mkdir(exist_ok=True)
    data = sdk / 'data'
    data.mkdir(exist_ok=True)
    if inputs['planned_sdk_info'] is not None:
        (sdk / 'sdk.info').write_text(inputs['planned_sdk_info'])
    private = root / '.local/certificates/private'
    profile = inputs['profile']
    tree = inputs['profiles_tree']
    for item in tree.getroot().iter('profileitem'):
        for key in ['key', 'ca', 'rootca']:
            value = item.get(key)
            if value:
                folder = private if key == 'key' else private.parent / 'ca'
                item.set(key, str(folder / Path(value).name))
    tree.write(profile, encoding='UTF-8', xml_declaration=True)
    profile.chmod(0o600)
    result = subprocess.run([str(inputs['cli']), 'cli-config', 'default.profiles.path=' + str(profile)], capture_output=True, timeout=30)
    if result.returncode:
        raise SystemExit('SDK signing profile configuration failed.')
    return dist


def sign(inputs, dist):
    cli = inputs['cli']
    signing_profile = inputs['signing_profile']
    password = inputs['password']
    unsigned = dist / 'CleanFrame-unsigned.wgt'
    write_widget_archive(unsigned)
    signed_dir = dist / 'signed'
    signed_dir.mkdir(exist_ok=True)
    command = [str(cli), 'package', '-t', 'wgt', '-s', signing_profile, '-o', str(signed_dir), '--', str(unsigned)]
    pid, terminal = pty.fork()
    if pid == 0:
        os.execv(command[0], command)
    output = b''
    passwords = saves = 0
    deadline = time.monotonic() + 60
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([terminal], [], [], 1)
            if ready:
                try:
                    chunk = os.read(terminal, 8192)
                except OSError:
                    break
                if not chunk:
                    break
                output += chunk
                count = output.lower().count(b'password:')
                if count > passwords:
                    os.write(terminal, password + b'\n')
                    passwords = count
                count = output.count(b'No: (N) ?')
                if count > saves:
                    os.write(terminal, b'n\n')
                    saves = count
        else:
            os.kill(pid, signal.SIGTERM)
            raise SystemExit('SDK signing timed out.')
    finally:
        os.close(terminal)
    os.waitpid(pid, 0)
    redacted = output.replace(password, b'[redacted]').decode(errors='replace')
    if 'is created successfully' not in redacted:
        print(redacted)
        raise SystemExit('SDK did not confirm a signed package.')
    signed = signed_dir / unsigned.name
    with zipfile.ZipFile(signed) as package:
        if not {'author-signature.xml', 'signature1.xml'}.issubset(package.namelist()):
            raise SystemExit('Package is missing its signing files.')
    target = dist / 'CleanFrame.wgt'
    target.write_bytes(signed.read_bytes())
    print('Signed widget created: ' + str(target))


def main():
    inputs = check_inputs()
    dist = prepare(inputs)
    sign(inputs, dist)


if __name__ == '__main__':
    main()
