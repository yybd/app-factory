#!/usr/bin/env python3
"""
scan_project.py — deterministic compliance signals for an Xcode project.

Emits JSON evidence the model interprets against the curated guidelines. It is
intentionally conservative: it reports what it *sees* (API references, plist
keys, entitlements, feature signals) and never decides pass/fail on its own.
Over-flagging is expected — confirm each signal against the real code.

Usage:
    python3 scan_project.py <project-root> [--json] [--target NAME]

Stdlib only (plistlib, re, json, os, argparse, glob).
"""

import argparse
import glob
import json
import os
import plistlib
import re
import sys

# --- API reference -> required Info.plist usage-description key (5.1.1) -------
# Each: list of code substrings that imply the permission -> plist key(s).
USAGE_STRING_APIS = {
    "NSCameraUsageDescription": ["AVCaptureDevice", "UIImagePickerController", ".camera"],
    "NSMicrophoneUsageDescription": ["AVAudioRecorder", "AVCaptureDevice.*audio", "requestRecordPermission"],
    "NSPhotoLibraryUsageDescription": ["PHPhotoLibrary", "PHAsset", "photoLibrary"],
    "NSPhotoLibraryAddUsageDescription": ["UIImageWriteToSavedPhotosAlbum", "PHAssetChangeRequest.creationRequestForAsset"],
    "NSLocationWhenInUseUsageDescription": ["CLLocationManager", "requestWhenInUseAuthorization", "requestLocation"],
    "NSLocationAlwaysAndWhenInUseUsageDescription": ["requestAlwaysAuthorization", "allowsBackgroundLocationUpdates"],
    "NSContactsUsageDescription": ["CNContactStore", "CNContact", "ABAddressBook"],
    "NSCalendarsUsageDescription": ["EKEventStore", "EKEvent"],
    "NSRemindersUsageDescription": ["EKReminder"],
    "NSBluetoothAlwaysUsageDescription": ["CBCentralManager", "CBPeripheralManager", "CoreBluetooth"],
    "NSLocalNetworkUsageDescription": ["NWBrowser", "NetServiceBrowser", "Bonjour", "_tcp.", "_udp."],
    "NSSpeechRecognitionUsageDescription": ["SFSpeechRecognizer"],
    "NSMotionUsageDescription": ["CMMotionManager", "CMPedometer", "CMSensorRecorder"],
    "NSFaceIDUsageDescription": ["LAContext", ".biometryType", "evaluatePolicy"],
    "NSAppleMusicUsageDescription": ["MPMediaLibrary", "MPMediaQuery", "MusicKit"],
    "NSHealthShareUsageDescription": ["HKHealthStore", "HealthKit"],
    "NSUserTrackingUsageDescription": ["ATTrackingManager", "advertisingIdentifier", "ASIdentifierManager"],
    "NSAppleEventsUsageDescription": ["NSAppleScript", "AEDeterminePermissionToAutomateTarget", "kAEDontExecute", "NSAppleEventDescriptor"],
}

# --- Required-Reason API categories (privacy manifest) -----------------------
# Apple defines exactly these five categories. Patterns below aim for broad
# detection within each; matches are evidence to confirm, not proof.
REQUIRED_REASON_APIS = {
    "NSPrivacyAccessedAPICategoryFileTimestamp": [
        r"\.creationDate", r"\.modificationDate", r"NSFileModificationDate",
        r"\.fileModificationDate", r"contentModificationDateKey",
        r"\b[lf]?stat\(", r"getattrlist", r"attributesOfItem",
    ],
    "NSPrivacyAccessedAPICategorySystemBootTime": [
        r"systemUptime", r"mach_absolute_time", r"\.bootTime",
        r"CLOCK_UPTIME", r"clock_gettime",
    ],
    "NSPrivacyAccessedAPICategoryDiskSpace": [
        r"volumeAvailableCapacity", r"systemFreeSize", r"systemSize",
        r"NSFileSystemFreeSize", r"resourceValues.*volumeAvailable",
        r"\bstatfs\b", r"\bstatvfs\b", r"\bfstatfs\b",
    ],
    "NSPrivacyAccessedAPICategoryActiveKeyboards": [
        r"activeInputModes",
    ],
    "NSPrivacyAccessedAPICategoryUserDefaults": [
        r"UserDefaults", r"NSUserDefaults",
    ],
}

