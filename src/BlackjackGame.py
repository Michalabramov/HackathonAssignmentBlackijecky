import random

class BlackjackGame:
    """
    The game logic, including deck management, card value calculation etc
    """
    def __init__(self):
        self.deck = [(r, s) for r in range(1, 14) for s in range(4)]
        random.shuffle(self.deck)

    def draw_card(self):
        return self.deck.pop() if self.deck else (1, 0)

    @staticmethod
    def get_card_value(rank: int) -> int:
        """
        Maps the card rank (1-13) to its actual Blackjack point value.
        Logic: Aces are 11, Face cards (J, Q, K) are 10, others are numeric.
        """
        if rank == 1: return 11
        if rank >= 10: return 10
        return rank

    @classmethod
    def calculate_total(cls, hand: list) -> int:
        return sum(cls.get_card_value(card[0]) for card in hand)
    
    @staticmethod
    def get_card_name(rank: int, suit: int) -> str:
        """
        Translates card number and suits into symbols
        """
        suits_map = {0: "♣ (Clubs)", 1: "♦ (Diamonds)", 2: "♥ (Hearts)", 3: "♠ (Spades)"}
        ranks_map = {1: "Ace", 11: "Jack", 12: "Queen", 13: "King"}
        card_rank = ranks_map.get(rank, str(rank))
        card_suit = suits_map.get(suit, "Unknown")
        return f"[{card_rank} of {card_suit}]"