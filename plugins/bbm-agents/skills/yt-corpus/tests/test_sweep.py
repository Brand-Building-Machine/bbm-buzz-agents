"""Unit tests for yt-corpus. Pure functions only -- no network, no API key.

Run:  python -m pytest "<yt-corpus skill dir>/tests" -q
      (or: python "<yt-corpus skill dir>/tests/test_sweep.py")
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import sweep  # noqa: E402


class TestJson3(unittest.TestCase):
    def _raw(self, events):
        return json.dumps({"events": events}).encode()

    def test_keeps_start_times(self):
        out = sweep.json3_timestamped(self._raw([
            {"tStartMs": 0, "segs": [{"utf8": "hello"}]},
            {"tStartMs": 30000, "segs": [{"utf8": "world"}]},
        ]))
        self.assertEqual([l["t"] for l in out], [0, 30])

    def test_merges_close_short_lines(self):
        """Auto-captions arrive word-by-word; merging keeps the FIRST start time
        so a quote's timestamp still points at where it began."""
        out = sweep.json3_timestamped(self._raw([
            {"tStartMs": 1000, "segs": [{"utf8": "the "}, {"utf8": "quick"}]},
            {"tStartMs": 3000, "segs": [{"utf8": "brown fox"}]},
        ]))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["t"], 1)
        self.assertEqual(out[0]["text"], "the quick brown fox")

    def test_does_not_merge_across_a_gap(self):
        out = sweep.json3_timestamped(self._raw([
            {"tStartMs": 0, "segs": [{"utf8": "before"}]},
            {"tStartMs": 60000, "segs": [{"utf8": "after"}]},
        ]))
        self.assertEqual(len(out), 2)

    def test_skips_empty_and_whitespace_events(self):
        out = sweep.json3_timestamped(self._raw([
            {"tStartMs": 0, "segs": [{"utf8": "\n"}]},
            {"tStartMs": 100, "segs": []},
            {"tStartMs": 200, "segs": [{"utf8": "real"}]},
        ]))
        self.assertEqual([l["text"] for l in out], ["real"])


class TestVtt(unittest.TestCase):
    def test_dedupes_rolling_repeats_keeping_longest(self):
        raw = (b"WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nthe quick\n\n"
               b"00:00:03.000 --> 00:00:05.000\nthe quick brown fox\n")
        out = sweep.vtt_timestamped(raw)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["text"], "the quick brown fox")

    def test_parses_cue_start_seconds(self):
        raw = b"WEBVTT\n\n01:02:03.000 --> 01:02:05.000\nlate line\n"
        self.assertEqual(sweep.vtt_timestamped(raw)[0]["t"], 3723)

    def test_strips_inline_tags(self):
        raw = b"WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<c.mono>tagged</c>\n"
        self.assertEqual(sweep.vtt_timestamped(raw)[0]["text"], "tagged")


class TestFormatting(unittest.TestCase):
    def test_hhmmss(self):
        self.assertEqual(sweep.hhmmss(59), "0:59")
        self.assertEqual(sweep.hhmmss(3723), "1:02:03")
        self.assertEqual(sweep.hhmmss(-5), "0:00")

    def test_fmt_date(self):
        self.assertEqual(sweep.fmt_date("20260224"), "2026-02-24")
        self.assertEqual(sweep.fmt_date(None), "unknown")
        self.assertEqual(sweep.fmt_date("garbage"), "garbage")


class TestPrefilter(unittest.TestCase):
    def _c(self, vid, ch, dur=600, views=10):
        return {"id": vid, "channel_id": ch, "duration_seconds": dur, "view_count": views}

    def test_drops_shorts(self):
        kept, dropped = sweep.prefilter([self._c("a", "c1", dur=45)], 180, 3)
        self.assertEqual(kept, [])
        self.assertIn("under 180s", dropped[0]["drop_reason"])

    def test_caps_per_channel(self):
        cands = [self._c(f"v{i}", "same") for i in range(5)]
        kept, dropped = sweep.prefilter(cands, 180, 2)
        self.assertEqual(len(kept), 2)
        self.assertEqual(len(dropped), 3)

    def test_keeps_unknown_duration(self):
        """Missing duration must not silently delete a candidate."""
        kept, _ = sweep.prefilter([self._c("a", "c1", dur=None)], 180, 3)
        self.assertEqual(len(kept), 1)


