#!/usr/bin/env python3

__author__ = "Simone Pandolfi <simopandolfi@gmail.com>"
__version__ = (1, 0, 0)


PROFILES = {
    "production": {},
    "test": {},
    "development": {
        "broadcast": {
            "port": 8091,
            "ttl": 20,
            "multicast_loop": 1,
        },
        "http": {
            "addr": "0.0.0.0",
            "port": 8080,
        },
    },
}

DEFAULT_PROFILE = 'development'


def setup_profile(name=DEFAULT_PROFILE):
    """ Selects a profile

    :param name: profile name
    :return: None
    """
    if name not in PROFILES:
        raise KeyError('Unknown profile: {0}'.format(name))
    for key, value in PROFILES[name].items():
        globals()[key.upper()] = value


HTTP_HOST = '0.0.0.0'
HTTP_PORT = 8081

UDP_PORT = 8082
UDP_TTL = 20
UPD_MULTICAST_LOOP = 1
