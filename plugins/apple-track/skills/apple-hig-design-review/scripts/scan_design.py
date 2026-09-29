#!/usr/bin/env python3
"""
scan_design.py — heuristic design-signal scanner for an Apple app.

Emits JSON the model interprets against the curated HIG topics. These are
HEURISTICS, not findings: e.g. "many hardcoded font sizes" is a prompt to look
at typography, not proof of a problem. Design needs human/visual judgment —
confirm everything against the code and, ideally, the running UI.

Usage:
    python3 scan_design.py <project-root>

Stdlib only.
"""

import argparse
import json
import os
import re
import sys

CODE_EXTS = (".swift", ".m", ".mm", ".h")
SKIP_DIRS = {".git", "Pods", "Carthage", "DerivedData", "build", ".build", "node_modules"}

# Pattern groups: name -> list of regexes. We count matches across the codebase
# and collect a few examples, so the model gets a sense of prevalence.
PATTERNS = {
    # Framework detection
    "uses_swiftui": [r"import SwiftUI"],
    "uses_uikit": [r"import UIKit"],
    "uses_appkit": [r"import (?:AppKit|Cocoa)"],

    # Accessibility coverage
    "accessibility_label": [r"\.accessibilityLabel\(", r"accessibilityLabel\s*="],
    "accessibility_hidden": [r"\.accessibilityHidden\(", r"accessibilityElementsHidden"],
    "accessibility_traits": [r"\.accessibility(?:AddTraits|Element|Value|Hint)\(", r"accessibilityTraits"],
    "reduce_motion": [r"accessibilityReduceMotion", r"isReduceMotionEnabled"],

    # Interactive elements (denominator for "do they have labels?")
    "buttons": [r"\bButton\b", r"UIButton", r"NSButton"],
    "icon_only_image": [r"Image\(systemName:", r"Image\(nsImage:", r"Image\(uiImage:"],
    "tap_gestures": [r"\.onTapGesture", r"addGestureRecognizer", r"UITapGestureRecognizer"],

    # Typography
    "hardcoded_font_size": [r"\.font\(\.system\(size:\s*\d", r"systemFont\(ofSize:", r"\.font\(\.custom\([^)]*,\s*size:\s*\d"],
    "dynamic_type_textstyle": [r"\.font\(\.(?:largeTitle|title|title2|title3|headline|subheadline|body|callout|footnote|caption|caption2)\b", r"preferredFont\(forTextStyle", r"adjustsFontForContentSizeCategory", r"@ScaledMetric", r"UIFontMetrics"],

    # Color & Dark Mode
    "hardcoded_color": [r"Color\(red:\s*[\d.]", r"UIColor\(red:\s*[\d.]", r"NSColor\(red:\s*[\d.]", r"Color\(\.sRGB"],
    "literal_bw": [r"\.foregroundColor\(\.(?:white|black)\)", r"\.background\(Color\.(?:white|black)\)"],
    "semantic_color": [r"Color\.(?:primary|secondary|accentColor)", r"UIColor\.(?:label|secondaryLabel|systemBackground|secondarySystemBackground|tintColor)", r"\.foregroundStyle\(\.(?:primary|secondary|tint)", r"Color\(\"", r"Color\(.*?bundle:"],
    "dark_mode_handling": [r"colorScheme", r"UITraitCollection.*userInterfaceStyle", r"overrideUserInterfaceStyle"],

    # Layout & adaptivity
    "fixed_frame": [r"\.frame\((?:[^)]*\b)?width:\s*\d", r"\.frame\((?:[^)]*\b)?height:\s*\d"],
    "flexible_frame": [r"\.frame\(.*(?:minWidth|maxWidth|minHeight|maxHeight)", r"\bSpacer\(", r"\.layoutPriority"],
    "ignores_safe_area": [r"ignoresSafeArea", r"edgesIgnoringSafeArea"],
    "size_classes": [r"horizontalSizeClass", r"verticalSizeClass", r"NavigationSplitView"],

    # Controls / platform
    "tooltip_help": [r"\.help\("],
    "context_menu": [r"\.contextMenu", r"NSMenu", r"menuForEvent"],
    "keyboard_shortcuts": [r"\.keyboardShortcut\(", r"keyEquivalent", r"\.commands\b"],
    "presentation_detents": [r"presentationDetents"],

    # State / feedback
    "progress_indicator": [r"ProgressView", r"UIActivityIndicatorView", r"NSProgressIndicator"],
    "empty_state_hint": [r"(?i)no (?:items|results|documents|data)", r"(?i)empty", r"emptyState"],
    "localization": [r"NSLocalizedString", r'String\(localized:'],
}


