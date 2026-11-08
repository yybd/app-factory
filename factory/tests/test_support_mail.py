"""Branch pipeline for the support-mail rule — the reader and every check that uses it.

    python3 factory/tests/test_support_mail.py

The rule lives in a hub's DATA.md ("### support mail"): one address, a subject that names
the app, a per-app support-URL table. What is pinned here: that the reader finds the
address and the table and falls back to the Contact email with a warning; that the two
copies of the reader (apple-track, android-track) are the same file; and that each check
built on it fires on the real cases it was written for — a mailto with no subject, a
foreign address, a support URL that is the studio home, a review email that differs.
Every hub here is a temporary fixture; nothing reads the machine's own hub.
"""
import importlib.util, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
P = os.path.join(REPO, "plugins")
APPLE_SM = os.path.join(P, "apple-track", "shared", "support_mail.py")
ANDROID_SM = os.path.join(P, "android-track", "shared", "support_mail.py")

RULE = """# studio data

email_address: old@example.org

### support mail — one address
- **address:** `help@studio.test` — the only one.
- **subject from inside an app:** `<App> <version> — Support`

| app (hub slug) | support URL |
|---|---|
| alpha / beta | `https://apps.studio.test/<slug>#contact` |
| gamma (Gamma Pro) | `https://gamma.test/#contact` |

### the next section
"""
NO_RULE = "first name: A\nemail_address: old@example.org\n"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def run(args, hub):
    env = dict(os.environ, APP_HUB=hub)
    env.pop("DEV_ROOT", None)
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True, env=env)
    return r.returncode, r.stdout + r.stderr


