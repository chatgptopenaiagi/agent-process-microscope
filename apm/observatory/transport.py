"""One bounded JSON request per loopback TCP connection. No pickle or HTTP."""
from __future__ import annotations

import hmac
import json
import secrets
import socket
import socketserver
import sqlite3
import struct
import threading
import time
from uuid import UUID

from apm.storage.memory import canonical

MAX_FRAME = 4 * 1024 * 1024  # response cap; requests have a smaller cap
MAX_REQUEST = 65536


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_json_key')
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError('nonfinite_json')


def receive(sock, cap):
    deadline = time.monotonic() + 3
    def read(n):
        data = bytearray()
        while len(data) < n:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('frame_timeout')
            sock.settimeout(remaining)
            chunk = sock.recv(n-len(data))
            if not chunk:
                raise ValueError('truncated_frame')
            data.extend(chunk)
        return data
    n = struct.unpack('!I', read(4))[0]
    if not 2 <= n <= cap:
        raise ValueError('frame_size')
    return json.loads(read(n), object_pairs_hook=unique, parse_constant=reject_constant)


def send(sock, value):
    data = canonical(value)
    if len(data) > MAX_FRAME:
        raise ValueError('response_size')
    sock.settimeout(3)
    sock.sendall(struct.pack('!I', len(data)) + data)


def request(port, credential, operation, **params):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('port_range')
    message = dict(version=1, credential=credential, operation=operation, params=params)
    if len(canonical(message)) > MAX_REQUEST:
        raise ValueError('request_size')
    with socket.create_connection(('127.0.0.1', port), timeout=3) as sock:
        send(sock, message)
        result = receive(sock, MAX_FRAME)
    if not isinstance(result, dict) or result.get('version') != 1:
        raise ValueError('response_schema')
    if not result.get('ok'):
        raise ValueError(result.get('error', 'receiver_error'))
    return result['result']


class Receiver(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = False
    daemon_threads = False
    block_on_close = True
    request_queue_size = 4

    def __init__(self, memory, grants, port=0):
        """Grants: credential -> {role: reporter|reader, session_id: UUID}.

        Tokens authenticate a capability, not the identity/truth of a producer.
        Filesystem access to capability files is the local trust boundary.
        """
        self.memory = memory
        if not grants or len(grants) > 32:
            raise ValueError('grant_count')
        for credential, grant in grants.items():
            if not isinstance(credential, str) or len(credential) != 64:
                raise ValueError('credential_format')
            bytes.fromhex(credential)
            if grant['role'] not in ('reader', 'reporter'):
                raise ValueError('role')
            UUID(grant['session_id'])
        self.grants = grants
        self.slots = threading.BoundedSemaphore(4)
        self.health = {'accepted': 0, 'rejected': 0, 'busy': 0}
        self.health_lock = threading.Lock()
        super().__init__(('127.0.0.1', port), Handler)

    def count(self, name):
        with self.health_lock:
            self.health[name] += 1

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.count('busy')
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def dispatch(self, message):
        if not isinstance(message, dict) or set(message) != {'version', 'credential', 'operation', 'params'}:
            raise ValueError('request_schema')
        if type(message['version']) is not int or message['version'] != 1:
            raise ValueError('unsupported_protocol')
        credential = message['credential']
        if not isinstance(credential, str) or len(credential) != 64:
            raise ValueError('unauthorized')
        grant = next((g for key, g in self.grants.items() if hmac.compare_digest(key, credential)), None)
        if grant is None:
            raise ValueError('unauthorized')
        params = message['params']; op = message['operation']
        if not isinstance(params, dict):
            raise ValueError('params_schema')
        session = grant['session_id']
        if op in ('append', 'append_batch') and grant['role'] == 'reporter':
            entries = [params] if op == 'append' else params.get('entries')
            if op == 'append_batch' and set(params) != {'entries'}:
                raise ValueError('batch_schema')
            if not isinstance(entries, list) or not 1 <= len(entries) <= 32:
                raise ValueError('batch_bounds')
            for entry in entries:
                if not isinstance(entry, dict) or set(entry) != {'event', 'stream', 'sequence'} or not isinstance(entry['event'], dict):
                    raise ValueError('append_schema')
                if entry['event'].get('session_id') != session:
                    raise ValueError('session_scope')
            # Stable nonsecret capability label; callers cannot claim host provenance.
            import hashlib
            principal = hashlib.sha256(credential.encode()).hexdigest()[:16]
            results = self.memory.append_batch(entries, origin='reporter', principal=principal)
            return results[0] if op == 'append' else results
        if grant['role'] != 'reader':
            raise ValueError('forbidden_operation')
        if op == 'events' and set(params) <= {'after', 'limit', 'search'}:
            return self.memory.events(session, **params)
        if op == 'investigate' and not params:
            return self.memory.investigate(session)
        if op == 'health' and not params:
            with self.health_lock:
                return dict(self.health, protocol=1, scope=session,
                            coverage='Authorized reports only unless a host observer is explicitly attached.')
        raise ValueError('forbidden_operation')


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            result = self.server.dispatch(receive(self.request, MAX_REQUEST))
            self.server.count('accepted')
            response = dict(version=1, ok=True, result=result)
        except (ValueError, TypeError, KeyError, RecursionError, OverflowError, OSError, sqlite3.Error):
            # Neither untrusted payloads nor exception strings enter logs/responses.
            self.server.count('rejected')
            response = dict(version=1, ok=False, error='request_rejected')
        try:
            send(self.request, response)
        except (OSError, ValueError):
            pass
