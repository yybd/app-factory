# Flow Audit — walking the user's journeys

The static phases find suspect *code*. This phase proves whether the **user
journeys actually work**. A flow bug is one a user hits while trying to get
something done: a screen they can't leave, a blank screen on a denied
permission, lost input after a phone call, a delete with no confirm. You find
these by *walking the app*, not by reading it.

## Step 1 — Enumerate the journeys

From Phase 0 you have a list. A typical app has:

1. **First-run / onboarding** — fresh install, no data, permissions not yet
   granted. The most fragile flow and the most skipped in testing.
2. **Core task(s)** — the 1–5 things the app exists to do (create/edit/save a
   thing, search, play, purchase, sync).
3. **Settings / account** — sign in/out, change a setting, delete account.
4. **Destructive / data-entry** — anything that deletes, overwrites, or holds
   unsaved input.

Write each as a concrete sequence of user actions with an expected end state.
That sequence is what the XCUITest smoke flow and the hands-on walk both follow.

## Step 2 — The state matrix

For **each screen** in a journey, every one of these must be deliberately
handled — not crash, not go blank, not get stuck:

| State | Trigger | A good app shows… | Common bug |
|-------|---------|-------------------|------------|
| **Loading** | data not yet arrived | spinner/skeleton, no frozen UI | infinite spinner; UI hung on main thread |
| **Empty** | no data yet (first run, deleted all) | helpful empty state + next action | blank screen; "0 results" with no guidance |
| **Error** | request/operation failed | clear message + retry/recovery | silent failure; stuck on stale data; generic alert with no way forward |
| **Success / populated** | the normal case | the content | (the only case most apps test) |
| **Offline** | no network | cached data or a clear offline state + retry | spinner forever; crash on nil response |
| **Permission-denied** | user said No (or Restricted) | graceful degradation + "Open Settings" | blank screen; the feature is dead with no explanation |

Build the matrix as **journey × state** and mark each cell ✅ handled / ⚠️ weak /
❌ broken / — n/a. The ❌ and ⚠️ cells are your findings. This table goes into the
report.

## Step 3 — Navigation & data-loss integrity

Walk each journey and verify:

- **Can always get back/out** — every pushed/presented screen has a working
  back/close; no dead-ends; modals dismiss; a deep-linked-into screen still has a
  way home.
- **Place is preserved** — background the app mid-journey and return: same
  screen, same scroll, same selection? State restoration honored?
- **No unsaved-data loss** — start editing, then: background, switch away, get
  interrupted, force-quit. Is the input still there (autosave / restore), or does
  it vanish silently? **This is the highest-value flow check** — silent data loss
  destroys trust.
- **Destructive actions** — delete/overwrite/reset asks for confirmation and/or
  offers undo. An accidental swipe shouldn't be unrecoverable.
- **Deep links / shortcuts / widgets / Handoff** — if present, the target loads
  and is valid; an invalid target degrades gracefully.

## Step 4 — Interruption & environment checklist

These are the most-missed flow bugs because they need deliberate setup.

**iOS**
- Rotate the device mid-screen — layout intact? state kept?
- Crank **Dynamic Type** to the largest accessibility size — does text clip, or
  does the flow still work (buttons reachable, labels readable)? *(Deep typography
  is HIG's job; here only flag when it blocks the flow.)*
- iPad **Split View / Slide Over / Stage Manager** — does it adapt or break?
- **Keyboard** covers the focused field? Can the user still see what they type and
  reach Submit?
- **Low memory** — background, open heavy apps, return: did the app lose state or
  crash?
- Incoming call / Face ID / control-center pull-down mid-action.

**macOS**
- **Resize** the window very small and very large — content clips, controls
  overlap, or scrolls correctly?
- **Multiple windows** of the same document/model — do edits in one reflect in the
  other? Do they fight over state?
- **Menu bar & keyboard shortcuts** mirror the in-window actions — and stay
  enabled/disabled correctly for context.
- **Full-screen**, becoming a background app, **Stage Manager**, second display.
- **Document lifecycle** (document-based apps) — unsaved-changes dot, revert,
  autosave, "Edited" state, recover-after-crash.
- **Drag-and-drop** in/out, copy-paste, services — if the app advertises them.

**Both**
- **Dark Mode / Light Mode** switch mid-use — does anything become invisible or
  break the flow? *(Look is HIG; flow-blocking invisibility is here.)*
- **Cold launch vs warm resume** — both reach a usable state.

## Step 5 — How to actually drive it

Two complementary methods — use both where it helps:

1. **Scripted XCUITest smoke flows** (repeatable, becomes regression suite).
   Adapt [../assets/FlowSmokeTests.template.swift](../assets/FlowSmokeTests.template.swift):
   one test per journey, driving via the app's accessibility identifiers,
   asserting the user reaches the end without a crash or a missing element.
   Launch with a demo/seed argument if one exists (reuse `appstore-media`'s demo
   mode). XCUITest can force some states (empty via a launch flag, error via a
   mock/launch flag) — wire those in if the app supports it.

2. **Hands-on driving** for states a script can't easily force:
   - **Deny a permission**: reset with `xcrun simctl privacy <udid> reset <service>`
     then launch and choose "Don't Allow".
   - **Kill the network**: simulator → Features, or toggle the host network, or a
     Network Link Conditioner profile; for "slow", use a conditioner.
   - **Background mid-edit / force-quit**: `xcrun simctl` background/terminate, or
     do it by hand, then relaunch and check for lost state.
   - Use Claude Code's built-in `run` skill, the simulator, or computer-use to observe.

Record, per journey: the sequence you ran, what worked, and the **exact** point
and state where it broke (screen + state-matrix cell). That precision is what
makes the finding actionable.

## Output of this phase

- The filled **journey × state matrix** (goes into the report verbatim).
- A list of concrete flow findings, each with repro steps and severity.
- The XCUITest smoke flows you wrote — offer to keep them as the regression
  suite.
