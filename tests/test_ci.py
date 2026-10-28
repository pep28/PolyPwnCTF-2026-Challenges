from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts.validate_challenges import validate
from scripts.test_deployments import wait_ready


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'challenge.yml'
        self.data = dict(name='Example', author='Author', category='Web', type='standard', value=1, description='Example', flags=['flag{example}'])

    def check(self, **changes):
        self.path.write_text(yaml.safe_dump(self.data | changes))
        return validate(self.path)

    def test_valid_manifest(self):
        self.assertEqual(self.check(), [])

    def test_invalid_flags(self):
        for flags in ([], [''], [{}], [False], [{'type': 'regex', 'content': '['}]):
            with self.subTest(flags=flags):
                self.assertTrue(self.check(flags=flags))

    def test_structured_flag_and_hint(self):
        self.assertEqual(self.check(flags=[{'type': 'static', 'content': 'flag{x}', 'data': 'case_sensitive'}], hints=[{'content': 'hint', 'cost': 0}]), [])

    def test_invalid_types(self):
        for changes in ({'value': True}, {'value': -1}, {'author': ' '}, {'tags': [1]}, {'hints': [{'content': 'hint', 'cost': -1}]}, {'requirements': False}):
            with self.subTest(changes=changes):
                self.assertTrue(self.check(**changes))

    def test_files(self):
        (self.path.parent / 'handout.txt').write_text('example')
        self.assertEqual(self.check(files=['handout.txt']), [])
        self.assertTrue(self.check(files=['missing.txt']))
        self.assertTrue(self.check(files=['../handout.txt']))
        self.assertTrue(self.check(file=['handout.txt']))

    def test_duplicate_keys(self):
        self.path.write_text(yaml.safe_dump(self.data) + 'value: 2\n')
        self.assertTrue(validate(self.path))

    def test_custom_deployment(self):
        self.assertTrue(self.check(type='zync'))
        self.assertEqual(self.check(type='zync', playbook_name='http', deploy_parameters={'image': 'example', 'unique': False}), [])

    def test_dynamic_scoring(self):
        self.assertTrue(self.check(type='dynamic', extra={'initial': 1, 'decay': 0, 'minimum': 5}))
        self.assertEqual(self.check(type='dynamic', extra={'initial': 100, 'decay': 10, 'minimum': 10}), [])


class ReadinessTests(unittest.TestCase):
    @patch('scripts.test_deployments.inspect', return_value={'State': {'Status': 'exited', 'ExitCode': 1}})
    def test_crashed_container_fails(self, inspect):
        with self.assertRaises(ValueError):
            wait_ready({'web': 'id'}, {'web': [{'port': 80, 'http': '/'}]})

    @patch('scripts.test_deployments.inspect', return_value={'State': {'Status': 'running'}})
    def test_running_without_probe_fails(self, inspect):
        with self.assertRaises(ValueError):
            wait_ready({'web': 'id'}, {'web': []})


if __name__ == '__main__':
    unittest.main()
