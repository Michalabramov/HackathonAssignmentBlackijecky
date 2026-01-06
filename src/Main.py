import sys
from Server import Server
from Client import Client

def main():
    """
    Main entry point for the application.
    arguments: Main.py [server/client] [team_name]
    """
    if len(sys.argv) < 2:
        print("Usage: python Main.py <mode: server/client> [team_name]")
        return

    mode = sys.argv[1].lower()
    team_name = sys.argv[2] if len(sys.argv) > 2 else "Joker"  #default????????

    if mode == "server":
        # Initialize and start the Server
        # This will automatically start the UDP Broadcast thread and listen for TCP Unicast
        print(f"--- Launching Server: {team_name} ---")
        blackjack_server = Server(team_name)
        blackjack_server.start()

    elif mode == "client":
        # Initialize and start the Client
        # The client will listen for offers and then prompt for rounds
        print(f"--- Launching Client: {team_name} ---")
        blackjack_client = Client(team_name)
        blackjack_client.start()

    else:
        print("Invalid mode. Please choose 'server' or 'client'.")

if __name__ == "__main__":
    main()