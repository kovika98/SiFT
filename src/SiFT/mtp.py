from Crypto import Random
from Crypto.Cipher import AES, PKCS1_OAEP
from SiFT.login import LoginRequest


class MTP:
    encoding = 'utf_8'
    version = b'\x01\x00'
    rsv = b'\x00\x00'
    header_len = 16
    mac_len = 12
    encr_keylen = 256
    LOGIN_REQ = b'\x00\x00'

    def create_header(typ: bytes, len: int, sqn: int, rnd: bytes) -> bytes:
        header = MTP.version + typ
        header += len.to_bytes(2, 'big')
        header += sqn.to_bytes(2, 'big')
        header += rnd + MTP.rsv
        return header

    def verify(msg: bytes) -> bool:
        """Check valid version and length."""

        if msg[0:2] != MTP.version:
            print("Bad MTP version, dropping packet.")
            return False
        if len(msg) != int.from_bytes(msg[4:6], 'big'):
            print("Bad length, dropping packet.")
            return False
        return True


class MTPEntity():
    def __init__(self, host) -> None:
        self.sqn = 1
        self.host = host

    def dissect(self, msg: bytes):
        """Check integrity of the message. If the message is valid, it is dissected, type and 
            important info are returned."""

        if not MTP.verify(msg):
            return None
        header, payload = self.check_integrity(msg)
        if not payload:
            return None

        typ = header[2:4]
        return typ, payload

    def check_integrity(self, msg: bytes):
        header, data = msg[0:MTP.header_len], msg[MTP.header_len:]
        data_len = int.from_bytes(header[4:6], 'big')
        if msg[2:4] == b'\x00\x00':         # login_req
            payload_len = data_len - MTP.mac_len - MTP.encr_keylen - MTP.header_len
            encr_tk = data[-MTP.encr_keylen:]
        else:                               # everything else
            payload_len = data_len - MTP.header_len - MTP.mac_len
        encr_payload = data[0:payload_len]
        authtag = data[payload_len: payload_len + MTP.mac_len]
        if msg[2:4] == b'\x00\x00':         # login_req
            RSA_cipher = PKCS1_OAEP.new(self.host.get_key())
            aes_key = RSA_cipher.decrypt(encr_tk)
        else:
            aes_key = self.host.get_key()
        nonce = msg[6:14]               # sqn + rnd
        AE = AES.new(aes_key, AES.MODE_GCM, nonce=nonce, mac_len=MTP.mac_len)
        try:
            payload = AE.decrypt_and_verify(encr_payload, authtag)
        except Exception as e:
            print("Integrity check failed, droppping packet.")
            return None
        return (header, payload)

    def send(self, transport, data):
        transport.write(data)
        self.sqn += 1

    def create_pdu(self, typ, length, payload, AES_key) -> bytes:
        r = Random.get_random_bytes(6)
        header = MTP.create_header(typ, length, self.sqn, r)
        nonce = self.sqn.to_bytes(2, 'big') + r
        AE = AES.new(AES_key, AES.MODE_GCM, nonce=nonce, mac_len=MTP.mac_len)
        encr_data, authtag = AE.encrypt_and_digest(payload)
        return header + encr_data + authtag


class ClientMTP(MTPEntity):
    def __init__(self, client) -> None:
        super().__init__(client)

    def dissect(self, msg: bytes):
        return super().dissect(msg)

    def send_login_req(self, data, rsakey):
        tk = Random.get_random_bytes(32)
        typ = b'\x00\x00'
        msg_len = MTP.header_len + len(data) + MTP.mac_len + MTP.encr_keylen
        pdu = self.create_pdu(typ, msg_len, data, tk)

        RSAcipher = PKCS1_OAEP.new(rsakey)
        encr_tk = RSAcipher.encrypt(tk)
        self.send(self.host.transport, pdu + encr_tk)

    def send_command_req(self):
        pass


class ServerMTP(MTPEntity):
    def __init__(self, server) -> None:
        super().__init__(server)

    def dissect(self, msg: bytes):
        typ, payload = super().dissect(msg)

        if typ == MTP.LOGIN_REQ:
            return (typ, LoginRequest.from_bytes(payload))

    def send_login_res(self, transport, data):
        pass
