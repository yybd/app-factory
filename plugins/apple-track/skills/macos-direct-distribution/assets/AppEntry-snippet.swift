// Wire the updater into the SwiftUI App entry point. Add the #if DIRECT bits to
// the app's existing `@main struct …: App`. The App Store target (no DIRECT flag,
// Sparkle not linked) compiles none of this and updates via the Mac App Store.

import SwiftUI
#if DIRECT
import Sparkle
#endif

@main
struct YourApp: App {        // ← keep the app's real struct name
    #if DIRECT
    private let updater = DirectUpdater()
    #endif

    var body: some Scene {
        WindowGroup {
            ContentView()    // ← the app's real root view
        }
        #if DIRECT
        .commands {
            CommandGroup(after: .appInfo) {
                CheckForUpdatesView(updater: updater.controller.updater)
            }
        }
        #endif
    }
}
