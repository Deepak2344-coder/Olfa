"""Weak EC public key detection: small private scalar k means trivially weak.

For elliptic curve keys the public key is computed as public = private * G
(generator). If the private scalar ``k`` is tiny (for example 4), the public
key is just ``k * G`` and can be derived instantly by the attacker - the key is
practically "free" to break. We detect this by checking whether the parsed
public key equals ``k * G`` for small ``k`` (default up to 100_000, configurable).

Point arithmetic uses incremental point addition, so checking all small ``k``
is fast.
"""

from __future__ import annotations

from typing import Optional

DEFAULT_MAX_SMALL_K = 100_000

# curve OID -> (prime p, coefficient a, generator (gx, gy)) for NIST P-256.
# Only curves with verified parameters are listed; others are treated as not weak.
_CURVE_PARAMS: dict[str, dict] = {
    "1.2.840.10045.3.1.7": {
        "p": 2**256 - 2**224 + 2**192 + 2**96 - 1,  # NIST P-256 prime
        "a": -3,
        "gx": 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
        "gy": 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5,
    },
}


# An affine EC point; ``None`` means the point at infinity.
_EcPoint = Optional[tuple[int, int]]


def _ec_add(p1: _EcPoint, p2: tuple[int, int], params: dict) -> _EcPoint:
    """Add two affine EC points (None = infinity) using the chord formula."""
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    p = params["p"]
    a = params["a"]
    if x1 == x2 and (y1 + y2) % p == 0:
        return None  # points are negatives -> infinity
    if x1 == x2 and y1 == y2:
        if y1 % p == 0:
            return None
        lam = (3 * x1 * x1 + a) * pow(2 * y1, -1, p) % p
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (lam * lam - x1 - x2) % p
    y3 = (lam * (x1 - x3) - y1) % p
    return (x3, y3)


def _small_ec_public_keys(max_small_k: int, params: dict) -> dict[int, _EcPoint]:
    """Return {k: public point for k*G} for k in 1..max_small_k (incremental addition)."""
    result: dict[int, _EcPoint] = {}
    point: _EcPoint = (params["gx"], params["gy"])  # k = 1
    result[1] = point
    generator = (params["gx"], params["gy"])
    for k in range(2, max_small_k + 1):
        point = _ec_add(point, generator, params)
        result[k] = point
    return result


def is_weak_ec_public_key(
    ec_point: _EcPoint,
    curve_oid: str | None,
    max_small_k: int = DEFAULT_MAX_SMALL_K,
) -> bool:
    """Return True when the EC public key equals k*G for some small k."""
    if ec_point is None:
        return False
    params = _CURVE_PARAMS.get(curve_oid or "")
    if params is None:
        return False
    keys = _small_ec_public_keys(max_small_k, params)
    for k, candidate in keys.items():
        if candidate is not None and candidate == ec_point:
            return True
    return False
