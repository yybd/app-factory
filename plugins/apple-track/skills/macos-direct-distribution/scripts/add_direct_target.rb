#!/usr/bin/env ruby
# Create a dedicated "Direct" distribution target for a macOS Xcode app, sharing
# the App Store target's synced source folder. The new target carries a DIRECT
# compile flag, has App Sandbox OFF + Hardened Runtime ON, embeds Sparkle's
# Info.plist update keys, and (by default) is the ONLY target that links Sparkle
# — so the App Store binary stays framework-free and App-Review compliant.
# Idempotent: safe to re-run (e.g. to patch SPARKLE_PUBKEY once you have a key).
#
# Why a separate target and not just a build config: a linked framework (Sparkle)
# is embedded per-TARGET, not per-configuration. A config split can gate Swift
# code with #if DIRECT but cannot keep Sparkle.framework out of the App Store
# product. See references/xcode-target.md.
#
# Config via environment variables:
#   PROJECT            path to .xcodeproj      (default: the only *.xcodeproj in CWD)
#   APP_TARGET         App Store target name   (default: auto-detected app target)
#   DIRECT_TARGET      new target name         (default: "<APP_TARGET> Direct")
#   SCHEME             new scheme name         (default: "<APP_TARGET> (Direct)")
#   SUFEED_URL         Sparkle appcast URL     (omit on first pass; set later)
#   SPARKLE_PUBKEY     SUPublicEDKey (base64)  (default: placeholder, patch later)
#   SPARKLE_MIN        min Sparkle version     (default: 2.0.0)
#   LINK_SPARKLE       link Sparkle? 1/0       (default: 1)
require 'xcodeproj'

def env(k, default = nil) v = ENV[k]; (v && !v.empty?) ? v : default end

project_path = env('PROJECT') || Dir.glob('*.xcodeproj').first
abort 'No .xcodeproj found (set PROJECT=path/to/App.xcodeproj)' unless project_path && File.exist?(project_path)
project = Xcodeproj::Project.open(project_path)

if (name = env('APP_TARGET'))
  app = project.targets.find { |t| t.name == name } or abort "No target named #{name.inspect}"
else
  apps = project.targets.select { |t| t.respond_to?(:product_type) && t.product_type == 'com.apple.product-type.application' && !t.name.end_with?(' Direct') }
  abort "Multiple app targets (#{apps.map(&:name).join(', ')}); set APP_TARGET=..." if apps.size > 1
  app = apps.first or abort 'No application target found (set APP_TARGET=...)'
end

DIRECT      = env('DIRECT_TARGET', "#{app.name} Direct")
SCHEME      = env('SCHEME', "#{app.name} (Direct)")
FEED        = env('SUFEED_URL')
PUBKEY      = env('SPARKLE_PUBKEY', 'REPLACE_WITH_SUPublicEDKey')
SPARKLE_MIN = env('SPARKLE_MIN', '2.0.0')
LINK        = env('LINK_SPARKLE', '1') != '0'
INTERVAL    = env('SU_CHECK_INTERVAL', '172800')  # background-check seconds (default 48h)

# 1) Sparkle remote package reference (idempotent).
pkg = nil
if LINK
  pkg = project.root_object.package_references.find { |r| r.respond_to?(:repositoryURL) && r.repositoryURL.to_s.include?('sparkle-project/Sparkle') }
  unless pkg
    pkg = project.new(Xcodeproj::Project::Object::XCRemoteSwiftPackageReference)
    pkg.repositoryURL = 'https://github.com/sparkle-project/Sparkle'
    pkg.requirement = { 'kind' => 'upToNextMajorVersion', 'minimumVersion' => SPARKLE_MIN }
    project.root_object.package_references << pkg
  end
end

# 2) The new application target.
new_t = project.targets.find { |t| t.name == DIRECT }
new_t ||= project.new_target(:application, DIRECT, :osx, app.deployment_target, nil, :swift)

