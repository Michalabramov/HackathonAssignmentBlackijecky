# UI.py
from BlackjackGame import BlackjackGame

RED = "\033[91m"
BLACK = "\033[90m"
RESET = "\033[0m"
SUITS_MAP = {0: "♣", 1: "♦", 2: "♥", 3: "♠"}

class UI:
    @staticmethod
    def suit_color(suit):
        return RED if suit in ('♥', '♦') else BLACK

    @staticmethod
    def rank_to_str(rank):
        if rank == 1:
            return "A"
        if rank == 11:
            return "J"
        if rank == 12:
            return "Q"
        if rank == 13:
            return "K"
        return str(rank)

    @staticmethod
    def draw_card(rank, suit, hidden=False):
        if hidden:
            return [
                "┌─────────┐",
                "│░░░░░░░░░│",
                "│░░░░░░░░░│",
                "│░░░░░░░░░│",
                "│░░░░░░░░░│",
                "│░░░░░░░░░│",
                "└─────────┘",
            ]

        suit_symbol = SUITS_MAP.get(suit, "?")
        color = UI.suit_color(suit_symbol)
        rank_str = UI.rank_to_str(rank).ljust(2)

        return [
            "┌─────────┐",
            f"│{rank_str}       │",
            "│         │",
            f"│    {color}{suit_symbol}{RESET}    │",
            "│         │",
            f"│       {rank_str}│",
            "└─────────┘",
        ]


    @staticmethod
    def draw_hand(cards, hide_second=False):
        drawings = []
        for i, (rank, suit) in enumerate(cards):
            hidden = hide_second and i == 1
            drawings.append(UI.draw_card(rank, suit, hidden))

        for row in range(7):
            print("  ".join(card[row] for card in drawings))

    @staticmethod
    def draw_table(player_hand, dealer_hand, hide_dealer=True):
        print("\n" * 5)
        print("___________________")
        print("🕵️  DEALER")
        if dealer_hand:
            UI.draw_hand(dealer_hand, hide_second=hide_dealer)

            if hide_dealer:
                visible = [dealer_hand[0]]
                dealer_sum = BlackjackGame.calculate_total(visible)
                print(f"\n   ➤ Visible Sum: {dealer_sum}")
            else:
                dealer_sum = BlackjackGame.calculate_total(dealer_hand)
                print(f"\n   ➤ Total Sum: {dealer_sum}")
        print("\n🃏 YOU")
        if player_hand:
            UI.draw_hand(player_hand)
            player_sum = BlackjackGame.calculate_total(player_hand)
            print(f"\n   ➤ Your Sum: {player_sum}")
