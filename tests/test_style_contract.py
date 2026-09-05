from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", "node_modules", "__pycache__", "dist", "build"}
TEXT_SUFFIXES = {".py", ".js", ".mjs", ".html", ".css", ".md", ".txt", ".yaml", ".yml", ".json", ".sh"}
FULL_STOP = chr(0x3002)
BANNED_HISTORY = (chr(0x65E7), chr(0x5386) + chr(0x53F2), chr(0x4E4B) + chr(0x524D), chr(0x8FC7) + chr(0x5F80) + chr(0x7248) + chr(0x672C), "leg" + "acy")
PARAGRAPH_END_PUNCT = tuple(chr(0x3002) + "！？!?；;，,：:")

FROZEN_CORE = {
    "algorithm_runner.py",
    "calibration_engine.py",
    "config.py",
    "ros_interface.py",
    "algorithms/bundle_adjust.py",
    "algorithms/calib_utils.py",
    "algorithms/diagnose.py",
    "algorithms/fk_utils.py",
    "algorithms/robot_params.yaml",
    "algorithms/solve.py",
    "algorithms/verify.py",
}


def text_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.relative_to(ROOT).as_posix() in FROZEN_CORE:
            continue
        yield path


class RepositoryStyleContractTests(unittest.TestCase):
    def test_no_chinese_full_stop_anywhere(self) -> None:
        offenders = []
        for path in text_files():
            text = path.read_text(encoding="utf-8")
            if FULL_STOP in text:
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_no_history_or_version_comparison_phrasing(self) -> None:
        offenders = []
        for path in text_files():
            text = path.read_text(encoding="utf-8")
            for token in BANNED_HISTORY:
                if token in text:
                    offenders.append(f"{path.relative_to(ROOT)}:{token}")
        self.assertEqual(offenders, [])

    def test_source_comments_have_no_terminal_punctuation(self) -> None:
        punctuation = set(".!?;:," + chr(0x3002) + "！？；，：…")
        offenders = []
        for path in text_files():
            if path.suffix.lower() not in {".py", ".js", ".mjs", ".sh", ".yaml", ".yml"}:
                continue
            for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith(("#", "//")) and stripped[-1:] in punctuation:
                    offenders.append(f"{path.relative_to(ROOT)}:{index}")
        self.assertEqual(offenders, [])

    def test_renderer_copy_has_no_ellipsis_terminal_style(self) -> None:
        text = (ROOT / "src" / "renderer" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("…", text)

    def test_markdown_prose_paragraphs_have_no_terminal_punctuation(self) -> None:
        offenders = []
        for name in ("README.md", "USER_GUIDE.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            in_fence = False
            paragraph = []

            def check_paragraph(lines):
                if not lines:
                    return
                joined = " ".join(line.strip() for line in lines).strip()
                if not joined or joined.startswith(("#", "- ", "* ", ">", "|")):
                    return
                if joined[-1] in PARAGRAPH_END_PUNCT or joined.endswith("."):
                    offenders.append(f"{name}:{joined[-40:]}")

            for line in text.splitlines() + [""]:
                if line.strip().startswith("```"):
                    check_paragraph(paragraph)
                    paragraph = []
                    in_fence = not in_fence
                    continue
                if in_fence:
                    continue
                if not line.strip():
                    check_paragraph(paragraph)
                    paragraph = []
                else:
                    paragraph.append(line)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
