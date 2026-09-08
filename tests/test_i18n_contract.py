from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class I18nContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = (ROOT / "src" / "renderer" / "app.js").read_text(encoding="utf-8")
        cls.html = (ROOT / "src" / "renderer" / "index.html").read_text(encoding="utf-8")
        cls.locale_path = ROOT / "src" / "renderer" / "locales.js"
        cls.locales = cls.locale_path.read_text(encoding="utf-8") if cls.locale_path.exists() else ""

    def test_locales_define_simplified_chinese_and_english(self) -> None:
        self.assertTrue(self.locale_path.exists())
        self.assertIn("'zh-CN'", self.locales)
        self.assertIn("'en'", self.locales)
        self.assertIn("简体中文", self.locales)
        self.assertIn("English", self.locales)

    def test_first_run_uses_system_language_and_persists_selection(self) -> None:
        combined = self.app + self.locales
        self.assertIn("navigator.language", combined)
        self.assertIn("handeye-language", combined)
        self.assertIn("localStorage.setItem", combined)
        self.assertIn("startsWith('zh')", combined)

    def test_settings_contains_language_selector(self) -> None:
        self.assertIn("language-selector", self.app)
        self.assertIn("setLanguage", self.app)
        self.assertIn("简体中文", self.locales)
        self.assertIn("English", self.locales)

    def test_renderer_loads_locales_before_app(self) -> None:
        locales_index = self.html.index("locales.js")
        app_index = self.html.index("app.js")
        self.assertLess(locales_index, app_index)

    def test_app_ui_copy_is_not_hardcoded_in_chinese(self) -> None:
        chinese = [ch for ch in self.app if "\u4e00" <= ch <= "\u9fff"]
        self.assertEqual(chinese, [])

    def test_language_switch_only_rerenders_ui(self) -> None:
        start = self.app.index("function setLanguage")
        end = self.app.index("function applyTheme", start)
        body = self.app[start:end]
        self.assertNotIn("backendRestart", body)
        self.assertNotIn("runtimeInstall", body)
        self.assertIn("renderPage", body)
        self.assertIn("updateShell", body)


if __name__ == "__main__":
    unittest.main()
