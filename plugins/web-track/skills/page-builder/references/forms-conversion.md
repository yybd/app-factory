# Forms, Conversion Mechanics & Privacy

**Read this whenever the page's primary goal is a form submission** (sign-up, lead, contact, subscribe). The `page-builder` skill decides *where* the CTA/form goes; this reference covers *how the form actually works* — submission, validation, spam defense, success/error states — and the **privacy obligations** that kick in the moment you collect personal data (a phone number, email, or name is PII).

Pairs with `i18n-rtl.md` (RTL inputs, locale-aware validation), `responsive-mobile.md` (≥16px inputs, thumb reach), and `seo-metadata.md` (`noindex` the thank-you page).

## 1. The submission path — decide it explicitly

A form is not done until you know **where the data goes**. Pick per project and record it:

| Stack / setup | Typical submission target |
|---------------|---------------------------|
| Plain HTML/CSS/JS (no backend) | A form-handling service (Formspree, Web3Forms, Basin), a serverless function, or a provider's API (e.g. an email/WhatsApp list provider) |
| Next.js | Route Handler / Server Action → validate server-side → forward to provider/DB |
| Astro | Server endpoint (`.ts` in `pages/api` with an adapter) or a form service |

- **Never trust the client.** Even with client-side validation, **validate again on the server / handler**. Client validation is UX; server validation is correctness and security.
- **Confirm the destination with the user** — which list/provider/inbox receives a WhatsApp sign-up? Don't invent an endpoint.

## 2. Accessible, mobile-correct form markup

```html
<form novalidate>                                  <!-- we handle messaging ourselves -->
  <label for="phone">Phone number</label>
  <input id="phone" name="phone" type="tel"
         inputmode="tel" autocomplete="tel"
         dir="ltr"                                  <!-- numbers stay LTR inside RTL page -->
         required aria-describedby="phone-err">
  <p id="phone-err" role="alert" hidden>Please enter a valid number</p>
  <button type="submit">Sign up</button>
</form>
```

- **Every input has a real `<label>`** (not just placeholder text — placeholders disappear and fail a11y).
- **Right `type`/`inputmode`/`autocomplete`** → correct mobile keyboard + autofill (`tel`, `email`, `name`).
- **Inputs ≥16px** to avoid iOS zoom (`responsive-mobile.md`); tap targets ≥44/48px.
- **`dir="auto"`** on free-text fields; **`dir="ltr"`** on phone/email/number fields inside an RTL page so they don't scramble.
- All form **strings come from the i18n catalog**, not hardcoded (`i18n-rtl.md`).

## 3. Validation & feedback states

Design all four states up front — a form is its states, not just its happy path:

- **Idle** — clear labels, required marked, expected format hinted.
- **Invalid** — inline message tied via `aria-describedby`, `aria-invalid="true"`, message in `role="alert"`; focus moves to the first error. Validate on blur/submit, not on every keystroke.
- **Submitting** — disable the button, show progress, prevent double-submit.
- **Success** — explicit confirmation (inline or a `noindex` thank-you page); tell the user **what happens next** ("You will get a confirmation message").
- **Server error** — a human, recoverable message; never lose what the user typed.

Locale-aware validation: phone/name/postal formats differ by locale; Hebrew names, international phone formats. Don't hardcode a US pattern.

## 4. Spam & abuse defense (no-JS-hostile)

- **Honeypot field** — a hidden input real users leave empty; bots fill it → reject. Zero friction, no privacy cost.
- **Time trap** — reject submissions faster than ~2–3s (bots are instant).
- **CAPTCHA only if needed**, and prefer privacy-friendly **Cloudflare Turnstile / hCaptcha** over reCAPTCHA. A CAPTCHA is friction — add it when you see real abuse, not preemptively.
- **Rate-limit** on the server/handler.
- Keep defenses **accessible** — never gate the form behind a puzzle that locks out keyboard/screen-reader users.

## 5. Privacy & legal (the moment you collect PII)

Collecting a phone number / email / name = collecting personal data → obligations apply (GDPR-style; Israel's Privacy Protection Law for Hebrew-first sites):

- **Consent & purpose** — say *why* you collect it and *what you'll send* ("Sign up for the weekly digest"). For marketing/broadcast messages, get **explicit opt-in** (a ticked-by-the-user checkbox, not pre-checked) — relevant for WhatsApp/email lists.
- **Privacy policy** — a real, linked page: what's collected, why, where it's stored, who it's shared with (e.g. the messaging provider), retention, and how to **unsubscribe / request deletion**. Link it next to the submit button.
- **Data minimization** — ask for the *fewest* fields that serve the goal (every extra field also costs conversions — see `page-archetypes.md` contact/lead).
- **No PII in anything a static site ships, or in client logs**; PII goes only to the chosen secure backend/provider.
- **Cookie/consent banner** — required **only if** you set non-essential cookies or load analytics/marketing scripts. A purely functional form needs none — don't add a banner you don't need.
- **Accessibility statement** — a short page is good practice (and legally expected in some jurisdictions) once the site is public.
- **Transport** — submit over **HTTPS** only.

> **Integrity:** never claim "we never share your data" or a subscriber count unless it's true (`PRODUCT.md` §7). Flag anything you can't verify as a TODO.

## 6. Measuring the goal (optional but recommended)

The whole page exists to drive **one** action — instrument it so success is visible:

- Fire one **conversion event** on successful submit (not on page load).
- Prefer **privacy-friendly analytics** (Plausible, Fathom, Umami, or GA4 with consent) — cookieless options avoid needing a consent banner.
- Only load analytics that respect the consent state above.

## Acceptance check

- [ ] Submission destination is decided, real, and confirmed with the user (not a placeholder endpoint).
- [ ] Server/handler-side validation exists (not client-only).
- [ ] Every field has a real `<label>`; errors use `aria-describedby` + `role="alert"`; focus moves to first error.
- [ ] Correct `type`/`inputmode`/`autocomplete`; inputs ≥16px; phone/email `dir="ltr"`, free text `dir="auto"`.
- [ ] All four states implemented: idle / submitting (no double-submit) / success ("what's next") / error (input preserved).
- [ ] Spam defense present (honeypot/time-trap min); CAPTCHA only if needed and accessible.
- [ ] Privacy policy linked; explicit opt-in for marketing/broadcast; HTTPS; data minimized.
- [ ] No PII in static `data/`/logs; consent banner present only if non-essential cookies/scripts are used.
- [ ] Conversion event fires on success (if analytics used), respecting consent.
