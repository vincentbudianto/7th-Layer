from hashlib import md5
from hashlib import sha1
from base64 import b64encode
from socket import error as SocketError
from socketserver import TCPServer
from socketserver import StreamRequestHandler
import errno
import logging
import struct

logger = logging.getLogger(__name__)
logging.basicConfig()

'''
0                   1                   2                   3
0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |             (16/64)           |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|     Extended payload length continued, if payload len == 127  |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                               |Masking-key, if MASK set to 1  |
+-------------------------------+-------------------------------+
| Masking-key (continued)       |          Payload Data         |
+-------------------------------- - - - - - - - - - - - - - - - +
:                     Payload Data continued ...                :
+ - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - +
|                     Payload Data continued ...                |
+---------------------------------------------------------------+
'''

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

# Class for websocket client
class WebSocketClient():
    # function to make the client run indefinitely
    def run(self):
        try:
            logger.info("Server port: %d" % self.port)
            self.serve_forever()
        except KeyboardInterrupt:
            self.server_close()
            logger.info("Server terminated.")
        except Exception as e:
            logger.error(str(e), exc_info=True)
            exit(1)

    # function for connecting client
    def client(self, client, server):
        pass

    # function for disconnecting client
    def client_disconnect(self, client, server):
        pass

    # function for receiving message
    def msg_received(self, client, server, msg):
        pass

    # function for connecting client
    def set_fn_client(self, fn):
        self.client = fn
    
    # function for disconnecting client
    def set_fn_client_disconnect(self, fn):
        self.client_disconnect = fn

    # function for receiving message
    def set_fn_msg_received(self, fn):
        self.msg_received = fn

    # function for returning response to one client
    def send_msg(self, client, msg):
        self._unicast_(client, msg)

class WebsocketServer(TCPServer, WebSocketClient):
    allow_reuse_address = True
    clients = []
    counter = 0
    daemon_threads = True

    # Websocket server initiator
    def __init__(self, port, host='0.0.0.0', loglevel=logging.WARNING):
        logger.setLevel(loglevel)
        TCPServer.__init__(self, (host, port), WebSocketHandler)
        self.port = self.socket.getsockname()[1]

    # Function for receiving !echo message
    def _msg_received_(self, handler, msg):
        received_msg = msg.decode('utf8')

        if '!echo' in received_msg:
            self.send_msg(received_msg[6:])

    # Function for receiving ping message
    def _ping_received_(self, handler, msg):
        handler.send_pong(msg)

    # Function for receiving pong message
    def _pong_received_(self, handler, msg):
        pass

    # Function for receiving binary message
    def _binary_received_(self, handler, msg):
        pass

    # Function for creating new websocket client
    def _client_(self, handler):
        self.counter += 1
        client = {'id': self.counter,'handler': handler,'address': handler.client_address}
        self.clients.append(client)
        self.client(client, self)

    # Function for removing disconnected websocket client
    def _client_disconnect_(self, handler):
        client = self.handler_to_client(handler)
        self.client_disconnect(client, self)

        if client in self.clients:
            self.clients.remove(client)
        
    # Function to send response to one client
    def _unicast_(self, to_client, msg):
        to_client['handler'].send_msg(msg)

    def handler_to_client(self, handler):
        for client in self.clients:
            if client['handler'] == handler:
                return client

