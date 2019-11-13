from WebSocketServer import WebSocketServer

def new_client_callback(client):
	print("New client just connected! ID:{}".format(client['id']))

def client_disconnect_callback(client):
	print("Client disconnected! ID:{}".format(client['id']))

def main():
	PORT=9001
	HOST='0.0.0.0'
	server = WebSocketServer(PORT, HOST)
	server.set_new_client_callback(new_client_callback)
	server.set_client_disconnect_callback(client_disconnect_callback)
	server.run()

if __name__ == "__main__":
	main()