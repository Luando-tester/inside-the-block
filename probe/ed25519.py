"""Minimal Ed25519 (RFC 8032) in pure Python — extended coordinates.

Implemented in-tree so the probe has no native crypto dependency. Used only for
deriving Solana public keys from seeds and for signing probe transactions.
Verified against the RFC 8032 test vectors in tests/test_units.py.
"""

import hashlib

_Q = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _Q - 2, _Q)) % _Q
_I = pow(2, (_Q - 1) // 4, _Q)


def _sha512(data: bytes) -> bytes:
    return hashlib.sha512(data).digest()


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * pow(_D * y * y + 1, _Q - 2, _Q) % _Q
    x = pow(xx, (_Q + 3) // 8, _Q)
    if (x * x - xx) % _Q != 0:
        x = (x * _I) % _Q
    if x % 2 != 0:
        x = _Q - x
    return x


_BY = (4 * pow(5, _Q - 2, _Q)) % _Q
_BX = _xrecover(_BY)
# Base point in extended coordinates (X, Y, Z, T)
_B = (_BX, _BY, 1, (_BX * _BY) % _Q)
_IDENTITY = (0, 1, 1, 0)


def _edwards_add(P, Q):
    # add-2008-hwcd for a = -1 (Ed25519), P/Q in (X, Y, Z, T) extended form.
    A = (P[0] * Q[0]) % _Q
    Bv = (P[1] * Q[1]) % _Q
    C = (_D * P[3] * Q[3]) % _Q
    Dv = (P[2] * Q[2]) % _Q
    E = ((P[0] + P[1]) * (Q[0] + Q[1]) - A - Bv) % _Q
    F = (Dv - C) % _Q
    G = (Dv + C) % _Q
    H = (Bv + A) % _Q  # B - a*A with a = -1
    return ((E * F) % _Q, (G * H) % _Q, (F * G) % _Q, (E * H) % _Q)


def _scalarmult(P, e: int):
    Q = _IDENTITY
    while e > 0:
        if e & 1:
            Q = _edwards_add(Q, P)
        P = _edwards_add(P, P)
        e >>= 1
    return Q


def _encode_point(P) -> bytes:
    x, y, z, _t = P
    zi = pow(z, _Q - 2, _Q)
    ax = (x * zi) % _Q
    ay = (y * zi) % _Q
    bits = [(ay >> i) & 1 for i in range(255)] + [ax & 1]
    return bytes(sum(bits[i * 8 + j] << j for j in range(8)) for i in range(32))


def _clamp(h: bytes) -> int:
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a


def public_key_from_seed(seed: bytes) -> bytes:
    """Derive the 32-byte Ed25519 public key for a 32-byte seed."""
    if len(seed) != 32:
        raise ValueError("seed must be 32 bytes")
    h = _sha512(seed)
    a = _clamp(h)
    return _encode_point(_scalarmult(_B, a))


def sign(seed: bytes, message: bytes) -> bytes:
    """Return the 64-byte Ed25519 signature of `message` under `seed`."""
    if len(seed) != 32:
        raise ValueError("seed must be 32 bytes")
    h = _sha512(seed)
    a = _clamp(h)
    prefix = h[32:]
    pub = _encode_point(_scalarmult(_B, a))
    r = int.from_bytes(_sha512(prefix + message), "little") % _L
    R = _encode_point(_scalarmult(_B, r))
    k = int.from_bytes(_sha512(R + pub + message), "little") % _L
    S = (r + k * a) % _L
    return R + S.to_bytes(32, "little")
