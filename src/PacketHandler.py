import struct
import Constants

class PacketHandler:
    """
    Handles the serialization (packing) and deserialization (unpacking) of binary network packets.
    """

    @staticmethod
    def pack_offer(tcp_port: int, server_name: str) -> bytes:
        """
        Packs a server offer message for UDP broadcast.
        Format: Magic(4B), Type(1B), Port(2B), ServerName(32B)
        """
        name_bytes = server_name.encode('utf-8').ljust(32, b'\x00')[:32]
        return struct.pack('>IBH32s', Constants.MAGIC_COOKIE, Constants.OFFER_TYPE, tcp_port, name_bytes)

    @staticmethod
    def pack_payload_server(result: int, rank: int, suit: int) -> bytes:
        """
        Packs the server's response containing game result and card details.
        """
        rank_part = str(rank).zfill(2).encode() # 2 bytes ASCII
        suit_part = struct.pack('B', suit)      # 1 byte binary
        card_value = rank_part + suit_part      # 3 bytes total        
        return struct.pack('>IBB3s', Constants.MAGIC_COOKIE, Constants.PAYLOAD_TYPE, result, card_value)

    @staticmethod
    def pack_payload_client(decision: str) -> bytes:
        """
        Packs the client's decision ('Hittt' or 'Stand').
        """
        decision_bytes = decision.encode('utf-8').ljust(5, b'\x00')[:5]
        return struct.pack('>IB5s', Constants.MAGIC_COOKIE, Constants.PAYLOAD_TYPE, decision_bytes)