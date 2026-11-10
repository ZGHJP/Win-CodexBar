"""Package public rates without PowerShell's case-insensitive JSON conversion."""
import argparse
import datetime as dt
import json
import pathlib
import urllib.request
import zipfile
import tomllib
import io
import math
import os
import stat

API_URL = 'https://models.dev/api.json'
REPOSITORY_URL = 'https://codeload.github.com/anomalyco/models.dev/zip/refs/heads/dev'

def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0

def text_cost(document):
    cost = document.get('cost', {})
    if number(cost.get('input')) and number(cost.get('output')):
        return cost
    text = cost.get('text', {})
    incoming, outgoing = text.get('input', {}), text.get('output', {})
    if not number(incoming.get('price')) or not number(outgoing.get('price')):
        return None
    result = {'input': incoming['price'], 'output': outgoing['price']}
    cache = incoming.get('cache', {})
    result.update({f'cache_{key}': cache[key] for key in ('read', 'write') if number(cache.get(key))})
    tiers = {}
    for kind, lane in (('input', incoming), ('output', outgoing)):
        for override in lane.get('overrides', []):
            threshold = override.get('when', {}).get('context', {}).get('gt')
            if isinstance(threshold, int) and threshold > 0 and number(override.get('price')):
                tier = tiers.setdefault(threshold, {})
                tier[kind] = override['price']
                if kind == 'input':
                    tier.update({f'cache_{key}': override.get('cache', {})[key] for key in ('read', 'write') if number(override.get('cache', {}).get(key))})
    if len(tiers) > 1:
        return None  # The desktop represents one long-context tier, never guess.
    if tiers:
        threshold, tier = next(iter(tiers.items()))
        if 'input' not in tier or 'output' not in tier:
            return None
        result.update(context_threshold=threshold, context_over_200k=tier)
    return result

def catalog_from_repository(content):
    providers = {}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for info in archive.infolist():
            parts = pathlib.PurePosixPath(info.filename).parts
            if len(parts) != 5 or parts[1] != 'providers' or parts[3] != 'models' or not parts[4].endswith('.toml') or info.file_size > 256_000 or stat.S_ISLNK(info.external_attr >> 16):
                continue
            document = tomllib.loads(archive.read(info).decode('utf-8-sig'))
            cost = text_cost(document)
            if cost is not None:
                provider = parts[2]
                model = pathlib.PurePosixPath(parts[4]).stem
                providers.setdefault(provider, {'id': provider, 'models': {}})['models'][model] = {'id': model, 'cost': cost}
    return {'providers': providers}

def fetch_catalog():
    try:
        with urllib.request.urlopen(API_URL, timeout=15) as response:
            catalog = json.load(response)
        prepare(catalog, 0)
        return catalog, API_URL
    except (OSError, ValueError):
        with urllib.request.urlopen(REPOSITORY_URL, timeout=30) as response:
            content = response.read(32 * 1024 * 1024 + 1)
        if len(content) > 32 * 1024 * 1024:
            raise ValueError('Public source archive exceeds the download budget')
        return catalog_from_repository(content), 'https://github.com/anomalyco/models.dev'

def metadata(artifact):
    if artifact.get('version') != 1 or not isinstance(artifact.get('fetched_at_unix_ms'), int):
        raise ValueError('Invalid public pricing artifact')
    providers = artifact['catalog'].get('providers', artifact['catalog'])
    if not all(isinstance(providers.get(p, {}).get('models'), dict) for p in ('openai', 'anthropic')):
        raise ValueError('Missing public pricing providers')
    return {'version': 1, 'fetched_at_unix_ms': artifact['fetched_at_unix_ms']}

def prepare(catalog, fetched_at):
    providers = catalog.get('providers', catalog)
    artifact = {'version': 1, 'fetched_at_unix_ms': fetched_at, 'catalog': {'providers': providers}}
    metadata(artifact)
    return artifact

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=pathlib.Path)
    parser.add_argument('--artifact', type=pathlib.Path)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    if args.inspect:
        artifact = json.loads(args.output.read_text(encoding='utf-8-sig'))
    elif args.artifact:
        original = json.loads(args.artifact.read_text(encoding='utf-8-sig'))
        metadata(original)
        artifact = prepare(original['catalog'], original['fetched_at_unix_ms'])
    else:
        now = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
        if args.refresh and args.output.exists():
            try:
                old = json.loads(args.output.read_text(encoding='utf-8-sig'))
                age = now - metadata(old)['fetched_at_unix_ms']
                if 0 <= age < 24 * 60 * 60 * 1000:
                    print(json.dumps(metadata(old)))
                    return
            except (OSError, ValueError, KeyError, TypeError):
                pass
        catalog, source = fetch_catalog()
        artifact = prepare(catalog, now)
        artifact['source_url'] = source
    if not args.inspect:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_name(args.output.name + f'.tmp-{os.getpid()}')
        temporary.write_text(json.dumps(artifact, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        os.replace(temporary, args.output)
    print(json.dumps(metadata(artifact)))

if __name__ == '__main__':
    main()
