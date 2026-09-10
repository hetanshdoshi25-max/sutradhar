"""
SUTRADHAR - Audit log (chain-of-custody)
-----------------------------------------
Every action the system takes (an analysis run, a PDF case-file export) is
recorded as a tamper-evident log entry: timestamp, action, a short input
summary, and a SHA-256 hash chained to the PREVIOUS entry's hash - exactly
like a blockchain. If any past entry is edited after the fact, every hash
after it breaks, so tampering is detectable. This is what BSA Sec 63 / IT
Act Sec 65B "chain of custody" means in practice for electronic evidence.

In-memory for the prototype (resets on restart); a production deployment
would append to a write-once store.
"""

import hashlib
import json
from datetime import datetime, timezone

_LOG = []          # ordered list of entries (in-memory for the demo)
_GENESIS = "0" * 64  # the chain's starting hash, like a blockchain genesis block


def _hash_entry(prev_hash, entry):
    """SHA-256 of (previous hash + this entry's content) -> chains entries
    together. Changing any past entry changes every hash after it."""
    payload = json.dumps(entry, sort_keys=True) + prev_hash
    return hashlib.sha256(payload.encode()).hexdigest()


def record(action, summary):
    """Append a new tamper-evident entry to the audit log."""
    prev_hash = _LOG[-1]["hash"] if _LOG else _GENESIS
    entry = {
        "seq": len(_LOG) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "action": action,
        "summary": summary,
        "prev_hash": prev_hash,
    }
    entry["hash"] = _hash_entry(prev_hash, entry)
    _LOG.append(entry)
    return entry


def get_log():
    return list(_LOG)


def verify_chain():
    """Recompute every hash from genesis - if anything was tampered with,
    this returns False and says exactly where the chain broke."""
    prev = _GENESIS
    for e in _LOG:
        check = dict(e)
        stored_hash = check.pop("hash")
        recomputed = _hash_entry(prev, check)
        if recomputed != stored_hash:
            return False, e["seq"]
        prev = stored_hash
    return True, None


if __name__ == "__main__":
    record("analyze", "5 personas, threshold 0.55")
    record("export_pdf", "case file for 2 attributions")
    ok, broke_at = verify_chain()
    print("chain valid:", ok)
    for e in get_log():
        print(f"  #{e['seq']} {e['timestamp']} {e['action']:<12} hash={e['hash'][:16]}...")
