#!/usr/bin/env python3
import random; random.seed()

from main import Repository, start_scream_routine, start_listeningto_screams, build_http_server

__author__ = "Simone Pandolfi <simopandolfi@gmail.com>"
__version__ = (1, 0, 0)

if __name__ == "__main__":
    repo = Repository({'role': 'SERVICE_{0}'.format(random.randint(1, 10))})
    start_scream_routine(repo)
    start_listeningto_screams(repo, lambda payload: isinstance(payload, dict) and 'role' in payload)
    httpd = build_http_server(repo)
    httpd.start()
