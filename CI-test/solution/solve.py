import os
import urllib.request

host = os.environ['CHALLENGE_HOST']
port = os.environ['CHALLENGE_PORT']
with urllib.request.urlopen(f'http://{host}:{port}/', timeout=5) as response:
    if response.status == 200:
        print('flag{ci_test}')
