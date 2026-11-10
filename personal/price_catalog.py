"""Package public rates without PowerShell's case-insensitive JSON conversion."""
import argparse
import datetime as dt
import json
import pathlib
import urllib.request

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
    args = parser.parse_args()
    if args.inspect:
        artifact = json.loads(args.output.read_text(encoding='utf-8-sig'))
    elif args.artifact:
        original = json.loads(args.artifact.read_text(encoding='utf-8-sig'))
        metadata(original)
        artifact = prepare(original['catalog'], original['fetched_at_unix_ms'])
    else:
        with urllib.request.urlopen('https://models.dev/api.json', timeout=30) as response:
            artifact = prepare(json.load(response), int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000))
    if not args.inspect:
        args.output.write_text(json.dumps(artifact, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(json.dumps(metadata(artifact)))

if __name__ == '__main__':
    main()
