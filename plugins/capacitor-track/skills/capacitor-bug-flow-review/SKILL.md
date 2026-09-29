---
name: capacitor-bug-flow-review
description: >-
  Find real bugs and broken flows in a Capacitor app — the JavaScript that runs inside
  the WebView and the seams where it meets the native shell. Use when a Capacitor/Ionic
  app misbehaves on one platform but not the other, when a button does nothing, when
  something is slow or unresponsive, when a change does not appear on the device after a
  rebuild, before shipping a release, or when asked to QA or debug such an app ("באג
  בקפסיטור", "לא עובד במכשיר"). It carries a catalog of WebView traps measured on real
  devices, and the recipe for driving the WebView from the Mac over devtools instead of
  tapping the user's phone. For a native Swift app use apple-bug-flow-review; its
  analyzer, sanitizers and XCUITest have nothing to work on here.
---

# Capacitor Bug & Flow Review — the WebView and its seams

> **Conversational language:** talk to the user — questions, summaries, reports — in the `conversational language` set in the hub `DATA.md` (`$APP_HUB/DATA.md`); fall back to the language the user writes in if it is unset. This sets the *conversation* language only.

A Capacitor app fails in three places, and only the first looks like ordinary web
work: **the JavaScript**, **the WebView it runs in** (which is not the browser you
tested in), and **the build pipeline between your source and the device**.

## Prerequisites

- **Tools:** `adb` (`brew install --cask android-platform-tools`) and `curl` for the
  devtools socket; Node/npm for `npm run sync`; Python 3 stdlib for the hand-rolled
  CDP client; Safari's Develop menu for iOS.
- **Credentials:** none.
- **Hub (`$APP_HUB`):** optional — only the conversational language from `DATA.md`;
  falls back to the language the user writes in.
- **Other tracks:** `apple-bug-flow-review`, `ship-apple-app`,
  `app-store-review-compliance` (apple-track); `play-store-ship`,
  `play-store-compliance` (android-track); `frontend-design` (design-track) and
  `web-design-guidelines` (web-track) own design review.

## The WebView is not a browser — the measured catalog

Everything here was measured on a real device, not inferred. Re-measure before
trusting a number on different hardware; the *shape* of each finding holds.

| Trap | What actually happens |
|---|---|
| **No Web Share API on Android** | `navigator.share` is simply **undefined** in Android's WebView — Chrome has it, the view an app embeds does not. Feature-detection then falls through to an `<a download>` fallback that is **equally inert** inside a WebView (no DownloadListener), so the button does nothing at all, with no error. Route native builds through the Share plugin instead. |
| **`canvas.toBlob` is pathologically slow** | 1080×1350 PNG: **4120 ms** via `toBlob`, **120 ms** via `toDataURL` — identical output. Not the codec (JPEG costs the same 4 s through `toBlob`, 39 ms through `toDataURL`) and not the readback (`getImageData` over the whole canvas is 75 ms). Also wildly non-linear: a half-size canvas is 17 ms. **Prefer `toDataURL` for anything a WebView must encode** — and it returns base64, which is what the native bridge wants anyway. |
| **No feedback = repeated taps** | Any handler that takes more than ~200 ms with no visible change gets tapped again, and again. Each tap starts another run. Guard re-entry AND paint a busy state — behind two `requestAnimationFrame`s, or the main thread enters the work and the frame that would have shown it never lands. |
| **Plugins without a JS bundle** | A page of plain `<script>` tags has no Capacitor JS module, so `Capacitor.Plugins.X` is undefined. The native bridge still exposes `Capacitor.nativePromise(plugin, method, opts)` — call plugins straight through it. |
| **Platform gates** | `window.Capacitor?.getPlatform?.()` and `isNativePlatform()` exist only in a native build. Guard every use; the same page runs in a desktop browser. |

## The build pipeline — where a fix silently does not ship

Two failure modes that look identical to "my change did nothing":

- **Forgot to sync.** Editing `app/` changes nothing on device until the web assets
  are copied into the native projects (`npm run sync` in this project). A rebuilt
  binary with stale HTML is the result, and the version number still went up.
- **Cache-busting.** Scripts are loaded as `js/cards.js?v=33`. Change the file and
  not the number and the WebView keeps the old one. **Bump the query on every web
  change** — and check the CSS link too, which is edited less often and forgotten
  more.

Before believing any device result, confirm the device is running what you think:
read the loaded file's `?v=` and compare it to the source.

## Drive the WebView, do not tap the phone

A debug Capacitor build exposes the WebView's devtools socket. Use it — it is
faster, it is repeatable, and it keeps you off a phone the user is holding.

```bash
adb shell cat /proc/net/unix | grep webview_devtools_remote      # socket = the pid
adb forward tcp:9222 localabstract:webview_devtools_remote_<pid>
curl -s http://localhost:9222/json                               # webSocketDebuggerUrl
```

Then speak CDP over that WebSocket (`Runtime.evaluate`, `awaitPromise: true`) to
time code with `performance.now()`, call app globals, and read state. Python's
stdlib has no WebSocket client; a hand-rolled handshake plus masked frames is
about 40 lines. On iOS the equivalent is Safari's Develop menu against the
simulator or a connected device.

**Never drive a phone the user is holding with `adb shell input tap`.** The taps
land on whatever holds focus, not on the app you launched — this has put taps into
a user's private chat. Check `adb shell dumpsys window | grep mCurrentFocus`
first, prefer an emulator, and prefer devtools over taps entirely.

## Flow review — what to actually walk

Per screen, on **both** platforms, because they diverge:
- Every control: does it do something, and does it say so within 200 ms?
- Back: does it go where the user expects, including from a native sheet?
- Empty, error, offline, and permission-denied states.
- Language switch mid-flow (see `capacitor-localization`), and RTL layout.
- Backgrounding during a native call — the plugin's `saveInstanceState` may warn.
- Rotation and small screens, which a desktop browser never showed you.

## Report
Rank by severity, name the file and line, and say **which platform** each finding
is on — "works in Chrome" is not evidence about a WebView, and an Android-only
bug is the norm here rather than the exception.

## Boundaries

- **The web layer and the seam, not the native shell.** A crash in Swift or Kotlin,
  or a problem that reproduces in a plain browser, is not this skill's:
  `apple-bug-flow-review` covers the Apple side.
- **It does not review design** (`frontend-design`, `web-design-guidelines`) or store
  policy (`app-store-review-compliance`, `play-store-compliance`).

## Related skills
- `capacitor-localization` — the strings side of the same web layer.
- `apple-bug-flow-review` — the native Swift counterpart.
- `play-store-ship` · `ship-apple-app` — what comes after the bugs are out.