# --- Sensitive entitlements (macOS / signing) --------------------------------
SENSITIVE_ENTITLEMENTS = [
    "com.apple.security.temporary-exception.apple-events",
    "com.apple.security.temporary-exception",
    "com.apple.security.automation.apple-events",
    "com.apple.security.cs.disable-library-validation",
    "com.apple.security.cs.allow-unsigned-executable-memory",
    "com.apple.security.cs.allow-jit",
    "com.apple.security.cs.allow-dyld-environment-variables",
    "com.apple.security.files.all",
]

# --- Feature signals ----------------------------------------------------------
FEATURE_SIGNALS = {
    "storekit": [r"import StoreKit", r"\.purchase\(", r"Product\.products", r"SKPaymentQueue"],
    "iap_restore": [r"AppStore\.sync", r"restoreCompletedTransactions", r"Transaction\.currentEntitlements", r"Restore"],
    "social_login": [r"GIDSignIn", r"FBSDKLoginKit", r"LoginManager", r"GoogleSignIn", r"fbsdk", r"facebook\.com/dialog/oauth", r"accounts\.google\.com"],
    "sign_in_with_apple": [r"ASAuthorizationAppleIDProvider", r"SignInWithAppleButton", r"ASAuthorizationController"],
    "account_creation": [r"createUser", r"/register", r"/signup", r"signUp", r"registerUser", r"Auth\.auth\(\)\.createUser"],
    "account_deletion": [r"deleteUser", r"/delete[-_]?account", r"deleteAccount", r"\.delete\(\).*user"],
    "att_prompt": [r"ATTrackingManager\.requestTrackingAuthorization"],
    "tracking_sdk": [r"AppsFlyer", r"Adjust", r"FBSDKCoreKit", r"BranchSDK", r"Amplitude", r"Mixpanel"],
    "third_party_app_dependency": [r'bundleIdentifier == "com\.', r"runningApplications", r"NSWorkspace\.shared\.runningApplications", r"com\.microsoft\.", r"AXUIElement"],
    "webview_only_hint": [r"WKWebView", r"UIWebView"],
    "private_api_hint": [r"\bdlopen\(", r"\bdlsym\(", r"performSelector\(", r"valueForKey"],
    "external_purchase_link": [r"openURL.*(buy|upgrade|pricing|checkout|subscribe)", r"(stripe|paypal|checkout)\.com", r"https?://[^\"']*(buy|pricing|upgrade|checkout)"],
}

CODE_EXTS = (".swift", ".m", ".mm", ".h", ".c", ".cpp")
SKIP_DIRS = {".git", "Pods", "Carthage", "DerivedData", "build", ".build", "node_modules", "fastlane"}


def iter_files(root, exts):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(exts):
                yield os.path.join(dirpath, fn)


def rel(root, path):
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def grep_signals(root, patterns_map):
    """Return {key: [{file, line, text}]} for first match of each pattern per file."""
    hits = {k: [] for k in patterns_map}
    compiled = {k: [re.compile(p) for p in pats] for k, pats in patterns_map.items()}
    for path in iter_files(root, CODE_EXTS):
        try:
            with open(path, "r", errors="ignore") as f:
                lines = f.readlines()
        except OSError:
            continue
        for key, regexes in compiled.items():
            for i, line in enumerate(lines, 1):
                if any(rx.search(line) for rx in regexes):
                    hits[key].append({"file": rel(root, path), "line": i, "text": line.strip()[:160]})
                    break  # one hit per file per key is enough as evidence
    return {k: v for k, v in hits.items() if v}


def find_plists(root):
    out = []
    for path in iter_files(root, (".plist",)):
        if os.path.basename(path) == "Info.plist" or "Info" in os.path.basename(path):
            out.append(path)
    # also any plist literally named Info.plist anywhere
    return out


def load_plist(path):
    try:
        with open(path, "rb") as f:
            return plistlib.load(f)
    except Exception:
        return None


def scan_info_plists(root):
    result = []
    for path in find_plists(root):
        data = load_plist(path)
        if not isinstance(data, dict):
            continue
        usage_keys = {k: data[k] for k in data if k.endswith("UsageDescription")}
        result.append({
            "file": rel(root, path),
            "usage_keys_present": sorted(usage_keys.keys()),
            "LSUIElement": data.get("LSUIElement"),
            "bundle_id": data.get("CFBundleIdentifier"),
            "url_schemes_present": "CFBundleURLTypes" in data,
        })
    return result


