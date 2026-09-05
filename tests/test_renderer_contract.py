from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RendererContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.js = (ROOT / "src" / "renderer" / "app.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "src" / "renderer" / "styles.css").read_text(encoding="utf-8")
        cls.html = (ROOT / "src" / "renderer" / "index.html").read_text(encoding="utf-8")

    def test_desktop_shell_is_present(self) -> None:
        for token in (
            "titlebar", "sidebar", "top-status", "runtime-card", "nav-item",
            "--accent: #f59e0b", "--page-bg: #0a0a10", "page-in",
        ):
            self.assertIn(token, self.js + self.css)


    def test_live_events_do_not_rebuild_the_page(self) -> None:
        start = self.js.index("function handleEvent")
        end = self.js.index("async function boot", start)
        handler = self.js[start:end]
        self.assertNotIn("renderPage()", handler)
        self.assertIn("updatePreviewFrame", handler)
        self.assertIn("updatePoseView", handler)

    def test_font_scale_is_exactly_1_15(self) -> None:
        self.assertIn("--font-scale: 1.15", self.css)
        self.assertIn("font-size:16.1px", self.css)

    def test_gui_does_not_name_reference_project(self) -> None:
        combined = (self.js + self.html + self.css).lower()
        self.assertNotIn("kudu", combined)

    def test_renderer_has_all_workflow_pages(self) -> None:
        for name in (
            "renderConnect", "renderIntrinsics", "renderHandeye", "renderSolve",
            "renderSettings", "renderAbout",
        ):
            self.assertIn(f"function {name}", self.js)

    def test_runtime_setup_is_actionable_from_settings(self) -> None:
        self.assertIn("install-runtime", self.js)
        self.assertIn("api.runtimeInstall", self.js)
        self.assertIn("onRuntimeInstall", self.js)
        self.assertIn("restart-backend", self.js)
        self.assertIn("api.backendRestart", self.js)

    def test_theme_supports_system_dark_light(self) -> None:
        for theme in ("system", "dark", "light"):
            self.assertIn(theme, self.js)
        self.assertIn(":root.light", self.css)
        self.assertIn("prefers-color-scheme", self.js)

    def test_theme_controls_use_fixed_icon_boxes(self) -> None:
        self.assertIn("theme-option-icon", self.js)
        self.assertIn(".theme-option-icon", self.css)
        self.assertIn("appearance-toggle", self.js)
        self.assertIn("appearance-menu", self.js)

    def test_motion_pipeline_uses_gpu_friendly_transforms(self) -> None:
        self.assertIn("--ease-spring", self.css)
        self.assertIn("translate3d", self.css)
        self.assertIn("will-change:transform", self.css.replace(" ", ""))
        self.assertIn("requestAnimationFrame", self.js)

    def test_renderer_is_local_only(self) -> None:
        combined = (self.js + self.html).lower()
        for forbidden in ("http://", "https://", "localhost", "websocket"):
            self.assertNotIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
