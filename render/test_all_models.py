"""Test all VRM/GLB models metadata."""
import os
import sys
import pygltflib

models_dir = r"D:\Vtuber\MODELOS VRM"

# Handle Unicode encoding for console
sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

for fn in sorted(os.listdir(models_dir)):
    if not fn.lower().endswith((".glb", ".vrm", ".vci")):
        continue
    path = os.path.join(models_dir, fn)
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".vrm", ".vci"):
            g = pygltflib.GLTF2().load_binary(path)
        else:
            g = pygltflib.GLTF2().load(path)
        sk = len(g.skins) if g.skins else 0
        js = sum(len(s.joints) for s in (g.skins or [])) if sk else 0
        ms = len(g.meshes)
        pr = sum(len(m.primitives) for m in (g.meshes or []))
        ext_used = getattr(g, "extensionsUsed", []) or []
        vrm = "VRM" in ext_used

        morph_prims = 0
        for m in (g.meshes or []):
            for p in m.primitives:
                if getattr(p, "targets", None) is not None and len(p.targets) > 0:
                    morph_prims += 1

        # Check VRM human bones
        bones = 0
        blends = 0
        springs = 0
        if vrm:
            try:
                vrm_ext = g.extensions.get("VRM", {})
                if vrm_ext:
                    hb = vrm_ext.get("humanoid", {}).get("humanBones", [])
                    bones = len(hb)
                    bs = vrm_ext.get("blendShapeMaster", {}).get("blendShapeGroups", [])
                    blends = len(bs)
                    sa = vrm_ext.get("secondaryAnimation", {})
                    springs = len(sa.get("boneGroups", []))
            except Exception:
                pass

        info = f"OK: {ms} meshes, {pr} prims, {sk} skins, {js} joints, VRM={vrm}, morph_prims={morph_prims}, bones={bones}, blends={blends}, springs={springs}"
        print(f"{fn:<50s} {info}")
    except Exception as e:
        err = str(e).replace("\n", " ")[:80]
        print(f"{fn:<50s} ERR: {err}")
