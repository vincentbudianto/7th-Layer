from hashlib import md5
from hashlib import sha1
from base64 import b64encode
from socket import error as SocketError
from socketserver import StreamRequestHandler
import errno
import struct

#BASE FRAMING
FIN    = 0x80
OPCODE = 0x0f
MASKED = 0x80
PAYLOAD_LEN = 0x7f
PAYLOAD_LEN_EXT16 = 0x7e
PAYLOAD_LEN_EXT64 = 0x7f

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT         = 0x1
OPCODE_BINARY       = 0x2
OPCODE_CLOSE_CONN   = 0x8
OPCODE_PING         = 0x9
OPCODE_PONG         = 0xA

# Class for websocket handler
class WebSocketHandler(StreamRequestHandler):
    # Websocket handler initiator
    def __init__(self, socket, addr, server):
        self.server = server
        StreamRequestHandler.__init__(self, socket, addr, server)

    # Websocket handler setting
    def setup(self):
        StreamRequestHandler.setup(self)
        self.running = True
        self.handshaked = False
        self.valid = False

    # Function to check handshake
    def handle(self):
        while self.running:
            if not self.handshaked:
                self.do_handshake()
            elif self.valid:
                self.read_next_message()

    # Function to read bytes
    def read_bytes(self, num):
        bytes = self.rfile.read(num)
        return bytes

    # Function to handle sending binary message
    def send(self, received_payload, opcode=OPCODE_BINARY):
        payload = received_payload

        if isinstance(received_payload, str):
            opcode = OPCODE_TEXT
            payload = payload.encode('UTF-8')

        payload_length = len(payload)
        header = self.create_header_by_payload_length_and_opcode(payload_length, opcode)
        self.request.send(header + payload)

    # Function to get header
    def read_http_headers(self):
        '''
            Header example:

            GET /chat HTTP/1.1
            Host: 127.0.0.1:9001
            Upgrade: websocket
            Connection: Upgrade
            Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
            Sec-WebSocket-Version: 13
        '''
        headers = {}
        http_get = self.rfile.readline().decode().strip()


        while (True):
            header = self.rfile.readline().decode().strip()

            if not header:
                break

            head, value = header.split(':', 1)
            headers[head.lower().strip()] = value.strip()

        return headers

    # Function to handle handshake
    def do_handshake(self):
        headers = self.read_http_headers()

        if not headers['upgrade'].lower() == 'websocket':
            self.running = False
            return

        if not headers['sec-websocket-key']:
            self.running = False
            return

        response = self.create_handshake_response(headers['sec-websocket-key'])
        self.handshaked = self.request.send(response.encode())
        self.valid = True
        self.server._client_(self)

    # Function to handle received message
    def read_next_message(self):
        try:
            b1, b2 = self.read_bytes(2)
        except Exception:
            print("Client closed connection")
            self.running = False
            return

        fin = b1 & FIN
        opcode = b1 & OPCODE
        payload_length = b2 & PAYLOAD_LEN

        if opcode == OPCODE_CLOSE_CONN:
            print("Client asked to close connection")
            self.running = False
            return

        if opcode == OPCODE_CONTINUATION:
            print("Continuation frames are not supported")
            self.running = False
            return

        if payload_length == 126:
            payload_length = struct.unpack(">H", self.rfile.read(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack(">Q", self.rfile.read(8))[0]

        masks = self.read_bytes(4)
        message_bytes = bytearray()

        for message_byte in self.read_bytes(payload_length):
            message_byte ^= masks[len(message_bytes) % 4]
            message_bytes.append(message_byte)

        if opcode == OPCODE_TEXT:
            received_message = message_bytes.decode('utf8')
            if '!echo' in received_message:
                self.send(received_message[6:])
            elif '!submission' in received_message:
                payload = bytearray(open('data3.zip', 'rb').read())
                self.send(payload)

        elif opcode == OPCODE_BINARY:
            received_message = message_bytes
            with open('data2.zip', 'wb') as file:
                file.write(received_message)
            file.close()
            hash1 = md5(open('data2.zip','rb').read()).hexdigest()
            hash2 = md5(open('data3.zip','rb').read()).hexdigest()
            if hash1.lower() == hash2.lower():
                self.send("1")
                return
            self.send("0")

        elif opcode == OPCODE_PING:
            payload = message_bytes
            header = self.create_header_by_payload_length_and_opcode(payload.length(), OPCODE_PONG)
            self.send(header+opcode)


    def create_handshake_response(self, key):
        return \
          'HTTP/1.1 101 Switching Protocols\r\n'\
          'Upgrade: websocket\r\n'              \
          'Connection: Upgrade\r\n'             \
          'Sec-WebSocket-Accept: %s\r\n'        \
          '\r\n' % self.calculate_response(key)

    def calculate_response(self, key):
        GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        hash = sha1(key.encode() + GUID.encode())
        response = b64encode(hash.digest()).strip()
        return response.decode('ASCII')

    # Function to handle disconnected client
    def finish(self):
        self.server._client_disconnect_(self)

	# Function for creating header
    def create_header_by_payload_length_and_opcode(self, payload_length, opcode):
        header = bytearray()

        if payload_length <= 125:
            header.append(FIN | opcode)
            header.append(payload_length)
        elif payload_length >= 126 and payload_length <= 65535:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT16)
            header.extend(struct.pack(">H", payload_length))
        elif payload_length < 18446744073709551616:
            header.append(FIN | opcode)
            header.append(PAYLOAD_LEN_EXT64)
            header.extend(struct.pack(">Q", payload_length))

        return header