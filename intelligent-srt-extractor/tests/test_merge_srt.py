import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("merge_srt", ROOT / "scripts/merge_srt.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MergeSrtTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.case = Path(self.temp.name)
        self.out = self.case / "张三-字幕汇总.srt"

    def source(self, name, content, encoding="utf-8"):
        path = self.case / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode(encoding))
        return path

    def merge(self, inputs, titles=None):
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            module.merge(self.out, inputs, titles or {})
        return log.getvalue()

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/merge_srt.py"), *map(str, args)],
                              capture_output=True, text=True)

    def test_exact_format_and_source_preservation(self):
        first = self.source("术前采访/DE1A0870.srt",
                            "8\r\n00:04:14,000 --> 00:04:14,966\r\n  昨天我们就修了一个  \r\n第二行\r\n\r\n"
                            "9\r\n00:04:16,166 --> 00:04:17,133\r\n他以前\r\n", "utf-8-sig")
        second = self.source("面诊/DE1A0871.srt",
                             "6\n00:00:01,800 --> 00:00:03,900\n现在很多\n")
        before = [p.read_bytes() for p in (first, second)]
        self.merge([first, second])
        expected = ("术前采访-DE1A0870\n\n1\n00:04:14,000 --> 00:04:14,966\n"
                    "  昨天我们就修了一个  \n第二行\n\n2\n00:04:16,166 --> 00:04:17,133\n他以前\n\n"
                    "面诊-DE1A0871\n\n1\n00:00:01,800 --> 00:00:03,900\n现在很多\n")
        self.assertEqual(self.out.read_bytes(), expected.replace("\n", "\r\n").encode("utf-8-sig"))
        self.assertEqual(before, [p.read_bytes() for p in (first, second)])

    def test_filter_whole_cues_without_deleting_normal_sentences(self):
        parts = ["字幕by索兰娅", "字幕製作人Zither Harp", "劇院", "滷汁", "在剧院工作需要自然一点"]
        source = self.source("采访/a.srt", "\n\n".join(
            f"{i}\n00:00:01,000 --> 00:00:02,000\n{text}" for i, text in enumerate(parts, 1)))
        log = self.merge([source])
        output = self.out.read_text(encoding="utf-8-sig")
        self.assertIn("在剧院工作需要自然一点", output)
        self.assertNotIn("索兰娅", output)
        self.assertIn("dropped=4", log)
        self.assertIn("\n1\n", output)

    def test_empty_and_all_junk_sections_are_skipped(self):
        empty = self.source("空镜/empty.srt", "\ufeff\n")
        junk = self.source("空镜/junk.srt", "1\n00:00:00,000 --> 00:00:01,000\n劇院\n")
        good = self.source("采访/good.srt", "1\n00:00:00,000 --> 00:00:01,000\n鼻子\n")
        log = self.merge([empty, junk, good])
        self.assertNotIn("空镜-", self.out.read_text(encoding="utf-8-sig"))
        self.assertIn("空字幕", log)
        self.assertIn("仅含幻觉/水印", log)

    def test_all_filtered_preserves_existing_output(self):
        self.out.write_bytes(b"previous output")
        source = self.source("a.srt", "1\n00:00:00,000 --> 00:00:01,000\n滷汁\n")
        with self.assertRaises(RuntimeError):
            self.merge([source])
        self.assertEqual(self.out.read_bytes(), b"previous output")

    def test_invalid_input_preserves_existing_output(self):
        self.out.write_bytes(b"previous output")
        for invalid in ["this is not SRT", "1\n00:00:02,000 --> 00:00:01,000\n文本\n",
                        "1\n00:61:00,000 --> 00:62:00,000\n文本\n"]:
            source = self.source("broken.srt", invalid)
            with self.assertRaises(ValueError):
                self.merge([source])
            self.assertEqual(self.out.read_bytes(), b"previous output")
        with self.assertRaises(FileNotFoundError):
            self.merge([self.case / "missing.srt"])
        self.assertEqual(self.out.read_bytes(), b"previous output")

    def test_cannot_overwrite_source(self):
        self.source(self.out.name, "1\n00:00:00,000 --> 00:00:01,000\n原文\n")
        before = self.out.read_bytes()
        with self.assertRaises(ValueError):
            self.merge([self.out])
        self.assertEqual(self.out.read_bytes(), before)

    def test_explicit_cli_order_titles_and_legacy_encoding(self):
        second = self.source("采访/10.srt", "00:00:01.000  -->  00:00:02.000\n鼻尖\n", "gb18030")
        first = self.source("采访/2.srt", "1\n00:00:00,000 --> 00:00:01,000\n鼻背\n")
        result = self.cli("--out", self.out, "--titles", "嵌套-术前-10|嵌套-术后-2", second, first)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.out.read_text(encoding="utf-8-sig")
        self.assertLess(output.index("嵌套-术前-10"), output.index("嵌套-术后-2"))
        self.assertIn("00:00:01.000  -->  00:00:02.000", output)

    def test_folder_cli_natural_order_and_repeat_no_self_merge(self):
        self.source("采访/10.srt", "1\n00:00:00,000 --> 00:00:01,000\n十\n")
        self.source("采访/2.SRT", "1\n00:00:00,000 --> 00:00:01,000\n二\n")
        self.source("旧-案例素材母稿.srt", "should not be parsed")
        result = self.cli("--folder", self.case, "--name", "张三")
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.out.read_bytes()
        output = before.decode("utf-8-sig")
        self.assertLess(output.index("采访-2"), output.index("采访-10"))
        result = self.cli("--folder", self.case, "--name", "张三")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("已有汇总文件", result.stdout)
        self.assertEqual(before, self.out.read_bytes())
        self.assertEqual(sorted(p.name for p in self.case.iterdir()),
                         ["张三-字幕汇总.srt", "旧-案例素材母稿.srt", "采访"])

    def test_invalid_cli_options_do_not_write(self):
        source = self.source("a.srt", "1\n00:00:00,000 --> 00:00:01,000\n鼻子\n")
        for options in [("--folder", self.case, "--out", self.out),
                        ("--out", self.out, "--titles", "a|b", source),
                        ("--folder", self.case, "--name", "../escape")]:
            result = self.cli(*options)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.out.exists())

    def test_term_fixer_skips_aggregate_even_with_correction_match(self):
        original = "采访-a\r\n\r\n1\r\n00:00:00,000 --> 00:00:01,000\r\n提鸡\r\n"
        self.out.write_bytes(original.encode("utf-8-sig"))
        source = self.source("a.srt", "1\n00:00:00,000 --> 00:00:01,000\n提鸡\n")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/fix_terms.py"), str(self.case), "--fix"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.out.read_bytes(), original.encode("utf-8-sig"))
        self.assertIn("提肌", source.read_text())


if __name__ == "__main__":
    unittest.main()
