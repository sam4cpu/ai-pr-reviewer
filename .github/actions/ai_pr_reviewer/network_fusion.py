"""
network_fusion.py
- Reads local adaptive_weights.json (if present)
- Reads adaptive_network_weights.json (hub snapshot) (if present)
- Produces adaptive_weights.json (fused) and adaptive_network_weights.json (local summarized)
"""
import json
from pathlib import Path

LOCAL = Path("adaptive_weights.json")
GLOBAL = Path("adaptive_network_weights.json")
OUT = Path("adaptive_weights.json")
OUT_NETWORK = Path("adaptive_network_weights.json")

def load(p):
    return json.loads(p.read_text()) if p.exists() else {}

def fuse(local, global_):
    # simple safe fusion: merge numeric fields by mean
    fused = {}
    keys = set(local.keys()) | set(global_.keys())
    for k in keys:
        lv = local.get(k)
        gv = global_.get(k)
        if isinstance(lv, (int, float)) and isinstance(gv, (int, float)):
            fused[k] = round((lv + gv) / 2.0, 4)
        else:
            fused[k] = local.get(k, global_.get(k))
    return fused

def main():
    local = load(LOCAL)
    global_ = load(GLOBAL)
    if not local and not global_:
        print("[INFO] No local or global weights found — creating default weights.")
        default = {"depth_multiplier":1.0, "security_bias":1.0}
        OUT.write_text(json.dumps(default, indent=2))
        OUT_NETWORK.write_text(json.dumps(default, indent=2))
        print("[INFO] Wrote default adaptive weights.")
        return
    fused = fuse(local, global_)
    OUT.write_text(json.dumps(fused, indent=2))
    OUT_NETWORK.write_text(json.dumps({"source":"fused","weights":fused}, indent=2))
    print("[INFO] Fused weights written to adaptive_weights.json and adaptive_network_weights.json")

if __name__ == "__main__":
    main()
