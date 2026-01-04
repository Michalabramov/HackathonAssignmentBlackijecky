class Constants:
    """
    Project constants Includes network ports, protocol magic cookies, and game state codes.
    """
    MAGIC_COOKIE = 0xabcddcba 
    OFFER_TYPE = 0x2
    REQUEST_TYPE = 0x3 
    PAYLOAD_TYPE = 0x4     
    UDP_PORT = 13122  
    
    ROUND_NOT_OVER = 0x0
    TIE = 0x1
    LOSS = 0x2
    WIN = 0x3

