from socket import AF_INET, SO_REUSEADDR, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, MSG_PEEK, socket
from PacketHandler import PacketHandler
from BlackjackGame import BlackjackGame
from Constants import Constants
import time
import select
from UI import UI

class Client:
    def __init__(self, team_name: str):
        """
        Initialize the client with a team name and statistics counters
        """
        self.team_name = team_name
        self.wins = 0
        self.total_rounds = 0
        self.current_points = 0

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
                        try:
                            rounds_to_play = int(rounds_input)
                        except ValueError:
                            print("❌ Invalid input: Please enter a numeric value for rounds.")
                            continue                
                        if rounds_to_play <= 0:
                            print("Closing connection and exiting as requested. Goodbye! 👋")
                            break 
                        if rounds_to_play > 50:
                            print("⚠️  That's a lot of rounds! For server stability, we'll limit this session to 50.")
                            rounds_to_play = 50

                        self.play_game(server_ip, server_port, rounds_to_play)
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
    
    
    def is_socket_closed(self, sock):
        """
        Checking if sok still open
        """
        readable, _, _ = select.select([sock], [], [], 0)
        if readable:
            data = sock.recv(1, MSG_PEEK)
            if not data:
                return True
        return False

    def play_game(self, ip, port, rounds):
        """
        Handles TCP communication, sends the initial game request, and loops through the specified number of rounds.
        """
        self.wins = 0
        self.total_rounds = 0
        self.current_points = 0  

        with socket(AF_INET, SOCK_STREAM) as tcp_sock:
            tcp_sock.settimeout(15.0)
            tcp_sock.connect((ip, port))

            # Send the initial request packet containing team name and round count
            request_packet = PacketHandler.pack_request(rounds, self.team_name)
            tcp_sock.sendall(request_packet)

            for r in range(rounds):
                print(f"\n--- Round {r+1} ---")
                result = self.run_round(tcp_sock)  # include updates points and wins internally
                self.total_rounds += 1 

                if r < rounds - 1:
                    if self.is_socket_closed(tcp_sock):
                        raise ConnectionError("Server disconnected before next round.")

                    # Prompt user to start the next round
                    print("\n" + "┈" * 40)
                    while True:
                        prompt = input("👉 Type 'DEAL' to start the next round: ").strip().upper()
                        if prompt == "DEAL":
                            print("Great! Let's see what the cards hold...")
                            break
                        else:
                            print("❌ Invalid input. Please type 'DEAL' to continue.")
                    print("┈" * 40)

            # Session summary
            win_rate = (self.wins / self.total_rounds) * 100 if self.total_rounds > 0 else 0
            print(f"\n🏆 Session Summary:")
            print(f"📊 Win Rate: {win_rate:.1f}% ({self.wins}/{self.total_rounds} rounds)")
            print(f"✨ Total Points Earned: {self.current_points}")


    def run_round(self, sock):
        """
        Manages a single round of blackjack
        """
        player_hand = []
        dealer_hand = []
        is_player_turn = True
        cards_received = 0

        while True:
            data = self.recv_exactly(sock, 9) #READ EXACTLY 9 BYTES (Server Payload size)
            if not data:
                raise ConnectionError("Server disconnected during round")
            try:
                res, rank, suit = PacketHandler.unpack_payload_server(data)
            except ValueError as e:
                print(f"\n❌ Protocol Error: Received corrupted data from server ({e})")
                raise
            cards_received += 1
            if res == Constants.ROUND_NOT_OVER:
                if cards_received <= 2:
                    player_hand.append((rank, suit))
                elif cards_received == 3:
                    dealer_hand.append((rank, suit))
                else:
                    if is_player_turn:
                        player_hand.append((rank, suit))
                    else:
                        dealer_hand.append((rank, suit))
                # Draw table, hide dealer card if player's turn
                UI.draw_table(player_hand, dealer_hand,hide_dealer=is_player_turn)
                player_sum = BlackjackGame.calculate_total(player_hand)
                if is_player_turn and cards_received >= 3:
                    if player_sum > 21:
                        is_player_turn = False
                    elif player_sum == 21:
                        print(f"\n✨ 🎉 21! PERFECT SCORE! 🎉 ✨")
                        print(f"✨ Automatically standing... You're a pro! 😎 ✨")
                        sock.sendall(PacketHandler.pack_payload_client("Stand"))
                        is_player_turn = False
                    else:
                        while True:
                            choice = input("\n(H)it or (S)tand? ").strip().upper()
                            if choice == 'H':
                                sock.sendall(PacketHandler.pack_payload_client("Hittt"))
                                break
                            elif choice == 'S':
                                sock.sendall(PacketHandler.pack_payload_client("Stand"))
                                is_player_turn = False
                                break
                            else:
                                print("❌ Invalid input! Please enter 'H' for Hit or 'S' for Stand.")
            else:
                # Update wins and points
                if res == Constants.WIN:
                    self.wins += 1
                    self.current_points += 1
                    print("\n🏆 YOU WIN! (+1 point)")

                elif res == Constants.WIN_BLACKJACK:
                    self.wins += 1
                    self.current_points += 2
                    print("\n🔥 BLACKJACK! (+2 points)")

                elif res == Constants.WIN_SUPER_BLACKJACK:
                    self.wins += 1
                    self.current_points += 10
                    print("\n⚡🔥 SUPER BLACKJACK! (+10 points)")

                elif res == Constants.LOSS:
                    self.current_points -= 1
                    print("\n💀 YOU LOSE! (-1 point)")

                else:
                    print("\n🤝 TIE! (0 points)")

                print(f"💰 Current Points: {self.current_points}")
                print("=" * 40)

                return res
