# WEAKKEY — weak EC key idea (simple words for the pitch)

## The idea

Some websites use an **elliptic curve (EC) public key** to secure their TLS
certificate. For EC keys the public key is mathematically tied to a private
number, called **k**: public key = k × G (G is a fixed starting point on the
curve).

If a website accidentally picks a **very small k** (for example `k = 4`), the
public key is just `4 × G` — an attacker can compute it instantly and recover
the private key by brute force. That means the encryption is basically
**free to break**. It's like using a house key that is just "key number 4".

## What the engine does

The new check in `engines/weak_key.py` asks: does this EC public key equal
`k × G` for some small `k` (default up to 100 000, configurable)?

- If yes → the key is **weak** → the engine raises a **high severity reason**
  and marks that certificate in the chain with status **`weak`**.
- If no → the key is fine → nothing flagged.

It uses **incremental point addition** (adding the generator point step by
step), so checking all small `k` values is fast.

## Why it matters for the hackathon

A phishing / malicious site with a trivially weak EC key is a red flag that
makes the trust check more suspicious — the certificate itself is broken, not
just the domain. The backend combines this with the other engines (certificate
chain, domain lookalike, reputation, content heuristics, transport) and
returns a trust score with reasons.

## How to test it offline

`engines/tools/make_weak_test_cert.py` generates two self-signed EC test
certificates into `engines/tests/fixtures/`:

- `weak_self_signed.pem` — EC private key `k = 4` (weak)
- `normal_self_signed.pem` — normal random EC key (not weak)

Then run the offline tests:

```powershell
python -m pytest engines/tests/test_weak_key.py -v
```