# 3) Share the App Store target's synced source folder (no per-file membership).
synced = app.file_system_synchronized_groups&.first
abort "#{app.name} doesn't use a synced source folder — see references/xcode-target.md for the explicit-file path" unless synced
new_t.file_system_synchronized_groups << synced unless new_t.file_system_synchronized_groups.include?(synced)

# 4) Build settings: clone the App Store target's per-config settings, then apply
#    the direct-channel overrides.
def add_flag(bs, flag)
  cond = bs['SWIFT_ACTIVE_COMPILATION_CONDITIONS']
  toks = cond.is_a?(Array) ? cond.dup : (cond ? cond.split : ['$(inherited)'])
  toks = ['$(inherited)'] if toks.empty?
  toks << flag unless toks.include?(flag)
  bs['SWIFT_ACTIVE_COMPILATION_CONDITIONS'] = toks.join(' ')
end

new_t.build_configurations.each do |conf|
  if (src = app.build_configurations.find { |c| c.name == conf.name })
    conf.build_settings = Marshal.load(Marshal.dump(src.build_settings))
  end
  bs = conf.build_settings
  bs['ENABLE_APP_SANDBOX'] = 'NO'        # direct distribution doesn't require the sandbox
  bs['ENABLE_HARDENED_RUNTIME'] = 'YES'  # still required for notarization
  add_flag(bs, 'DIRECT')
  if LINK
    # Sparkle's SUFeedURL/SUPublicEDKey are arbitrary keys: the INFOPLIST_KEY_
    # prefix only injects Apple-known keys, so they MUST live in a real
    # Info.plist merged with the generated one via INFOPLIST_FILE.
    bs['INFOPLIST_FILE'] = 'DirectInfo.plist'
    bs.delete('INFOPLIST_KEY_SUFeedURL')
    bs.delete('INFOPLIST_KEY_SUPublicEDKey')
  end
end

# Write the Sparkle Info.plist (merged into the generated plist; public values only).
if LINK
  File.write('DirectInfo.plist', <<~PLIST)
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
        <key>SUFeedURL</key>
        <string>#{FEED}</string>
        <key>SUPublicEDKey</key>
        <string>#{PUBKEY}</string>
        <key>SUScheduledCheckInterval</key>
        <integer>#{INTERVAL}</integer>
    </dict>
    </plist>
  PLIST
end

# 5) Link Sparkle to THIS target only.
if LINK && !new_t.package_product_dependencies.any? { |d| d.product_name == 'Sparkle' }
  dep = project.new(Xcodeproj::Project::Object::XCSwiftPackageProductDependency)
  dep.package = pkg
  dep.product_name = 'Sparkle'
  new_t.package_product_dependencies << dep
  bf = project.new(Xcodeproj::Project::Object::PBXBuildFile)
  bf.product_ref = dep
  new_t.frameworks_build_phase.files << bf
end

# 6) Drop any stray "<name>-Direct" configs (from an earlier config-only attempt).
[project.build_configuration_list, app.build_configuration_list, new_t.build_configuration_list].each do |list|
  list.build_configurations.dup.each do |c|
    if c.name.end_with?('-Direct')
      list.build_configurations.delete(c)
      c.remove_from_project
    end
  end
end

project.save

# 7) (Re)create the scheme: Debug for Run, Release for Archive (Xcode defaults).
scheme = Xcodeproj::XCScheme.new
scheme.add_build_target(new_t)
scheme.set_launch_target(new_t)
scheme.save_as(project_path, SCHEME, true)

puts "OK: target #{DIRECT.inspect} (sandbox off, DIRECT#{LINK ? ', Sparkle-linked' : ''}), scheme #{SCHEME.inspect}."
puts "  App Store target #{app.name.inspect} untouched (sandbox: #{app.build_configurations.map { |c| c.build_settings['ENABLE_APP_SANDBOX'] }.uniq.inspect})."
puts "  SUFeedURL: #{FEED || '(not set — re-run with SUFEED_URL=...)'}"
puts "  SUPublicEDKey: #{PUBKEY == 'REPLACE_WITH_SUPublicEDKey' ? '(placeholder — generate a key, then re-run with SPARKLE_PUBKEY=...)' : PUBKEY}"
