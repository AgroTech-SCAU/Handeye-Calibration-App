from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReleaseContractTests(unittest.TestCase):
    def test_packaged_renderer_and_python_core_have_separate_roots(self) -> None:
        text = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
        self.assertIn("function rendererRoot()", text)
        self.assertIn("function coreRoot()", text)
        self.assertRegex(text, r"loadFile\(path\.join\(rendererRoot\(\)")
        self.assertIn("const root = coreRoot()", text)
        self.assertIn("path.join(root, 'backend', 'bridge.py')", text)

    def test_runtime_installer_is_packaged_and_exposed(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        resources = package["build"]["extraResources"]
        sources = {entry["from"] for entry in resources if isinstance(entry, dict)}
        self.assertIn("scripts/install-runtime.sh", sources)
        preload = (ROOT / "desktop" / "preload.js").read_text(encoding="utf-8")
        self.assertIn("runtimeInstall", preload)
        main = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
        self.assertIn("handeye:runtime-install", main)

    def test_release_workflow_builds_linux_artifacts(self) -> None:
        workflow = ROOT / ".github" / "workflows" / "release-linux.yml"
        self.assertTrue(workflow.exists())
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("build_linux.sh", text)
        self.assertRegex(text, r"AppImage")
        self.assertRegex(text, r"\.deb")

    def test_scripts_cover_supported_ubuntu_ros_mapping(self) -> None:
        launch = (ROOT / "launch.sh").read_text(encoding="utf-8")
        main = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
        for version, distro in (("20.04", "foxy"), ("22.04", "humble"), ("24.04", "jazzy")):
            self.assertIn(version, launch)
            self.assertIn(distro, launch)
            self.assertIn(version, main)
            self.assertIn(distro, main)

    def test_python38_zip_strict_compatibility_is_installed_outside_frozen_core(self) -> None:
        text = (ROOT / "backend" / "bridge.py").read_text(encoding="utf-8")
        self.assertIn("_install_zip_strict_compat", text)
        self.assertIn("sys.version_info < (3, 10)", text)
        self.assertIn("builtins.zip", text)

    def test_runtime_installer_prefers_system_python_for_ros_abi(self) -> None:
        text = (ROOT / "scripts" / "install-runtime.sh").read_text(encoding="utf-8")
        self.assertIn("/usr/bin/python3", text)
        self.assertIn("--system-site-packages", text)

    def test_linux_release_packaging_shape(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["devDependencies"]["electron"], "41.10.5")
        self.assertEqual(package["devDependencies"]["electron-builder"], "26.15.3")
        self.assertEqual(package["build"]["linux"]["target"], ["AppImage", "deb"])
        self.assertIn("libfuse2 | libfuse2t64", package["build"]["deb"]["depends"])

    def test_release_workflow_does_not_assume_a_lockfile(self) -> None:
        text = (ROOT / ".github" / "workflows" / "release-linux.yml").read_text(encoding="utf-8")
        self.assertNotIn("cache: npm", text)
        self.assertIn("npm install", text)

    def test_python_runtime_ignores_user_site_packages(self) -> None:
        install = (ROOT / "install.sh").read_text(encoding="utf-8")
        launch = (ROOT / "launch.sh").read_text(encoding="utf-8")
        main = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
        runtime = (ROOT / "scripts" / "install-runtime.sh").read_text(encoding="utf-8")
        for text in (install, launch, main, runtime):
            self.assertIn("PYTHONNOUSERSITE", text)

    def test_source_installer_prefers_system_python_for_ros_abi(self) -> None:
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("/usr/bin/python3", text)
        self.assertIn("PYTHON_BIN", text)
        self.assertIn("--system-site-packages", text)

    def test_python_backend_uses_headless_opencv(self) -> None:
        text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("opencv-python-headless", text)
        self.assertNotIn("opencv-python>=", text)

    def test_source_installer_checks_node_major_version(self) -> None:
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("NODE_MAJOR", text)
        self.assertIn("Node.js 20+", text)

    def test_source_installer_retries_electron_download_via_mirror(self) -> None:
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("ELECTRON_MIRROR", text)
        self.assertIn("npmmirror.com/mirrors/electron", text)
        self.assertIn("retry", text.lower())

    def test_source_installer_keeps_npm_output_focused_on_errors(self) -> None:
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("--no-audit", text)
        self.assertIn("--no-fund", text)
        self.assertIn("--loglevel=error", text)

    def test_linux_builder_retries_binary_download_via_mirror(self) -> None:
        text = (ROOT / "build_linux.sh").read_text(encoding="utf-8")
        self.assertIn("ELECTRON_BUILDER_BINARIES_MIRROR", text)
        self.assertIn("npmmirror.com/mirrors/electron-builder-binaries", text)

    def test_public_docs_follow_repository_style_contract(self) -> None:
        for name in ("README.md", "USER_GUIDE.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn(chr(0x3002), text, name)
            self.assertNotIn(chr(0x5F53) + chr(0x524D) + chr(0x7248) + chr(0x672C), text, name)
        self.assertIn("Kudu", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertFalse((ROOT / "docs" / "superpowers").exists())

    def test_backend_lifecycle_smoke_is_part_of_test_command(self) -> None:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertIn("smoke:lifecycle", package["scripts"])
        self.assertIn("smoke:lifecycle", package["scripts"]["test"])
        self.assertTrue((ROOT / "scripts" / "smoke_backend_lifecycle.cjs").exists())

    def test_backend_startup_waits_for_ready_before_serving_requests(self) -> None:
        text = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
        self.assertIn("backendReadyPromise", text)
        self.assertIn("awaitBackendReady", text)
        self.assertIn("backendReadyResolve", text)
        self.assertIn("backendReadyReject", text)
        create_start = text.index("function createWindow()")
        load_index = text.index("win.loadFile", create_start)
        start_index = text.index("startPython()", create_start)
        self.assertLess(start_index, load_index)

    def test_source_installer_runs_backend_smoke_before_node_install(self) -> None:
        smoke = ROOT / "scripts" / "smoke_backend.py"
        self.assertTrue(smoke.exists())
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        smoke_index = text.index("scripts/smoke_backend.py")
        npm_index = text.index("npm install --ignore-scripts")
        self.assertLess(smoke_index, npm_index)

    def test_source_installer_cleans_up_child_on_interrupt(self) -> None:
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("trap", text)
        self.assertIn('kill "$pid"', text)
        self.assertIn("INT TERM", text)

    def test_source_installer_separates_npm_packages_from_electron_binary(self) -> None:
        text = (ROOT / "install.sh").read_text(encoding="utf-8")
        self.assertIn("npm install --ignore-scripts", text)
        self.assertIn("node_modules/electron/install.js", text)
        self.assertIn("run_with_heartbeat", text)
        self.assertIn("Electron binary", text)

    def test_no_tauri_websocket_or_vite_runtime(self) -> None:
        self.assertFalse((ROOT / "src-tauri").exists())
        package_text = (ROOT / "package.json").read_text(encoding="utf-8").lower()
        self.assertNotIn("vite", package_text)
        self.assertNotIn("websocket", package_text)
        self.assertNotIn("localhost", (ROOT / "desktop" / "main.js").read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
