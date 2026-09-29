// Drop this into the app's source folder (shared by both targets). Everything is
// guarded by `#if DIRECT`, so the App Store target compiles it to nothing and
// never links Sparkle. Requires the Direct target to link the Sparkle package.
#if DIRECT
import SwiftUI
import Combine
import Sparkle

/// Sparkle auto-updater for the direct (non-Mac-App-Store) build.
///
/// The feed URL and public EdDSA key are read from Info.plist
/// (`SUFeedURL` / `SUPublicEDKey`, set on the Direct target). Sparkle checks the
/// appcast automatically in the background and verifies every downloaded update
/// against the embedded key before installing. This type also drives the manual
/// "Check for Updates…" menu command.
final class DirectUpdater {
    let controller: SPUStandardUpdaterController

    init() {
        // startingUpdater: true → begins scheduled background checks on launch
        // (after the user's first-run consent prompt), per the Info.plist settings.
        controller = SPUStandardUpdaterController(
            startingUpdater: true,
            updaterDelegate: nil,
            userDriverDelegate: nil
        )
    }
}

/// Tracks whether a manual update check is currently allowed, so the menu item
/// can grey itself out while a check/install is already in flight.
final class UpdaterViewModel: ObservableObject {
    @Published var canCheckForUpdates = false

    init(updater: SPUUpdater) {
        updater.publisher(for: \.canCheckForUpdates)
            .assign(to: &$canCheckForUpdates)
    }
}

/// The "Check for Updates…" command, placed in the application menu.
struct CheckForUpdatesView: View {
    @ObservedObject private var model: UpdaterViewModel
    private let updater: SPUUpdater

    init(updater: SPUUpdater) {
        self.updater = updater
        self.model = UpdaterViewModel(updater: updater)
    }

    var body: some View {
        Button("Check for Updates…") {
            updater.checkForUpdates()
        }
        .disabled(!model.canCheckForUpdates)
    }
}
#endif
