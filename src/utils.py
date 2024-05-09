from hashlib import sha256
from datetime import datetime

record = False

def time_difference(start_time_str, end_time_str):
    '''
    Calculates the time difference between two datetime strings.
    '''
    time_format = "%m/%d/%Y, %H:%M:%S"

    start_time = datetime.strptime(start_time_str, time_format)
    end_time = datetime.strptime(end_time_str, time_format)
    
    delta = end_time - start_time
    return delta.total_seconds()

def switch_difficulty(mine_time:float, curr_difficulty:str):
    '''
    Switches the difficulty level based on the mining time.
    '''

    if float(mine_time) < 10:
        if curr_difficulty == "easy":
            print("Difficulty level switched from easy to medium")
            curr_difficulty = "medium"
        elif curr_difficulty == "medium":
            print("Difficulty level switched from medium to hard")
            curr_difficulty = "hard"
    if float(mine_time) > 20:
        if curr_difficulty == "medium":
            print("Difficulty level switched from medium to easy")
            curr_difficulty = "easy"
        elif curr_difficulty == "hard":
            print("Difficulty level switched from hard to medium")
            curr_difficulty = "medium"

    return curr_difficulty

def meet_hash_criteria(data, difficulty:str):
    '''
    Checks if the hash of the data meets the difficulty criteria.

    Difficulty Level     Criteria
    'easy'               Hash must start with 5 zeros
    'medium'             Hash must start with '000000', '000001' or '000002'
    'hard'               Hash must start with 6 zeros

    Returns : True if the hash meets the difficulty criteria.
    '''

    if difficulty not in ['easy', 'medium', 'hard']:
        print("Warning : Invalid difficulty level! Using 'easy' as default.")
        return data.startswith('0' * 5)

    if difficulty == 'easy':
        return data.startswith('0' * 5)
    elif difficulty == 'medium':
        return data.startswith('000000') or data.startswith('000001') or data.startswith('000002')
    elif difficulty == 'hard':
        return data.startswith('0' * 6)
    else:
        return False

record = True

def calc_mrkl_root(data):
    '''
    Calculates the merkle root of a list of transactions.
    '''

    if not data:
        return 0

    if type(data) == str:
        data = [data]

    if len(data) == 1:
        return data[0]
    if len(data) % 2 != 0:
        data.append(data[-1])
    new_data = []
    for i in range(0, len(data), 2):
        new_data.append(sha256(data[i].encode() + data[i+1].encode()).hexdigest())
    return calc_mrkl_root(new_data)

def hash_song(filename):
    '''
    Returns the sha256 hash of a song(.mp3 file).
    '''

    sha256_hash = sha256()
    try:
        with open(filename, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except FileNotFoundError:
        return "File not found"
    except Exception as e:
        return f"Errors occur when dealing with {filename}: {str(e)}"