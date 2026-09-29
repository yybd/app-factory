# asc_common.rb — shared App Store Connect token auth + raw-request helpers for the
# app-store-deliver helper scripts. The API key comes from the track's resolver
# (`shared/credentials.rb`): the environment, then $KEYS_ROOT/credentials.json.
#
#   require_relative "asc_common"
#   ASC.token!                       # authenticate
#   rc = ASC.rc                      # raw client: rc.get/.post/.patch/.delete (paths "v1/..", "v2/..")
#   ASC.body(rc.get("v1/..."))       # parsed JSON hash
#   t = ASC.tree(slug, opts)         # where the listing lives: a hub, or the repo's fastlane/

require "spaceship"
require "json"
require_relative "../../../shared/credentials"

module ASC
  module_function

  # The hub, when there is one: --hub, then $APP_HUB, then $DEV_ROOT/app-hub. nil when
  # none of those names a directory that exists — which is not an error, it is the
  # standalone mode below.
  def hub(explicit = nil)
    cands = [explicit, ENV["APP_HUB"]]
    root = ENV["DEV_ROOT"]
    cands << File.join(File.expand_path(root), "app-hub") unless root.nil? || root.empty?
    cands.compact.reject(&:empty?).find { |d| Dir.exist?(d) }
  end

  # ── where the listing lives ──────────────────────────────────────────────────
  # Two modes, the same two sync_from_hub.sh has. A HUB — a studio's shared data repo,
  # `<hub>/<slug>/store/apple` + `<hub>/<slug>/media/apple` — or STANDALONE: the app
  # repo's own `fastlane/` tree, the layout `deliver` reads. The hub used to be the only
  # answer and this module aborted without one, so every helper here failed in the mode
  # both SKILL.md files promised — including the one the skill calls MANDATORY.
  #
  # Detected, not declared: a hub that exists wins; otherwise --repo DIR, $APP_REPO, or
  # the working directory when it holds `fastlane/`. Standalone paths:
  #   metadata        fastlane/metadata/<locale>/*.txt      (release_notes.txt inside)
  #   review info     fastlane/metadata/review_information/
  #   review media    fastlane/review/*.{mp4,mov,pdf}
  #   IAP text        fastlane/iap/<product-id>/<locale>/*.txt
  #   media           fastlane/screenshots/<locale>/*        (stills and previews, flat)
  def tree(slug, opts = {})
    # An explicit --repo is a decision, so it wins over a hub that merely exists in the
    # environment. Everything else: a hub if there is one, the repo otherwise.
    h = opts[:repo] ? nil : hub(opts[:hub])
    if h
      store = File.join(h, slug, "store", "apple")
      media = File.join(h, slug, "media", "apple")
      return { mode: :hub, name: "hub", root: h,
               metadata:      File.join(store, "metadata"),
               release_notes: ->(version) { File.join(store, "release-notes", version) },
               review_info:   File.join(store, "metadata", "review_information"),
               review_media:  File.join(media, "review"),
               iap:           ->(pid) { File.join(store, "iap", pid) },
               media_glob:    File.join(media, "*", "*", "{screenshots,app-preview}", "*") }
    end
    repo = opts[:repo] || ENV["APP_REPO"]
    repo = Dir.pwd if (repo.nil? || repo.empty?) && Dir.exist?(File.join(Dir.pwd, "fastlane"))
    if repo && Dir.exist?(File.join(File.expand_path(repo), "fastlane"))
      fl = File.join(File.expand_path(repo), "fastlane")
      return { mode: :standalone, name: "repo", root: fl,
               metadata:      File.join(fl, "metadata"),
               release_notes: ->(_version) { nil },      # deliver layout: metadata/<loc>/release_notes.txt
               review_info:   File.join(fl, "metadata", "review_information"),
               review_media:  File.join(fl, "review"),
               iap:           ->(pid) { File.join(fl, "iap", pid) },
               media_glob:    File.join(fl, "screenshots", "*", "*") }
    end
    abort "✗ no listing source. Either a hub — set $APP_HUB, or pass --hub DIR — or the app " \
          "repo's own fastlane/ tree: run from the repo, set $APP_REPO, or pass --repo DIR."
  end

  def token!
    # Where the credential comes from is ONE question with one answer, and it used to
    # have three: this file read labelled prose out of the hub's DATA.md (including a
    # line called `n8:`), publish_aab.py looked in a folder under $KEYS_ROOT, and the
    # Play diff script grepped a heading. A developer who is not this one has none of
    # those. `shared/credentials.rb` asks in the documented order — environment, then
    # credentials.json, then DATA.md for an installation that predates it.
    c = AppleCredentials.asc_key
    Spaceship::ConnectAPI.token = Spaceship::ConnectAPI::Token.create(
      key_id: c[:key_id], issuer_id: c[:issuer_id], filepath: c[:p8]
    )
    Spaceship::ConnectAPI
  end

  def rc
    Spaceship::ConnectAPI.client.tunes_request_client
  end

  def body(resp)
    resp.body.is_a?(Hash) ? resp.body : JSON.parse(resp.body)
  end

  def app_id(bundle_id)
    app = Spaceship::ConnectAPI::App.find(bundle_id)
    raise "app not found for bundle #{bundle_id}" unless app
    app.id
  end

  # The editable App Store version for a platform + version string.
  def version(app_id, platform:, version:)
    v = body(rc.get("v1/apps/#{app_id}/appStoreVersions",
                    {"filter[platform]" => platform, "filter[versionString]" => version}))["data"]
    raise "version #{version} (#{platform}) not found" if v.nil? || v.empty?
    v.first
  end

  def localizations(version_id)
    body(rc.get("v1/appStoreVersions/#{version_id}/appStoreVersionLocalizations"))["data"]
  end

  # minimal --flag parser: returns [positionals, {flag => value}]
  #
  # A flag followed by another flag, or by nothing, is a boolean and takes no value.
  # It used to swallow whatever came next: `--force --locales en-US` made `--locales`
  # the value of `force`, dropped it, and left `en-US` as a positional — so the
  # preview went up in EVERY locale. The scripts read booleans with ARGV.include?,
  # which is why the bug was in the argument after the flag and not in the flag.
  def parse_args(argv)
    pos = []; opts = {}
    i = 0
    while i < argv.length
      a = argv[i]
      if a.start_with?("--")
        nxt = argv[i + 1]
        if nxt.nil? || nxt.start_with?("--")
          opts[a.sub(/^--/, "").to_sym] = true; i += 1
        else
          opts[a.sub(/^--/, "").to_sym] = nxt; i += 2
        end
      else
        pos << a; i += 1
      end
    end
    [pos, opts]
  end

  def locales_arg(opts, default = nil)
    (opts[:locales] || default)&.split(",")&.map(&:strip)
  end
end
