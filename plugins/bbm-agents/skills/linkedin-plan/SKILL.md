---
name: linkedin-plan
description: Plan the owner's LinkedIn posting - a week (or two) of posts, each with a day, topic pillar, format (text, image or carousel), formula, the real story or number it uses, and a first-line idea - or a bank of 20-30 post ideas crossing their topics with formats. Sets up their LinkedIn profile (who they write for, their topics, how often, which visual route) the first time. Use when the owner says "what should I post", "plan my LinkedIn", "content calendar", "give me post ideas", "LinkedIn this week", or "set up LinkedIn". Plans only; the other LinkedIn skills write the posts.
---

# linkedin-plan

A plan is only as good as the real material behind each slot. Every slot names the story, number or opinion it will use; a slot with nothing behind it is a slot to cut or a question for the owner.

Helper: `scripts/linkedin.py` in the **linkedin-post** skill (`python3` on macOS/Linux, `python` or `py` on Windows).

## First time: the profile

`linkedin.py paths` → if `profile_exists` is false, `linkedin.py profile init`, then fill `linkedin.json` with the owner (propose from `brand-bible.md`; they correct):

| Field | What to put |
|---|---|
| `author`, `author_line` | Name and the short line under it on slides ("Founder, Acme Roofing") |
| `page` | `personal` (the owner's own profile, usually best for reach) or `company` |
| `audience` | Who the posts are for, in one line, in customer terms |
| `goal` | What LinkedIn is for: leads, trust with a niche, hiring, referrals |
| `pillars` | 3-5 topics they know and customers care about. At least one about how they work, one about the customer's world |
| `posts_per_week` | What they'll actually keep up. 2-3 beats 5 abandoned |
| `offer_cta` | The real next step posts can point to (from `offers.md`), or empty |
| `visuals` | `default`: `html` (free) / `image` / `hybrid`; `provider`: `fal` or `higgsfield` if image or hybrid; `size`: `1080x1350` |
| `avoid` | Topics, clients or claims never to use |

`linkedin.py profile check` must pass. If there's no story bank, suggest `linkedin-stories` now; a plan built on it is far better.

## Weekly plan

1. Read `linkedin.json`, `linkedin-stories.md`, `offers.md`, and the last plan and posts in the drafts folder (don't repeat a story or formula used in the last two weeks).
2. Ask one question if useful: "Anything happening this week worth posting about?" (a win, a hire, an event, a customer question).
3. Build `posts_per_week` slots, spread across the week (weekday mornings in the audience's time zone are a sensible default; the owner knows their audience better). Mix:
   - **Formats:** at most one carousel a week unless they ask for more; text-only posts are fine and often best. Never the same format twice in a row.
   - **Pillars:** rotate; no pillar twice in a row.
   - **Goals:** at least one post that asks for nothing (pure value) for every post that points at the offer.
   - **Formulas** (from `linkedin-post/references/hooks.md`) and **structures** (from `linkedin-carousel/references/frameworks.md`): all different within the week.
4. For each slot: day, pillar, format, formula or structure, **the source** (story bank entry, receipt, position, or "owner to supply: <the one question>"), a first-line idea, and the goal (comments, reposts, likes, saves).

## Idea bank

When they want a list, not a week: cross each pillar with 6-8 formats (story, how-to, contrarian take, numbers, customer question answered, mistake, behind the scenes, explainer) and write 20-30 one-line ideas, each marked with the story-bank source or "needs: <question>". Drop any idea with no possible real source.

## Output

`linkedin.py new plan --slug "week of <date>"` → `plan.md`:

```
# LinkedIn plan: <week of date>
Page: <personal/company> | Posts: <n> | Audience: <line>

| Day | Pillar | Format | Formula / structure | Source | First-line idea | Goal |

## Questions for <owner>
<only the "owner to supply" items, one line each>

## Next
<which skill writes each slot>
```

No em dashes in anything you write for the owner, including README and plan files (use a comma, colon or full stop).

## Report to the owner

A top-level message: the week in a few lines (day, format, topic), the questions they need to answer, the path to `plan.md`, and "from linkedin-plan". Offer to draft the first slot now. If the workspace has task rules (`TASK_RULES` in the config) and the owner wants tasks, create one per slot only after they say yes.

## Limits

Plans only. Never posts or schedules. Never plans around invented stories, results or customers.
