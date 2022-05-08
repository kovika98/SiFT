from ast import Raise
from SiFT.mtp import ITCP, MTPEntity, MTP
from SiFT.login import LoginRequest
from Crypto.Hash import SHA256


class Command:
    def __init__(self, cmd: str, host) -> None:
        self.cmd = cmd
        self.host = host

    def execute(self):
        mtp: MTPEntity = self.host.MTP
        data = self.cmd.strip().replace(' ', '\n')
        mtp.send_message(MTP.COMMAND_REQ, data.encode(MTP.encoding))
        self.host.cmd_handler.last_sent(data.encode(MTP.encoding))

    def choose_cmd_type(self):
        pass


class CommandHandler:
    def __init__(self, host) -> None:
        self.host = host

    def hash_command(self, command: bytes):
        hashfn = SHA256.new()
        hashfn.update(command)
        hashval = hashfn.hexdigest()
        return hashval

    def last_sent(self, cmd: bytes):
        self.last_cmd_hash = self.hash_command(cmd)

    def handle(self, cmd_b: bytes):
        cmd_str = cmd_b.decode(MTP.encoding)
        l = cmd_str.split('\n')
        command = l[0]
        # if command not in []:
        #       return
        if command == 'pwd':
            self.handle_pwd(cmd_b, l)

    def handle_pwd(self, cmd_b: bytes, l):
        pass


class ServerCommandHandler(CommandHandler):
    def __init__(self, host, dir) -> None:
        super().__init__(host)
        self.rootdir: str = dir
        self.pwd: str = dir

    ##defines what happens when pwd command is executed
    ##when pwd command is valid the correct response packet is created
    ##when pwd command is invalid error is returned
    def handle_pwd(self, cmd_b: bytes, l):
        cmd_s = cmd_b.decode(MTP.encoding)
        hashval = self.hash_command(cmd_b)

        params = cmd_s.split('\n')
        if len(params) == 1:
            status = 'success'
            resp = '\n'.join(['pwd', hashval, status, self.pwd])
        else:
            status = 'failure'
            resp = '\n'.join(['pwd', hashval, status, 'Too many arguments'])
    
        mtp: MTPEntity = self.host.MTP
        mtp.send_message(MTP.COMMAND_RES, resp.encode(MTP.encoding))


class ClientCommandHandler(CommandHandler):
    def __init__(self, host) -> None:
        return super().__init__(host)

    def handle_pwd(self, cmd_b: bytes, l):
        command_str = cmd_b.decode(MTP.encoding)
        l = command_str.split('\n')
        if l[1] != self.last_cmd_hash:
            pass
        if l[2] == 'failure':
            pass
        print(l[3])
