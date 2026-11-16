"""Offline machine/asset/request inspection. Never logs in or submits media."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def located(base, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Path is missing')
    p = Path(value).expanduser()
    return p.resolve() if p.is_absolute() else (base / p).resolve()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


MEDIA_FIELDS = {
    '图片': ('images',),
    '视频': ('video', 'videos', 'referenceVideo', 'referenceVideos'),
    '音频': ('audio', 'audios'),
}
MEDIA_LABEL = re.compile(r'(图片|图|视频|音频|\bimage|\bvideo|\baudio)\s*([0-9]+)(?![0-9a-z]|\.[0-9])', re.I)
LABEL_KIND = {'图': '图片', 'image': '图片', 'video': '视频', 'audio': '音频'}


def media_slots(parameters, errors):
    slots = {}
    for kind, aliases in MEDIA_FIELDS.items():
        fields = [field for field in aliases if field in parameters]
        if len(fields) > 1:
            errors.append(f'{kind}: multiple aliases present; attachment order is ambiguous')
        for field in fields:
            value = parameters[field]
            if field in {'video', 'audio', 'referenceVideo'} and isinstance(value, str):
                items = [(field, value)]
            elif isinstance(value, list):
                items = [(f'{field}[{index}]', item) for index, item in enumerate(value)]
            else:
                errors.append(f'{field}: expected an attachment array or a supported singular URL')
                continue
            for index, (slot, url) in enumerate(items, 1):
                if isinstance(url, str) and url.strip():
                    slots[slot] = (kind, index, url)
                else:
                    errors.append(f'{slot}: expected a nonempty attachment URL')
    return slots


def bound_fingerprint(binding, assets, request_dir):
    asset_id = binding.get('asset_id')
    path = binding.get('path')
    if asset_id and not path and isinstance(asset_id, str) and asset_id in assets:
        return assets[asset_id]
    if path and not asset_id:
        source = located(request_dir, path)
        if source.is_file():
            return digest(source)
        raise ValueError('local attachment file is missing')
    raise ValueError('use a verified asset_id or a local attachment path')


def reviewed_opening(binding, fingerprint, request_dir):
    try:
        review = read(located(request_dir, binding.get('review_file')))
    except (ValueError, OSError):
        return False
    return isinstance(review, dict) and review.get('passed') is True and review.get('sha256') == fingerprint


def check_bindings(request, slots, assets, policy, request_dir, errors):
    bindings = request.get('bindings', [])
    if not isinstance(bindings, list):
        raise ValueError('request.bindings must be an array')
    checked = {}
    opening_passed = False
    for binding in bindings:
        if not isinstance(binding, dict):
            raise ValueError('binding must be an object')
        field = binding.get('field')
        if field == 'video' and 'video[0]' in slots and 'video[1]' not in slots and not policy.get('require_upload_binding'):
            field = 'video[0]'
        if not isinstance(field, str) or field not in slots or field in checked:
            errors.append('binding field is missing, invalid or duplicated in the actual payload')
            continue
        kind, index, url = slots[field]
        label = binding.get('label')
        if label is not None:
            match = MEDIA_LABEL.fullmatch(label.strip().lstrip('@')) if isinstance(label, str) else None
            if not match or (LABEL_KIND.get(match[1].lower(), match[1]), int(match[2])) != (kind, index):
                errors.append(f'{field}: label does not match actual binding index')
        if policy.get('require_upload_binding') or 'uploaded_url' in binding:
            if binding.get('uploaded_url') != url:
                errors.append(f'{field}: actual attachment differs from the recorded upload URL')
        try:
            fingerprint = bound_fingerprint(binding, assets, request_dir)
        except (ValueError, OSError) as exc:
            errors.append(f'{field}: {exc}')
            continue
        if binding.get('sha256') != fingerprint:
            errors.append(f'{field}: fingerprint differs from the verified local file')
        checked[field] = {'field': field, 'asset_id': binding.get('asset_id'), 'sha256': fingerprint}
        if binding.get('purpose') == 'replacement_opening':
            if kind == '图片' and reviewed_opening(binding, fingerprint, request_dir):
                opening_passed = True
            else:
                errors.append(f'{field}: replacement opening needs a passed image review for the same SHA256')
    for field in slots:
        if field not in checked:
            errors.append(f'{field}: missing verified binding')
    return checked, opening_passed


def inspect_request(request_path, assets, policy, errors, warnings, checks):
    request_path = Path(request_path).resolve()
    request = read(request_path)
    if not isinstance(request, dict):
        raise ValueError('request must be an object')
    if 'payload_file' in request and 'payload' in request:
        raise ValueError('use either request.payload_file or request.payload')
    payload = read(located(request_path.parent, request['payload_file'])) if 'payload_file' in request else request.get('payload')
    if not isinstance(payload, dict) or not isinstance(payload.get('parameters'), dict):
        raise ValueError('actual payload and its parameters must be objects')
    parameters = payload['parameters']
    kind = request.get('reference_kind')
    prompt = parameters.get('prompt')
    if kind not in ('images-only', 'video', 'text-only'):
        errors.append('request.reference_kind must be images-only, video or text-only')
    if not isinstance(prompt, str) or not prompt.strip():
        errors.append('actual parameters.prompt missing')
        prompt = ''
    if policy.get('require_native_audio') and parameters.get('generateAudio') is not True:
        silent = request.get('explicit_silent_reason')
        if parameters.get('generateAudio') is False and isinstance(silent, str) and silent.strip():
            warnings.append('Explicit silent exception recorded; operator must verify user instruction')
        else:
            errors.append('native audio policy requires actual generateAudio: true')
    if not isinstance(request.get('sound_plan'), str) or not request['sound_plan'].strip():
        errors.append('sound_plan: record character/action/environment sound and BGM choices')

    ratio = policy.get('aspect_ratio')
    if ratio and parameters.get('aspectRatio') != ratio:
        exception = request.get('aspect_ratio_exception')
        if (isinstance(exception, dict) and parameters.get('aspectRatio')
                and exception.get('value') == parameters['aspectRatio']
                and isinstance(exception.get('basis'), str) and exception['basis'].strip()):
            warnings.append('Aspect ratio exception recorded; operator must verify user instruction')
        else:
            errors.append(f'actual parameters.aspectRatio must match policy {ratio}')
    expected_parameters = request.get('expected_parameters', {})
    if not isinstance(expected_parameters, dict):
        raise ValueError('request.expected_parameters must be an object')
    for field, expected in expected_parameters.items():
        actual = parameters.get(field)
        if field not in parameters or type(actual) is not type(expected) or actual != expected:
            errors.append(f'actual parameters.{field} differs from the planned value')
    if 'expected_model' in request and payload.get('model') != request['expected_model']:
        errors.append('actual model differs from the planned model')

    slots = media_slots(parameters, errors)
    media = {slot[:2] for slot in slots.values()}
    if any(field in payload for fields in MEDIA_FIELDS.values() for field in fields):
        errors.append('attachments must be inside the actual parameters object')
    if kind in ('images-only', 'text-only') and any(key in parameters for key in MEDIA_FIELDS['视频']):
        errors.append('non-video request must omit video fields, including empty fields')
    if kind == 'text-only' and slots:
        errors.append('text-only request must omit media attachments')
    if kind == 'images-only' and (('图片', 1) not in media or parameters.get('roleMode') not in ('reference', 'frame')):
        errors.append('images-only: actual images and explicit reference/frame roleMode required')
    if kind == 'video' and ('视频', 1) not in media:
        errors.append('video reference kind needs an actual video attachment')
    if parameters.get('roleMode') == 'frame' and not request.get('literal_boundary_evidence'):
        errors.append('frame mode needs explicit literal boundary-frame instruction')
    if request.get('previous_task_status') in ('submitted', 'running', 'unknown'):
        errors.append('query the original task before preparing another submission')

    checked, opening_passed = check_bindings(request, slots, assets, policy, request_path.parent, errors)
    for label, number in MEDIA_LABEL.findall(prompt):
        label_kind = LABEL_KIND.get(label.lower(), label)
        if not any(slots[field][:2] == (label_kind, int(number)) for field in checked):
            errors.append(f'{label}{number}: label has no verified attachment at that index')
    if policy.get('require_full_replacement_image'):
        intent = request.get('intent')
        if intent not in ('recreation', 'other'):
            errors.append('intent: identify a recreation or other current production')
        if intent == 'recreation' and not opening_passed:
            exception = request.get('opening_exception')
            if isinstance(exception, str) and exception.strip():
                warnings.append('Opening exception recorded; operator must verify user instruction')
            else:
                errors.append('recreation needs the checked complete replacement opening in the actual image slots')
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    checks.append('Actual payload inspected offline; compare upload receipts; remote URL contents were not authenticated')
    return {'payload_sha256': hashlib.sha256(serialized.encode('utf-8')).hexdigest(),
            'attachments': list(checked.values())}


def inspect(config_path, request_path=None):
    config_path = Path(config_path).resolve()
    config = read(config_path)
    if not isinstance(config, dict):
        raise ValueError('machine configuration must be an object')
    base = config_path.parent
    errors, warnings, checks = [], [], []
    route = config.get('route')
    if route not in {'planning', 'direct-haiyi', 'hypit'}:
        errors.append('route must be planning, direct-haiyi or hypit')
    policy = config.get('policy', {})
    if 'policy_from' in config:
        if 'policy' in config:
            raise ValueError('use either policy or policy_from')
        policy_source = read(located(base, config['policy_from']))
        if not isinstance(policy_source, dict) or 'policy' not in policy_source:
            raise ValueError('policy_from must point to a configuration with a policy object')
        policy = policy_source['policy']
    if not isinstance(policy, dict) or not isinstance(policy.get('require_native_audio'), bool):
        errors.append('policy.require_native_audio must be explicitly true or false')
        policy = {}
    for key in ('require_upload_binding', 'require_full_replacement_image'):
        if key in policy and not isinstance(policy[key], bool):
            errors.append(f'policy.{key} must be true or false')
    try:
        ZoneInfo(config.get('timezone', ''))
    except (ValueError, TypeError, ZoneInfoNotFoundError):
        errors.append('timezone unavailable: use a valid IANA name; install tzdata if needed')
    for key in ('workspace', 'asset_root', 'delivery_root'):
        try:
            p = located(base, config.get(key))
            if not p.is_dir():
                errors.append(f'{key}: directory missing')
            else:
                checks.append(f'{key}: readable directory')
        except ValueError as exc:
            errors.append(f'{key}: {exc}')
    tools = config.get('tools', {})
    if not isinstance(tools, dict):
        raise ValueError('tools must be an object')
    required = [] if route == 'planning' else ['python', 'ffmpeg', 'ffprobe'] if route == 'direct-haiyi' else ['node', 'git', 'ffmpeg', 'ffprobe']
    resolved_tools = {}
    for name in required:
        value = tools.get(name, '')
        exe = None
        if isinstance(value, str) and value:
            if '/' in value or '\\' in value:
                p = located(base, value)
                exe = str(p) if p.is_file() else None
            else:
                exe = shutil.which(value)
        if not exe:
            errors.append(f'tool {name}: not found; configure tools.{name}')
            continue
        resolved_tools[name] = exe
        try:
            result = subprocess.run([exe, '-version' if name in {'ffmpeg', 'ffprobe'} else '--version'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15)
            version = (result.stdout or result.stderr).splitlines()
            if result.returncode:
                errors.append(f'tool {name}: version command failed')
            else:
                checks.append(f'{name}: {version[0] if version else "available"}')
                match = re.search(r'(\d+)\.(\d+)', '\n'.join(version))
                if name == 'python' and (not match or tuple(map(int, match.groups())) < (3, 11)):
                    errors.append('python: requires >=3.11')
                if name == 'node' and (not match or tuple(map(int, match.groups())) < (22, 15)):
                    errors.append('node: requires >=22.15')
        except (OSError, subprocess.TimeoutExpired):
            errors.append(f'tool {name}: cannot run version check')
    entry = config.get('executor', '')
    if route != 'planning':
        if not entry or not located(base, entry).is_file():
            errors.append('executor: entry file missing')
        if not config.get('auth_source'):
            errors.append('auth_source: name the new-machine authorization method, never paste a token')
    if route == 'direct-haiyi' and 'python' in resolved_tools:
        result = subprocess.run([resolved_tools['python'], '-c', 'import requests'], capture_output=True, timeout=15)
        if result.returncode:
            errors.append('direct-haiyi Python requires requests; install into the selected interpreter')

    manifest = read(located(base, config.get('asset_manifest')))
    if not isinstance(manifest, dict) or not isinstance(manifest.get('assets'), list):
        raise ValueError('manifest.assets must be an array')
    root = located(base, config.get('asset_root'))
    assets = {}
    asset_ids = set()
    for asset in manifest.get('assets', []):
        if not isinstance(asset, dict):
            raise ValueError('asset entry must be an object')
        aid = asset.get('id')
        if not isinstance(aid, str) or not aid or aid in asset_ids:
            errors.append('asset id missing or duplicate')
            continue
        asset_ids.add(aid)
        p = located(root, asset.get('path'))
        try:
            p.relative_to(root)
        except ValueError:
            errors.append(f'asset {aid}: path must stay within asset_root')
            continue
        expected = asset.get('sha256', '')
        if not re.fullmatch(r'[0-9a-f]{64}', expected):
            errors.append(f'asset {aid}: expected SHA256 missing or invalid')
        if not p.is_file():
            errors.append(f'asset {aid}: file missing')
        elif digest(p) != expected:
            errors.append(f'asset {aid}: SHA256 mismatch')
        else:
            checks.append(f'asset {aid}: SHA256 matches')
            assets[aid] = expected
        if asset.get('purpose') == 'voice' and asset.get('default_bind') and not asset.get('adoption_evidence'):
            errors.append(f'asset {aid}: default voice binding needs adoption evidence')
    if not assets:
        warnings.append('No assets listed; select approved identities before production')

    inspected = inspect_request(request_path, assets, policy, errors, warnings, checks) if request_path else {}
    return {'ok': not errors, 'offline': True, 'paid_requests': 0, 'errors': errors, 'warnings': warnings,
            'checks': checks, **inspected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, help='Private machine JSON; relative paths resolve beside it')
    parser.add_argument('--request', help='Optional actual-payload handoff JSON; inspected, never submitted')
    args = parser.parse_args()
    try:
        result = inspect(args.config, args.request)
    except (ValueError, OSError, TypeError, KeyError, subprocess.TimeoutExpired) as exc:
        result = {'ok': False, 'offline': True, 'paid_requests': 0, 'errors': [f'Invalid local input: {type(exc).__name__}; check config paths and JSON structure']}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
