from block import *
from utils import meet_hash_criteria

class Blockchain:
    def __init__(self, my_ip):
        self.my_ip = my_ip
        self.chain = []
        self.genesis_block()

    def genesis_block(self):
        """
        Creates the genesis block, its data is "Genesis Block"
        and previous_hash is "0". Difficulty is to be set by the user.
        """

        create_time = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        genesis_block = Block(index=0, timestamp=create_time, transaction="Genesis Block", previous_hash="0",\
                              signature="Genesis Block", difficulty='easy')
        genesis_block.mine()
        self.chain.append(genesis_block)

    def add_block(self, block, blk_hash, addr=None):
        """
        Validates the block and adds it to the chain if it is valid.
        This verification process includes:
            - Checking if the proof is valid
            - Checking if the previous_hash is correct

        TODO: Could easily check if the owner is changed. (signature->username)
        """
        last_block = self.chain[-1]
        previous_hash = last_block.calc_hash()

        # Check if the signature is valid.
        if addr and block.signature != sha256(addr.encode('utf-8')).hexdigest():
            print("Received a block but it fails the signature check.")
            return False

        # Check if the block has been tampered.
        elif blk_hash != block.calc_hash():
            print("Received a tampered block.")
            return False

        # Check if the previous hash match
        elif previous_hash != block.previous_hash and last_block.data != "Genesis Block":
            print("Received a block but the previous hash didn't match.")
            return False

        # Check if the PoW is valid.
        elif not meet_hash_criteria(block.hash, block.difficulty):
            print("Received a block with invalid PoW.")
            return False

        # Check if the block is already in the chain.
        for b in self.chain:
            if b.calc_hash() == block.calc_hash():
                print("Block already in the chain.")
                return False

        self.chain.append(block)

        return True

    def is_chain_valid(self):
        """
        Checks if the entire blockchain is valid.
        """
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            if curr.hash != curr.calc_hash():
                return False
            if curr.previous_hash != prev.calc_hash():
                return False
        return True

    def log(self):
        """
        Log the contents of the blockchain in a specific file for each peer.
        """
        with open("../log/Peer {self.my_ip} log.txt", "a") as f:
            f.write(f"\n\n\n")
            f.write(f"==================== Peer {self.my_ip} blockchain ====================\n")
            f.write("Index \t Timestamp \t\t\t Difficulty \t\t Previous_hash \t Nonce \t Hash\n")
            for block in self.chain:               
                header = block.get_header()
                f.write(f"{header['index']} \t {header['timestamp']} \t {header['difficulty']} \t\t {header['previous_hash']} \t {header['nonce']} \t {header['hash']}")