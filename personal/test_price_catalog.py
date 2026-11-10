import unittest
from price_catalog import prepare, metadata

class PublicPricingTest(unittest.TestCase):
    def test_preserves_case_sensitive_model_ids_and_real_fetch_time(self):
        providers = {'openai': {'models': {'Model': {'id': 'Model'}, 'model': {'id': 'model'}}}, 'anthropic': {'models': {}}}
        result = prepare(providers, 123456)
        self.assertEqual(list(result['catalog']['providers']['openai']['models']), ['Model', 'model'])
        self.assertEqual(metadata(result)['fetched_at_unix_ms'], 123456)

    def test_rejects_non_catalog_input(self):
        with self.assertRaises(ValueError):
            prepare({'account': 'must not package'}, 123)

if __name__ == '__main__':
    unittest.main()
