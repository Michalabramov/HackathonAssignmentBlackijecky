import socket
import struct
import threading
import time
import PacketHandler
import BlackjackGame
import Constants


class Server:
    """
    Blackjack Server class that manages concurrent TCP clients and periodic UDP service announcements.
    """
    def __init__(self, team_name: str):
        self.team_name = team_name
        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind(('', 0)) # Bind to any free port provided by the OS
        self.tcp_port = self.tcp_sock.getsockname()[1]
        self.tcp_sock.listen(10) #how much? 15?
        self.is_active = True
        self.ip= socket.gethostbyname(socket.gethostname())

    def start(self):
        print(f"Server started, listening on IP address {self.ip}")
        # Start the UDP broadcasting thread (discovery)
        threading.Thread(target=self.broadcast_offers, daemon=True).start()
       
        while self.is_active:
            try:
                # Accept incoming TCP connections from players
                client_conn, addr = self.tcp_sock.accept()
                threading.Thread(target=self.handle_player, args=(client_conn, ), daemon=True).start()
            except Exception as e:
                #Add if is active?
                print(f"Server socket error: {e}")

    def broadcast_offers(self):
        """
        Broadcasts UDP packets every 1 second to announce server availability
        """
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  #to reach all clients on the local network
            packet = PacketHandler.pack_offer(self.tcp_port, self.team_name)
            while self.is_active:
                try:
                    udp.sendto(packet, ('<broadcast>', Constants.UDP_PORT))
                    time.sleep(1)
                except Exception as e:
                    print(f"UDP broadcast error: {e}")
                    break

    def handle_player(self, conn: socket.socket):
        """
        Manages the game session for a single connected client.
        """
        try:
            conn.settimeout(10.0)
            data = conn.recv(1024)
            # Unpacking logic for Request (Magic, Type, Rounds, Name)
            magic, m_type, rounds, client_name = PacketHandler.unpack_request(data)
            print(f"Connection established with team: {client_name}")

            for _ in range(rounds):
                self.run_round(conn)
           
        except Exception as e:
            print(f"Session error: {e}")
        finally:
            conn.close()

    def run_round(self, conn: socket.socket):
        """
        Implements the main Blackjack round flow.
        """
        game = BlackjackGame()
        player_hand = [game.draw_card(), game.draw_card()]
        dealer_hand = [game.draw_card(), game.draw_card()]

        # Initial Card Distribution
        for c in player_hand:
            conn.send(PacketHandler.pack_payload_server(Constants.ROUND_NOT_OVER, c[0], c[1]))
        # Dealer visible card
        conn.send(PacketHandler.pack_payload_server(Constants.ROUND_NOT_OVER, dealer_hand[0][0], dealer_hand[0][1]))

        # Player Turn Logic
        player_sum = BlackjackGame.calculate_total(player_hand)
        while player_sum <= 21:
            raw_decision = conn.recv(1024)
            # Format: Magic(4), Type(1), Decision(5)
            _, _, decision = PacketHandler.unpack_payload_client(raw_decision)
            if decision == "Stand": break
            new_card = game.draw_card()
            player_hand.append(new_card)
            player_sum = BlackjackGame.calculate_total(player_hand)
            conn.send(PacketHandler.pack_payload_server(Constants.ROUND_NOT_OVER, new_card[0], new_card[1]))

        # Dealer Turn Logic (Only if player didn't bust)
        conn.send(PacketHandler.pack_payload_server(Constants.ROUND_NOT_OVER, dealer_hand[1][0], dealer_hand[1][1]))
        dealer_sum = BlackjackGame.calculate_total(dealer_hand)
       
        if player_sum <= 21:
            while dealer_sum < 17:
                c = game.draw_card()
                dealer_hand.append(c)
                dealer_sum = BlackjackGame.calculate_total(dealer_hand)
                conn.send(PacketHandler.pack_payload_server(Constants.ROUND_NOT_OVER, c[0], c[1]))

        # Final Evaluation
        res = Constants.TIE
        if player_sum > 21: res = Constants.LOSS
        elif dealer_sum > 21 or player_sum > dealer_sum: res = Constants.WIN
        elif dealer_sum > player_sum: res = Constants.LOSS
       
        conn.send(PacketHandler.pack_payload_server(res, 0, 0))
