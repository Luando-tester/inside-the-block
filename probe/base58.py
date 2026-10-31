"""Base58 encode/decode (Bitcoin/Solana alphabet)."""

_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_INDEX = {c: i for i, c in enumerate(_ALPHABET)}


def b58encode(data: bytes) -> str:
    if not data:
        return ""
    zeros = 0
    for byte in data:
        if byte == 0:
            zeros += 1
        else:
            break
    n = int.from_bytes(data, "big")
    chars = []
    while n > 0:
        n, rem = divmod(n, 58)
        chars.append(_ALPHABET[rem])
    return "1" * zeros + "".join(reversed(chars))


def b58decode(text: str) -> bytes:
    if not text:
        return b""
    zeros = 0
    for ch in text:
        if ch == "1":
            zeros += 1
        else:
            break
    n = 0
    for ch in text:
        n = n * 58 + _INDEX[ch]
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * zeros + body
