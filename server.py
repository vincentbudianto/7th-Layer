from WebSocketServer import WebsocketServer

def client(client, server):
	print("New client. Id: %d" % client['id'])

def client_disconnect(client, server):
	print("Client %d disconnected" % client['id'])

def msg_received(client, server, msg):
	if len(msg) > 200:
		msg = msg[:200]+'..'
	print("Client %d sent: %s" % (client['id'], msg))

def main():
	PORT=9001
	server = WebsocketServer(PORT)
	server.set_fn_client(client)
	server.set_fn_client_disconnect(client_disconnect)
	server.set_fn_msg_received(msg_received)
	server.run()

if __name__ == "__main__":
	main()