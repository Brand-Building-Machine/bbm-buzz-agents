---
name: content-cascade
description: "Turn a supplied video or transcript into brand-aware blog and social drafts, with an optional practical guide for tutorial material."
---

Resolve the selected workspace using `bbm-client.json` or explicit `BBM_CLIENT_CONFIG`, following [workspace-start](../workspace-start/SKILL.md). Read its map and boundaries before saving. Resolve paths from that config, never from the plugin cache or another workspace. If no workspace is configured, conversation-only work can continue; use workspace-setup before filing. Preserve existing files and keep private information in its selected scope.

Resolve the intended brand and audience from the selected workspace's existing brand and voice notes. If they are absent, use the owner's stated voice or ask for the material choice. Do not borrow another business's voice.

Get the actual transcript from supplied text, an authorized caption connector or an installed subtitle tool. For a local recording, use video-transcribe. Confirm the transcript matches the video title, opening and topic. Missing or unrelated captions mean stop and request an export; do not reconstruct a video from its title. Paid extraction and cloud uploads require explicit permission. Record source URL/title and available timestamps; distinguish quotes from paraphrases.

Produce only the formats requested. For a full cascade, draft:
- A blog post with a clear premise, useful structure, title, excerpt, slug and suggested search description. Let source substance determine length; no filler to hit a word count.
- An X thread built around one strong angle; ensure each post fits the selected account's supported length, defaulting to 280 characters when unknown.
- A LinkedIn post reflecting the video's premise in the brand's voice, with a relevant call to action only if supported.
- For an actual tutorial, optionally a practical guide and a separate LinkedIn guide-introduction draft. Do not invent missing steps or promise a guide that does not exist.

Preserve uncertainty, context and qualifications. Verify added factual claims or mark them for review. Avoid invented results, testimonials and quotations. Apply humanizer when useful without stripping meaning. Return drafts with source references and material review notes. Save only when authorized, under PROPOSED_PATH or the map's approved draft area, using new filenames. Never auto-post, connect a CMS, upload media or write to a marketing platform. No external content service is bundled.
