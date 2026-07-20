"""3D modeling and AI asset generation tools.

Pure-Python helpers that model 3D workflows: text-to-mesh, retopology,
UV unwrapping, PBR texture generation, rigging, physics sim, and more.
Each tool returns a structured dict describing the planned/analyzed result.
"""

from __future__ import annotations

def _lod_levels(base_tris: int, levels: int) -> list[dict]:
    return [{"level": i, "tris": max(base_tris // (2 ** (i + 1)), 64), "screen_size": 0.5 ** i} for i in range(levels)]

def _uv_islands_count(verts: int) -> int:
    return max(1, verts // 500)

def _bone_count(rig_type: str) -> int:
    return {"humanoid": 65, "quadruped": 80, "face": 52, "simple": 12}.get(rig_type, 20)

def _pbr_maps(material: str) -> list[str]:
    base = ["baseColor", "normal", "roughness", "metallic", "height"]
    extra = {"skin": ["subsurface", "sss"], "fabric": ["sheen", "fuzz"], "metal": ["anisotropy"]}
    return base + extra.get(material.lower(), [])

def _voxel_resolution(bbox: dict, voxel_size: float) -> tuple[int, int, int]:
    return (int(bbox.get("x", 1) / voxel_size), int(bbox.get("y", 1) / voxel_size), int(bbox.get("z", 1) / voxel_size))

def _light_setup(scene_type: str) -> list[dict]:
    setups = {
        "studio": [{"type": "key", "intensity": 1000, "angle": 45}, {"type": "fill", "intensity": 400, "angle": -30}, {"type": "rim", "intensity": 600, "angle": 180}],
        "outdoor": [{"type": "sun", "intensity": 5000, "angle": 60}, {"type": "sky", "intensity": 800}],
        "product": [{"type": "key", "intensity": 1500, "angle": 0}, {"type": "fill", "intensity": 500, "angle": 90}, {"type": "back", "intensity": 300, "angle": 180}],
    }
    return setups.get(scene_type, setups["studio"])

def _export_formats(engine: str) -> list[str]:
    return {"unity": ["fbx", "obj"], "unreal": ["fbx", "gltf"], "web": ["gltf", "glb"], "blender": ["blend", "fbx"]}.get(engine, ["fbx", "obj"])

def _physics_materials(material: str) -> dict:
    return {
        "metal": {"density": 7800, "restitution": 0.3, "friction": 0.6},
        "wood": {"density": 600, "restitution": 0.2, "friction": 0.5},
        "glass": {"density": 2500, "restitution": 0.5, "friction": 0.3},
        "rubber": {"density": 1100, "restitution": 0.8, "friction": 0.9},
    }.get(material, {"density": 1000, "restitution": 0.4, "friction": 0.5})

def _terrain_erosion(steps: int) -> list[str]:
    return ["hydraulic" if i % 2 == 0 else "thermal" for i in range(steps)]

TOOLS: list[dict] = [
    {"name": "three_d_text_to_mesh", "description": "Generate a 3D mesh from a text prompt using AI text-to-3D.",
     "params": {"prompt": "str", "poly_count": "int", "style": "str"},
     "run": lambda a: {"mesh": {"vertices": a.get("poly_count", 10000), "faces": a.get("poly_count", 10000) // 2},
                      "prompt": a.get("prompt", ""), "style": a.get("style", "realistic"), "format": "glb"}},

    {"name": "three_d_image_to_mesh", "description": "Reconstruct a 3D mesh from one or more 2D images.",
     "params": {"images": "list[str]", "method": "str", "resolution": "int"},
     "run": lambda a: {"method": a.get("method", "nerf"), "input_images": a.get("images", []),
                      "output_resolution": a.get("resolution", 512), "mesh_tris": a.get("resolution", 512) * 50}},

    {"name": "three_d_retopology", "description": "Retopologize a high-poly mesh into clean quad topology.",
     "params": {"input_tris": "int", "target_tris": "int", "method": "str"},
     "run": lambda a: {"input_tris": a.get("input_tris", 100000), "target_tris": a.get("target_tris", 10000),
                      "method": a.get("method", "instant_meshes"), "quad_ratio": 0.95}},

    {"name": "three_d_uv_unwrap", "description": "Plan UV unwrapping for a mesh with given vertex count.",
     "params": {"vertices": "int", "method": "str", "atlas_size": "int"},
     "run": lambda a: {"method": a.get("method", "smart"), "islands": _uv_islands_count(a.get("vertices", 1000)),
                      "atlas_resolution": a.get("atlas_size", 4096), "padding_px": 4}},

    {"name": "three_d_pbr_texture", "description": "Generate PBR texture maps for a material description.",
     "params": {"material": "str", "resolution": "int", "tiling": "bool"},
     "run": lambda a: {"maps": _pbr_maps(a.get("material", "metal")), "resolution": a.get("resolution", 2048),
                      "tiling": a.get("tiling", True), "format": "exr"}},

    {"name": "three_d_rig", "description": "Generate a skeleton rig for a mesh based on rig type.",
     "params": {"mesh": "str", "rig_type": "str", "auto_weight": "bool"},
     "run": lambda a: {"rig_type": a.get("rig_type", "humanoid"), "bones": _bone_count(a.get("rig_type", "humanoid")),
                      "auto_weight": a.get("auto_weight", True), "ik_chains": ["arm_l", "arm_r", "leg_l", "leg_r"]}},

    {"name": "three_d_motion_retarget", "description": "Retarget motion capture data from source rig to target rig.",
     "params": {"source_rig": "str", "target_rig": "str", "animation": "str"},
     "run": lambda a: {"source": a.get("source_rig", "mixamo"), "target": a.get("target_rig", "custom"),
                      "animation": a.get("animation", "walk_cycle"), "retarget_mode": "bone_mapping", "root_motion": True}},

    {"name": "three_d_lod", "description": "Generate LOD levels for a mesh at decreasing triangle counts.",
     "params": {"base_tris": "int", "levels": "int"},
     "run": lambda a: {"lod_levels": _lod_levels(a.get("base_tris", 50000), a.get("levels", 4)),
                      "base_tris": a.get("base_tris", 50000)}},

    {"name": "three_d_decimate", "description": "Reduce mesh polygon count by a decimation ratio.",
     "params": {"input_tris": "int", "ratio": "float", "preserve_edges": "bool"},
     "run": lambda a: {"input_tris": a.get("input_tris", 100000),
                      "output_tris": int(a.get("input_tris", 100000) * a.get("ratio", 0.3)),
                      "ratio": a.get("ratio", 0.3), "preserve_edges": a.get("preserve_edges", True)}},

    {"name": "three_d_voxel_to_mesh", "description": "Convert a voxel grid to a smooth mesh via marching cubes.",
     "params": {"bbox": "dict", "voxel_size": "float", "smooth": "bool"},
     "run": lambda a: {"voxel_grid": _voxel_resolution(a.get("bbox", {"x": 1, "y": 1, "z": 1}), a.get("voxel_size", 0.05)),
                      "method": "marching_cubes", "smooth": a.get("smooth", True), "iso_level": 0.5}},

    {"name": "three_d_photogrammetry", "description": "Plan a photogrammetry reconstruction from a set of photos.",
     "params": {"photos": "list[str]", "resolution": "int", "quality": "str"},
     "run": lambda a: {"photo_count": len(a.get("photos", [])),
                      "sparse_cloud_points": len(a.get("photos", [])) * 5000,
                      "dense_cloud_points": len(a.get("photos", [])) * 50000, "quality": a.get("quality", "medium")}},

    {"name": "three_d_sculpt", "description": "Plan a digital sculpting session with brush list and subdivision levels.",
     "params": {"base_mesh": "str", "subdiv_levels": "int", "brushes": "list[str]"},
     "run": lambda a: {"subdiv_levels": a.get("subdiv_levels", 6), "max_polygons": 2 ** (a.get("subdiv_levels", 6) + 10),
                      "brushes": a.get("brushes", ["standard", "clay", "smooth", "pinch"])}},

    {"name": "three_d_material_graph", "description": "Build a node-based material graph from a material description.",
     "params": {"material": "str", "nodes": "list[str]"},
     "run": lambda a: {"nodes": [{"name": n, "type": "noise" if "noise" in n else "math", "inputs": []}
                      for n in a.get("nodes", ["noise", "color_ramp", "output"])],
                      "material": a.get("material", "procedural")}},

    {"name": "three_d_lighting", "description": "Set up scene lighting based on scene type.",
     "params": {"scene_type": "str", "hdri": "str", "samples": "int"},
     "run": lambda a: {"lights": _light_setup(a.get("scene_type", "studio")), "hdri": a.get("hdri", "studio_small.hdr"),
                      "samples": a.get("samples", 128)}},

    {"name": "three_d_turntable", "description": "Generate turntable render settings for a 360-degree showcase.",
     "params": {"frames": "int", "resolution": "int", "fps": "int"},
     "run": lambda a: {"frames": a.get("frames", 72), "resolution": a.get("resolution", 1080), "fps": a.get("fps", 24),
                      "rotation_per_frame": 360.0 / a.get("frames", 72)}},

    {"name": "three_d_export", "description": "Export a 3D scene to engine-specific formats.",
     "params": {"engine": "str", "selection": "list[str]", "embed_textures": "bool"},
     "run": lambda a: {"formats": _export_formats(a.get("engine", "unity")), "selection": a.get("selection", []),
                      "embed_textures": a.get("embed_textures", True),
                      "axis_conversion": {"unity": "-Z forward, Y up", "unreal": "X forward, Z up"}.get(a.get("engine", "unity"), "Y up")}},

    {"name": "three_d_physics_sim", "description": "Configure a rigid-body physics simulation for 3D objects.",
     "params": {"objects": "list[dict]", "gravity": "float", "frames": "int"},
     "run": lambda a: {"objects": [{"name": o.get("name", f"obj_{i}"), "material": _physics_materials(o.get("material", "metal"))}
                      for i, o in enumerate(a.get("objects", []))],
                      "gravity": a.get("gravity", -9.81), "frames": a.get("frames", 250), "substeps": 10}},

    {"name": "three_d_blendshape", "description": "Generate blendshape targets for facial animation.",
     "params": {"base_mesh": "str", "expressions": "list[str]", "method": "str"},
     "run": lambda a: {"targets": a.get("expressions", ["smile", "frown", "blink", "jaw_open"]), "method": a.get("method", "sculpt"),
                      "base_mesh": a.get("base_mesh", "face"), "delta_count": len(a.get("expressions", [])) * 1000}},

    {"name": "three_d_hair_groom", "description": "Plan hair grooming with guide curves and interpolation settings.",
     "params": {"guides": "int", "strands_per_guide": "int", "length": "float"},
     "run": lambda a: {"guide_count": a.get("guides", 500), "total_strands": a.get("guides", 500) * a.get("strands_per_guide", 10),
                      "strand_length": a.get("length", 0.15), "interpolation": "interpolate_curve", "root_uv": True}},

    {"name": "three_d_terrain", "description": "Generate terrain heightmap settings with erosion simulation.",
     "params": {"size": "int", "height_scale": "float", "erosion_steps": "int"},
     "run": lambda a: {"size": a.get("size", 1024), "height_scale": a.get("height_scale", 100.0),
                      "erosion_passes": _terrain_erosion(a.get("erosion_steps", 5)), "noise_type": "ridged"}},

    {"name": "three_d_style_transfer", "description": "Apply artistic style transfer to a 3D mesh's textures.",
     "params": {"mesh": "str", "style_image": "str", "strength": "float"},
     "run": lambda a: {"mesh": a.get("mesh", "model.glb"), "style": a.get("style_image", "vangogh.jpg"),
                      "strength": a.get("strength", 0.8), "target": "albedo"}},

    {"name": "three_d_to_lineart", "description": "Convert a 3D scene to 2D lineart / technical drawing.",
     "params": {"mesh": "str", "line_style": "str", "edges": "bool"},
     "run": lambda a: {"line_style": a.get("line_style", "technical"), "include_edges": a.get("edges", True),
                      "include_silhouette": True, "include_creases": True, "output": "svg"}},
]