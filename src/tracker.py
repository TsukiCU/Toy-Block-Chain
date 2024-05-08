import time
import socket
from struct import pack
from threading import Thread, Lock

class Tracker:
    def __init__(self, host='0.0.0.0', port=65431):
        self.host = host
        self.port = port
        self.peers = {}   # {"peer_ip" : last_response}
        self.lock = Lock()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()

    def start(self):
        """
        Starts the tracker and listens for peers to join.
        """
        print(f"Tracker starts on port {self.port}")

        Thread(target=self.listening_thread).start()
        Thread(target=self.heartbeat_thread).start()

    def listening_thread(self):
        """
        The tracker listens for peers on a certain port.
        """
        while True:
            client_socket, client_addr = self.server_socket.accept()
            addr = client_addr[0]
            Thread(target=self.handle_peer, args=(client_socket, addr)).start()

    def handle_peer(self, client_socket, addr):
        """
        The tracker listens for peers. 
        Different message types have corresponding prefixes and are handled differently.
        Below is the message type it can receive.

        "JOIN" : A new peer requests a connection.
        "KEEPALIVE" : A peer requests to maintain a connection.
        "LEAVE" : A peer requests to end a connection.
        """
        while True:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    break

                # if received 'JOIN', register a new peer.
                if data.startswith('JOIN'):
                    self.register_peer(addr)

                # if received "KEEPALIVE", update the heartbeat dict.
                elif data.startswith('KEEPALIVE'):
                    self.update_heartbeat(addr)

                # if received "LEAVE", remove this peer.
                elif data.startswith('LEAVE'):
                    self.remove_peer(addr)

            except Exception as e:
                print("Error handling peer:", e)
                break

        client_socket.close()

    def register_peer(self, addr):
        """
        Adds a peer to the network of peers.
        """
        with self.lock:
            self.peers[addr] = time.time()
        print(f"Registered a peer {addr} ")
        self.broadcast_peers()

    def update_heartbeat(self, addr):
        """
        Updates the time of the peer in the network.
        """
        with self.lock:
            if addr not in self.peers:
            # This is weird, but let's add it to the list anyway.
                print(f"Peer {addr} rejoins")
            self.peers[addr] = time.time()

    def remove_peer(self, addr):
        """
        Removes a peer from the network of peers.
        """
        with self.lock:
            if addr in self.peers:
                del self.peers[addr]
        print(f"Removed a peer {addr} ")
        self.broadcast_peers()

    def broadcast_peers(self):
        """
        Sends an updated peer list to all peers.
        """
        with self.lock:
            message = "PEER_LIST:" + str(list(self.peers.keys()))
        for peer in self.peers:
            print(f"sent to {peer}")
            self.send_message(peer, message)

    def send_message(self, peer_addr, message):
        """
        Sends specific message to a specific peer in the network of peers.
        """
        # Create a new socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # peer addr should be (host, port), assume peers are listening on port 54321 for tracker's message.
                s.connect((peer_addr, 54321))
                s.sendall(pack('>I', len(message)) + message.encode())
        
        except Exception as e:
            print(f"Failed to send message to peer: {peer_addr}, {e}")

    def heartbeat_thread(self):
        """
        Confirms that peers are active; if not, removes them from the network.
        """
        while True:
            time.sleep(10)  # Check every 10 seconds
            current_time = time.time()
            if not self.peers:
                continue
            to_remove = []
            with self.lock:
                for peer, last_seen in self.peers.items():
                    if current_time - last_seen > 20:  # 20 seconds timeout
                        to_remove.append(peer)
            for peer in to_remove:
                self.remove_peer(peer)


if __name__ == "__main__":
    tracker = Tracker()
    tracker.start()
