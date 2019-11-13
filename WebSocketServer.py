from socketserver import TCPServer
from WebSocketHandler import WebSocketHandler

'''
    Frame format:

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

class WebSocketServer(TCPServer):
    allow_reuse_address = True
    clients = []
    counter = 0
    daemon_threads = True

    # Websocket server initiator
    def __init__(self, port, host):
        TCPServer.__init__(self, (host, port), WebSocketHandler)
        self.address = self.socket.getsockname()[0]
        self.port = self.socket.getsockname()[1]

    # Function for receiving ping message
    def _ping_received_(self, handler, msg):
        handler.send(msg)

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
        self.set_new_client_callback(client)

    # Function for removing disconnected websocket client
    def _client_disconnect_(self, handler):
        client = self.handler_to_client(handler)
        self.client_disconnect(client)

        if client in self.clients:
            self.clients.remove(client)

    # Function to get client with handler
    def handler_to_client(self, handler):
        for client in self.clients:
            if client['handler'] == handler:
                return client

    # function to make the client run indefinitely
    def run(self):
        print("Server is running!")
        print("Host: {}".format(self.address))
        print("Port: {}".format(self.port))
        self.serve_forever()

    # function for connecting client
    def set_new_client_callback(self, new_client_callback):
        self.set_new_client_callback = new_client_callback

    # function for disconnecting client
    def set_client_disconnect_callback(self, callback):
        self.client_disconnect = callback

    # function for returning response to one client
    def send_msg(self, client, message):
        client['handler'].send(message)