# Class for websocket handler
class WebSocketHandler(StreamRequestHandler):
    # Websocket handler initiator
    def __init__(self, socket, addr, server):
        self.server = server
        StreamRequestHandler.__init__(self, socket, addr, server)

    # Websocket handler setting
    def setup(self):
        StreamRequestHandler.setup(self)
        self.keep_alive = True
        self.handshake_done = False
        self.valid_client = False

    # Function to check handshake
    def handle(self):
        while self.keep_alive:
            if not self.handshake_done:
                self.handshake()
            elif self.valid_client:
                self.read_next_msg()
    
    # Function to read bytes
    def read_bytes(self, num):
        bytes = self.rfile.read(num)
        return bytes

    # Function to handle sending text message
    def send_text(self, msg, opcode=OPCODE_TEXT):
        if isinstance(msg, bytes):
            msg = msg.decode('UTF-8')
        
            if not msg:
                logger.warning("Message is not UTF8")
                return False
        elif isinstance(msg, str):
            pass
        else:
            logger.warning("Message has to be string or bytes.")
            return False

        header  = bytearray()
        payload = msg.encode('UTF-8')
        payload_length = len(payload)

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
        else:
            raise Exception("Message is too big. Can't process")
            return

        self.request.send(header + payload)
    
    # Function to handle sending binary message
    def send_binary(self, msg, opcode=OPCODE_BINARY):
        header  = bytearray()
        payload = msg
        payload_length = len(payload)

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
        else:
            raise Exception("Message is too big. Can't process")
            return

        self.request.send(header + payload)

    # Function to handle sending message (default message type = text)
    def send_msg(self, msg):
        self.send_text(msg)

    # Function to handle sending pong
    def send_pong(self, msg):
        self.send_text(msg, OPCODE_PONG)

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
        assert http_get.upper().startswith('GET')

        while True:
            header = self.rfile.readline().decode().strip()

            if not header:
                break

            head, value = header.split(':', 1)
            headers[head.lower().strip()] = value.strip()

        return headers

    # Function to handle handshake
    def handshake(self):
        headers = self.read_http_headers()

        try:
            assert headers['upgrade'].lower() == 'websocket'
        except AssertionError:
            self.keep_alive = False
            return

        try:
            key = headers['sec-websocket-key']
        except KeyError:
            logger.warning("Client is missing a key")
            self.keep_alive = False
            return

        response = self.handshake_response(key)
        self.handshake_done = self.request.send(response.encode())
        self.valid_client = True
        self.server._client_(self)

    # Function to handle received message
    def read_next_msg(self):
        try:
            b1, b2 = self.read_bytes(2)
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                logger.info("Client closed connection.")
                self.keep_alive = False
                return

            b1, b2 = 0, 0
        except ValueError as e:
            b1, b2 = 0, 0
        
        fin = b1 & FIN
        opcode = b1 & OPCODE
        masked = b2 & MASKED
        payload_length = b2 & PAYLOAD_LEN

        if opcode == OPCODE_CLOSE_CONN:
            logger.info("Client asked to close connection.")
            self.keep_alive = False
            return

        if opcode == OPCODE_CONTINUATION:
            logger.warn("Continuation frames are not supported.")
            return
        elif opcode == OPCODE_BINARY:
            pass
        elif opcode == OPCODE_TEXT:
            opcode_handler = self.server._msg_received_
        elif opcode == OPCODE_PING:
            opcode_handler = self.server._ping_received_
        elif opcode == OPCODE_PONG:
            opcode_handler = self.server._pong_received_
        else:
            logger.warn("Unknown opcode %#x." % opcode)
            self.keep_alive = False
            return

        solution_payload_length = 65536-1-1

        if payload_length == 126:
            solution_payload_length -= 2
            payload_length = struct.unpack(">H", self.rfile.read(2))[0]
        elif payload_length == 127:
            solution_payload_length -= 8
            payload_length = struct.unpack(">Q", self.rfile.read(8))[0]

        masks = self.read_bytes(4)
        msg_bytes = bytearray()

        for msg_byte in self.read_bytes(payload_length):
            msg_byte ^= masks[len(msg_bytes) % 4]
            msg_bytes.append(msg_byte)

        if opcode == OPCODE_TEXT:
            received_msg = msg_bytes.decode('utf8')

            if '!echo' in received_msg:
                self.send_msg(received_msg[6:])
            elif '!submission' in received_msg:
                payload = bytearray()
                
                with open('data3.zip', 'rb') as file:
                    while True:
                        byte = file.read(1)

                        if byte == b"":
                            break

                        payload.extend(byte)
                        
                self.send_binary(payload)

        if opcode == OPCODE_BINARY:
            received_msg = msg_bytes

            with open('data2.zip', 'wb') as file:
                file.write(received_msg)

            file.close()
            hash1 = md5(open('data2.zip','rb').read()).hexdigest()
            hash2 = md5(open('data3.zip','rb').read()).hexdigest()

            if hash1.lower() == hash2.lower():
                self.send_msg("1")
            else:
                self.send_msg("0")

    @classmethod
    def handshake_response(cls, key):
        return \
          'HTTP/1.1 101 Switching Protocols\r\n'\
          'Upgrade: websocket\r\n'              \
          'Connection: Upgrade\r\n'             \
          'Sec-WebSocket-Accept: %s\r\n'        \
          '\r\n' % cls.calculate_response(key)

    @classmethod
    def calculate_response(cls, key):
        GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        hash = sha1(key.encode() + GUID.encode())
        response = b64encode(hash.digest()).strip()
        return response.decode('ASCII')

    # Function to handle disconnected client
    def finish(self):
        self.server._client_disconnect_(self)