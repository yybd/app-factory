# frozen_string_literal: true
#
# Where this machine's Apple credentials are — the Ruby half of the same answer.
#
#   require_relative "../../../shared/credentials"
#   creds = AppleCredentials.asc_key            # {key_id:, issuer_id:, p8:, from:}
#
# The same three sources in the same order as `credentials.py` beside this file:
# the environment, then `$KEYS_ROOT/credentials.json`, then the hub's `DATA.md` for a
# studio installation that predates the JSON.
#
# **Why a second implementation rather than shelling out to the Python one.** These
# scripts already load `spaceship` and run inside fastlane's Ruby; adding a subprocess
# to read three strings would make the failure modes worse, not better — a missing
# Python, a different Python, an exit code to interpret. What must not diverge is the
# ORDER and the FORMAT, and those are stated once in `docs/keys/1-contract.md`. The
# resolver is small enough that two copies of it are cheaper than the coupling.
#
# It returns paths and identifiers. It never reads the .p8's bytes and never prints them.

require "json"

module AppleCredentials
  module_function

  def keys_root
    File.expand_path(ENV["KEYS_ROOT"] || "~/keys")
  end

  def from_env
    kid = ENV["ASC_KEY_ID"]
    iss = ENV["ASC_ISSUER_ID"]
    p8  = ENV["ASC_KEY_PATH"]
    return nil unless kid && iss && p8 && !kid.empty? && !iss.empty? && !p8.empty?
    { key_id: kid, issuer_id: iss, p8: File.expand_path(p8), from: "the environment" }
  end

  def store
    path = File.join(keys_root, "credentials.json")
    return [nil, path] unless File.file?(path)
    [JSON.parse(File.read(path, encoding: "UTF-8")), path]
  rescue StandardError
    [nil, path]
  end

  def from_store
    data, path = store
    return nil unless data
    a = data["appstoreconnect"] || {}
    return nil unless a["key_id"] && a["issuer_id"] && a["p8"]
    p8 = File.expand_path(a["p8"])
    p8 = File.join(keys_root, a["p8"]) unless a["p8"].start_with?("/", "~")
    { key_id: a["key_id"], issuer_id: a["issuer_id"], p8: p8, from: path }
  end

  def from_data_md
    hub = ENV["APP_HUB"]
    hub ||= File.join(ENV["DEV_ROOT"], "app-hub") if ENV["DEV_ROOT"]
    return nil unless hub
    path = File.join(hub, "DATA.md")
    return nil unless File.file?(path)
    # DATA.md may hold any script; without an explicit encoding Ruby reads it as
    # US-ASCII whenever LANG is unset (cron, a bare shell) and every match below raises.
    text = File.read(path, encoding: "UTF-8")
    kid = text[/key id:\s*(\S+)/i, 1]
    iss = text[/issuer id:\s*(\S+)/i, 1]
    p8  = text[/^\s*(?:n8|p8|key path):\s*(\S+)/i, 1]
    return nil unless kid && iss && p8
    { key_id: kid, issuer_id: iss, p8: File.expand_path(p8),
      from: "#{path}  (legacy: move it to credentials.json)" }
  end

  def asc_key
    got = from_env || from_store || from_data_md
    return got if got

    raise <<~MSG
      No App Store Connect credential found. Looked in, in order:
        1. $ASC_KEY_ID / $ASC_ISSUER_ID / $ASC_KEY_PATH in the environment
        2. #{File.join(keys_root, 'credentials.json')}  (appstoreconnect)
        3. the hub's DATA.md, for a studio installation

        python3 factory/init_keys.py --create   writes the folder and a template
        (run it in the app-factory checkout — ~/.claude/plugins/marketplaces/app-factory
        when the marketplace was added from GitHub).
        The key itself comes from App Store Connect -> Users and Access -> Integrations.
    MSG
  end
end
