from base64 import b64encode
import errno
from hashlib import md5
from hashlib import sha1
import logging
from socket import error as SocketError
from socketserver import TCPServer
from socketserver import ThreadingMixIn
from socketserver import StreamRequestHandler
import struct

'''
+-+-+-+-+-------+-+-------------+-------------------------------+
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)     |            (16/64)            |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+ - - - - - - - - - - - - - - - +
|    Extended payload length continued, if payload len == 127   |
+ - - - - - - - - - - - - - - - +-------------------------------+
|                   Payload Data continued ...                  |
+---------------------------------------------------------------+
'''

logger = logging.getLogger(__name__)
logging.basicConfig()

FIN                 = 0x80
OPCODE              = 0x0f
MASKED              = 0x80
PAYLOAD_LEN         = 0x7f
PAYLOAD_LEN_EXT16   = 0x7e
PAYLOAD_LEN_EXT64   = 0x7f

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT         = 0x1
OPCODE_BINARY       = 0x2
OPCODE_CLOSE_CONN   = 0x8
OPCODE_PING         = 0x9
OPCODE_PONG         = 0xA

# Function for encoding data to UTF-8
def encodeUTF8(data):
    try:
        return data.encode('UTF-8')
    except UnicodeEncodeError as e:
        logger.error("Encoding error -- %s" % e)
        return False
    except Exception as e:
        raise(e)
        return False

# Function for decoding data from UTF-8
def decodeUTF8(data):
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        logger.error("Decoding error -- %s" % e)
        return False
    except Exception as e:
        raise(e)

# Class for websocket client
class WebsocketClient():
    # function to make the client run indefinitely
    def run_forever(self):
        try:
            logger.info("Listening on port %d for clients.." % self.port)
            self.serve_forever()
        except KeyboardInterrupt:
            self.server_close()
            logger.info("Server terminated.")
        except Exception as e:
            logger.error(str(e), exc_info=True)
            exit(1)

    # function for connecting client
    def new_client(self, client, server):
        pass

    # function for disconnecting client
    def client_left(self, client, server):
        pass

    # function for receiving message
    def message_received(self, client, server, message):
        pass

    # function for connecting client
    def set_fn_new_client(self, client):
        self.new_client = client

    # function for disconnecting client
    def set_fn_client_left(self, client):
        self.client_left = client

    # function for receiving message
    def set_fn_message_received(self, message):
        self.message_received = message

    # function for returning response to one client
    def send_message(self, client, message):
        self._unicast_(client, message)

    # function for returning response to all client
    def send_message_to_all(self, message):
        self._multicast_(message)

# Class for websocket server
class WebsocketServer(TCPServer, WebsocketClient):
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
    def _message_received_(self, handler, message):
        received_messaged = message.decode('utf8')

        if '!echo' in received_messaged:
            self.send_message(received_messaged[6:])

    # Function for receiving ping message
    def _ping_received_(self, handler, message):
        handler.send_pong(message)

    # Function for receiving pong message
    def _pong_received_(self, handler, message):
        pass

    # Function for receiving binary message
    def _binary_received_(self, handler, message):
        pass

    # Function for creating new websocket client
    def _new_client_(self, handler):
        self.counter += 1
        client = {
            'id': self.counter,
            'handler': handler,
            'address': handler.client_address
        }
        self.clients.append(client)
        self.new_client(client, self)

    # Function for removing disconnected websocket client
    def _client_left_(self, handler):
        client = self.handler_to_client(handler)
        self.client_left(client, self)

        if client in self.clients:
            self.clients.remove(client)

    # Function to send response to one client
    def _unicast_(self, to_client, message):
        to_client['handler'].send_message(message)

    # Function to send response to all client
    def _multicast_(self, message):
        for client in self.clients:
            self._unicast_(client, message)

    #
    def handler_to_client(self, handler):
        for client in self.clients:
            if client['handler'] == handler:
                return client

