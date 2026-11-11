import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import challenge
import discover


class TestCI(unittest.TestCase):
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

    def test_detection_fichier_imbrique_et_espaces(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', '-C', str(root), 'config', 'user.email', 'ci@example.invalid'], check=True)
            subprocess.run(['git', '-C', str(root), 'config', 'user.name', 'CI'], check=True)
            for name in ('Web/Un challenge', 'Web/Autre'):
                (root / name).mkdir(parents=True)
                (root / name / 'challenge.yml').write_text('name: test\n')
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(root), 'commit', '-qm', 'base'], check=True)
            base = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
            (root / 'Web/Un challenge/nouveau').write_text('test')
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(root), 'commit', '-qm', 'changement'], check=True)
            self.assertEqual(discover.discover(root, {'before': base}), ['Web/Un challenge'])
            self.assertEqual(len(discover.discover(root, {'before': '0' * 40})), 2)


if __name__ == '__main__':
    unittest.main()
