import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import challenge
import discover


class TestCI(unittest.TestCase):
    def test_sortie_standard_separee_des_avertissements(self):
        command = [sys.executable, '-c', 'import sys; print("{}") ; print("avertissement", file=sys.stderr)']
        self.assertEqual(challenge.run(command, capture=True), '{}')

    def test_images_versionnees(self):
        with patch.object(challenge, 'run') as run:
            challenge.check_image('python:3.12')
            run.assert_called_once()
            for image in ('ubuntu:latest', 'alpine:edge', 'python', 'debian:stable-slim'):
                with self.subTest(image=image), self.assertRaises(ValueError):
                    challenge.check_image(image)

    def test_solution_regex(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'solution').mkdir()
            (root / 'solution' / 'solve.py').write_text("print('flag{123}')")
            challenge.solution(root, {'flags': [{'type': 'regex', 'content': r'flag\{[0-9]+\}'}]}, None, None)
            with self.assertRaisesRegex(ValueError, 'aucun flag'):
                challenge.solution(root, {'flags': ['flag{autre}']}, None, None)

    def test_flag_sans_distinction_de_casse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'solution').mkdir()
            (root / 'solution' / 'solve.py').write_text("print('FLAG{TEST}')")
            challenge.solution(root, {'flags': [{'type': 'static', 'content': 'flag{test}', 'data': 'case_insensitive'}]}, None, None)

    def test_documentation_solution_ignoree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'solution').mkdir()
            (root / 'solution/solve.md').write_text('Étapes manuelles')
            challenge.solution(root, {'flags': ['flag{test}']}, None, None)

    def test_ports_manifestes_et_compose(self):
        self.assertEqual(challenge.manifest_ports({'deploy_parameters': {'http_port': 5000, 'published_ports': [8888, '80:8080']}}), [5000, 8080, 8888])
        self.assertEqual(challenge.compose_ports({'ports': [{'target': 5000}], 'expose': ['80/tcp', '53/udp']}, ['8080/tcp']), [80, 5000, 8080])
        self.assertEqual(challenge.service_ports({'deploy_parameters': {}}, 'web'), [])
        self.assertEqual(challenge.service_ports({'deploy_parameters': {'expose': [{'service': 'web', 'port': 8080, 'type': 'http'}]}}, 'web'), [8080])
        self.assertEqual(challenge.selected_ports({}, [8080], [8080], ['80/tcp', '8080/tcp']), [8080])
        self.assertEqual(challenge.selected_ports({}, [], [], ['80/tcp']), [80])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'Dockerfile'
            path.write_text('FROM python:3.12\nEXPOSE 80 8080/tcp 53/udp\n')
            self.assertEqual(challenge.dockerfile_ports(path), [80, 8080])

    def test_image_non_accessible(self):
        with patch.object(challenge, 'run', side_effect=RuntimeError('introuvable')):
            with self.assertRaisesRegex(ValueError, 'introuvable ou privée'):
                challenge.check_image('python:3.12')

    def test_verification_http(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'pret')

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            check = {'port': server.server_port, 'http': '/', 'contains': 'pret'}
            challenge.probe('id', '127.0.0.1', check)
            with self.assertRaises(RuntimeError):
                challenge.probe('id', '127.0.0.1', check | {'contains': 'absent'})
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_detection_fichier_imbrique_et_espaces(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', '-C', str(root), 'config', 'user.email', 'ci@example.invalid'], check=True)
            subprocess.run(['git', '-C', str(root), 'config', 'user.name', 'CI'], check=True)
            for name in ('Web/Un challenge', 'Web/Autre'):
                (root / name).mkdir(parents=True)
                (root / name / 'challenge.yml').write_text('name: test\n')
            (root / 'Web/Autre/.challenge-ci.yml').write_text('stack: Web/Un challenge\n')
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(root), 'commit', '-qm', 'base'], check=True)
            base = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
            (root / 'Web/Un challenge/nouveau').write_text('test')
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(root), 'commit', '-qm', 'changement'], check=True)
            self.assertEqual(discover.discover(root, {'before': base}), ['Web/Autre', 'Web/Un challenge'])
            self.assertEqual(len(discover.discover(root, {'before': '0' * 40})), 2)
            with patch.dict(os.environ, {'TOUS': 'true'}):
                self.assertEqual(len(discover.discover(root, {'before': base})), 2)


if __name__ == '__main__':
    unittest.main()