# Class for websocket handler
class WebSocketHandler(StreamRequestHandler):
    # Websocket handler initiator
    def __init__(self, socket, address, server):
        self.server = server
        StreamRequestHandler.__init__(self, socket, address, server)

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
                self.read_next_message()

    # Function to read bytes
    def read_bytes(self, num):
        bytes = self.rfile.read(num)
        return bytes

    # Function to handle received message
    def read_next_message(self):
        try:
            b1, b2 = self.read_bytes(2)
        except SocketError as e:
            if e.errno == errno.ECONNRESET:
                logger.info("Client closed connection.")
                self.keep_alive = 0
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
            self.keep_alive = 0
            return

        if opcode == OPCODE_CONTINUATION:
            logger.warn("Continuation frames are not supported.")
            return
        elif opcode == OPCODE_BINARY:
            pass
        elif opcode == OPCODE_TEXT:
            opcode_handler = self.server._message_received_
        elif opcode == OPCODE_PING:
            opcode_handler = self.server._ping_received_
        elif opcode == OPCODE_PONG:
            opcode_handler = self.server._pong_received_
        else:
            logger.warn("Unknown opcode %#x." % opcode)
            self.keep_alive = 0
            return

        solution_payload_length = 65536 - 1 - 1

        if payload_length == 126:
            solution_payload_length -= 2
            payload_length = struct.unpack(">H", self.rfile.read(2))[0]
        elif payload_length == 127:
            solution_payload_length -= 8
            payload_length = struct.unpack(">Q", self.rfile.read(8))[0]

        masks = self.read_bytes(4)
        message_bytes = bytearray()

        for message_byte in self.read_bytes(payload_length):
            message_byte ^= masks[len(message_bytes) % 4]
            message_bytes.append(message_byte)

        if opcode == OPCODE_TEXT:
            received_messaged = message_bytes.decode('utf8')

            if '!echo' in received_messaged:
                self.send_message(received_messaged[6:])
            elif '!submission' in received_messaged:
                payload = bytearray()

                with open('data3.zip', 'rb') as file:
                    while True:
                        byte = file.read(1)

                        if byte == b"":
                            break

                        payload.extend(byte)

                self.send_binary(payload)

        if opcode == OPCODE_BINARY:
            received_messaged = message_bytes

            with open('data2.zip', 'wb') as file:
                file.write(received_messaged);

            file.close()
            hash1 = md5(open('data2.zip','rb').read()).hexdigest()
            hash2 = md5(open('data3.zip','rb').read()).hexdigest()

            if hash1.lower() == hash2.lower():
                self.send_message("1")
            else:
                self.send_message("0")

    # Function to handle sending message (default message type = text)
    def send_message(self, message):
        self.send_text(message)

    # Function to handle sending pong
    def send_pong(self, message):
        self.send_text(message, OPCODE_PONG)

    # Function to handle sending text message
    def send_text(self, message, opcode=OPCODE_TEXT):
        if isinstance(message, bytes):
            message = decodeUTF8(message)  # this is slower but ensures we have UTF-8

            if not message:
                logger.warning("Can\'t send message, message is not valid UTF-8")
                return False
        elif sys.version_info < (3,0) and (isinstance(message, str) or isinstance(message, unicode)):
            pass
        elif isinstance(message, str):
            pass
        else:
            logger.warning('Can\'t send message, message has to be a string or bytes. Given type is %s' % type(message))
            return False

        header  = bytearray()
        payload = encodeUTF8(message)
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
            raise Exception("Message is too big. Consider breaking it into chunks.")
            return

        self.request.send(header + payload)

    # Function to handle sending binary message
    def send_binary(self, message, opcode=OPCODE_BINARY):
        header  = bytearray()
        payload = message
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
            raise Exception("Message is too big. Consider breaking it into chunks.")
            return

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
            logger.warning("Client tried to connect but was missing a key")
            self.keep_alive = False
            return

        response = self.make_handshake_response(key)
        self.handshake_done = self.request.send(response.encode())
        self.valid_client = True
        self.server._new_client_(self)

    # Function to handle handshake response
    @classmethod
    def make_handshake_response(cls, key):
        return \
          'HTTP/1.1 101 Switching Protocols\r\n'\
          'Upgrade: websocket\r\n'              \
          'Connection: Upgrade\r\n'             \
          'Sec-WebSocket-Accept: %s\r\n'        \
          '\r\n' % cls.calculate_response_key(key)

    # Function to handle handshake response key
    @classmethod
    def calculate_response_key(cls, key):
        GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        hash = sha1(key.encode() + GUID.encode())
        response_key = b64encode(hash.digest()).strip()
        return response_key.decode('ASCII')

    # Function to handle disconnected client
    def finish(self):
        self.server._client_left_(self)