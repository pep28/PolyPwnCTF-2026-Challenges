from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
import tempfile
import threading
import unittest
from unittest.mock import patch

import yaml

from scripts.validate_challenges import validate
from scripts.test_deployments import probe, wait_ready


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

    def test_legacy_compose(self):
        params = {'expose': [{'service': 'web', 'port': 80, 'type': 'http'}]}
        self.assertTrue(self.check(type='zync', deploy_parameters=params))
        (self.path.parent / 'compose.yaml').write_text('services: {web: {image: example}}')
        self.assertEqual(self.check(type='zync', deploy_parameters=params), [])


class ReadinessTests(unittest.TestCase):
    @patch('scripts.test_deployments.inspect', return_value={'State': {'Status': 'exited', 'ExitCode': 1}})
    def test_crashed_container_fails(self, inspect):
        with self.assertRaises(ValueError):
            wait_ready({'web': 'id'}, {'web': [{'port': 80, 'http': '/'}]})

    @patch('scripts.test_deployments.inspect', return_value={'State': {'Status': 'running'}})
    def test_running_without_probe_fails(self, inspect):
        with self.assertRaises(ValueError):
            wait_ready({'web': 'id'}, {'web': []})

    @patch('scripts.test_deployments.inspect', return_value={'NetworkSettings': {'Networks': {'test': {'IPAddress': '127.0.0.1'}}}})
    def test_http_responses(self, inspect):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(500 if self.path == '/broken' else 200)
                self.end_headers()
                self.wfile.write(b'ready')

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            check = {'port': server.server_port, 'http': '/', 'contains': 'ready'}
            probe('id', check)
            with self.assertRaises(RuntimeError):
                probe('id', check | {'http': '/broken'})
            with self.assertRaises(RuntimeError):
                probe('id', check | {'contains': 'missing'})
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
