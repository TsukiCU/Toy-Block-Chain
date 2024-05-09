import pygame
import sys
import os
from datetime import datetime
sys.path.append("../src")
from ast import literal_eval
from utils import *
from block import *
from peer import Peer
from threading import Thread


class Timer:
    def __init__(self, stay_time):
        self.stay_time = stay_time
        self.start_time = datetime.now()

    def should_leave(self):
        current_time = datetime.now()
        return (current_time - self.start_time).seconds >= self.stay_time

class App(Peer):
    def __init__(self, stay_time=float('inf')):
        super().__init__(stay_time)
        self.black_color = (30, 3, 66)

        # Transaction variables
        self.user_name = ''
        self.song_name = ''
        self.signature = ''
        self.receiver = ''
        self.song = ''

        # Pop up message
        self.show_pop_up = False
        self.error_message = ''
        self.pop_up_timer = None

    def exit_app(self):
        self.leave()
        pygame.quit()
        sys.exit(0)

    def clear_ts_info(self):
        '''
        Clear the transaction info.
        '''
        self.user_name = ''
        self.song_name = ''
        self.signature = ''

    def get_local_blockchain(self):
        '''
        Get the local blockchain.
        '''
        bc_copy = self.block_chain.chain[1:]
        if (len(bc_copy) > 12):
            bc_copy = bc_copy[-12:]
        return bc_copy

    def get_song_info(self, block:Block):
        '''
        Get song's info for displaying it on the main screen.

        Info format : [Author name] created [Song name] on [Timestamp].
        Returns : (author_name, song_name, timestamp) in seconds.
        '''
        ts = literal_eval(block.data)
        author_name = ts['user_name']
        song_name   = ts['song_name']
        timestamp   = datetime.strptime(ts['timestamp'], '%Y-%m-%d %H:%M:%S.%f').strftime('%H:%M:%S')
        return author_name, song_name, timestamp

    def ts_valid_check(self):
        '''
        Check if a transaction is valid.
        '''

        if not self.user_name:
            self.error_message = "User name missing !"
        elif not self.song_name:
            self.error_message = "Song name missing !"
        elif not self.signature:
            self.error_message = "Signature missing !"
        elif self.user_name != self.signature:
            # let's do this for simplicity and assume that signature and user name are the same.
            # It's also better for displaying the songs' information.
            self.error_message = "The name and signature don't match"
        elif not os.path.exists("songs/" + self.song_name + ".mp3"):
            self.error_message = "Song doens't exist, please upload it first."

    def handle_user_input(self, event, user_input):
        '''
        Handle user input.
        '''
        if user_input == 'user_name':
            if event.key == pygame.K_BACKSPACE:
                self.user_name = self.user_name[:-1]
            else:
                self.user_name += event.unicode
        elif user_input == 'song_name':
            if event.key == pygame.K_BACKSPACE:
                self.song_name = self.song_name[:-1]
            else:
                self.song_name += event.unicode
        elif user_input == 'signature':
            if event.key == pygame.K_BACKSPACE:
                self.signature = self.signature[:-1]
            else:
                self.signature += event.unicode

    def handle_transfer_input(self, event, user_input):
        '''
        Handle user input for transferring license
        '''
        if user_input == 'receiver':
            if event.key == pygame.K_BACKSPACE:
                self.receiver = self.receiver[:-1]
            else:
                self.receiver += event.unicode
        elif user_input == 'song':
            if event.key == pygame.K_BACKSPACE:
                self.song = self.song[:-1]
            else:
                self.song += event.unicode

    def get_local_blockchain(self):
        '''
        Return peer's local blockchain
        '''
        return self.block_chain.chain[1:]
    
    def make_app_transaction(self, type:str):
        '''
        Create a new transaction and add it to the transaction pool.
        # FIXME: signature redefined.
        '''
        if type == 'Register':
            new_transaction = Register(self.user_name, str(datetime.now()), self.signature, self.song_name)
            print(f"{self.user_name} registered a song named {self.song_name}. Current pool size : {len(self.transaction_pool)+1}")
        elif type == 'Transfer':
            new_transaction = Transfer(self.user_name, str(datetime.now()), self.signature, self.song_name)
            print(f"{self.user_name} transferred a song named {self.song_name}. Current pool size : {len(self.transaction_pool)+1}")
        self.transaction_pool.append(new_transaction)
        self.broadcast_transaction(new_transaction)
        self.clear_ts_info()

    def draw_main_screen(self, screen, sync=False):
        '''
        Draw the contents of the main screen
        '''
        screen.fill((173, 216, 230))
        # Draw the welcome message at the top
        font = pygame.font.Font("../asset/Sedan.ttf", 30)
        text = font.render("Welcome to the Blockchain - based Song Management", True, self.black_color)
        text_rect = text.get_rect(center=(400, 50))
        screen.blit(text, text_rect)

        # Add three buttons on the left side.
        button_font = pygame.font.Font("../asset/Sedan.ttf", 20)
        button_text = ["Register Song", "Transfer License", "Exit"]
        button_y = 170

        # Register
        register_text = button_text[0]
        register_button = pygame.draw.rect(screen, self.black_color, (50, button_y, 200, 50))
        register_text = button_font.render(register_text, True, (255, 255, 255))
        text_rect1 = register_text.get_rect(center=register_button.center)
        screen.blit(register_text, text_rect1)
        button_y += 130

        # Transfer
        transfer_text = button_text[1]
        transfer_button = pygame.draw.rect(screen, self.black_color, (50, button_y, 200, 50))
        transfer_text = button_font.render(transfer_text, True, (255, 255, 255))
        text_rect2 = transfer_text.get_rect(center=transfer_button.center)
        screen.blit(transfer_text, text_rect2)
        button_y += 130

        # Some other functions
        exit_text = button_text[2]
        exit_button = pygame.draw.rect(screen, (30, 3, 66), (50, button_y, 200, 50))
        exit_text = button_font.render(exit_text, True, (255, 255, 255))
        text_rect3 = exit_text.get_rect(center=exit_button.center)
        screen.blit(exit_text, text_rect3)
        button_y += 130

        # Local blockchain text area
        # TODO: (But will never do lol) Add a scrollbar
        pygame.draw.rect(screen, (255, 255, 255), (325, 150, 450, 360))
        text = font.render("Recent Events", True, self.black_color)
        text_rect = text.get_rect(center=(550, 130))
        screen.blit(text, text_rect)

        # Left bottom corner, a text area showing # of peers.9D4034
        font = pygame.font.Font("../asset/Sedan.ttf", 26)
        text = font.render(f"Current Peers : {len(self.peer_list) + 1}", True, (0x9D, 0x40, 0x34))
        text_rect = text.get_rect(center=(150, 550))
        screen.blit(text, text_rect)

        # Text area borders
        pygame.draw.rect(screen, self.black_color, (325, 150, 450, 360), 2)

        if sync:
            # Fetch the local blockchain to display.
            blockchain = self.get_local_blockchain()
            font = pygame.font.Font('../asset/Sedan.ttf', 19)
            y = 160
            for block in blockchain:
                author_name, song_name, timestamp = self.get_song_info(block)
                text = font.render(f"{author_name} created {song_name} on {timestamp}", True, self.black_color)
                text_rect = text.get_rect(center=(550, y+6))
                pygame.draw.line(screen, (0,0,0), (325, y + 20), (773, y + 20), 2)
                screen.blit(text, text_rect)
                y += 30

        # Add sync button at the bottom.
        sync_button = pygame.draw.rect(screen, (49, 54, 63), (480, 535, 175, 50))
        text = button_font.render("Sync", True, (255, 255, 255))
        text_rect = text.get_rect(center=sync_button.center)
        screen.blit(text, text_rect)

        return register_button, transfer_button, exit_button, sync_button

    def draw_register_screen(self, screen, reset=False):
        '''
        Song registration screen
        '''
        screen.fill((245, 245, 220))
        font = pygame.font.Font("../asset/Sedan.ttf", 28)
        text = font.render("Hello artist !  Please register your song here! ", True, (0, 0, 0))
        text_rect = text.get_rect(center=(400, 40))
        screen.blit(text, text_rect)

        # User clicked on reset, clear the input boxes.
        if reset:
            self.user_name = ''
            self.song_name = ''
            self.signature = ''
            reset = False

        # User name
        font = pygame.font.Font('../asset/Sedan.ttf', 18)
        text = font.render("Your  name  is", True, (0, 0, 0))
        text_rect = text.get_rect(center=(280, 113))
        screen.blit(text, text_rect)
        pygame.draw.rect(screen, (255, 255, 255), (360, 100, 200, 30))

        if self.user_name:
            font = pygame.font.Font('../asset/Sedan.ttf', 18)
            text = font.render(self.user_name, True, (0, 0, 0))
            text_rect = text.get_rect(center=(445, 113))
            screen.blit(text, text_rect)

        # Song name
        text = font.render("Your  song  is ", True, (0, 0, 0))
        text_rect = text.get_rect(center=(280, 213))
        screen.blit(text, text_rect)
        pygame.draw.rect(screen, (255, 255, 255), (360, 200, 200, 30))

        if self.song_name:
            font = pygame.font.Font('../asset/Sedan.ttf', 18)
            text = font.render(self.song_name, True, (0, 0, 0))
            text_rect = text.get_rect(center=(445, 213))
            screen.blit(text, text_rect)

        # Signature
        text = font.render("Sign  here  please", True, (0, 0, 0))
        text_rect = text.get_rect(center=(280, 313))
        screen.blit(text, text_rect)
        pygame.draw.rect(screen, (255, 255, 255), (360, 300, 200, 30))

        if self.signature:
            font = pygame.font.Font('../asset/BodoniFLF-Italic.ttf', 18)
            text = font.render(self.signature, True, (0, 0, 0))
            text_rect = text.get_rect(center=(445, 313))
            screen.blit(text, text_rect)

        # Return button
        return_button = pygame.draw.rect(screen, (49, 54, 63), (240, 400, 100, 50))
        font = pygame.font.Font('../asset/Sedan.ttf', 18)
        text = font.render("Return", True, (255, 255, 255))
        text_rect = text.get_rect(center=return_button.center)
        screen.blit(text, text_rect)

        # Reset button
        reset_button = pygame.draw.rect(screen, (49, 54, 63), (365, 400, 100, 50))
        text = font.render("Reset", True, (255, 255, 255))
        text_rect = text.get_rect(center=reset_button.center)
        screen.blit(text, text_rect)

        # Submit button
        submit_button = pygame.draw.rect(screen, (49, 54, 63), (490, 400, 100, 50))
        text = font.render("Submit", True, (255, 255, 255))
        text_rect = text.get_rect(center=submit_button.center)
        screen.blit(text, text_rect)

        if self.show_pop_up:
            self.pop_up_message(screen, self.error_message)
            pygame.display.update()

        return return_button, reset_button, submit_button, reset

    def pop_up_message(self, screen, message):
        '''
        Shows a pop up message. For simplicity, let the message always appear in
        the center of the screen and stay for 2 seconds.
        '''
        font = pygame.font.Font('../asset/Sedan.ttf', 20)
        popup_rect = pygame.Rect(200, 200, 400, 150)
        pygame.draw.rect(screen, (255, 200, 200), popup_rect)
        pygame.draw.rect(screen, (0, 0, 0), popup_rect, 2)

        text = font.render(message, True, (0, 0, 0))
        text_rect = text.get_rect(center=popup_rect.center)
        screen.blit(text, text_rect)

    def draw_transfer_screen(self, screen, reset=False):
        '''
        Draw the screen for transferring the license
        '''
        screen.fill((245, 245, 220))
        font = pygame.font.Font("../asset/Sedan.ttf", 28)
        text = font.render("Transfer License", True, (0, 0, 0))
        text_rect = text.get_rect(center=(400, 40))
        screen.blit(text, text_rect)

        if reset:
            self.receiver = ''
            self.song = ''
            reset = False

        # Receiver
        font = pygame.font.Font('../asset/Sedan.ttf', 16)
        text = font.render("Receiver", True, (0, 0, 0))
        text_rect = text.get_rect(center=(120, 150))
        screen.blit(text, text_rect)
        pygame.draw.rect(screen, (255, 255, 255), (200, 135, 400, 30))

        if self.receiver:
            font = pygame.font.Font('../asset/Sedan.ttf', 16)
            text = font.render(self.receiver, True, (0, 0, 0))
            text_rect = text.get_rect(center=(445, 150))
            screen.blit(text, text_rect)

        # Song name
        text = font.render("Song Name", True, (0, 0, 0))
        text_rect = text.get_rect(center=(120, 250))
        screen.blit(text, text_rect)
        pygame.draw.rect(screen, (255, 255, 255), (200, 235, 400, 30))
        
        if self.song:
            font = pygame.font.Font('../asset/Sedan.ttf', 16)
            text = font.render(self.song, True, (0, 0, 0))
            text_rect = text.get_rect(center=(445, 250))
            screen.blit(text, text_rect)

        # Transfer button
        transfer_button = pygame.draw.rect(screen, (49, 54, 63), (450, 450, 100, 50))
        text = font.render("Transfer", True, (255, 255, 255))
        text_rect = text.get_rect(center=transfer_button.center)
        screen.blit(text, text_rect)

        # Return button
        return_button = pygame.draw.rect(screen, (49, 54, 63), (150, 450, 100, 50))
        text = font.render("Return", True, (255, 255, 255))
        text_rect = text.get_rect(center=return_button.center)
        screen.blit(text, text_rect)

        # Reset button
        reset_button = pygame.draw.rect(screen, (49, 54, 63), (300, 450, 100, 50))
        text = font.render("Reset", True, (255, 255, 255))
        text_rect = text.get_rect(center=reset_button.center)
        screen.blit(text, text_rect)

        if self.show_pop_up:
            self.pop_up_message(screen, self.error_message)
            pygame.display.update()

        return transfer_button, return_button, reset_button, reset

    def check_transfer(self):
        '''
        Check if the transfer submission is valid.
        '''
        if not self.receiver:
            self.error_message = "Receiver missing !"
            return False
        elif not self.song:
            self.error_message = "Song name missing !"
            return False
        else:
            for block in self.get_local_blockchain():
                transaction = json.loads(block.data)
                if transaction['song_path'] == self.song:
                    if transaction['user_name'] != self.name:
                        self.error_message = "You are not the owner!"
                        return False
                    else:
                        return True
            self.error_message = "Song doesn't exist!"     
        return False
    
    def issue_license_change(self):
        '''
        Change the owner of a song according to the transfer submission.
        '''
        for block in self.get_local_blockchain():
                transaction = json.loads(block.data)
                if transaction['song_path'] == self.song:
                    if transaction['user_name'] == self.name:
                        new_transaction = Transaction(self.receiver, self.song, str(datetime.now()), self.receiver)
                        block.data = new_transaction.serialize_transaction()
        print("Licensing changed")
        self.receiver, self.song = '', ''

    def start(self):
        '''
        Start the Peer node.
        '''
        self.join()
        Thread(target=self.listen, daemon=True).start()
        Thread(target=self.heartbeat, daemon=True).start()
        Thread(target=self.start_mine, daemon=True).start()

    def main(self):
        '''
        Run the contents of the game and act according to user input.
        '''
        screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Blockchain-based Song Management")
        pygame.display.flip()

        self.start()
        timer = Timer(self.stay_time)

        # Buttons and flags for the main screen
        sync_button = None
        register_button = None
        transfer_button = None
        exit_button = None
        sync = False

        # Buttons for the register screen
        return_button = None
        reset_button = None
        submit_button = None
        reset = False
        user_input = None

        # main by default
        current_screen = "main"

        while True:
            # check if we have stayed for the required time.
            if timer.should_leave():
                self.leave()
                break

            if current_screen == 'main':
                register_button, transfer_button, exit_button, sync_button = self.draw_main_screen(screen, sync)
            elif current_screen == 'register':
                return_button, reset_button, submit_button, reset = self.draw_register_screen(screen, reset)
            elif current_screen == 'transfer':
                transfer_button, return_button, reset_button, reset = self.draw_transfer_screen(screen, reset)

            # Check out if it's during a pop up message.
            if self.show_pop_up:
                if self.pop_up_timer.should_leave():
                    self.show_pop_up = False
                    self.pop_up_timer = None
                    self.error_message = ''
                continue

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.exit_app()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    # Buttons on the main screen
                    if current_screen == 'main':
                        if register_button and register_button.collidepoint(event.pos):
                            current_screen = 'register'
                        if transfer_button and transfer_button.collidepoint(event.pos):
                            current_screen = 'transfer'
                        if exit_button and exit_button.collidepoint(event.pos):
                            self.exit_app()
                        if sync_button and sync_button.collidepoint(event.pos):
                            sync = True

                    # Buttons on the register screen
                    if current_screen == 'register':
                        if return_button and return_button.collidepoint(event.pos):
                            current_screen = 'main'
                        if reset_button and reset_button.collidepoint(event.pos):
                            reset = True

                        # User clicks on either of the text input box in register screen
                        if current_screen == 'register':
                            if 360 <= event.pos[0] <= 560 and 100 <= event.pos[1] <= 130:
                                user_input = 'user_name'
                            elif 360 <= event.pos[0] <= 560 and 200 <= event.pos[1] <= 230:
                                user_input = 'song_name'
                            elif 360 <= event.pos[0] <= 560 and 300 <= event.pos[1] <= 330:
                                user_input = 'signature'
                            else:
                                user_input = None
                    
                    # Buttons on the transfer screen
                    if current_screen == 'transfer':
                        if return_button and return_button.collidepoint(event.pos):
                            current_screen = 'main'
                            continue
                        if reset_button and reset_button.collidepoint(event.pos):
                            reset = True
                            user_input = None
                            continue
                        # User clicks on either of the text input box in transfer screen
                        if current_screen == 'transfer':
                            if 200 <= event.pos[0] <= 600 and 100 <= event.pos[1] <= 165:
                                user_input = 'receiver'
                            elif 200 <= event.pos[0] <= 600 and 200 <= event.pos[1] <= 265:
                                user_input = 'song'
                            else:
                                user_input = None


                if event.type == pygame.KEYDOWN and user_input:
                    self.handle_user_input(event, user_input)
                    self.handle_transfer_input(event, user_input)
                
                if event.type == pygame.MOUSEBUTTONDOWN and submit_button and submit_button.collidepoint(event.pos):
                    # Check the validity of this transaction.
                    self.ts_valid_check()
                    if self.error_message:
                        self.show_pop_up = True
                        self.pop_up_timer = Timer(2)
                        continue
                    current_screen = 'main'
                    self.make_app_transaction('Register')
           
                if event.type == pygame.MOUSEBUTTONDOWN and transfer_button and transfer_button.collidepoint(event.pos):
                    answer = self.check_transfer()
                    if self.error_message:
                        self.show_pop_up = True
                        self.pop_up_timer = Timer(2)
                        continue
                    if answer:
                        self.issue_license_change()
                        current_screen = 'main'

            pygame.display.update()


if __name__ == "__main__":
    # user can specify a stay time or close the app manually.
    pygame.init()
    if len(sys.argv) > 2:
        print("Usage: python app.py [stay_time] or python app.py")
        sys.exit(1)
    elif len(sys.argv) == 2:
        app = App(int(sys.argv[1]))
    else:
        app = App()
    app.main()