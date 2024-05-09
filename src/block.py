import json
from utils import *


class Transaction:
    def __init__(self, user_name, transaction_type, timestamp, signature):
        self.user_name = user_name
        self.timestamp = timestamp
        self.transaction_type = transaction_type
        self.signature = signature

    def serialize_transaction(self):
        """
        Store Transaction object data as a json.
        """
        serialized_ts = {
            'transaction_type': self.transaction_type, # 'Register' or 'Transfer
            'user_name': self.user_name,
            'timestamp': self.timestamp,
            'signature': self.signature
        }
        return json.dumps(serialized_ts)


class Register(Transaction):
    def __init__(self, user_name, timestamp, signature, song_name):
        super().__init__(user_name, "Register", timestamp, signature)
        self.song_name = song_name
        self.song_hash = hash_song("songs/" + self.song_name + ".mp3")

    def serialize_transaction(self):
        """
        Store Registration object data as a json.
        """
        serialized_ts = {
            'transaction_type': 'Register', # 'Register' or 'Transfer
            'user_name': self.user_name,
            'timestamp': self.timestamp,
            'song_name': self.song_name,
            'song_hash': self.song_hash,
            'signature': self.signature
        }
        return json.dumps(serialized_ts)
    
    def __str__(self):
        return f"User : {self.user_name} registered."


class Transfer(Transaction):
    def __init__(self, user_name, song_path, timestamp, signature):
        super().__init__(user_name, song_path, timestamp, signature)

    def serialize_transaction(self):
        """
        Store Transfer object data as a json.
        """
        serialized_ts = {
            'user_name': self.user_name,
            'timestamp': self.timestamp,
            'song_path': self.song_path,
            'song_hash': self.song_hash,
            'signature': self.signature
        }
        return json.dumps(serialized_ts)
    
    def __str__(self):
        return f"User : {self.user_name} transferred a song."


class Block:
    def __init__(self, index, timestamp, transaction:str, previous_hash:str, signature:str, difficulty:str, nonce=0, mine_time=-1):
        self.index = index
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce 
        self.mine_time = mine_time
        self.signature = signature
        self.difficulty = difficulty

        # Body of the block
        self.data = transaction
        self.hash = self.calc_hash()

        # Not used for now
        self.mrkl_root = calc_mrkl_root(transaction)

    def calc_hash(self):
        """
        Calculate the hash of the block's data
        """
        return sha256(
            (str(self.index) + str(self.timestamp) + str(self.previous_hash) +\
             str(self.nonce) + self.data).encode()).hexdigest()

    def serialize_block(self):
        """
        Store Block object data as a json
        """
        self.hash = self.calc_hash() # Update the hash before serialization.
        serialized_blk = {
            'hash':         self.hash,
            'index':        str(self.index),
            'timestamp':    str(self.timestamp),
            'mine_time':    str(self.mine_time),
            'data':         self.data,
            'previous_hash':self.previous_hash,
            'signature':    self.signature,
            'difficulty':   self.difficulty,
            'nonce':        str(self.nonce)
        }
        return json.dumps(serialized_blk)
    
    def mine(self):
        '''
        Proof of Work. 
        Loop till it finds a hash that starts with {self.difficulty} number of zeros.
        '''

        while True:
            self.hash = self.calc_hash()
            if meet_hash_criteria(self.hash, self.difficulty):
                break
            self.nonce += 1
        self.mine_time = time_difference(self.timestamp, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))

    