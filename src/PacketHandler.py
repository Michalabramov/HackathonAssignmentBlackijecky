import struct
import Constants

class PacketHandler:
    """
    Handles the serialization (packing) and deserialization (unpacking) of binary network packets.
    """

    @staticmethod
    def pack_offer(tcp_port: int, server_name: str) -> bytes:
        """
        Packs a server offer message for UDP broadcast
        """
        name_bytes = server_name.encode('utf-8').ljust(32, b'\x00')[:32]
        return struct.pack('>IBH32s', Constants.MAGIC_COOKIE, Constants.OFFER_TYPE, tcp_port, name_bytes)
    
    @staticmethod
    def unpack_offer(data: bytes):
        """
        Deserializes a UDP offer packet. Returns (port, name) or None if invalid.
        """
        try:
            magic, m_type, port, name = struct.unpack('>IBH32s', data)
            if magic == Constants.MAGIC_COOKIE and m_type == Constants.OFFER_TYPE:
                return port, name.decode('utf-8').strip('\x00')
        except Exception:
            return None
        return None


    @staticmethod
    def pack_payload_server(result: int, rank: int, suit: int) -> bytes:
        """
        Packs the server's response containing game result and card details
        """
        rank_part = str(rank).zfill(2).encode() # 2 bytes ASCII
        suit_part = struct.pack('B', suit)      # 1 byte binary
        card_value = rank_part + suit_part      # 3 bytes total        
        return struct.pack('>IBB3s', Constants.MAGIC_COOKIE, Constants.PAYLOAD_TYPE, result, card_value)
    
    @staticmethod
    def unpack_payload_server(data: bytes):
        """
        Extracts results and card data from the server's binary payload.
        """
        magic, m_type, res, card_val = struct.unpack('>IBB3s', data)
        if magic != Constants.MAGIC_COOKIE:
            raise ValueError("Invalid Magic Cookie received")
       
        # Decoding the 3-byte Card Value back into rank and suit
        rank = int(card_val[:2].decode())
        suit = card_val[2]
        return res, rank, suit
    
    @staticmethod
    def pack_request(rounds: int, team_name: str) -> bytes:
        """
        Serializes a client game request.
        """
        name_bytes = team_name.encode('utf-8').ljust(32, b'\x00')[:32]
        return struct.pack('>IBB32s', Constants.MAGIC_COOKIE, Constants.REQUEST_TYPE, rounds, name_bytes)
    
    @staticmethod
    def unpack_request(data: bytes):
        """
        Deserializes a TCP request packet. Returns (rounds, name).
        """
        try:
            magic, m_type, rounds, name = struct.unpack('>IBB32s', data)
            if magic == Constants.MAGIC_COOKIE and m_type == Constants.REQUEST_TYPE:
                return rounds, name.decode('utf-8').strip('\x00')
        except Exception:
            return None
        return None

    @staticmethod
    def pack_payload_client(decision: str) -> bytes:
        """
        Packs the client's decision ('Hittt' or 'Stand')
        """
        decision_bytes = decision.encode('utf-8').ljust(5, b'\x00')[:5]
        return struct.pack('>IB5s', Constants.MAGIC_COOKIE, Constants.PAYLOAD_TYPE, decision_bytes)
    
    @staticmethod
    def unpack_payload_client(data: bytes) -> str:
        """
        Extracts the client's decision ("Hittt" or "Stand") from the packet.
        """
        magic, m_type, decision_bytes = struct.unpack('>IB5s', data)
        return decision_bytes.decode('utf-8').strip('\x00').strip()