def scan_entitlements(root):
    result = []
    for path in iter_files(root, (".entitlements",)):
        data = load_plist(path)
        if not isinstance(data, dict):
            continue
        sensitive = [k for k in data if any(k.startswith(s) or k == s for s in SENSITIVE_ENTITLEMENTS)]
        result.append({
            "file": rel(root, path),
            "app_sandbox": data.get("com.apple.security.app-sandbox"),
            "all_keys": sorted(data.keys()),
            "sensitive_entitlements": sorted(sensitive),
        })
    return result


def scan_privacy_manifest(root):
    manifests = []
    for path in iter_files(root, (".xcprivacy",)):
        data = load_plist(path)
        manifests.append({
            "file": rel(root, path),
            "tracking": (data or {}).get("NSPrivacyTracking") if isinstance(data, dict) else None,
            "accessed_api_categories": [
                t.get("NSPrivacyAccessedAPIType")
                for t in (data.get("NSPrivacyAccessedAPITypes") or [])
            ] if isinstance(data, dict) else [],
        })
    # also catch files literally named PrivacyInfo.xcprivacy that os.walk found above
    return manifests


# A subset of Apple's "commonly used SDKs" that must ship a signature + privacy
# manifest. Matched against framework/dependency folder names (case-insensitive).
KNOWN_SDKS = [
    "Alamofire", "Firebase", "FirebaseAnalytics", "FirebaseCrashlytics",
    "FirebaseAuth", "FirebaseFirestore", "FirebaseMessaging", "GoogleSignIn",
    "GoogleMobileAds", "GoogleUtilities", "FBSDKCoreKit", "FBAEMKit",
    "FBLPromises", "FBSDKLoginKit", "OneSignal", "Lottie", "SDWebImage",
    "SnapKit", "Realm", "RealmSwift", "RxSwift", "Kingfisher", "Adjust",
    "AppsFlyerLib", "Branch", "Amplitude", "Mixpanel", "Nimble", "Quick",
    "Sentry", "Charts", "PromiseKit", "Stripe", "Bugsnag", "Datadog",
    "Instabug", "AppLovin", "Crashlytics", "GTMSessionFetcher", "abseil",
]

# Dirs we WILL descend into here (the main scan skips these, but SDK manifests
# live exactly there). Still avoid build artifacts.
SDK_SEARCH_SKIP = {".git", "DerivedData", "build", ".build/artifacts"}


def scan_sdk_manifests(root):
    """Find bundled third-party SDK frameworks and whether each ships a privacy
    manifest. On iOS-family targets, a commonly-used SDK without a manifest is a
    frequent ITMS-91053 cause; the app's own manifest does NOT cover SDKs."""
    bundles = []
    for dirpath, dirnames, _ in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "DerivedData"}]
        for d in list(dirnames):
            if d.endswith((".framework", ".xcframework")):
                bundle = os.path.join(dirpath, d)
                has_manifest = False
                for bp, _bd, bf in os.walk(bundle):
                    if any(f.endswith(".xcprivacy") for f in bf):
                        has_manifest = True
                        break
                lower = d.lower()
                known = next((s for s in KNOWN_SDKS if s.lower() in lower), None)
                bundles.append({
                    "name": d,
                    "path": rel(root, bundle),
                    "has_privacy_manifest": has_manifest,
                    "known_sdk": known,
                })
    # Also note dependency manager presence (their checkouts may not be vendored
    # in-repo, so absence here doesn't mean no SDKs).
    managers = {
        "cocoapods": os.path.isfile(os.path.join(root, "Podfile")),
        "carthage": os.path.isfile(os.path.join(root, "Cartfile")),
        "spm": os.path.isfile(os.path.join(root, "Package.swift"))
               or bool(glob.glob(os.path.join(root, "**", "Package.resolved"), recursive=True)),
    }
    flagged = [b for b in bundles if not b["has_privacy_manifest"]]
    return {
        "dependency_managers": {k: v for k, v in managers.items() if v},
        "frameworks_found": len(bundles),
        "frameworks_without_manifest": [b for b in flagged],
        "all_frameworks": bundles,
        "note": ("SPM/CocoaPods packages are often resolved outside the repo "
                 "(DerivedData/SourcePackages); if a manager is present but few "
                 "frameworks were found here, check the resolved packages too."),
    }


def read_pbxproj(root):
    pbx = glob.glob(os.path.join(root, "*.xcodeproj", "project.pbxproj"))
    pbx += glob.glob(os.path.join(root, "**", "*.xcodeproj", "project.pbxproj"), recursive=True)
    text = ""
    for p in set(pbx):
        try:
            with open(p, "r", errors="ignore") as f:
                text += f.read()
        except OSError:
            pass
    return bool(pbx), text


