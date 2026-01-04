from socket import AF_INET, SO_REUSEADDR, SO_REUSEPORT, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, socket
from PacketHandler import PacketHandler
from BlackjackGame import BlackjackGame
from Constants import Constants
class Client:
    def __init__(self, team_name: str):
        """
        Initialize the client with a team name and statistics counters
        """
        self.team_name = team_name
        self.wins = 0
        self.total_rounds = 0

    def start(self):
        """
        Main client loop. Listens for UDP offers, connects to servers via TCP, and manages game sessions.
        """
        print(f"Client started, listening for offer requests...")
        while True:
            # Wait and listen for UDP broadcast offers from servers
            offer_data = self.wait_for_offer()
            if offer_data:
                server_ip, server_port, server_name = offer_data
                print(f"Received offer from {server_name} at {server_ip}, attempting to connect...")
                # Establish TCP connection and execute the game logic
                try:
                    # Request the number of rounds to play from the user
                    rounds_to_play = int(input("How many rounds would you like to play? "))
                    self.play_game(server_ip, server_port, rounds_to_play)
                except ValueError:
                    print("Invalid input, please enter a numeric value for rounds.")
                except Exception as e:
                    print(f"Error during game session: {e}")
                # After finishing or an error, return to listening for offers
                print(f"Client started, listening for offer requests...")

    def wait_for_offer(self):
        """
        Listens on a UDP port for server advertisements. Returns server connection details upon receiving a valid offer packet.
        """
        with socket(AF_INET, SOCK_DGRAM) as udp_sock:
            # Enable port reuse to allow multiple clients on the same machine
            udp_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
            try:
                udp_sock.setsockopt(SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                pass     
            # Bind to the broadcast port defined in the requirements
            udp_sock.bind(('', Constants.UDP_PORT))
            while True:
                data, addr = udp_sock.recvfrom(1024)
                # Use PacketHandler to validate the magic cookie and type
                result = PacketHandler.unpack_offer(data)
                if result:
                    port, name = result
                    return addr[0], port, name

    def play_game(self, ip, port, rounds):
        """
        Handles TCP communication, sends the initial game request, and loops through the specified number of rounds.
        """
        with socket(AF_INET, SOCK_STREAM) as tcp_sock:
            tcp_sock.connect((ip, port))
            # Send the initial request packet containing team name and round count
            request_packet = PacketHandler.pack_request(rounds, self.team_name)
            tcp_sock.sendall(request_packet)
            current_wins = 0
            for r in range(rounds):
                print(f"\n--- Round {r+1} ---")
                result = self.run_round(tcp_sock)
                if result == Constants.WIN:
                    current_wins += 1
                    self.wins += 1
                self.total_rounds += 1
            
            # Print final statistics for the session
            win_rate = (current_wins / rounds) * 100 if rounds > 0 else 0
            print(f"\nFinished playing {rounds} rounds, win rate: {win_rate}%")

    def run_round(self, sock):
        """
        Manages the communication flow for a single Blackjack round.
        Decides whether to 'Hit' or 'Stand' based on current hand value.
        """
        player_hand_sum = 0
        
        while True:
            # Receive card or result payload from the server
            data = sock.recv(1024)
            if not data: break
            
            res, rank, suit = PacketHandler.unpack_payload_server(data)
            
            # Check if the round is still active
            if res == Constants.ROUND_NOT_OVER:
                # Calculate card value using the game logic rules
                card_val = BlackjackGame.get_card_value(rank)
                player_hand_sum += card_val
                print(f"Received card: Rank {rank}, Suit {suit}. Current sum: {player_hand_sum}")
                
                # Decision logic: Automatically 'Hit' until the sum reaches at least 17
                if player_hand_sum < 17:
                    decision = "Hittt"
                else:
                    decision = "Stand"
                
                print(f"Decision: {decision}")
                # Send the decision back to the server using the client payload format
                sock.sendall(PacketHandler.pack_payload_client(decision))
                
                if decision == "Stand":
                    # Wait for the final result packet after choosing to Stand
                    continue 
            else:
                # The round has concluded; process the final result
                if res == Constants.WIN: print("Result: YOU WIN!")
                elif res == Constants.LOSS: print("Result: YOU LOSE!")
                else: print("Result: IT'S A TIE!")
                return res