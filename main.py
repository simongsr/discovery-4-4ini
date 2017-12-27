#!/usr/bin/env python3
import json
import random;

import multiprocessing

random.seed()
import socket
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

import functools

import atexit

import time

import requests
from flask import Flask, request
from flask.json import jsonify
from flask_api import status
from singleton_decorator import singleton

import settings

__author__ = "Simone Pandolfi <simopandolfi@gmail.com>"
__version__ = (1, 0, 0)


# def synchronized(cls):
#     class SynchronizedClass:
#         def __init__(self, *args, **kwargs):
#             self.wrapped_obj = cls(*args, **kwargs)
#             self.__lock = threading.Lock()
#
#         def __getattr__(self, item):
#             obj = getattr(type(self.wrapped_obj), item)
#             if callable(obj) and not isinstance(obj, property):
#                 def hook(*args, **kwargs):
#                     self.__lock.acquire()
#                     result = obj(self.wrapped_obj, *args, **kwargs)
#                     self.__lock.release()
#                     return result if result != self.wrapped_obj else self
#                 return hook
#             self.__lock.acquire()
#             result = self.wrapped_obj.__getattribute__(item)
#             self.__lock.release()
#             return result if result != self.wrapped_obj else self
#     return SynchronizedClass


def get_localhost_external_ipaddress():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    addr = s.getsockname()[0]
    s.close()
    return addr


@singleton
# @synchronized
class Repository:
    def __init__(self, localhost_info):
        self.__addr = get_localhost_external_ipaddress()
        self.__localhost_info = localhost_info
        self.__hosts = {self.__addr: self.__localhost_info}
        self.__lock = threading.Lock()

    @property
    def addr(self):
        return self.__addr

    @property
    def info(self):
        with self.__lock:
            return self.__localhost_info.copy()

    @property
    def hosts(self):
        with self.__lock:
            return self.__hosts.copy()

    def set_hosts(self, info):
        with self.__lock:
            self.__hosts.update(info)

    def del_hosts(self, addr):
        with self.__lock:
            if isinstance(addr, list):
                for addr_ in (a for a in addr if a in self.__hosts):
                    del self.__hosts[addr_]
            elif addr in self.__hosts:
                del self.__hosts[addr]


# ----------------------------------------------------------------------------------------------------------------------


def build_http_server(repository):
    app = Flask(__name__)

    @app.route('/api/info', methods=['POST', 'PUT'])
    def update_hosts():
        repository.set_hosts(request.json)
        return '', status.HTTP_200_OK

    @app.route('/api/info', methods=['GET'])
    def get_hosts():
        result = jsonify(repository.hosts)
        result.status_code = status.HTTP_200_OK
        return result

    @app.route('/api/info', methods=['DELETE'])
    def del_hosts():
        repository.del_hosts(request.json)
        return '', status.HTTP_200_OK

    class Bar:
        def start(self):
            app.run(host=settings.HTTP_HOST, port=settings.HTTP_PORT, threaded=True, debug=True)
    return Bar()


def check_httpd_startup():
    while True:
        try:
            requests.get('http://localhost:{port}/api/info'.format(port=settings.HTTP_PORT))
            return True
        except:
            pass


# ----------------------------------------------------------------------------------------------------------------------


def send_broadcast(data):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, settings.UDP_TTL)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(json.dumps(data).encode('utf-8'), ('<broadcast>', settings.UDP_PORT))
    sock.close()


def scream_routine(repository):
    check_httpd_startup()
    send_broadcast(repository.info)
    while True:
        time.sleep(2 * 60 * random.random() + 20)  # time range [20;120) [s]
        send_broadcast(repository.info)


def start_scream_routine(repository):
    thread = threading.Thread(target=scream_routine, args=(repository, ))
    thread.daemon = True
    thread.start()


# ----------------------------------------------------------------------------------------------------------------------


def manage_scream(sock, repository, validation_func):
    check_httpd_startup()

    def update_network(info):
        current_host = None
        try:
            for host in (h for h in info if h not in ('127.0.0.1', repository.addr)):
                current_host = host
                requests.post('http://{host}:{port}/api/info'.format(host=host, port=settings.HTTP_PORT), json=info)
        except:
            # TODO unreachable host, write to log
            if current_host is not None:
                repository.del_hosts(current_host)
                update_network(repository.info)

    while True:
        payload, host = sock.recvfrom(2048)  # TODO gestire i messaggi più lunghi di 2048 byte
        host, pid = host
        payload = json.loads(payload.decode('utf-8', 'replace'))
        if host not in ('127.0.0.1', repository.addr) and validation_func(payload):
            # updates new entered host
            response = requests.post('http://{host}:{port}/api/info'.format(host=host, port=settings.HTTP_PORT),
                                     json=repository.info)
            if not (status.HTTP_200_OK <= response.status_code < status.HTTP_300_MULTIPLE_CHOICES):
                pass  # TODO an exception occurred, write to log
            # updates local repository
            repository.set_hosts({host: payload})
            # updates hosts which were already in the network
            update_network(repository.info)


def init_udp_server_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, settings.UDP_TTL)
    sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, settings.UPD_MULTICAST_LOOP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except:
        pass  # socket.SO_REUSEPORT is not available
    sock.bind(('', settings.UDP_PORT))
    atexit.register(lambda: sock.close())
    return sock


def start_listeningto_screams(repository, validation_func):
    sock = init_udp_server_socket()
    for _ in range(multiprocessing.cpu_count() * 4):  # avoids requests waiting
        thread = threading.Thread(target=manage_scream, args=(sock, repository, validation_func))
        thread.daemon = True
        thread.start()


# ----------------------------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    repo = Repository({})
    start_scream_routine(repo)
    start_listeningto_screams(repo, lambda buff: True)
    httpd = build_http_server(repo)
    httpd.start()