def infoplist_keys_from_pbxproj(text):
    """Modern projects generate Info.plist from build settings. Extract the
    INFOPLIST_KEY_* entries so usage strings defined there aren't reported as
    missing. Returns (usage_keys_set, lsuielement_value_or_None)."""
    usage = set()
    for m in re.finditer(r"INFOPLIST_KEY_(NS\w*UsageDescription)\s*=", text):
        usage.add(m.group(1))
    lsui = None
    m = re.search(r"INFOPLIST_KEY_LSUIElement\s*=\s*([^;]+);", text)
    if m:
        lsui = m.group(1).strip().strip('"')
    return usage, lsui


ORIENT_UPSIDE = "UIInterfaceOrientationPortraitUpsideDown"


def _orient_from_setting(text, key_regex):
    m = re.search(key_regex, text)
    if not m:
        return None
    return [t for t in re.split(r"[\s,]+", m.group(1).strip())
            if t.startswith("UIInterfaceOrientation")]


def scan_ipad_multitasking(text, root):
    """iPad multitasking orientation requirement (upload-time bundle validation).

    An iPad app that does NOT opt out of multitasking (no UIRequiresFullScreen)
    must support all four interface orientations — including
    UIInterfaceOrientationPortraitUpsideDown — or App Store upload fails with
    "Invalid bundle ... orientations ... to support iPad multitasking".

    THE TRAP: the `~ipad` device suffix on `INFOPLIST_KEY_*` build settings is
    IGNORED by GENERATE_INFOPLIST_FILE (it won't even appear in
    `xcodebuild -showBuildSettings`). So a project can set
    `INFOPLIST_KEY_UISupportedInterfaceOrientations~ipad` to all four, look
    correct, yet ship a bundle whose base UISupportedInterfaceOrientations has
    only three — and get rejected. Only the BASE build-setting key (or a real
    Info.plist `~ipad` key) actually lands in the bundle. This check therefore
    credits the base build setting, the base plist array, and the plist `~ipad`
    array — but NOT the `~ipad` build setting."""
    families = set()
    for m in re.finditer(r"TARGETED_DEVICE_FAMILY = \"?([0-9,]+)\"?;", text):
        for n in m.group(1).split(","):
            families.add(n.strip())
    targets_ipad = "2" in families

    base_bs = _orient_from_setting(
        text, r"INFOPLIST_KEY_UISupportedInterfaceOrientations\s*=\s*\"([^\"]*)\"")
    ipad_bs = _orient_from_setting(
        text, r"INFOPLIST_KEY_UISupportedInterfaceOrientations~ipad\"?\s*=\s*\"([^\"]*)\"")
    rfs_bs = None
    m = re.search(r"INFOPLIST_KEY_UIRequiresFullScreen\s*=\s*([^;]+);", text)
    if m:
        rfs_bs = m.group(1).strip().strip('"')

    base_plist, ipad_plist, rfs_plist = None, None, None
    for path in find_plists(root):
        data = load_plist(path)
        if not isinstance(data, dict):
            continue
        if data.get("UISupportedInterfaceOrientations"):
            base_plist = list(data["UISupportedInterfaceOrientations"])
        if data.get("UISupportedInterfaceOrientations~ipad"):
            ipad_plist = list(data["UISupportedInterfaceOrientations~ipad"])
        if rfs_plist is None and "UIRequiresFullScreen" in data:
            rfs_plist = data.get("UIRequiresFullScreen")

    requires_full_screen = (str(rfs_bs).lower() in ("yes", "true", "1")) or bool(rfs_plist)
    # Orientation sources that ACTUALLY reach the bundle (base setting/plist, or
    # plist ~ipad) — deliberately excluding the ignored ~ipad build setting.
    effective_ipad = base_bs or base_plist or []
    if ipad_plist:  # a real plist ~ipad key overrides for iPad and DOES work
        effective_ipad = ipad_plist
    has_all_four = bool(effective_ipad) and ORIENT_UPSIDE in effective_ipad
    trap = (bool(ipad_bs) and ORIENT_UPSIDE in ipad_bs and not has_all_four)
    return {
        "targets_ipad": targets_ipad,
        "device_families": sorted(families),
        "requires_full_screen": requires_full_screen,
        "base_orientations_build_setting": base_bs,
        "ipad_orientations_build_setting_IGNORED": ipad_bs,
        "base_orientations_plist": base_plist,
        "ipad_orientations_plist": ipad_plist,
        "effective_ipad_orientations": effective_ipad or None,
        "ipad_suffix_build_setting_trap": trap,
        "likely_finding": targets_ipad and not requires_full_screen and not has_all_four,
    }


