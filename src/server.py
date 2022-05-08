#!/usr/bin/env python3

import asyncio
import os.path as path
from SiFT.mtp import ServerMTP, MTP, ITCP
from Crypto import Random
import SiFT.login as login
from rsa_keygen import load_keypair
from time import time_ns
import sys
import getopt

HOST = 'localhost'
PORT = 5150
keyfile = None


class Server(asyncio.Protocol, ITCP):
    _sessions = {}

    def __init__(self) -> None:
        super().__init__()
        self.MTP = ServerMTP(self)
        self.homedir = path.abspath("../data")
        self.logins = login.Logins('eznemegyerossalt')
        self.key = load_keypair(keyfile)

    def get_RSA(self):
        return self.key

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport

    def send_TCP(self, data):
        self.transport.write(data)

    def data_received(self, data):
        msg_info = self.MTP.dissect(data)
        if msg_info is None:        # Some error
            self.transport.close()
            return
        self.handle_message(msg_info)

    def handle_message(self, msg_info: tuple):
        typ = msg_info[0]
        if typ == MTP.LOGIN_REQ:
            self.handle_login_req(msg_info[1])

    def handle_login_req(self, req: login.LoginRequest):
        if not req.valid_timestamp(time_ns(), 2):
            self.transport.close()
        if not self.logins.check_login(req.uname, req.pw):
            self.transport.close()
        self.MTP.send_login_res(login.LoginResponse(
            req, Random.get_random_bytes(16)))


async def main():
    # Get a reference to the event loop as we plan to use
    # low-level APIs.
    loop = asyncio.get_running_loop()

    server = await loop.create_server(
        lambda: Server(),
        HOST, PORT)

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'h', ['help'])
    except getopt.GetoptError:
        print('Error: Unknown option detected.')
        print('Type "server.py -h" for help.')
        sys.exit(1)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('Usage:')
            print('  server.py <keyfile>')
            print('  <keyfile> must contain the 2048 bit RSA key of the server.')
            sys.exit(0)

    if len(args) < 1:
        print('Error: Key file name is missing.')
        print('Type "server.py -h" for help.')
        sys.exit(1)
    else:
        keyfile = args[0]
    asyncio.run(main())
