#!/usr/bin/env python3
"""
scan_bugs.py — heuristic bug-signal scanner for an Apple (iOS/macOS) app.

Emits JSON the model interprets against the curated bug catalog. These are
HEURISTICS, not findings: a `try!` on a constant regex is fine; a `try!` on
network input is a crash. Confirm every candidate by reading the actual code
path before reporting it. Runtime bugs (races, leaks, off-main UI) are only
*suspected* here — confirm them with the analyzer/sanitizers (see
references/runtime-diagnostics.md).

Usage:
    python3 scan_bugs.py <project-root>

Stdlib only. Line-based regex matching; counts are line-match counts (prevalence
signals), not exact occurrence counts.
"""

import argparse
import json
import os
import re
import sys

CODE_EXTS = (".swift", ".m", ".mm", ".h")
SKIP_DIRS = {".git", "Pods", "Carthage", "DerivedData", "build", ".build",
             "node_modules", ".swiftpm", "fastlane"}
# Test files: still scanned, but the model should weight findings there lower.
TEST_HINT = re.compile(r"(?i)(tests?|spec|mock|fixture)")

# Pattern groups: name -> list of regexes. Match per line; collect a few examples.
PATTERNS = {
    # --- Framework detection ---
    "uses_swiftui": [r"import SwiftUI"],
    "uses_uikit": [r"import UIKit"],
    "uses_appkit": [r"import (?:AppKit|Cocoa)"],

    # --- A1: unsafe optionals & force operations ---
    "try_bang": [r"\btry!\s"],
    "as_bang": [r"\bas!\s"],
    "force_unwrap": [r"[A-Za-z0-9_\)\]]\!\.",        # foo!.bar
                     r"[A-Za-z0-9_\)\]]\![\)\],;]",   # foo!)  foo!]  foo!,  foo!;
                     r"[\)\]]\!(?=\s|$)"],            # URL(...)!  arr[i]!  (then space/EOL)
    "iuo_decl": [r"\b(?:var|let)\s+\w+\s*:\s*[A-Za-z_][\w<>\.\[\], ]*\!\s*(?:$|=|//|\{)"],
    "fatal_error": [r"\bfatalError\(", r"\bpreconditionFailure\("],

    # --- A2: SwiftUI state ownership (the @StateObject bug) ---
    "observedobject_assigned": [r"@ObservedObject\s+(?:private\s+|fileprivate\s+)?var\s+\w+\s*="],
    "stateobject": [r"@StateObject\b"],
    "observable_macro": [r"@Observable\b", r"@Bindable\b"],

    # --- A4/A5: concurrency ---
    "main_actor": [r"@MainActor\b"],
    "dispatch_main_async": [r"DispatchQueue\.main\.async"],
    "dispatch_main_sync": [r"DispatchQueue\.main\.sync"],  # deadlock risk
    "dispatch_global": [r"DispatchQueue\.global"],
    "task_block": [r"\bTask\s*\{", r"\bTask\(priority"],
    "detached_task": [r"Task\.detached"],
    "continuation": [r"with(?:Checked|Unsafe)(?:Throwing)?Continuation"],
    "semaphore": [r"DispatchSemaphore", r"\.wait\(\)"],

    # --- B1/B2: memory & lifecycle hygiene ---
    "escaping_closure": [r"@escaping\b"],
    "weak_self": [r"\[weak self\]"],
    "unowned_self": [r"\[unowned self\]"],
    "combine_sink": [r"\.sink\b", r"\.assign\(to:"],
    "cancellable_store": [r"store\(in:\s*&", r"Set<AnyCancellable>"],
    "timer_scheduled": [r"Timer\.scheduledTimer", r"Timer\(timeInterval"],
    "notification_add": [r"\.addObserver\("],
    "notification_remove": [r"\.removeObserver\("],
    "kvo_observe": [r"\bobserve\(\\?\.", r"addObserver\(self,\s*forKeyPath"],
    "delegate_property": [r"\bvar\s+\w*[Dd]elegate\b"],
    "weak_delegate": [r"\bweak\s+var\s+\w*[Dd]elegate\b"],
    "deinit_defined": [r"\bdeinit\b"],

    # --- A6: error handling ---
    "try_optional": [r"\btry\?\s"],
    "empty_catch": [r"catch\s*\{\s*\}"],
    "catch_block": [r"\bcatch\b"],
    "catch_print_only": [r"catch\s*\{\s*print\("],

    # --- A8/A9: dates, persistence, data integrity ---
    "dateformatter": [r"DateFormatter\(\)", r"NSDateFormatter"],
    "posix_locale": [r'Locale\(identifier:\s*"en_US_POSIX"'],
    "context_save": [r"\.save\(\)", r"try\s+\w*[Cc]ontext\.save"],
    "userdefaults": [r"UserDefaults\b"],
    "file_write": [r"\.write\(to:", r"Data\(contentsOf:"],
    "codable_decode": [r"JSONDecoder\(\)", r"\.decode\("],

    # --- B5: networking ---
    "urlsession": [r"URLSession\b"],
    "url_timeout": [r"timeoutInterval", r"timeoutIntervalFor"],
    "offline_handling": [r"notConnectedToInternet", r"NWPathMonitor", r"Reachability", r"NSURLErrorNotConnectedToInternet"],

    # --- B7: debug & dead code ---
    "debug_print": [r"\bprint\(", r"\bNSLog\(", r"\bdebugPrint\("],
    "todo_marker": [r"(?i)//\s*(?:TODO|FIXME|HACK|XXX|BUG)\b", r"(?i)#warning\("],
    "hardcoded_local": [r"http://localhost", r"127\.0\.0\.1", r"http://\d", r"\.ngrok\."],

    # --- C: user-flow code smells ---
    "progress_view": [r"\bProgressView\b", r"UIActivityIndicatorView", r"NSProgressIndicator"],
    "empty_state": [r"(?i)\bempty\b", r"(?i)no (?:items|results|data|documents)"],
    "error_alert": [r"\.alert\(", r"UIAlertController", r"NSAlert\("],
    "permission_request": [r"requestAuthorization", r"requestAccess\(for", r"PHPhotoLibrary\.requestAuthorization",
                            r"CLLocationManager", r"UNUserNotificationCenter", r"AVCaptureDevice\.requestAccess"],
    "authorization_status": [r"authorizationStatus", r"\.denied\b", r"\.restricted\b", r"\.notDetermined\b"],
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
    test_counts = {k: 0 for k in PATTERNS}
    examples = {k: [] for k in PATTERNS}
    files_scanned = 0
    for path in iter_files(root):
        files_scanned += 1
        is_test = bool(TEST_HINT.search(os.path.basename(path)))
        try:
            with open(path, "r", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            continue
        for i, line in enumerate(lines, 1):
            for key, regexes in compiled.items():
                if any(rx.search(line) for rx in regexes):
                    counts[key] += 1
                    if is_test:
                        test_counts[key] += 1
                    if len(examples[key]) < 3:
                        examples[key].append({
                            "file": rel(root, path), "line": i,
                            "text": line.strip()[:140],
                            "in_test": is_test,
                        })
    return counts, test_counts, examples, files_scanned


def derive(c):
    """Interpreted hints to orient the reviewer. Still heuristics."""
    framework = []
    if c["uses_swiftui"]:
        framework.append("SwiftUI")
    if c["uses_uikit"]:
        framework.append("UIKit")
    if c["uses_appkit"]:
        framework.append("AppKit")

    unsafe_optionals = c["try_bang"] + c["as_bang"] + c["force_unwrap"] + c["iuo_decl"]
    escaping = c["escaping_closure"] + c["combine_sink"] + c["timer_scheduled"]
    weak_captures = c["weak_self"] + c["unowned_self"]

    hints = []
    if unsafe_optionals > 0:
        hints.append(f"A1: {unsafe_optionals} unsafe-optional sites (try!/as!/force-unwrap/IUO) — confirm each is a safe constant, not runtime/user/network input.")
    if c["observedobject_assigned"] > 0:
        hints.append(f"A2: {c['observedobject_assigned']} @ObservedObject assigned at declaration — likely should be @StateObject (state silently lost on re-render).")
    if escaping > 0 and weak_captures == 0:
        hints.append(f"B1: {escaping} escaping/closure/timer sites and 0 [weak/unowned self] — inspect for retain cycles.")
    elif escaping > weak_captures * 3 and escaping > 5:
        hints.append(f"B1: {escaping} escaping sites vs {weak_captures} weak/unowned captures — spot-check the escaping closures that capture self.")
    if c["dispatch_main_sync"] > 0:
        hints.append(f"A4: {c['dispatch_main_sync']} DispatchQueue.main.sync — deadlock risk if ever called on the main thread.")
    if c["empty_catch"] > 0 or c["catch_print_only"] > 0:
        hints.append(f"A6: {c['empty_catch']} empty catch + {c['catch_print_only']} print-only catch — swallowed errors; check the user is not left stuck.")
    if c["try_optional"] > 0:
        hints.append(f"A6: {c['try_optional']} try? sites — confirm a discarded error doesn't proceed with wrong/empty state.")
    if c["dateformatter"] > 0 and c["posix_locale"] == 0:
        hints.append(f"A8: {c['dateformatter']} DateFormatter uses and 0 en_US_POSIX locale — check locale/timezone correctness on machine-format parsing.")
    if c["notification_add"] > c["notification_remove"]:
        hints.append(f"B2: addObserver ({c['notification_add']}) > removeObserver ({c['notification_remove']}) — check observers are balanced/removed.")
    if c["delegate_property"] - c["weak_delegate"] > 0:
        hints.append(f"B1: {c['delegate_property'] - c['weak_delegate']} delegate properties not declared weak — possible retain cycle.")
    if c["urlsession"] > 0 and c["url_timeout"] == 0:
        hints.append(f"B5: URLSession used with no explicit timeoutInterval — check request timeouts.")
    if c["urlsession"] > 0 and c["offline_handling"] == 0:
        hints.append("B5: networking present with no offline-detection signal — verify the offline state in the flow audit.")
    if c["permission_request"] > 0 and c["authorization_status"] == 0:
        hints.append(f"C3: {c['permission_request']} permission requests and no authorization-status checks — verify the DENIED/restricted branch is handled.")
    if c["debug_print"] > 0:
        hints.append(f"B7: {c['debug_print']} print/NSLog sites — remove or gate behind #if DEBUG.")
    if c["todo_marker"] > 0:
        hints.append(f"B7: {c['todo_marker']} TODO/FIXME/HACK/#warning markers — known-unfinished paths to review.")
    if c["hardcoded_local"] > 0:
        hints.append(f"B7: {c['hardcoded_local']} hardcoded localhost/IP/tunnel endpoints — must not ship.")
    if c["continuation"] > 0:
        hints.append(f"A5: {c['continuation']} continuations — verify each resumes exactly once (double-resume traps, never-resume hangs).")

    return {
        "ui_frameworks": framework or ["unknown"],
        "unsafe_optional_sites": unsafe_optionals,
        "escaping_vs_weak": {"escaping_sites": escaping, "weak_unowned_captures": weak_captures},
        "swiftui_state_risk": c["observedobject_assigned"],
        "swallowed_errors": {"empty_catch": c["empty_catch"], "try_optional": c["try_optional"], "print_only_catch": c["catch_print_only"]},
        "observer_balance": {"add": c["notification_add"], "remove": c["notification_remove"]},
        "permission_flow_risk": c["permission_request"] > 0 and c["authorization_status"] == 0,
        "debug_leftovers": {"print": c["debug_print"], "todo": c["todo_marker"], "hardcoded_local": c["hardcoded_local"]},
        "hints": hints,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(json.dumps({"error": f"not a directory: {root}"}))
        sys.exit(1)
    counts, test_counts, examples, files_scanned = scan(root)
    report = {
        "project_root": root,
        "files_scanned": files_scanned,
        "derived": derive(counts),
        "raw_counts": counts,
        "matches_in_test_files": {k: v for k, v in test_counts.items() if v},
        "examples": {k: v for k, v in examples.items() if v},
        "notes": [
            "Heuristics only — confirm each candidate against the real code path before reporting.",
            "Force-unwrap/try!/as! on compile-time constants are usually fine; on user/network/IO input they are crash risks.",
            "Runtime bugs (races, leaks, off-main UI) are only SUSPECTED here — confirm with the analyzer + sanitizers (references/runtime-diagnostics.md).",
            "Counts are line-match counts, not exact occurrence counts; treat as prevalence signals.",
            "matches_in_test_files: weight findings in test/mock files lower.",
            "Map each candidate to a bug-catalog category (A1, A4, B1, ...) and rank by user impact.",
        ],
    }
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
