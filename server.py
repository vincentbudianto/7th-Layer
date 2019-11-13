from WebSocketServer import WebSocketServer

def client(client, server):
	print("New client. Id: %d" % client['id'])

def client_disconnect(client, server):
	print("Client %d disconnected" % client['id'])

def main():
	PORT=9001
	HOST='0.0.0.0'
	server = WebSocketServer(PORT, HOST)
	server.set_client(client)
	server.set_client_disconnect(client_disconnect)
	server.run()

if __name__ == "__main__":
	main()