def iter_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(CODE_EXTS):
                yield os.path.join(dirpath, fn)


def rel(root, path):
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def scan(root):
    compiled = {k: [re.compile(p) for p in pats] for k, pats in PATTERNS.items()}
    counts = {k: 0 for k in PATTERNS}
    examples = {k: [] for k in PATTERNS}
    files_scanned = 0
    for path in iter_files(root):
        files_scanned += 1
        try:
            with open(path, "r", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for key, regexes in compiled.items():
                if any(rx.search(line) for rx in regexes):
                    counts[key] += 1
                    if len(examples[key]) < 3:
                        examples[key].append({"file": rel(root, path), "line": i, "text": line.strip()[:140]})
    return counts, examples, files_scanned


def derive(counts):
    """A few interpreted ratios to orient the reviewer. Still heuristics."""
    interactive = counts["buttons"] + counts["icon_only_image"] + counts["tap_gestures"]
    labels = counts["accessibility_label"] + counts["accessibility_traits"]
    framework = []
    if counts["uses_swiftui"]:
        framework.append("SwiftUI")
    if counts["uses_uikit"]:
        framework.append("UIKit")
    if counts["uses_appkit"]:
        framework.append("AppKit")
    return {
        "ui_frameworks": framework or ["unknown"],
        "interactive_elements_est": interactive,
        "accessibility_annotations": labels,
        "accessibility_coverage_hint": (
            "none" if labels == 0 and interactive > 0
            else "partial" if labels < interactive
            else "ok-ish"
        ),
        "typography": {
            "hardcoded_sizes": counts["hardcoded_font_size"],
            "dynamic_type_uses": counts["dynamic_type_textstyle"],
            "hint": "review typography" if counts["hardcoded_font_size"] > counts["dynamic_type_textstyle"] else "looks dynamic",
        },
        "color": {
            "hardcoded_colors": counts["hardcoded_color"] + counts["literal_bw"],
            "semantic_colors": counts["semantic_color"],
            "dark_mode_signals": counts["dark_mode_handling"],
            "hint": "check dark mode / contrast" if (counts["hardcoded_color"] + counts["literal_bw"]) > counts["semantic_color"] and counts["dark_mode_handling"] == 0 else "has semantic/dark handling",
        },
        "localization_present": counts["localization"] > 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(json.dumps({"error": f"not a directory: {root}"}))
        sys.exit(1)
    counts, examples, files_scanned = scan(root)
    report = {
        "project_root": root,
        "files_scanned": files_scanned,
        "derived": derive(counts),
        "raw_counts": counts,
        "examples": {k: v for k, v in examples.items() if v},
        "notes": [
            "Heuristics only — confirm against code and the running UI before recommending.",
            "accessibility_coverage_hint 'none'/'partial' with interactive elements => inspect for unlabeled controls.",
            "typography.hint 'review typography' => many fixed font sizes vs Dynamic Type styles.",
            "color.hint 'check dark mode' => hardcoded colors and no dark-mode handling.",
            "fixed_frame >> flexible_frame => check adaptivity / resizing.",
            "Counts are line-match counts, not exact element counts; treat as prevalence signals.",
        ],
    }
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
