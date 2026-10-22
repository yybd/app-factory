# Channels — what each is for, and the rules that bite

Two kinds of rule below. **Mechanical** ones the checker enforces: break them and the
channel cuts, mangles or ignores the post. **Conventions** are judgment — widely held,
not documented by the channel, and said as such.

## Hacker News — Show HN

- **For:** a thing people can try now. Link the thing (the repo, the page), not an
  article about it.
- **Mechanical:** title ≤ 80 characters, starting `Show HN: `. When a URL is submitted
  the text field stays empty. Comments are plain text: backticks, `>`, `#` and `**` show
  as typed — write paragraphs separated by a blank line.
- **Convention:** the author posts the first comment at once — what it is, why it exists,
  its known limits, a link to the write-up. Be there for hours and answer everything.
  Most Show HN posts stay on /newest; that is the normal outcome, not a failure. Never
  ask for votes.
- **Convention, the first comment's shape:** what it is, end to end, in the first
  sentence; then why it exists, how it works, where it stops. No cost or investment line
  — here it reads as marketing. Close by asking where it gets in the way, and that pull
  requests improving it are welcome.

## Reddit

- **For:** a community that already has the problem (a tool's own subreddit, a platform's).
- **Mechanical:** title ≤ 300 characters.
- **Convention:** read the subreddit's rules first — many forbid self-promotion outright.
  Lead with the lesson or the problem, not the product. New accounts with no karma are
  filtered in most communities.
- **Convention, by kind of subreddit:** a general one (r/ClaudeAI) takes the pain, then
  the end-to-end line, and may say what it cost to build and that it is open source. A
  technical one (r/ClaudeCode and the like) takes lessons, not a pitch — no cost line.
  Both end inviting the reader to try it, fork it, improve it.

## LinkedIn

- **For:** people who know the author. Write in their language.
- **Mechanical:** no Markdown — `**`, backticks, `#` headings and `[text](url)` show as
  typed. Plain paragraphs; a bare URL becomes a link.
- **Mechanical, in a right-to-left UI:** when the LinkedIn interface is in Hebrew (or
  another RTL language), an @mention at the **start** of an English comment or reply is
  wrapped in U+200F (right-to-left) marks, and the whole comment flips right-to-left.
  Put the mention at the end, or leave it out, and check the rendered comment.
- **Convention:** the link goes in the first comment rather than the post body — posts
  with external links are commonly believed to be shown less. A belief, not a documented
  rule; say so if asked.
- **Convention, the post's shape:** the pain in concrete steps in the opening lines (all
  the feed shows before *see more*), then what it is end to end, then the investment and
  the open-source release in the owner's words, the details, the why, and a closing
  invitation — try it, fork the repo, improve it — before "Link in the first comment".

## X and Bluesky

- **For:** an existing following. A new account with no followers reaches almost no one;
  replies in existing conversations reach more than posts.
- **Mechanical:** X — 280 characters per post, every URL counted as 23, and **weighted**:
  Latin, Hebrew and most scripts, spaces, dashes and quotes count 1; anything else counts
  2 — `•`, `…`, `→`, CJK, and every emoji however it is built. A bulleted list can pass a
  plain count and still be refused; the checker counts the way X does. Bluesky — 300.
- A thread: the problem, what did not work, what does, the link last. The first post
  carries the pain and the end-to-end line (and, for something given away, the
  investment and that it is open source); the last carries the invitation to try, fork
  and improve, with the link.

## dev.to and Medium — cross-posts

- **For:** a second audience for an article that already lives at its canonical URL.
- **Mechanical (dev.to):** front matter must be the first thing in the file;
  `canonical_url` names the original; `published: false` keeps it a draft; at most 4 tags.
- **Medium:** prefer *Import a story* with the canonical URL — Medium sets the canonical
  link itself. Pasted by hand, set *Customize canonical link* in the story's settings.
- **Both:** absolute links only. Add an "Originally published at" line.
- **When:** after the launch channel, not before — the launch is where it should be seen
  first.

## Posting by browser

For step 6 of the skill, when the user asked Claude to post. Practical, learned by doing:

- **File inputs.** The image button on most composers creates its `<input type="file">`
  on click and opens the operating system's file picker, which the browser tools cannot
  drive. Do not click it: find the input (or expose the one the button creates) and use
  the browser tool's file-upload action on it. Then confirm the preview appeared.
- **Line breaks.** Type paragraphs with the channel's own line-break key — in comment
  boxes Enter often submits, and shift+Enter is the line break. After typing, count the
  paragraphs in the composer against the draft before asking for the yes.
- **What you see is the check.** Read the rendered post or comment after it is live, not
  the composer: direction, paragraphs, the link and the image are only certain there.
- **Login pages are a stop.** A sign-in form, a consent banner or a "create account"
  step is the user's to handle; ask them and wait.
