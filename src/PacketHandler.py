import struct
from Constants import Constants


class PacketHandler:
    """
    Handles the serialization (packing) and deserialization (unpacking) of binary network packets.
    """

    OFFER_FMT = '>IBH32s'        # 39 bytes
    REQUEST_FMT = '>IBB32s'      # 38 bytes
    CLIENT_PAYLOAD_FMT = '>IB5s' # 10 bytes
    SERVER_PAYLOAD_FMT = '>IBBHB' # 9 bytes

    @staticmethod
    def pack_offer(tcp_port: int, server_name: str) -> bytes:
        """
        Packs a server offer message for UDP broadcast
        """
        name_bytes = server_name.encode('utf-8').ljust(32, b'\x00')[:32]
        return struct.pack(
            PacketHandler.OFFER_FMT,
            Constants.MAGIC_COOKIE,
            Constants.OFFER_TYPE,
            tcp_port,
            name_bytes
        )

    @staticmethod
    def unpack_offer(data: bytes):
        """
        Deserializes a UDP offer packet. Returns (port, name) or None if invalid.
        """
        expected_len = struct.calcsize(PacketHandler.OFFER_FMT)
        if len(data) != expected_len:
            return None

        try:
            magic, m_type, port, name = struct.unpack(PacketHandler.OFFER_FMT, data)
        except struct.error:
            return None

        if magic != Constants.MAGIC_COOKIE or m_type != Constants.OFFER_TYPE:
            return None

        return port, name.decode('utf-8', errors='strict').strip('\x00')

    @staticmethod
    def pack_payload_server(result: int, rank: int, suit: int) -> bytes:
        """
        Packs the server's response containing game result and card details
        """
        return struct.pack(
            PacketHandler.SERVER_PAYLOAD_FMT,
            Constants.MAGIC_COOKIE,
            Constants.PAYLOAD_TYPE,
            result,
            rank,
            suit
        )

    @staticmethod
    def unpack_payload_server(data: bytes):
        """
        Extracts results and card data from the server's binary payload.
        Raises ValueError on any protocol violation.
        """
        expected_len = struct.calcsize(PacketHandler.SERVER_PAYLOAD_FMT)
        if len(data) != expected_len:
            raise ValueError(f"Invalid server payload length: got {len(data)}, expected {expected_len}")

        try:
            magic, m_type, res, rank, suit = struct.unpack(PacketHandler.SERVER_PAYLOAD_FMT, data)
        except struct.error as e:
            raise ValueError(f"Malformed server payload (unpack error): {e}")

        if magic != Constants.MAGIC_COOKIE:
            raise ValueError("Invalid Magic Cookie received in server payload")
        if m_type != Constants.PAYLOAD_TYPE:
            raise ValueError("Invalid Payload Type from server")

        if rank != 0:
            if not (1 <= rank <= 13):
                raise ValueError(f"Malformed card data received: Rank {rank}")
            if not (0 <= suit <= 3):
                raise ValueError(f"Malformed card data received: Suit {suit}")
        else:
            if suit != 0:
                raise ValueError(f"Malformed end-of-round payload: rank=0 but suit={suit}")

        return res, rank, suit

    @staticmethod
    def pack_request(rounds: int, team_name: str) -> bytes:
        """
        Serializes a client game request.
        """
        name_bytes = team_name.encode('utf-8').ljust(32, b'\x00')[:32]
        return struct.pack(
            PacketHandler.REQUEST_FMT,
            Constants.MAGIC_COOKIE,
            Constants.REQUEST_TYPE,
            rounds,
            name_bytes
        )

    @staticmethod
    def unpack_request(data: bytes):
        """
        Deserializes a TCP request packet. Returns (rounds, name) or None if invalid.
        """
        expected_len = struct.calcsize(PacketHandler.REQUEST_FMT)
        if len(data) != expected_len:
            return None

        try:
            magic, m_type, rounds, name = struct.unpack(PacketHandler.REQUEST_FMT, data)
        except struct.error:
            return None

        if magic != Constants.MAGIC_COOKIE or m_type != Constants.REQUEST_TYPE:
            return None

        return rounds, name.decode('utf-8', errors='strict').strip('\x00')

    @staticmethod
    def pack_payload_client(decision: str) -> bytes:
        """
        Packs the client's decision ('Hittt' or 'Stand')
        """
        decision_bytes = decision.encode('utf-8').ljust(5, b'\x00')[:5]
        return struct.pack(
            PacketHandler.CLIENT_PAYLOAD_FMT,
            Constants.MAGIC_COOKIE,
            Constants.PAYLOAD_TYPE,
            decision_bytes
        )

    @staticmethod
    def unpack_payload_client(data: bytes) -> str:
        """
        Extracts the client's decision ("Hittt" or "Stand") from the packet.
        """
        expected_len = struct.calcsize(PacketHandler.CLIENT_PAYLOAD_FMT)
        if len(data) != expected_len:
            raise ValueError(f"Invalid client payload length: got {len(data)}, expected {expected_len}")

        try:
            magic, m_type, decision_bytes = struct.unpack(PacketHandler.CLIENT_PAYLOAD_FMT, data)
        except struct.error as e:
            raise ValueError(f"Malformed client payload (unpack error): {e}")

        if magic != Constants.MAGIC_COOKIE:
            raise ValueError("Invalid Magic Cookie received in client payload")
        if m_type != Constants.PAYLOAD_TYPE:
            raise ValueError("Invalid Payload Type from client")

        decision = decision_bytes.decode('utf-8', errors='strict').strip('\x00').strip()
        return decision