def detect_platforms_and_targets(root):
    platforms, targets, bundle_ids = set(), [], set()
    pbx_found, text = read_pbxproj(root)
    pbx = [1] if pbx_found else []
    if "SDKROOT = iphoneos" in text or "iphoneos" in text:
        platforms.add("iOS")
    if "SDKROOT = macosx" in text or "macosx" in text:
        platforms.add("macOS")
    for m in re.finditer(r"PRODUCT_BUNDLE_IDENTIFIER = ([^;]+);", text):
        bundle_ids.add(m.group(1).strip())
    for m in re.finditer(r"productType = \"com\.apple\.product-type\.application\";", text):
        targets.append("application")
    return {
        "platforms": sorted(platforms) or ["unknown"],
        "app_target_count": len(targets),
        "bundle_ids": sorted(bundle_ids),
        "pbxproj_found": bool(pbx),
    }


def cross_check_usage_strings(root, info_plists, generated_usage_keys):
    """For each usage API referenced in code, is the key present in any plist
    file OR in the generated-plist build settings (INFOPLIST_KEY_*)?"""
    present = set(generated_usage_keys)
    for p in info_plists:
        present.update(p["usage_keys_present"])
    findings = []
    api_hits = grep_signals(root, USAGE_STRING_APIS)
    for key, hits in api_hits.items():
        findings.append({
            "usage_key": key,
            "referenced_in_code": True,
            "present_in_plist": key in present,
            "evidence": hits[:3],
        })
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--json", action="store_true", help="(default) emit JSON")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(json.dumps({"error": f"not a directory: {root}"}))
        sys.exit(1)

    info_plists = scan_info_plists(root)
    _, pbx_text = read_pbxproj(root)
    generated_usage_keys, generated_lsui = infoplist_keys_from_pbxproj(pbx_text)
    report = {
        "project_root": root,
        "project": detect_platforms_and_targets(root),
        "info_plists": info_plists,
        "generated_infoplist": {
            "usage_keys_in_build_settings": sorted(generated_usage_keys),
            "LSUIElement": generated_lsui,
            "note": "Modern projects generate Info.plist from these settings; no Info.plist file may exist.",
        },
        "entitlements": scan_entitlements(root),
        "privacy_manifests": scan_privacy_manifest(root),
        "sdk_privacy_manifests": scan_sdk_manifests(root),
        "usage_string_checks": cross_check_usage_strings(root, info_plists, generated_usage_keys),
        "required_reason_apis_used": grep_signals(root, REQUIRED_REASON_APIS),
        "ipad_multitasking_orientations": scan_ipad_multitasking(pbx_text, root),
        "feature_signals": grep_signals(root, FEATURE_SIGNALS),
        "notes": [
            "Evidence only — confirm each signal against the code before reporting.",
            "usage_string_checks: present_in_plist=false is a likely 5.1.1 finding.",
            "PRIVACY MANIFEST IS PLATFORM-SPECIFIC: the Required-Reason API manifest is enforced only on iOS/iPadOS/tvOS/watchOS/visionOS. For a macOS-only app, do NOT report a missing manifest as a blocker.",
            "required_reason_apis_used + empty privacy_manifests => likely manifest finding ONLY on iOS-family targets (see project.platforms).",
            "sdk_privacy_manifests.frameworks_without_manifest: on iOS-family, a commonly-used SDK (known_sdk set) without a manifest is a frequent ITMS-91053 cause; the app's own manifest does not cover SDKs.",
            "feature_signals social_login present without sign_in_with_apple => check 4.8.",
            "feature_signals account_creation present without account_deletion => check 5.1.1(v).",
            "feature_signals storekit present without iap_restore => check 3.1.1 restore.",
            "feature_signals third_party_app_dependency => check 2.1 demo path.",
            "ipad_multitasking_orientations.likely_finding=true => upload-time blocker: an iPad target without UIRequiresFullScreen must list all four orientations incl. PortraitUpsideDown on the BASE key; see guideline 2.4.1 in the curated reference.",
            "ipad_multitasking_orientations.ipad_suffix_build_setting_trap=true => the ~ipad orientations are set in build settings but Xcode IGNORES the ~ipad suffix on INFOPLIST_KEY_*; the bundle ships only the base orientations. Move all four to the BASE INFOPLIST_KEY_UISupportedInterfaceOrientations.",
        ],
    }
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
