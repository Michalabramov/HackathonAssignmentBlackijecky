from socket import AF_INET, SO_REUSEADDR, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, socket
from PacketHandler import PacketHandler
from BlackjackGame import BlackjackGame
from Constants import Constants
import time

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
                    rounds_input = input("How many rounds would you like to play? ")
                    if not rounds_input: continue
                    rounds_to_play = int(rounds_input)
                    self.play_game(server_ip, server_port, rounds_to_play)
                except (ValueError, EOFError):
                    print("Invalid input or session interrupted.")
                except Exception as e:
                    print(f"Connection lost or error: {e}")
                    time.sleep(2)
                # After finishing or an error, return to listening for offers
                print(f"Client started, listening for offer requests...")

    def wait_for_offer(self):
        """
        Listens on a UDP port for server advertisements. Returns server connection details upon receiving a valid offer packet.
        """
        with socket(AF_INET, SOCK_DGRAM) as udp_sock:
            # Enable port reuse to allow multiple clients on the same machine
            udp_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

            if hasattr(socket, "SO_REUSEPORT"):
                udp_sock.setsockopt(SOL_SOCKET, socket.SO_REUSEPORT, 1)

            # Bind to the broadcast port defined in the requirements
            udp_sock.bind(('', Constants.UDP_PORT))
            while True:
                data, addr = udp_sock.recvfrom(1024)
                # Use PacketHandler to validate the magic cookie and type
                result = PacketHandler.unpack_offer(data)
                if result:
                    port, name = result
                    return addr[0], port, name
                
    def recv_exactly(self, sock, n):
        """
        Helper function to ensure we read exactly n bytes from the TCP stream.
        """
        buffer = b''
        while len(buffer) < n:
            packet = sock.recv(n - len(buffer))
            if not packet:
                return None
            buffer += packet
        return buffer

    def play_game(self, ip, port, rounds):
        """
        Handles TCP communication, sends the initial game request, and loops through the specified number of rounds.
        """
        self.wins=0
        self.total_rounds=0

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
        player_hand_sum = 0
        dealer_hand_sum = 0
        is_player_turn= True
        cards_received = 0  # Counter to track initial deal (3 cards total)

        while True:
            # READ EXACTLY 9 BYTES (Server Payload size)
            data = self.recv_exactly(sock, 9)
            if not data:
                raise ConnectionError("Server sidconnected during the round.")
        
            res, rank, suit = PacketHandler.unpack_payload_server(data)
            cards_received += 1
            card_name = BlackjackGame.get_card_name(rank, suit)
            card_val = BlackjackGame.get_card_value(rank)

            if res == Constants.ROUND_NOT_OVER:
                # According to rules: First 2 cards are player's, 3rd is Dealer visible
                if cards_received <= 2:
                    player_hand_sum += card_val
                    print(f"🃏 You were dealt: {card_name}")

                elif cards_received == 3:
                    dealer_hand_sum += card_val
                    print(f"🕵️  Dealer's visible card: {card_name}")
                    print(f"📊 Current Status -> YOU: {player_hand_sum} | DEALER: {dealer_hand_sum}")
                    # Now we have the full picture to make the first decision
                else:
                    if is_player_turn:
                        # This is a card received after a 'Hit'
                        player_hand_sum += card_val
                        print(f"➕ Hit! You drew: {card_name}")
                    else:
                        dealer_hand_sum += card_val
                        print(f"🏠 Dealer draws: {card_name}")
                if is_player_turn and cards_received >= 3:
                    if player_hand_sum > 21:
                        print(f"💥 BUST! Your sum ({player_hand_sum}) is over 21. Waiting for dealer...")
                        is_player_turn = False
                        # We don't send anything here, just wait for the dealer's reveals/result
                    else:
                        decision = "Hittt" if player_hand_sum < 17 else "Stand"
                        print(f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
                        print(f"  Current Sum: {player_hand_sum} | Decision: {decision.upper()}")
                        print(f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
                        sock.sendall(PacketHandler.pack_payload_client(decision))
                    
                        if decision == "Stand":
                            is_player_turn = False
        
            # HANDLING THE RESULT (Round finished)
            else:
                print("\n" + "="*30)
                if res == Constants.WIN:
                    print("\033[92m🏆 RESULT: YOU WIN! 💰\033[0m")
                elif res == Constants.LOSS:
                    print("\033[91m💀 RESULT: YOU LOSE! 💸\033[0m")
                else:
                    print("🤝 RESULT: IT'S A TIE! ⚖️")
                print("="*30 + "\n")
                return res