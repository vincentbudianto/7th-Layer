from socketserver import TCPServer, ThreadingMixIn
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

class WebSocketServer(ThreadingMixIn, TCPServer):
    clients = []
    counter = 0
    daemon_threads = True

    # Websocket server initiator
    def __init__(self, port, host):
        server_adrress = (host, port)
        TCPServer.__init__(self, server_adrress, WebSocketHandler)
        self.address = self.socket.getsockname()[0]
        self.port = self.socket.getsockname()[1]

    # Function for creating new websocket client
    def new_client(self, handler):
        self.counter += 1
        client = {'handler': handler, 'id': self.counter}
        self.clients.append(client)
        self.new_client_callback(client)

    # Function for removing disconnected websocket client
    def client_disconnect(self, handler):
        client = self.get_client_by_handler(handler)
        self.client_disconnect_callback(client)

        if client in self.clients:
            self.clients.remove(client)

    # Function to get client with handler
    def get_client_by_handler(self, handler):
        for client in self.clients:
            if client['handler'] != handler:
                continue
            return client

    # function to make the client run indefinitely
    def run(self):
        print("Server is running!")
        print("Host: {}".format(self.address))
        print("Port: {}".format(self.port))
        try:
            self.serve_forever()
        except KeyboardInterrupt:
            self.server_close()

    # function for connecting client
    def set_new_client_callback(self, new_client_callback):
        self.new_client_callback = new_client_callback

    # function for disconnecting client
    def set_client_disconnect_callback(self, callback):
        self.client_disconnect_callback = callback
