"""
asset_resolver.py
=================
Finds a real client asset (image/video) that matches an ad angle,
so fb_campaign_runner.py can use real photos instead of AI-generated ones.

Usage (from campaign runner):
    from asset_resolver import resolve_asset
    path = resolve_asset("sugar_shack", "bulk_candy_budget")
    # Returns absolute path string if match found, None otherwise
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
SUPPORTED_VIDEOS = {".mp4", ".mov", ".avi"}


def _assets_dir(business_key: str) -> Path:
    return BASE_DIR / business_key / "assets"


def _load_index(business_key: str) -> list:
    index_path = _assets_dir(business_key) / "assets_index.json"
    if not index_path.exists():
        return []
    try:
        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("assets", [])
    except Exception:
        return []


def resolve_asset(business_key: str, angle: str, media_type: str = "image") -> str | None:
    """
    Find the best matching asset for a given ad angle.

    Priority:
      1. Exact angle match in assets_index.json  (best_for contains angle)
      2. Tag match                                (tags overlap with angle words)
      3. Any available image if index is empty    (auto-scan folder)

    Returns absolute path string, or None if nothing found.
    """
    assets = _load_index(business_key)
    angle_words = set(angle.lower().replace("_", " ").split())
    ext_filter = SUPPORTED_IMAGES if media_type == "image" else SUPPORTED_VIDEOS

    # -- Pass 1: exact best_for match
    for asset in assets:
        best_for = [b.lower() for b in asset.get("best_for", [])]
        if angle.lower() in best_for or any(angle_words & set(b.split()) for b in best_for):
            path = _assets_dir(business_key) / asset["file"]
            if path.exists() and path.suffix.lower() in ext_filter:
                return str(path)

    # -- Pass 2: tag overlap
    for asset in assets:
        tags = [t.lower() for t in asset.get("tags", [])]
        if angle_words & set(tags):
            path = _assets_dir(business_key) / asset["file"]
            if path.exists() and path.suffix.lower() in ext_filter:
                return str(path)

    # -- Pass 3: auto-scan folder (no index entry needed — just drop files in)
    scan_dirs = ["images"] if media_type == "image" else ["videos"]
    for subdir in scan_dirs:
        folder = _assets_dir(business_key) / subdir
        if folder.exists():
            files = [f for f in folder.iterdir() if f.suffix.lower() in ext_filter]
            if files:
                # Return most recently modified file as best guess
                files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                return str(files[0])

    return None


def list_assets(business_key: str) -> dict:
    """Return a summary of all available assets for a business."""
    assets_dir = _assets_dir(business_key)
    result = {"indexed": [], "unindexed": {"images": [], "videos": [], "references": []}}

    # Indexed entries
    for asset in _load_index(business_key):
        path = assets_dir / asset["file"]
        result["indexed"].append({
            "file": asset["file"],
            "exists": path.exists(),
            "description": asset.get("description", ""),
            "tags": asset.get("tags", []),
            "best_for": asset.get("best_for", []),
        })

    # Unindexed files (dropped in without an index entry)
    indexed_files = {a["file"] for a in _load_index(business_key)}
    for subdir, key in [("images", "images"), ("videos", "videos"), ("references", "references")]:
        folder = assets_dir / subdir
        if folder.exists():
            for f in sorted(folder.iterdir()):
                rel = f"{subdir}/{f.name}"
                if rel not in indexed_files:
                    result["unindexed"][key].append(f.name)

    return result


def add_asset(business_key: str, file_relative: str, description: str = "",
              tags: list = None, best_for: list = None) -> bool:
    """
    Add or update an entry in assets_index.json.

    file_relative: path relative to assets/ folder, e.g. "images/storefront.jpg"
    """
    index_path = _assets_dir(business_key) / "assets_index.json"
    try:
        with open(index_path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"assets": []}

    assets = data.get("assets", [])

    # Update existing or append
    for asset in assets:
        if asset["file"] == file_relative:
            asset["description"] = description
            if tags is not None:
                asset["tags"] = tags
            if best_for is not None:
                asset["best_for"] = best_for
            break
    else:
        assets.append({
            "file": file_relative,
            "description": description,
            "tags": tags or [],
            "best_for": best_for or [],
        })

    data["assets"] = assets
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return True


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Asset resolver CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser("list", help="List all assets for a business")
    p_list.add_argument("business")

    p_resolve = sub.add_parser("resolve", help="Find best asset for an angle")
    p_resolve.add_argument("business")
    p_resolve.add_argument("angle")
    p_resolve.add_argument("--type", default="image", choices=["image", "video"])

    p_add = sub.add_parser("add", help="Add/update an asset index entry")
    p_add.add_argument("business")
    p_add.add_argument("file", help="Relative path, e.g. images/storefront.jpg")
    p_add.add_argument("--description", default="")
    p_add.add_argument("--tags", nargs="*", default=[])
    p_add.add_argument("--best-for", nargs="*", default=[], dest="best_for")

    args = parser.parse_args()

    if args.cmd == "list":
        summary = list_assets(args.business)
        print(f"\n=== Assets: {args.business} ===")
        print(f"Indexed ({len(summary['indexed'])}):")
        for a in summary["indexed"]:
            status = "✓" if a["exists"] else "✗ MISSING"
            print(f"  [{status}] {a['file']} — {a['description']}")
            print(f"         tags: {a['tags']}  best_for: {a['best_for']}")
        for kind, files in summary["unindexed"].items():
            if files:
                print(f"\nUnindexed {kind} ({len(files)}) — drop in folder, auto-used as fallback:")
                for f in files:
                    print(f"  {f}")

    elif args.cmd == "resolve":
        result = resolve_asset(args.business, args.angle, args.type)
        if result:
            print(f"[MATCH] {result}")
        else:
            print("[NO MATCH] No asset found — will use fal.ai generation")

    elif args.cmd == "add":
        add_asset(args.business, args.file, args.description, args.tags, args.best_for)
        print(f"[OK] Added {args.file} to {args.business} index")

    else:
        parser.print_help()
