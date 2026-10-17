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

## Reddit

- **For:** a community that already has the problem (a tool's own subreddit, a platform's).
- **Mechanical:** title ≤ 300 characters.
- **Convention:** read the subreddit's rules first — many forbid self-promotion outright.
  Lead with the lesson or the problem, not the product. New accounts with no karma are
  filtered in most communities.

## LinkedIn

- **For:** people who know the author. Write in their language.
- **Convention:** the link goes in the first comment rather than the post body — posts
  with external links are commonly believed to be shown less. A belief, not a documented
  rule; say so if asked.

## X and Bluesky

- **For:** an existing following. A new account with no followers reaches almost no one;
  replies in existing conversations reach more than posts.
- **Mechanical:** X — 280 characters per post, every URL counted as 23. Bluesky — 300.
- A thread: the problem, what did not work, what does, the link last.

## dev.to and Medium — cross-posts

- **For:** a second audience for an article that already lives at its canonical URL.
- **Mechanical (dev.to):** front matter must be the first thing in the file;
  `canonical_url` names the original; `published: false` keeps it a draft; at most 4 tags.
- **Medium:** prefer *Import a story* with the canonical URL — Medium sets the canonical
  link itself. Pasted by hand, set *Customize canonical link* in the story's settings.
- **Both:** absolute links only. Add an "Originally published at" line.
- **When:** after the launch channel, not before — the launch is where it should be seen
  first.
