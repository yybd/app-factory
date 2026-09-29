import os
import glob
import re

skills = glob.glob("plugins/*/skills/*/SKILL.md")
issues = []
stats = {"total": len(skills), "no_frontmatter": 0, "hardcoded_paths": 0, "git_commands": 0}

for s in skills:
    with open(s, 'r') as f:
        content = f.read()
    
    # Check frontmatter
    if not content.startswith("---"):
        stats["no_frontmatter"] += 1
        issues.append(f"{s}: Missing YAML frontmatter")
    
    # Check hardcoded absolute paths (like ~/Developer/app-hub) instead of relative or parameterized
    # Although sometimes this is okay, it's worth checking.
    if re.search(r'~/Developer/(app-hub|web)', content):
        stats["hardcoded_paths"] += 1
        issues.append(f"{s}: Contains hardcoded ~/Developer paths (might break portability)")
        
    # Check if they try to do cross-repo git commits manually (git -C ... commit -am)
    if re.search(r'git\s+-C\s+.*?commit', content):
        stats["git_commands"] += 1
        issues.append(f"{s}: Instructs to do cross-repo git commits directly (should use close.py or targeted add)")

    # Check for direct calls to AppStore/PlayStore APIs if they lack fastlane
    if "fastlane" not in content.lower() and ("app store" in content.lower() or "play store" in content.lower()) and "ship" in s:
        issues.append(f"{s}: Mention shipping but no fastlane reference?")

print("=== STATS ===")
for k, v in stats.items():
    print(f"{k}: {v}")

print("\n=== POTENTIAL ISSUES ===")
for issue in issues:
    print(issue)