def main():
    fails = 0

    def check(ok, label, detail=""):
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'✓' if ok else '✗'} {label}" + (f"   [{detail[:400]}]" if detail and not ok else ""))

    sm = load(APPLE_SM, "support_mail")

    # the reader
    got = sm.parse(RULE)
    check(got["address"] == "help@studio.test", "the address is read from the rule, not the Contact email")
    check(got["urls"].get("beta") == "https://apps.studio.test/beta#contact", "<slug> is substituted per row")
    check(got["urls"].get("gamma") == "https://gamma.test/#contact", "a parenthetical is not part of the slug")
    check(not got["warnings"], "a complete rule warns about nothing", str(got["warnings"]))
    fb = sm.parse(NO_RULE)
    check(fb["address"] == "old@example.org" and fb["warnings"], "no rule: the Contact email, with a warning")
    check(sm.parse("nothing here")["address"] is None, "no rule, no contact: None, and no crash")
    check(sm.matches("https://gamma.test/he/#contact", "https://gamma.test/#contact"),
          "a language version of the same page matches")
    check(not sm.matches("https://gamma.test/", "https://gamma.test/#contact"), "the bare home does not")
    check(sm.is_home("https://www.studio.test/") and not sm.is_home("https://studio.test/#contact"),
          "is_home: a bare root, not one with #contact")
    check(sm.web_mailto("a@b.test", "Alpha").endswith("subject=Alpha%20%E2%80%94%20Support%20%28web%29"),
          "the web subject is encoded, parentheses included")
    check(open(APPLE_SM, "rb").read() == open(ANDROID_SM, "rb").read(),
          "apple-track and android-track carry the same support_mail.py")

    with tempfile.TemporaryDirectory() as t:
        hub = os.path.join(t, "hub")
        write(os.path.join(hub, "DATA.md"), RULE)

        # app-store-metadata: scaffold fills, validate warns
        md = os.path.join(hub, "alpha", "store", "apple", "metadata")
        scaffold = os.path.join(P, "apple-track", "skills", "app-store-metadata", "scripts", "scaffold_metadata.py")
        validate = os.path.join(P, "apple-track", "skills", "app-store-metadata", "scripts", "validate_metadata.py")
        rc, out = run([scaffold, md, "--locales", "en-US"], hub)
        surl = open(os.path.join(md, "en-US", "support_url.txt")).read()
        mail = open(os.path.join(md, "review_information", "email_address.txt")).read()
        check(rc == 0 and surl == "https://apps.studio.test/alpha#contact",
              "scaffold writes the app's support URL from the table", out + surl)
        check(mail == "help@studio.test", "scaffold writes the review email from the rule", mail)
        write(os.path.join(md, "en-US", "support_url.txt"), "https://www.studio.test/")
        write(os.path.join(md, "review_information", "email_address.txt"), "me@gmail.test")
        rc, out = run([validate, md], hub)
        check("studio home page" in out, "validate warns on a support URL that is the studio home", out)
        check("me@gmail.test" in out and "help@studio.test" in out,
              "validate warns on a review email that is not the rule's", out)

        # play-store-metadata: the contact block
        play = os.path.join(hub, "alpha", "store", "play")
        write(os.path.join(play, "metadata", "en-US", "title.txt"), "Alpha")
        pval = os.path.join(P, "android-track", "skills", "play-store-metadata", "scripts", "validate_metadata.py")
        rc, out = run([pval, play], hub)
        check("contact email: help@studio.test" in out and "alpha#contact" in out,
              "play validate names the contact email and website it will set", out)
        hub2 = os.path.join(t, "hub2")
        write(os.path.join(hub2, "DATA.md"), "first name: A\n")
        play2 = os.path.join(hub2, "alpha", "store", "play")
        write(os.path.join(play2, "metadata", "en-US", "title.txt"), "Alpha")
        rc, out = run([pval, play2], hub2)
        check(rc != 0 and "contact email" in out and "ERROR" in out,
              "play validate fails when DATA.md names no address at all", out)

        # app-store-review-compliance: the in-app contact
        app = os.path.join(t, "app")
        write(os.path.join(app, "About.swift"),
              'let supportEmail = "support.app@other-domain.test"\n'
              'let url = URL(string: "mailto:\\(supportEmail)")!\n')
        scan = os.path.join(P, "apple-track", "skills", "app-store-review-compliance", "scripts", "scan_project.py")
        rc, out = run([scan, app], hub)
        sc = json.loads(out)["support_contact"]
        f = " | ".join(sc["likely_findings"])
        check("no subject" in f, "scan flags a mailto with no subject", f)
        check("other-domain.test" in f, "scan flags an address that is not the rule's", f)
        write(os.path.join(app, "About.swift"),
              'let url = URL(string: "mailto:help@studio.test?subject=Alpha%201.0%20%E2%80%94%20Support")!\n')
        sc = json.loads(run([scan, app], hub)[1])["support_contact"]
        check(not sc["likely_findings"], "scan is quiet on the right address with a subject",
              str(sc["likely_findings"]))
        write(os.path.join(app, "About.swift"), "struct About {}\n")
        sc = json.loads(run([scan, app], hub)[1])["support_contact"]
        check(any("no in-app support contact" in x for x in sc["likely_findings"]),
              "scan flags an app with no contact at all")

        # web-track: mail links on pages and in Markdown
        site = os.path.join(t, "site")
        write(os.path.join(site, "index.html"),
              '<html lang="en"><head><title>A page title that is long enough here</title>'
              '<link rel="canonical" href="https://www.studio.test/"></head><body><main>'
              '<a href="mailto:help@studio.test">mail</a> '
              '<a href="mailto:help@other.test">theirs</a></main></body></html>')
        seo = os.path.join(P, "web-track", "skills", "web-seo", "scripts", "audit.py")
        rc, out = run([seo, "--root", site], hub)
        check("mail link(s) with no subject (mailto:help@studio.test)" in out,
              "web-seo flags the support mailto with no subject", out[-800:])
        check("help@other.test" not in out, "…and leaves someone else's address alone", out[-800:])

        cs = os.path.join(t, "content")
        write(os.path.join(cs, "locales.json"), json.dumps({"default": "en", "locales": ["en"]}))
        write(os.path.join(cs, "src", "text", "en", "contact.md"),
              "---\ntitle: Contact\n---\n[write](mailto:help@studio.test) "
              "[x](mailto:help@studio.test?subject=Alpha%20—%20Support%20(web))\n")
        chk = os.path.join(P, "web-track", "skills", "content-site-structure", "scripts", "check_content.py")
        rc, out = run([chk, "--root", cs], hub)
        check("with no subject" in out, "content check flags a Markdown mailto with no subject", out)
        check("raw '('" in out, "content check flags a raw parenthesis in a subject", out)

    print(f"\n{'✗' if fails else '✓'} {fails} failure(s)")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
