import sys
import time
import math
import socket
import os
from random import uniform
from ast import literal_eval
from threading import Thread
from datetime import datetime

from struct import pack, unpack
from utils import *
from block import Block, Transaction
from blockchain import Blockchain

################################
# Peers are listening on 54321 #
################################

#tracker_addr = ("<tracker_internal_ip_address>", 65432)
tracker_addr = ("172.16.213.130", 65431)
peer_port = 54321

class Peer:
    def __init__(self, stay_time):
        self.my_ip = socket.gethostbyname(socket.gethostname())
        self.connected = False
        self.stay_time = stay_time
        self.peer_port = peer_port
        self.peer_list = []
        self.peer_block_chain = {}  # key: bc sent by each peer. value: # of times they appear. used when initializing and handling conflicts.
        self.tracker_addr = tracker_addr

        self.local_bc_built = False # Set to True when the local bc is built.
        self.conflict_solve = True  # Set to False when received "REQ_CHANGE", set back to True after resolving the conflict.

        # User's information
        self.name = f"{self.my_ip}@4119.com"
        self.signature = sha256(self.my_ip.encode('utf-8')).hexdigest()

        # Initialize the block chain
        self.block_chain = Blockchain(self.my_ip)
        self.transaction_pool = []
        self.curr_difficulty = "medium"
    
    def start(self):
        '''
        Start the peer. The peer first joins the network, then stays for a
        certain amount of time, and finally leaves the network.
        '''
        with open(f"../log/{self.my_ip} peer_list_log.txt", "w") as f:
            f.write(f"Peer : {self.my_ip}, Stay time : {self.stay_time}\n")

        self.join()
        Thread(target=self.listen, daemon=True).start()
        Thread(target=self.heartbeat, daemon=True).start()
        Thread(target=self.make_transaction, daemon=True).start()
        Thread(target=self.start_mine, daemon=True).start()

        time.sleep(self.stay_time)
        self.leave()

    def join(self):
        '''
        When a peer wants to join the network, it first notifies the tracker
        After receiving the active peer list, it requires all the members on
        this list to send it their copy of the block chain, and make its own
        local block chain based on the majority rule.
        '''

        time.sleep(0.8) # Ensure the listen thread is running!!!!
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                print(self.tracker_addr)
                s.connect(self.tracker_addr)
                message = "JOIN"
                self.connected = True
                s.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"Error connecting to Tracker: {e}")

    def listen(self):
        '''
        The peer listens from both the tracker and other peers on a certain port.
        Different message types have corresponding prefixes and are handled differently.
        Below is the message type it can received.

        "PEER_LIST:"  : Peer list from the tracker.
        "NEW_BLOCK:"  : New block from other peers.
        "TRANSACTION:": New transaction made by one peer.
        "REQUEST_BC"  : Request for the block chain. Sent by newly joined peers.
        "RECEIVE_BC:" : Newly joined peer receives bc from others.
        "REQ_CHANGE:" : One peer receives an invalid block, informing the sender.

        TODO: Perhaps use different ports.
        '''

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", self.peer_port))
            s.listen(50)
            print("Stay thread started. Listening .....")

            while True:
                client_socket, addr = s.accept()
                # print(f"Connected to {addr[0]}")
                try:
                    while True:
                        # First get the size of the message so that we know when to stop.
                        size = client_socket.recv(4)
                        if not size:
                            break
                        size = unpack(">I", size)[0]

                        # Receive the message from the client.
                        data = b""
                        while len(data) < size:
                            data += client_socket.recv(size - len(data))
                        data = data.decode()

                        if data:
                            # Received updated peer list from tracker.
                            if data.startswith("PEER_LIST:"): 
                                self.handle_received_pl(data[10:])

                            # Received new block from other peers.
                            elif data.startswith("NEW_BLOCK:"):   
                                self.handle_received_blk(data[10:], addr[0])

                            # Received new transaction from others.
                            elif data.startswith("TRANSACTION:"):
                                self.handle_received_ts(data[12:], addr[0])

                            # Received new peer asking for local blockchain.
                            elif data.startswith("REQUEST_BC"):
                                self.send_block_chain(addr[0])

                            # Received blockchain from others. Used when initializing local bc.
                            elif data.startswith("RECEIVE_BC:"):
                                if not self.local_bc_built:
                                    self.handle_received_bc(data[11:], addr[0])

                            # Received request to modify the local blockchain.
                            elif data.startswith("REQ_CHANGE:"):
                                self.conflict_solve = False
                                self.handle_req_change(data[11:], addr[0])

                            # TODO: Other message types received.
                        else:
                            break
                except Exception as e:
                    print("Error during communication:", e)

    def handle_req_change(self, data:str, addr):
        """
        Handle the request to modify the local blockchain.
        """

        # Check if we know this peer. This has to be done here.
        if addr not in self.peer_list:
            print(f"<!!! WARNING !!!> : Suspicious change request from unknown sender {addr} !")
            # TODO: Send "Who is this???" to the sender. If necessary, inform the tracker to block this ip.
            self.conflict_solve = True
            return
        
        received_bc = self.get_chain_from_data(data)
        print(f"Received request change from {addr}")

        if not self.is_valid_bc(received_bc):
            self.conflict_solve = True
            return

        # Always have a genesis block.
        if len(received_bc) > len(self.block_chain.chain) - 1:
            self.block_chain.chain = [self.block_chain.chain[0]]
            for blk in received_bc:
                self.block_chain.chain.append(blk)
            print(f"Updated local blockchain from {addr} as it's longer.")

        # Use a heuristic method here. If two chains are of the same length, choose the one with the smaller hash.
        elif len(received_bc) == len(self.block_chain.chain) - 1:
            if received_bc[-1].hash < self.block_chain.chain[-1].hash:
                self.block_chain.chain = [self.block_chain.chain[0]]
                for blk in received_bc:
                    self.block_chain.chain.append(blk)
                print(f"Updated local blockchain from {addr} as it's the same length but has smaller hash.")
            else:
                print(f"Received an blockchain from {addr}. Same length, but larger hash. Ignored.")

        else:
            print(f"Received an blockchain from {addr} but it's shorter than the local one. Ignored.")

        # Whatever the final decision is, we are done with the conflict solving.
        self.conflict_solve = True
    
    def is_valid_bc(self, received_bc):
        """
        Checks if the received blockchain is valid.
        """
        if not received_bc:
            print("Received an empty blockchain.")
            return False

        for i in range(1, len(received_bc)):
            curr = received_bc[i]
            prev = received_bc[i - 1]
            if curr.hash != curr.calc_hash() or curr.previous_hash != prev.hash:
                print("Received a blockchain but it might be tampered.")
                print(curr.hash != curr.calc_hash(), curr.previous_hash != prev.hash)
                return False

        return True

    def handle_received_ts(self, data:str, addr):
        """
        Handle the received transaction. Add it to the transaction pool if it's valid.
        """
        # Check if we know this peer. This has to be done here.
        if addr not in self.peer_list:
            print(f"<!!! WARNING !!!> : Suspicious transaction from unknown sender {addr} !")
            # TODO: Send "Who is this???" to the sender. If necessary, inform the tracker to block this ip.
            return

        ts = literal_eval(data)
        ts = Transaction(ts['user_name'], ts['song_path'], ts['timestamp'], ts['signature'])
        self.transaction_pool.append(ts)
        print(f"Received new transaction from {addr}. Transaction pool size : {len(self.transaction_pool)}")

    def handle_received_bc(self, data:str, addr):
        """
        data format : '{"index": "0", "timestamp":  ...  }END'
        Collect the received data in peer_block_chain. If one
        key corresponds to a value that is greater than half 
        of the peer #, go with this and change local_bc_built
        to True, and send it to self.build_chain_from_data().
        """

        print(f"Received a blockchain sent by {addr}")

        peer_number = len(self.peer_list)
        self.peer_block_chain[data] = self.peer_block_chain.get(data, 0) + 1
        if self.peer_block_chain[data] >= math.ceil(peer_number / 2):
            self.local_bc_built = True
            self.peer_block_chain = {} # Clear peer_block_chain.

        block_serial = self.get_chain_from_data(data)
        for blk in block_serial:
            self.block_chain.chain.append(blk)

        print(f"Local blockchain built. Length : {len(self.block_chain.chain)}")

    def get_chain_from_data(self, data:str):
        """
        Build a chain from the received data.
        Data format : '[Block 1][END][Block 2][END] ... [Block N][END]'
        """

        block_serial = []
        block_list = data.split("END")[:-1]
        for b in block_list:
            b = literal_eval(b)
            blk = Block(b['index'], b['timestamp'], b['data'], b['previous_hash'], b['signature'], b['difficulty'], b['nonce'], b['mine_time'])
            block_serial.append(blk)

        return block_serial

    def send_block_chain(self, addr):
        """
        Send the local block chain to the newly joined peer. This does not
        include the genesis block. Place an "END" string at the end of each
        block so that the receiver can parse the blocks and build the chain.

        XXX: We are sending the entire blockchain in one go.
        """

        # There is always a genesis block.
        if len(self.block_chain.chain) == 1:
            print(f"{self.my_ip} has no block chain to send.")
            return

        data = ""
        for blk in self.block_chain.chain[1:]:
            data += blk.serialize_block() + "END"

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # Connect to port 54321!!!!
            s.connect((addr, peer_port))
            message = "RECEIVE_BC:" + data
            s.sendall(pack('>I', len(message)) + message.encode('utf-8'))
            print(f"Sent local blockchain to {addr}. Length : {len(self.block_chain.chain) - 1}")

    def broadcast_block(self, block:str):
        """
        After mining a new block (and proves it's valid), the peer broadcasts
        this serialised block to all other peers.
        """

        for peer in self.peer_list:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect((peer, peer_port))
                    message = "NEW_BLOCK:" + block
                    s.sendall(pack('>I', len(message)) + message.encode('utf-8'))
                    print(f"\n\nSent a block \n\n {block}\n\n")
                except Exception as e:
                    print(f"{self.my_ip} failed to broadcast a block to {peer} : {e}")

    def handle_received_blk(self, block, addr):
        """
        After proving the block is valid, stop mining, add the block
        to the chain and start over.
        """

        # Check if we know this peer. This has to be done here.
        if addr not in self.peer_list:
            print(f"<!!! WARNING !!!> : Suspicious block from unknown sender {addr} !")
            # TODO: Send "Who is this???" to the sender. If necessary, inform the tracker to block this ip.
            return

        block = literal_eval(block)
        blk = Block(index=block['index'], timestamp=block['timestamp'], transaction=block['data'],\
        previous_hash=block['previous_hash'], signature=block['signature'], difficulty=block['difficulty'], nonce=block['nonce'], mine_time=block['mine_time'])
        blk_hash = block['hash']

        #print(f"Hey it's a new block! Size is {len(block)}")
        print(f"\n\nReceived a block from {addr} \n\n {blk.serialize_block()}\n\n")

        if self.block_chain.add_block(blk, blk_hash, addr):
            print(f"{self.my_ip} added a block to local coming from {addr}")
            mine_time = block["mine_time"]
            self.curr_difficulty = switch_difficulty(mine_time, self.curr_difficulty)

        else:
            # print some information about the blocks
            print(f"\n\nLast block index : {self.block_chain.chain[-1].index}, received block index : {blk.index}\n\n")
            data = ""
            for blk in self.block_chain.chain[1:]:
                data += blk.serialize_block() + "END"
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((addr, peer_port))
                message = "REQ_CHANGE:" + data
                s.sendall(pack('>I', len(message)) + message.encode('utf-8'))
                print(f"Sent block chain to {addr}, requesting change.")

    def handle_received_pl(self, data):
        '''
        If it's joining the network, initialize the peer_list, and build a TCP
        connection to all the members. Otherwise, check if the local peer_list
        and the received data differ and update the list.

        NOTE: Normally, len(self.peer_list) = len(received_list) - 1, because
        self.peer_list doesn't include the peer itself.
        '''

        received_list = literal_eval(data)
        print(f"{self.my_ip} received peer list with {len(received_list)} peers.")

        # If peer list is empty, initialize peer list, build connection with them and ask for their bc.
        if not self.peer_list and len(received_list) > 1:
            for peer in received_list:
                if peer != self.my_ip:
                    self.peer_list.append(peer)
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                        try:
                            sock.connect((peer, peer_port))
                            message = 'REQUEST_BC'
                            sock.sendall(pack('>I', len(message)) + message.encode('utf-8'))
                            print(f"Sent request bc message to {peer}")
                        except Exception as e:
                            print(f"Errors when connecting to peers : {e}")
                            sys.exit()

            if record:
                self.log(peer_or_block='peer', to_file=True)

        # An old peer leaves
        elif len(self.peer_list) == len(received_list):
            peer = None
            for peer in self.peer_list:
                if peer not in received_list:
                    self.peer_list.remove(peer)
                    break
            print(f"{self.my_ip} removing {peer} from the its peer list.")

            if record:
                self.log(peer_or_block='peer', to_file=True)

        # A new peer joins. Should always be the last one.
        elif len(self.peer_list) == len(received_list) - 2:
            new_peer = received_list[-1]
            try:
                assert(new_peer not in self.peer_list)
            except AssertionError:
                print(f"{self.my_ip} received a redundant peer : {new_peer}")

            self.peer_list.append(new_peer)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.connect((new_peer, peer_port))
                    # print(f"Connected to {new_peer}")
                except Exception as e:
                    print(f"Failed when trying to connect with {new_peer} : {e}")
                    sys.exit()
            print(f"{new_peer} joined the network.")

            if record:
                self.log(peer_or_block='peer', to_file=True)

        else:
            # This should only happen when initializing.
            try:
                assert(len(received_list) == 1 and received_list[0] == self.my_ip)
            except AssertionError as e:
                print(e)

    def heartbeat(self):
    # Connect to the tracker and send a heartbeat message every 5 seconds.
        time.sleep(5)
        while self.connected:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(self.tracker_addr)
                    message = "KEEPALIVE"
                    s.sendall(message.encode('utf-8'))
                    # print("Sent heartbeat to Tracker")
            except Exception as e:
                print(f"Error connecting to Tracker in heartbeat: {e}")
            time.sleep(5)

    def connect_to_peers(self):
        for peer in self.peer_list:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                try:
                    sock.connect((peer, peer_port))
                    self.peer_sockets[peer] = sock
                except Exception as e:
                    print(f"Errors when connecting to peers : {e}")
                    sys.exit()   
        print(f"{self.my_ip} successfully connected to all peers.")

        if record:
            self.log()

    def leave(self):
        # Send a "LEAVE" message to the tracker. Close all the connections with other peers.
        # Before it leaves, log its local blockchain.
        print(f"{self.my_ip} is leaving the network.")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(self.tracker_addr)
                message = "LEAVE"
                self.connected = False
                s.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"Error leaving the tracker : {e}")

        # Log the blockchain information before leaving.
        self.log(peer_or_block='block', to_file=True)

    def make_transaction(self):
        """
        Make a transaction after a period of time (random number from 5 to 10), and
        broadcast the transaction to all its peers immediately. Transactions contain
        personal information of the creator and the song's metadata.

        TODO: May add transfer of ownership, licensing, etc.
        """

        sleep_time = uniform(5, 10)
        time.sleep(sleep_time)

        # song name is a fixed string for now.
        song_path = "../application/songs/welcome_to_new_york.mp3"

        while self.connected:
            # If we are in conflict solving mode, just wait until it's resolved.
            if not self.conflict_solve:
                continue

            ts = Transaction(self.name, song_path, str(datetime.now()), self.signature)
            self.transaction_pool.append(ts)
            print(f"{self.my_ip} made a transaction. Transaction pool size : {len(self.transaction_pool)}")
            self.broadcast_transaction(ts)
            time.sleep(sleep_time)

    def broadcast_transaction(self, ts):
        for peer in self.peer_list:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect((peer, peer_port))
                    message = "TRANSACTION:" + ts.serialize_transaction()
                    s.sendall(pack('>I', len(message)) + message.encode('utf-8'))
                except Exception as e:
                    print(f"{self.my_ip} failed to broadcast transaction to {peer} : {e}")

    def start_mine(self):
        '''
        Two conditions for a peer to start mining:
            - Every 20 seconds.
            - Transaction pool reaches a certain size (4). (I am using this one)

        NOTE: Consider a block contains only one ts for now. Using a fixed difficulty (medium).
        '''
        while self.connected:
            # If we are in conflict solving mode, just wait until it's resolved.
            if not self.conflict_solve:
                continue
            if len(self.transaction_pool) >= 3:
                ts = self.transaction_pool[0].serialize_transaction()
                create_time = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
                block = Block(index=len(self.block_chain.chain), timestamp=create_time, transaction=ts,\
                        previous_hash=self.block_chain.chain[-1].hash, difficulty=self.curr_difficulty, signature=self.signature)

                start_time = time.time()
                block.mine()

                # If the peer is disconnected during mining, just discard the block.
                if not self.connected:
                    break
                end_time = time.time()
                mine_time = round(end_time - start_time, 2)

                print(f"{self.my_ip} mined a block in {mine_time} seconds.")
                block.mine_time = mine_time

                self.curr_difficulty = switch_difficulty(mine_time, self.curr_difficulty)
                if self.block_chain.add_block(block, block.hash):
                    self.broadcast_block(block.serialize_block())
                    del self.transaction_pool[0]
                else:
                    continue

    def log(self, peer_or_block, to_file=False):
        """
        Log the peer list or the blockchain information.
        """
        if peer_or_block != 'peer' and peer_or_block != 'block':
            print(" Warning : Invalid argument for self.log().")
            return

        if peer_or_block == 'peer':
            # Log the peer list information.
            print(f"\n\n=========== {self.my_ip} log ===========")
            print("Peers")
            print(self.peer_list)
            print(f"========================================\n")

            if to_file:
                with open(f"../log/{self.my_ip} peer_list_log.txt", "a") as f:
                    f.write(f"=========== {self.my_ip} log ===========\n")
                    f.write("Peers\n")
                    f.write(str(self.peer_list) + "\n")
                    f.write("========================================\n")

        elif peer_or_block == 'block':
            # Log the blockchain information.
            # Truncate to last 10 blocks in the terminal if the chain is too long.
            print(f"\n\n\n=========== {self.my_ip} Final Blockchain ===========")
            bc_copy = self.block_chain.chain
            if (len(bc_copy) > 10):
                print("\n\n Blockchain too long, truncating to last 10 blocks.")
                bc_copy = bc_copy[-10:]
            for b in bc_copy:
                print("\n\n", b.serialize_block())

            if to_file:
                with open(f"../log/{self.my_ip} blockchain_log.txt", "w") as f:
                    f.write(f"=========== {self.my_ip} Final Blockchain ===========\n")
                    for b in self.block_chain.chain:
                        f.write(f"\n\n{b.serialize_block()}")
                    f.write("\n\n=======================================================\n")


if __name__ == "__main__":
    # get the stay time from the command line
    stay_time = int(sys.argv[1])

    peer = Peer(stay_time)
    peer.start()