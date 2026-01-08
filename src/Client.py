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
        try:
            while True:
                # Wait and listen for UDP broadcast offers from servers
                offer_data = self.wait_for_offer()
                if offer_data:
                    server_ip, server_port, server_name = offer_data
                    print(f"Received offer from {server_name} at {server_ip}, attempting to connect...")
                    # Establish TCP connection and execute the game logic
                    try:
                        # Request the number of rounds to play from the user
                        rounds_input = input("How many rounds would you like to play?(Enter 0 to quit) ")
                        if not rounds_input: continue
                        rounds_to_play = int(rounds_input)
                        if rounds_to_play <= 0:
                            print("Closing connection and exiting as requested. Goodbye! 👋")
                            break 
                        if rounds_to_play > 50:
                            print("⚠️  That's a lot of rounds! For server stability, we'll limit this session to 50.")
                            rounds_to_play = 50

                        self.play_game(server_ip, server_port, rounds_to_play)
                    except ValueError:
                        print("Invalid input, please enter a numeric value.")
                    except (ConnectionAbortedError, ConnectionResetError):
                        print("\n❌ Connection lost: The server closed the session (maybe a timeout?)")
                        time.sleep(2) 
                    except Exception as e:
                        print(f"\n⚠️  An unexpected error occurred: {e}")
                        time.sleep(2) 

                    # After finishing or an error, return to listening for offers
                    print(f"Client started, listening for offer requests...")
        except KeyboardInterrupt:
            print("\n\n🛑 Ctrl+C detected. Exiting....")

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
            try:
                packet = sock.recv(n - len(buffer))
                if not packet:
                    return None
                buffer += packet
            except OSError: 
                return None
        return buffer

    def play_game(self, ip, port, rounds):
        """
        Handles TCP communication, sends the initial game request, and loops through the specified number of rounds.
        """
        self.wins=0
        self.total_rounds=0
        self.current_points = 0  
        with socket(AF_INET, SOCK_STREAM) as tcp_sock:
            tcp_sock.connect((ip, port))
            # Send the initial request packet containing team name and round count
            request_packet = PacketHandler.pack_request(rounds, self.team_name)
            tcp_sock.sendall(request_packet)
            for r in range(rounds):
                print(f"\n--- Round {r+1} ---")
                result = self.run_round(tcp_sock)
                if result == Constants.WIN:
                    self.wins += 1

                if result == Constants.WIN:
                    self.current_points += 1
                elif result == Constants.WIN_BLACKJACK:
                    self.current_points += 2
                elif result == Constants.WIN_SUPER_BLACKJACK:
                    self.current_points += 10
                    print("🔥 ⚡ SUPER BLACKJACK! +10 POINTS! ⚡ 🔥")
                self.total_rounds += 1
                print(f"💰 Current Session Points: {self.current_points}")

                if r < rounds - 1:
                    print("\n" + "┈" * 40)
                    while True:
                        prompt = input("👉 Type 'DEAL' to start the next round: ").strip().upper()
                        if prompt == "DEAL":
                            print("Great! Let's see what the cards hold...")
                            break
                        else:
                            print("❌ Invalid input. Please type 'DEAL' to continue.")
                    print("┈" * 40)
            win_rate = (self.wins / self.total_rounds) * 100 if self.total_rounds > 0 else 0
            print(f"\n🏆 Session Summary:")
            print(f"📊 Win Rate: {win_rate:.1f}% ({self.wins}/{self.total_rounds} rounds)")
            print(f"✨ Total Points Earned: {self.current_points}")

    def run_round(self, sock):
        player_hand = [] #list of (rank,suit) cards
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

            if res == Constants.ROUND_NOT_OVER:
                # According to rules: First 2 cards are player's, 3rd is Dealer visible
                if cards_received <= 2:
                    player_hand.append((rank, suit))
                    print(f"🃏 You were dealt: {card_name}")

                elif cards_received == 3:
                    dealer_hand_sum += BlackjackGame.get_card_value(rank)
                    print(f"🕵️  Dealer's visible card: {card_name}")
                    # Now we have the full picture to make the first decision
                else:
                    if is_player_turn:
                        # This is a card received after a 'Hit'
                        player_hand.append((rank, suit))
                        print(f"➕ Hit! You drew: {card_name}")
                    else:
                        dealer_hand_sum += BlackjackGame.get_card_value(rank)
                        print(f"🏠 Dealer draws: {card_name}")
                player_hand_sum = BlackjackGame.calculate_total(player_hand)

                if is_player_turn and cards_received >= 3:
                    print(f"📊 Current Status -> YOU: {player_hand_sum} | DEALER: {dealer_hand_sum}")
                    if player_hand_sum > 21:
                        print(f"💥 BUST! Your sum ({player_hand_sum}) is over 21. Waiting for dealer...")
                        is_player_turn = False
                        # We don't send anything here, just wait for the dealer's reveals/result
                    
                    elif player_hand_sum == 21:
                        print(f"\n✨ 🎉 21! PERFECT SCORE! 🎉 ✨")
                        print(f"✨ Automatically standing... You're a pro! 😎 ✨")
                        decision = "Stand"
                        is_player_turn = False
                        sock.sendall(PacketHandler.pack_payload_client(decision))

                    else:
                        while True:
                            print(f"\n👉 Your current sum: {player_hand_sum}")
                            choice = input("Do you want to (H)it or (S)tand? ").strip().upper()
                            if choice == 'H':
                                decision = "Hittt" 
                                break
                            elif choice == 'S':
                                decision = "Stand"
                                is_player_turn = False
                                break
                            else:
                                print("❌ Invalid input! Please enter 'H' for Hit or 'S' for Stand.")
                        print(f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
                        print(f"  Decision: {decision.upper()}  ")
                        print(f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
                        sock.sendall(PacketHandler.pack_payload_client(decision))
        
            # HANDLING THE RESULT (Round finished)
            else:
                print("\n" + "="*40)
               
                final_sum = BlackjackGame.calculate_total(player_hand)
                is_natural = (final_sum == 21 and len(player_hand) == 2)

                if res in [Constants.WIN, Constants.WIN_BLACKJACK, Constants.WIN_SUPER_BLACKJACK]:
                    if is_natural:
                        print("\033[1;92m🔥 🃏 BLACKJACK! 🃏 🔥\033[0m")
                        print("\033[92m🏆 You won with a Natural 21! Pure skill! 🏆\033[0m")
                    else:
                        print("\033[92m🏆 RESULT: YOU WIN! 💰\033[0m")       
                elif res == Constants.LOSS:
                    if final_sum == 21:
                        print("\033[91m😱 UNBELIEVABLE! You had 21, but the Dealer had a Natural Blackjack!\033[0m")
                    print("\033[91m💀 RESULT: YOU LOSE! 💸\033[0m")
               
                else:
                    print("\033[93m🤝 RESULT: IT'S A TIE! ⚖️\033[0m")
               
                print("="*40 + "\n")
                return res


