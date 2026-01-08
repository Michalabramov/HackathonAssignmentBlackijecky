from socket import AF_INET, SO_BROADCAST, SOCK_DGRAM, SOCK_STREAM, SOL_SOCKET, gethostbyname, gethostname, socket, timeout
import threading
import time
from PacketHandler import PacketHandler
from BlackjackGame import BlackjackGame
from Constants import Constants


class Server:
    """
    Blackjack Server class that manages concurrent TCP clients and periodic UDP service announcements.
    """
    def __init__(self, team_name: str):
        self.team_name = team_name
        self.tcp_sock = socket(AF_INET, SOCK_STREAM)
        self.tcp_sock.bind(('', 0)) # Bind to any free port provided by the OS
        self.tcp_port = self.tcp_sock.getsockname()[1]
        self.tcp_sock.listen(10) #how much? 15?
        self.is_active = True
        self.ip= gethostbyname(gethostname())
        self.active_connections = []

    def get_local_ip(self):
        s = socket(AF_INET, SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 1))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = '127.0.0.1'
        finally:
            s.close()
        return local_ip

    def start(self):
        print(f"Server started, listening on IP address {self.ip}")
        # Start the UDP broadcasting thread (discovery)
        threading.Thread(target=self.broadcast_offers, daemon=True).start()
        try:
            while self.is_active:
                try:
                    # Accept incoming TCP connections from players
                    client_conn, addr = self.tcp_sock.accept()
                    self.active_connections.append(client_conn)
                    threading.Thread(target=self.handle_player, args=(client_conn, ), daemon=True).start()
                except Exception as e:
                    if self.is_active:
                        print(f"Server socket error: {e}")
        except KeyboardInterrupt:
            print("\n🛑 Server is shutting down... Closing all sockets.")
            self.is_active = False 
            
            for conn in self.active_connections:
                try:
                    conn.close() 
                except:
                    pass
            
            self.tcp_sock.close() 


    def broadcast_offers(self):
        """
        Broadcasts UDP packets every 1 second to announce server availability
        """
        real_ip = self.get_local_ip()
        prefix = '.'.join(real_ip.split('.')[:-1])
        specific_broadcast = f"{prefix}.255"
    
        print(f"Server will broadcast on {specific_broadcast} (via {real_ip})")

        with socket(AF_INET, SOCK_DGRAM) as udp:
            udp.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
            packet = PacketHandler.pack_offer(self.tcp_port, self.team_name)
            while self.is_active:
                try:
                    udp.sendto(packet, (specific_broadcast, Constants.UDP_PORT))
                    time.sleep(1)
                except Exception as e:
                    print(f"UDP broadcast error: {e}")
                    break

    def recv_exactly(self, conn, n):
        """ Helper to read exactly n bytes from the TCP stream. """
        buffer = b''
        while len(buffer) < n:
            packet = conn.recv(n - len(buffer))
            if not packet: return None
            buffer += packet
        return buffer

    def handle_player(self, conn: socket):
        try:
            conn.settimeout(60.0)
            data = self.recv_exactly(conn, 38) # Adjusted for your pack_request format
            if not data: return
            rounds, client_name = PacketHandler.unpack_request(data)
            print(f"✅ Connection established with team: {client_name}")

            for _ in range(rounds):
                self.run_round(conn)
                
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            print(f"👋 Player '{client_name}' disconnected abruptly.")
        except timeout:
            print(f"⏰ Player '{client_name}' timed out (too slow to decide).")
        except Exception as e:
            print(f"⚠️  Unexpected session error with '{client_name}': {e}")
        finally:
            conn.close()
            print(f"🔌 Connection closed for '{client_name}'")


    def run_round(self, conn: socket):
        game = BlackjackGame()
        player_hand = [game.draw_card(), game.draw_card()]
        dealer_hand = [game.draw_card(), game.draw_card()]

        # Initial distribution
        for c in player_hand:
            conn.sendall(PacketHandler.pack_payload_server(Constants.ROUND_NOT_OVER, c[0], c[1]))
        conn.sendall(PacketHandler.pack_payload_server(Constants.ROUND_NOT_OVER, dealer_hand[0][0], dealer_hand[0][1]))

        player_sum = BlackjackGame.calculate_total(player_hand)
        while player_sum <= 21:
            raw_decision = self.recv_exactly(conn, 10)
            if not raw_decision: break
            decision = PacketHandler.unpack_payload_client(raw_decision)
           
            if decision == "Stand":
                break
           
            new_card = game.draw_card()
            player_hand.append(new_card)
            player_sum = BlackjackGame.calculate_total(player_hand)
            conn.sendall(PacketHandler.pack_payload_server(Constants.ROUND_NOT_OVER, new_card[0], new_card[1]))

        # Dealer logic and final results continue here...
        # Ensure you send the dealer's hidden card before the final result!
        conn.sendall(PacketHandler.pack_payload_server(Constants.ROUND_NOT_OVER, dealer_hand[1][0], dealer_hand[1][1]))
        dealer_sum = BlackjackGame.calculate_total(dealer_hand)
       
        if player_sum <= 21:
            while dealer_sum < 17:
                c = game.draw_card()
                dealer_hand.append(c)
                dealer_sum = BlackjackGame.calculate_total(dealer_hand)
                conn.sendall(PacketHandler.pack_payload_server(Constants.ROUND_NOT_OVER, c[0], c[1]))
        # Final Evaluation
        res = Constants.TIE
        if player_sum > 21: 
            res = Constants.LOSS
        elif dealer_sum > 21 or player_sum > dealer_sum: 
            res = Constants.WIN
            if player_sum == 21 and len(player_hand) == 2:
                res = Constants.WIN_BLACKJACK
                ranks = [c[0] for c in player_hand]
                suits = [c[1] for c in player_hand]
                
                if (1 in ranks) and (11 in ranks): 
                    if all(s in [0, 3] for s in suits):
                        res = Constants.WIN_SUPER_BLACKJACK
        elif dealer_sum > player_sum: 
            res = Constants.LOSS

        conn.sendall(PacketHandler.pack_payload_server(res, 0, 0))
