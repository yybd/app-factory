#!/usr/bin/env python3
"""Say which language fell behind — and which reference points at nothing.

    python3 scripts/check_content.py            # from anywhere inside the site repo
    python3 scripts/check_content.py --root .   # or name the root explicitly
    python3 scripts/check_content.py --strict   # treat every warning as an error

**Why this exists.** Under the `strict` fallback policy the build already fails on a
missing translation. Under `fallback` and `hide` it does not — and that is exactly when
a language quietly stops being maintained and nobody notices for a year. A checker is
the only thing that looks.

**What it checks** — against `locales.json`, which is the one authority on the
language set:

  mirror      a page the default language has and another language does not
  orphan      a page that exists ONLY outside the default language, so nothing routes it
  media       an image/video/audio named in Markdown that is not in media/
  captions    a video or audio file with no caption track in some declared language
  frontmatter a .md with no `title`, or two files sharing a `slug` in one language
  data        a localized field present in one language and missing in another

**Stdlib only** — no install, so it runs in CI and on a machine that never ran `npm i`.
The front-matter parser is deliberately minimal (top-level `key: value`); it reads
`title` and `slug` and nothing else, and does not pretend to be YAML.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

MEDIA_REF = re.compile(
    r"!\[[^\]]*\]\(\s*<?([^)>\s]+)"          # ![alt](path)
    r"|<(?:img|source|video|audio|track)\b[^>]*?\bsrc=[\"']([^\"']+)"
)
VIDEO_AUDIO = {".mp4", ".webm", ".ogg", ".ogv", ".mov", ".m4a", ".mp3", ".wav"}
SKIP_REF = ("http://", "https://", "//", "data:", "mailto:", "tel:", "#")

errors: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def find_root(start: Path) -> Path:
    for d in [start, *start.parents]:
        if (d / "locales.json").is_file():
            return d
    sys.exit("check_content: no locales.json found — run inside a scaffolded content site.")


def front_matter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    data = {}
    for line in text[3:end].splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        data[k.strip()] = v.strip().strip("\"'")
    return data


def pages(text_dir: Path, code: str) -> dict:
    """{'reference/shabbat': Path} for one language."""
    base = text_dir / code
    if not base.is_dir():
        return {}
    return {
        str(p.relative_to(base).with_suffix("")).replace(os.sep, "/"): p
        for p in sorted(base.rglob("*.md"))
    }


def check_media_refs(root: Path, md: Path, code: str, page: str) -> None:
    for m in MEDIA_REF.finditer(md.read_text(encoding="utf-8", errors="replace")):
        ref = (m.group(1) or m.group(2) or "").strip()
        if not ref or ref.startswith(SKIP_REF):
            continue
        rel = ref.split("?", 1)[0].split("#", 1)[0].lstrip("/")
        where = (root / "src" / rel, root / rel, root / "public" / rel, md.parent / rel)
        if not any(c.exists() for c in where):
            fail(f"media: {code}/{page}.md references '{ref}' — no such file")


def check_captions(root: Path, codes: list[str]) -> None:
    media = root / "src" / "media"
    if not media.is_dir():
        return
    captions = media / "captions"
    for f in sorted(media.rglob("*")):
        if f.suffix.lower() not in VIDEO_AUDIO or captions in f.parents:
            continue
        for code in codes:
            if not (captions / code / f"{f.stem}.vtt").is_file():
                warn(
                    f"captions: {f.relative_to(root)} has no "
                    f"captions/{code}/{f.stem}.vtt — that content is unavailable in {code}"
                )


def localized_fields(node, path: str, codes: set, default: str, where: str) -> None:
    if isinstance(node, dict):
        keys = set(node)
        if keys and keys <= codes and default in keys:
            missing = sorted(codes - keys)
            if missing:
                warn(f"data: {where}{path} is missing {', '.join(missing)}")
            return
        for k, v in node.items():
            localized_fields(v, f"{path}.{k}", codes, default, where)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            localized_fields(v, f"{path}[{i}]", codes, default, where)


def main() -> int:
    ap = argparse.ArgumentParser(description="Check a multilingual content tree.")
    ap.add_argument("--root", default=".", help="site root (default: search upward)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = ap.parse_args()

    root = find_root(Path(args.root).resolve())
    manifest = json.loads((root / "locales.json").read_text(encoding="utf-8"))
    default = manifest["default"]
    codes = list(manifest["locales"])
    policy = manifest.get("fallback", "fallback")
    if default not in codes:
        sys.exit(f"check_content: default '{default}' is not in locales.")

    text_dir = root / "src" / "text"
    if not text_dir.is_dir():
        sys.exit(f"check_content: {text_dir.relative_to(root)} does not exist.")

    by_code = {c: pages(text_dir, c) for c in codes}
    missing_is_error = policy == "strict"

    for code in codes:
        if not (text_dir / code).is_dir():
            fail(f"tree: no folder for declared locale '{code}' — create it even if empty")

    # mirror + orphan
    for page in sorted(by_code[default]):
        for code in codes:
            if code == default or page in by_code[code]:
                continue
            msg = f"mirror: '{page}' exists in {default} but not in {code}"
            (fail if missing_is_error else warn)(msg + f" (policy: {policy})")

    for code in codes:
        if code == default:
            continue
        for page in sorted(set(by_code[code]) - set(by_code[default])):
            fail(f"orphan: '{page}' exists only in {code} — nothing routes it")

    # front-matter + media
    for code in codes:
        slugs: dict[str, str] = {}
        for page, path in sorted(by_code[code].items()):
            data = front_matter(path.read_text(encoding="utf-8", errors="replace"))
            if not data.get("title"):
                fail(f"frontmatter: {code}/{page}.md has no title")
            slug = data.get("slug") or page
            if slug in slugs:
                fail(f"slug: '{slug}' used by both {code}/{slugs[slug]}.md and {code}/{page}.md")
            slugs[slug] = page
            check_media_refs(root, path, code, page)

    check_captions(root, codes)

    data_dir = root / "src" / "data"
    if data_dir.is_dir():
        for f in sorted(data_dir.rglob("*.json")):
            try:
                payload = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                fail(f"data: {f.relative_to(root)} is not valid JSON — {e}")
                continue
            localized_fields(payload, "", set(codes), default, f"{f.relative_to(root)}")

    if args.strict:
        errors.extend(warnings)
        warnings.clear()

    for w in warnings:
        print(f"warn   {w}")
    for e in errors:
        print(f"ERROR  {e}")

    counted = sum(len(v) for v in by_code.values())
    print(
        f"\n{counted} content files across {len(codes)} languages "
        f"(default: {default}, fallback: {policy}) — "
        f"{len(errors)} errors, {len(warnings)} warnings"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
