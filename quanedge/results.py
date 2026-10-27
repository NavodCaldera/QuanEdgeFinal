"""Pure result identity and UI availability rules."""
import hashlib
import json
from .portfolio import canonical_weights,weight_hash


def digest(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()


def artifact_key(weight,method,data_snapshot_hash,config_hash,code_rev):
    return digest(dict(weight_hash=weight,method=method,data_snapshot_hash=data_snapshot_hash,
                       config_hash=config_hash,code_rev=code_rev))


def result_state(view_key,index):
    if view_key.get("input_error"):return "INPUT_ERROR"
    entry=index.get(view_key.get("artifact_key"))
    if entry and entry.get("failed"):return "FAILED"
    if entry:return "MATCHED"
    return "LIVE" if view_key.get("cheap") else "RERUN_REQUIRED"
