import unittest
import io
import zipfile
import urllib.error
from unittest.mock import patch
from price_catalog import prepare, metadata, catalog_from_repository, fetch_catalog, API_URL, REPOSITORY_URL

class PublicPricingTest(unittest.TestCase):
    def test_preserves_case_sensitive_model_ids_and_real_fetch_time(self):
        providers = {'openai': {'models': {'Model': {'id': 'Model'}, 'model': {'id': 'model'}}}, 'anthropic': {'models': {}}}
        result = prepare(providers, 123456)
        self.assertEqual(list(result['catalog']['providers']['openai']['models']), ['Model', 'model'])
        self.assertEqual(metadata(result)['fetched_at_unix_ms'], 123456)

    def test_rejects_non_catalog_input(self):
        with self.assertRaises(ValueError):
            prepare({'account': 'must not package'}, 123)

    def archive(self):
        content = io.BytesIO()
        with zipfile.ZipFile(content, 'w') as archive:
            archive.writestr('repo/providers/openai/models/example.toml', '''
[cost.text.input]
price = 2
cache = {read = 0.1}
[[cost.text.input.overrides]]
when = {context = {gt = 272000}}
price = 4
cache = {read = 0.2}
[cost.text.output]
price = 10
[[cost.text.output.overrides]]
when = {context = {gt = 272000}}
price = 15
''')
            archive.writestr('repo/providers/anthropic/models/example.toml', '[cost]\ninput = 3\noutput = 15\n')
        return content.getvalue()

    def test_repository_conversion_keeps_exact_threshold_and_cache_rates(self):
        result = catalog_from_repository(self.archive())
        cost = result['providers']['openai']['models']['example']['cost']
        self.assertEqual(cost['context_threshold'], 272000)
        self.assertEqual(cost['cache_read'], 0.1)
        self.assertEqual(cost['context_over_200k'], {'input': 4, 'output': 15, 'cache_read': 0.2})
        metadata(prepare(result, 123))

    def test_api_403_falls_back_to_official_repository(self):
        with patch('price_catalog.urllib.request.urlopen', side_effect=[
            urllib.error.HTTPError(API_URL, 403, 'Forbidden', {}, None), io.BytesIO(self.archive())
        ]) as download:
            result, source = fetch_catalog()
        self.assertIn('openai', result['providers'])
        self.assertEqual(source, 'https://github.com/anomalyco/models.dev')
        self.assertEqual(download.call_args_list[1].args[0], REPOSITORY_URL)

if __name__ == '__main__':
    unittest.main()