class TestWindow(unittest.TestCase):
    def test_filters_by_cutoff(self):
        self.assertFalse(sweep.within_window({"upload_date": "20240101"}, "20260101"))
        self.assertTrue(sweep.within_window({"upload_date": "20260601"}, "20260101"))

    def test_undated_is_kept_not_dropped(self):
        self.assertTrue(sweep.within_window({}, "20260101"))

    def test_no_cutoff_keeps_everything(self):
        self.assertTrue(sweep.within_window({"upload_date": "19990101"}, None))


class TestRender(unittest.TestCase):
    def test_index_escapes_pipes_in_claims(self):
        """A pipe in claim text would otherwise blow up the markdown table."""
        manifest = {"question": "q", "run_slug": "s", "built_at": "now", "queries": ["x"],
                    "discovered": 1, "prefilter_dropped": 0, "attempted": 1,
                    "videos": [{"id": "v1", "status": "ok", "title": "T", "url": "u",
                                "channel": "C", "upload_date": "20260101",
                                "duration_seconds": 60, "transcript_words": 10,
                                "transcript": "transcripts/v1.md", "relevant": True}]}
        extracts = {"v1": {"status": "ok", "relevant": True, "summary": "s",
                           "claims": [{"claim": "a | b", "evidence": "demonstrated",
                                       "timestamp": "0:01"}]}}
        md = sweep.render_index(manifest, extracts)
        self.assertIn("a \\| b", md)
        self.assertIn("**1 demonstrated**", md)

    def test_index_lists_failures_as_gaps(self):
        manifest = {"question": "q", "run_slug": "s", "built_at": "now", "queries": [],
                    "discovered": 1, "prefilter_dropped": 0, "attempted": 1,
                    "videos": [{"id": "v1", "status": "fetch-failed", "title": "T",
                                "url": "u", "error": "boom"}]}
        md = sweep.render_index(manifest, {})
        self.assertIn("Gaps — not in this corpus", md)
        self.assertIn("boom", md)

    def test_transcript_markdown_carries_provenance(self):
        md = sweep.transcript_markdown({
            "id": "v1", "title": "T", "channel": "C", "url": "u",
            "upload_date": "20260224", "duration_seconds": 60, "view_count": 5,
            "fetch_method": "captions-auto", "found_via": "q",
            "lines": [{"t": 0, "text": "hi"}]})
        self.assertIn("upload_date: 2026-02-24", md)
        self.assertIn("fetch_method: captions-auto", md)
        self.assertIn("**[0:00]** hi", md)


class TestPortability(unittest.TestCase):
    """Sibling skills are found from this skill's own file, never from the cwd."""

    SKILL = Path(__file__).resolve().parents[1]

    def test_yt_intel_resolved_as_sibling(self):
        self.assertEqual(sweep.paths.yt_intel_dir(), self.SKILL.parent / "yt-intel")

    def test_loaded_fetch_is_yt_intels(self):
        self.assertEqual(Path(sweep.ytfetch.__file__).resolve(),
                         self.SKILL.parent / "yt-intel" / "scripts" / "fetch.py")
        self.assertTrue(hasattr(sweep.ytfetch.paths, "data_root"))

    def test_default_corpus_dir_under_data_root(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            d = sweep.paths.default_corpus_dir("my-slug", Path(td))
            self.assertEqual(d, Path(td) / "yt-corpus" / "my-slug")
            self.assertTrue(d.is_dir())


if __name__ == "__main__":
    unittest.main(verbosity=2)
