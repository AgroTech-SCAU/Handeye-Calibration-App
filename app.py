from __future__ import annotations

import queue
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox

import cv2
import customtkinter as ctk
from PIL import Image

from algorithm_runner import run_algorithm
from calibration_engine import (
    HandEyeCollection,
    IntrinsicCalibration,
    detect_chessboard,
)
from camera_info_utils import save_camera_info_intrinsics
from config import AppConfig
from ros_interface import ContractTopics, RosCameraInfo, RosImage, RosInterface, RosPose

APP_TITLE = "HandEye Calibration"
QUALITY_LABELS = {
    "标准质量（推荐）": "standard",
    "严格质量": "strict",
    "极简采样": "minimal",
}
SOLVE_MODES = {
    "标准鲁棒求解（推荐）": "robust",
    "极简 OpenCV 求解": "minimal",
    "标准求解 + Bundle Adjustment": "ba",
}


class HandEyeApp(ctk.CTk):
    def __init__(self) -> None:
        self.config_data = AppConfig.load()
        ctk.set_appearance_mode(self.config_data.appearance_mode)
        ctk.set_default_color_theme("blue")
        # Linux 桌面默认字号偏小，统一放大控件与文字以提升可读性
        ctk.set_widget_scaling(1.25)
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1240x800")
        self.minsize(1080, 700)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.latest_pose: RosPose | None = None
        self.latest_image: RosImage | None = None
        self.latest_camera_info: RosCameraInfo | None = None
        self.intrinsic = IntrinsicCalibration()
        self.handeye = HandEyeCollection()
        self.tool_running = False
        self._preview_images: dict[object, ctk.CTkImage] = {}
        self._preview_labels: list[ctk.CTkLabel] = []
        self._last_preview_render = 0.0

        self.ros = RosInterface(
            lambda value: self.events.put(("pose", value)),
            lambda value: self.events.put(("image", value)),
            lambda value: self.events.put(("camera_info", value)),
            lambda text: self.events.put(("error", text)),
        )

        self._build_shell()
        self._show_page("connect")
        self.after(50, self._tick)

    # ---------- shell ----------
    def _build_shell(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        ctk.CTkLabel(
            sidebar,
            text="HandEye",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(28, 2))
        ctk.CTkLabel(
            sidebar,
            text="Calibration Workstation",
            text_color=("#6E6E73", "#A1A1A6"),
        ).pack(anchor="w", padx=24, pady=(0, 28))

        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for key, text in (
            ("connect", "01   Connect"),
            ("intrinsics", "02   Intrinsics"),
            ("handeye", "03   Hand-Eye"),
            ("solve", "04   Solve"),
        ):
            button = ctk.CTkButton(
                sidebar,
                text=text,
                anchor="w",
                height=42,
                corner_radius=10,
                fg_color="transparent",
                hover_color=("#E8E8ED", "#2C2C2E"),
                text_color=("#1D1D1F", "#F5F5F7"),
                command=lambda page=key: self._show_page(page),
            )
            button.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[key] = button

        ctk.CTkFrame(sidebar, height=1).pack(fill="x", padx=18, pady=(18, 12))
        self.sidebar_status = ctk.CTkLabel(
            sidebar,
            text="● ROS2 未启动",
            text_color="#FF9500",
            anchor="w",
        )
        self.sidebar_status.pack(side="bottom", fill="x", padx=24, pady=24)

        self.content = ctk.CTkFrame(
            self, corner_radius=0, fg_color=("#F5F5F7", "#1C1C1E")
        )
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.content, corner_radius=0, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(22, 8))
        header.grid_columnconfigure(0, weight=1)
        self.page_title = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=25, weight="bold"),
        )
        self.page_title.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            header,
            text="保存设置",
            width=92,
            corner_radius=9,
            command=self.save_config,
        ).grid(row=0, column=1, sticky="e")

        self.page_host = ctk.CTkFrame(self.content, fg_color="transparent")
        self.page_host.grid(row=1, column=0, sticky="nsew", padx=30, pady=(8, 28))
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)

        self.pages = {
            "connect": self._build_connect_page(),
            "intrinsics": self._build_intrinsics_page(),
            "handeye": self._build_handeye_page(),
            "solve": self._build_solve_page(),
        }

    def _new_page(self) -> ctk.CTkScrollableFrame:
        page = ctk.CTkScrollableFrame(
            self.page_host,
            fg_color="transparent",
            corner_radius=0,
        )
        page.grid_columnconfigure(0, weight=1)
        return page

    def _card(self, parent, title: str, subtitle: str = "") -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=14, fg_color=("#FFFFFF", "#2C2C2E"))
        card.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 10))
        ctk.CTkLabel(head, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w"
        )
        if subtitle:
            ctk.CTkLabel(
                head,
                text=subtitle,
                text_color=("#6E6E73", "#A1A1A6"),
                wraplength=760,
                justify="left",
            ).pack(anchor="w", pady=(3, 0))
        return card

    def _build_preview(self, parent, row: int) -> ctk.CTkLabel:
        box = self._card(
            parent, "RGB Preview", "实时显示当前选择的 sensor_msgs/msg/Image"
        )
        box.grid(row=row, column=0, sticky="ew", pady=(12, 0))
        label = ctk.CTkLabel(
            box,
            text="等待 ROS 图像…",
            height=330,
            corner_radius=10,
            fg_color=("#ECECF0", "#111113"),
            text_color=("#6E6E73", "#A1A1A6"),
        )
        label.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))
        self._preview_labels.append(label)
        return label

    # ---------- Connect ----------
    def _build_connect_page(self):
        page = self._new_page()

        project = self._card(page, "Project", "输出文件统一保存在该目录")
        project.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        row = ctk.CTkFrame(project, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))
        row.grid_columnconfigure(0, weight=1)
        self.output_var = ctk.StringVar(value=self.config_data.output_dir)
        ctk.CTkEntry(row, textvariable=self.output_var).grid(
            row=0, column=0, sticky="ew"
        )
        ctk.CTkButton(row, text="浏览", width=74, command=self.choose_output).grid(
            row=0, column=1, padx=(8, 0)
        )

        ros_card = self._card(
            page,
            "ROS2 Sources",
            "Topic 名称不固定；刷新后从当前 ROS graph 选择，也可以直接输入自己的话题",
        )
        ros_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ros_card.grid_columnconfigure(1, weight=1)

        self.pose_topic_var = ctk.StringVar(value=self.config_data.pose_topic)
        self.image_topic_var = ctk.StringVar(value=self.config_data.image_topic)
        self.camera_info_topic_var = ctk.StringVar(
            value=self.config_data.camera_info_topic
        )
        fields = (
            ("Robot Pose", self.pose_topic_var, "geometry_msgs/msg/PoseStamped"),
            ("RGB Image", self.image_topic_var, "sensor_msgs/msg/Image"),
            (
                "Camera Info（可选）",
                self.camera_info_topic_var,
                "sensor_msgs/msg/CameraInfo",
            ),
        )
        self.topic_boxes: list[ctk.CTkComboBox] = []
        for index, (label, variable, type_name) in enumerate(fields, start=1):
            ctk.CTkLabel(ros_card, text=label, anchor="w").grid(
                row=index, column=0, sticky="w", padx=(18, 12), pady=6
            )
            combo = ctk.CTkComboBox(
                ros_card,
                variable=variable,
                values=[variable.get()] if variable.get() else [""],
                state="normal",
                height=34,
            )
            combo.grid(row=index, column=1, sticky="ew", padx=(0, 10), pady=6)
            ctk.CTkLabel(
                ros_card,
                text=type_name,
                text_color=("#6E6E73", "#A1A1A6"),
                width=250,
                anchor="w",
            ).grid(row=index, column=2, sticky="w", padx=(0, 18), pady=6)
            self.topic_boxes.append(combo)

        actions = ctk.CTkFrame(ros_card, fg_color="transparent")
        actions.grid(row=4, column=0, columnspan=3, sticky="ew", padx=18, pady=(12, 10))
        ctk.CTkButton(
            actions, text="启动 / 刷新 ROS2", command=self.start_or_refresh_ros
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="应用订阅",
            fg_color="#34C759",
            hover_color="#2DAE4B",
            command=self.apply_ros_topics,
        ).pack(side="left", padx=8)
        self.connection_status = ctk.CTkLabel(
            actions, text="未连接", text_color="#FF9500"
        )
        self.connection_status.pack(side="left", padx=8)

        status_row = ctk.CTkFrame(ros_card, fg_color="transparent")
        status_row.grid(
            row=5, column=0, columnspan=3, sticky="ew", padx=18, pady=(0, 16)
        )
        self.pose_status = ctk.CTkLabel(status_row, text="Pose: 等待", anchor="w")
        self.pose_status.pack(side="left", padx=(0, 24))
        self.image_status = ctk.CTkLabel(status_row, text="Image: 等待", anchor="w")
        self.image_status.pack(side="left", padx=(0, 24))
        self.info_status = ctk.CTkLabel(status_row, text="CameraInfo: 可选", anchor="w")
        self.info_status.pack(side="left")

        guide = self._card(
            page, "接入约定", "机械臂控制、拖拽和正运动学由用户自己的机器人程序负责"
        )
        guide.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        guide_text = (
            "机械臂只需持续发布 geometry_msgs/msg/PoseStamped，语义为 ^base T_gripper；"
            "position 单位 m，orientation 为 xyzw 四元数\n"
            "相机只需发布 sensor_msgs/msg/Image；v1 支持 mono8 / bgr8 / rgb8 / bgra8 / rgba8\n"
            "如果已有可靠内参，可额外发布 sensor_msgs/msg/CameraInfo，并在 Intrinsics 页直接导入"
        )
        ctk.CTkLabel(
            guide,
            text=guide_text,
            justify="left",
            anchor="w",
            wraplength=900,
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))

        self._build_preview(page, 3)
        return page

    # ---------- Intrinsics ----------
    def _build_intrinsics_page(self):
        page = self._new_page()
        board = self._card(
            page, "Calibration Board", "角点列/行填写内角点数量，方格边长单位 mm"
        )
        board.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        grid = ctk.CTkFrame(board, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.cols_var = ctk.StringVar(value=str(self.config_data.chessboard_cols))
        self.rows_var = ctk.StringVar(value=str(self.config_data.chessboard_rows))
        self.square_var = ctk.StringVar(value=str(self.config_data.square_size_mm))
        for col, (label, variable) in enumerate(
            (
                ("角点列数", self.cols_var),
                ("角点行数", self.rows_var),
                ("方格边长 / mm", self.square_var),
            )
        ):
            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=0, column=col, sticky="w", padx=(0, 20))
            ctk.CTkLabel(cell, text=label).pack(anchor="w")
            ctk.CTkEntry(cell, textvariable=variable, width=150).pack(
                anchor="w", pady=(4, 0)
            )

        capture = self._card(
            page,
            "Camera Intrinsics",
            "已有 CameraInfo 可直接导入；否则使用当前 ROS RGB 图像采集棋盘并求解",
        )
        capture.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        line = ctk.CTkFrame(capture, fg_color="transparent")
        line.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        self.intrinsic_quality_var = ctk.StringVar(value="标准质量（推荐）")
        ctk.CTkOptionMenu(
            line,
            values=list(QUALITY_LABELS),
            variable=self.intrinsic_quality_var,
            width=190,
        ).pack(side="left")
        ctk.CTkButton(
            line, text="从 CameraInfo 导入", command=self.import_camera_info
        ).pack(side="left", padx=8)
        ctk.CTkButton(line, text="采集当前图像", command=self.capture_intrinsic).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(line, text="计算并保存内参", command=self.solve_intrinsic).pack(
            side="left"
        )
        ctk.CTkButton(
            line,
            text="清空",
            width=70,
            fg_color="transparent",
            border_width=1,
            text_color=("#1D1D1F", "#F5F5F7"),
            command=self.clear_intrinsic,
        ).pack(side="right")
        self.intrinsic_status = ctk.CTkLabel(
            capture,
            text="已采集 0 张；标准模式建议 20～30 张",
            anchor="w",
        )
        self.intrinsic_status.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        self._build_preview(page, 2)
        return page

    # ---------- HandEye ----------
    def _build_handeye_page(self):
        page = self._new_page()
        pose_card = self._card(
            page,
            "Current Robot Pose",
            "读取当前选择的 PoseStamped；APP 不计算机械臂 FK",
        )
        pose_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.pose_value_label = ctk.CTkLabel(
            pose_card,
            text="等待 PoseStamped…",
            font=ctk.CTkFont(family="monospace", size=14),
            justify="left",
            anchor="w",
        )
        self.pose_value_label.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))

        sample = self._card(
            page,
            "Hand-Eye Sampling",
            "固定棋盘，手动拖拽机械臂到不同位置与姿态；停稳后记录当前 Image + Pose",
        )
        sample.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        actions = ctk.CTkFrame(sample, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        self.handeye_quality_var = ctk.StringVar(value="标准质量（推荐）")
        ctk.CTkOptionMenu(
            actions,
            values=list(QUALITY_LABELS),
            variable=self.handeye_quality_var,
            width=190,
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="记录当前样本",
            fg_color="#FF9500",
            hover_color="#E68600",
            command=self.capture_handeye,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            actions, text="保存 samples.yaml", command=self.save_samples
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="清空",
            width=70,
            fg_color="transparent",
            border_width=1,
            text_color=("#1D1D1F", "#F5F5F7"),
            command=self.clear_samples,
        ).pack(side="right")
        self.sample_status = ctk.CTkLabel(
            sample, text="已采集 0 组；建议 20～30 组", anchor="w"
        )
        self.sample_status.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        self._build_preview(page, 2)
        return page

    # ---------- Solve ----------
    def _build_solve_page(self):
        page = self._new_page()
        solve = self._card(
            page,
            "Diagnose · Solve · Verify",
            "直接调用仓库内已经验证的 algorithms，不改变求解数学实现",
        )
        solve.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        controls = ctk.CTkFrame(solve, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.solve_mode_var = ctk.StringVar(value="标准鲁棒求解（推荐）")
        ctk.CTkOptionMenu(
            controls,
            values=list(SOLVE_MODES),
            variable=self.solve_mode_var,
            width=220,
        ).pack(side="left")
        for text, action in (
            ("诊断", lambda: self.run_tool("diagnose")),
            ("求解", lambda: self.run_tool("solve")),
            ("验证", lambda: self.run_tool("verify")),
            ("完整流程", self.run_all),
        ):
            ctk.CTkButton(controls, text=text, width=82, command=action).pack(
                side="left", padx=(8, 0)
            )
        self.solve_status = ctk.CTkLabel(solve, text="等待 samples.yaml", anchor="w")
        self.solve_status.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.log = ctk.CTkTextbox(
            solve,
            height=470,
            corner_radius=10,
            font=ctk.CTkFont(family="monospace", size=13),
        )
        self.log.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))
        return page

    # ---------- navigation/config ----------
    def _show_page(self, name: str) -> None:
        titles = {
            "connect": "Connect",
            "intrinsics": "Intrinsics",
            "handeye": "Hand-Eye Sampling",
            "solve": "Solve & Verify",
        }
        for page in self.pages.values():
            page.grid_forget()
        self.pages[name].grid(row=0, column=0, sticky="nsew")
        self.page_title.configure(text=titles[name])
        for key, button in self.nav_buttons.items():
            button.configure(
                fg_color=("#E8E8ED", "#3A3A3C") if key == name else "transparent"
            )

    def choose_output(self) -> None:
        folder = filedialog.askdirectory(
            initialdir=self.output_var.get() or str(Path.home())
        )
        if folder:
            self.output_var.set(folder)

    def _numbers(self) -> tuple[int, int, float]:
        cols = int(self.cols_var.get())
        rows = int(self.rows_var.get())
        square = float(self.square_var.get())
        if cols < 2 or rows < 2 or square <= 0:
            raise ValueError("棋盘参数无效")
        return cols, rows, square

    def _paths(self) -> tuple[Path, Path, Path]:
        output = Path(self.output_var.get()).expanduser().resolve()
        return output, output / "camera_intrinsics.yaml", output / "samples.yaml"

    def save_config(self) -> None:
        try:
            cols, rows, square = self._numbers()
            config = AppConfig(
                output_dir=self.output_var.get(),
                chessboard_cols=cols,
                chessboard_rows=rows,
                square_size_mm=square,
                pose_topic=self.pose_topic_var.get().strip(),
                image_topic=self.image_topic_var.get().strip(),
                camera_info_topic=self.camera_info_topic_var.get().strip(),
                appearance_mode=self.config_data.appearance_mode,
            )
            config.save()
            self.config_data = config
            self._toast("设置已保存")
        except Exception as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    # ---------- ROS ----------
    def start_or_refresh_ros(self) -> None:
        try:
            if not self.ros.running:
                self.ros.start()
                self.sidebar_status.configure(
                    text="● ROS2 已启动", text_color="#34C759"
                )
                self.connection_status.configure(
                    text="ROS2 已启动", text_color="#34C759"
                )
                self.after(250, self._refresh_topics)
            else:
                self._refresh_topics()
        except Exception as exc:
            self._show_error(str(exc))

    def _refresh_topics(self) -> None:
        try:
            topics = self.ros.discover_topics()
            self._set_topic_values(topics)
            self.connection_status.configure(
                text="话题列表已刷新", text_color="#34C759"
            )
        except Exception as exc:
            self._show_error(str(exc))

    def _set_topic_values(self, topics: ContractTopics) -> None:
        values = (
            topics.pose_topics,
            topics.image_topics,
            ("",) + topics.camera_info_topics,
        )
        variables = (
            self.pose_topic_var,
            self.image_topic_var,
            self.camera_info_topic_var,
        )
        for combo, variable, options in zip(
            self.topic_boxes, variables, values, strict=True
        ):
            current = variable.get().strip()
            merged = list(options) or [""]
            if current and current not in merged:
                merged.insert(0, current)
            combo.configure(values=merged)
            if not current and merged and merged[0]:
                variable.set(merged[0])

    def apply_ros_topics(self) -> None:
        try:
            if not self.ros.running:
                self.ros.start()
                self.sidebar_status.configure(
                    text="● ROS2 已启动", text_color="#34C759"
                )
            self.ros.subscribe(
                self.pose_topic_var.get(),
                self.image_topic_var.get(),
                self.camera_info_topic_var.get(),
            )
            self.connection_status.configure(text="● 已订阅", text_color="#34C759")
            self.save_config()
        except Exception as exc:
            self._show_error(str(exc))

    # ---------- intrinsics ----------
    def import_camera_info(self) -> None:
        if self.latest_camera_info is None:
            self._show_error(
                "尚未收到 CameraInfo；请先在 Connect 页选择并应用 CameraInfo topic"
            )
            return
        try:
            _, intrinsics_path, _ = self._paths()
            payload = save_camera_info_intrinsics(
                intrinsics_path, self.latest_camera_info
            )
            self.intrinsic_status.configure(
                text=f"已从 CameraInfo 保存内参：{payload['image_width']}×{payload['image_height']} → {intrinsics_path}"
            )
        except Exception as exc:
            self._show_error(str(exc))

    def capture_intrinsic(self) -> None:
        if self.latest_image is None:
            self._show_error("尚未收到 RGB 图像")
            return
        try:
            cols, rows, square = self._numbers()
            mode = QUALITY_LABELS[self.intrinsic_quality_var.get()]
            result = self.intrinsic.add(
                self.latest_image.frame.copy(), cols, rows, square, quality_mode=mode
            )
            self.intrinsic_status.configure(
                text=(
                    f"已采集 {len(self.intrinsic.image_sets)} 张 · "
                    f"清晰度 {result.sharpness:.0f} · 棋盘覆盖 {result.board_coverage_percent:.1f}%"
                )
            )
        except Exception as exc:
            self._show_error(str(exc))

    def solve_intrinsic(self) -> None:
        try:
            cols, rows, square = self._numbers()
            mode = QUALITY_LABELS[self.intrinsic_quality_var.get()]
            _, path, _ = self._paths()
            payload = self.intrinsic.solve(path, cols, rows, square, quality_mode=mode)
            self.intrinsic_status.configure(
                text=f"内参已保存 · RMS {payload['reprojection_error_px']:.3f}px · {path}"
            )
        except Exception as exc:
            self._show_error(str(exc))

    def clear_intrinsic(self) -> None:
        self.intrinsic = IntrinsicCalibration()
        self.intrinsic_status.configure(text="已采集 0 张；标准模式建议 20～30 张")

    # ---------- hand-eye ----------
    def capture_handeye(self) -> None:
        if self.latest_pose is None:
            self._show_error("尚未收到 PoseStamped")
            return
        if self.latest_image is None:
            self._show_error("尚未收到 RGB Image")
            return
        try:
            cols, rows, square = self._numbers()
            _, intrinsics_path, _ = self._paths()
            if not intrinsics_path.exists():
                raise ValueError(
                    "缺少 camera_intrinsics.yaml；请先完成 Intrinsics 或导入 CameraInfo"
                )
            mode = QUALITY_LABELS[self.handeye_quality_var.get()]
            result = self.handeye.add(
                self.latest_image.frame.copy(),
                self.latest_pose.values,
                intrinsics_path,
                cols,
                rows,
                square,
                input_mode="ros_pose_stamped",
                pose_timestamp=self.latest_pose.timestamp,
                robot_pose_input=self.latest_pose.values,
                quality_mode=mode,
            )
            self.sample_status.configure(
                text=(
                    f"已采集 {len(self.handeye.samples)} 组 · 重投影 {result.reprojection_error_px:.3f}px · "
                    f"清晰度 {result.sharpness:.0f} · 方格 {result.pixels_per_square:.1f}px"
                )
            )
        except Exception as exc:
            self._show_error(str(exc))

    def save_samples(self) -> None:
        try:
            cols, rows, square = self._numbers()
            _, intrinsics_path, samples_path = self._paths()
            self.handeye.save(samples_path, intrinsics_path, cols, rows, square)
            self.sample_status.configure(
                text=f"已保存 {len(self.handeye.samples)} 组样本 → {samples_path}"
            )
        except Exception as exc:
            self._show_error(str(exc))

    def clear_samples(self) -> None:
        self.handeye = HandEyeCollection()
        self.sample_status.configure(text="已采集 0 组；建议 20～30 组")

    # ---------- algorithms ----------
    def _append_log(self, text: str) -> None:
        self.log.insert("end", text)
        self.log.see("end")

    def run_tool(self, name: str) -> None:
        if self.tool_running:
            return
        _, _, samples = self._paths()
        if not samples.exists():
            self._show_error("缺少 samples.yaml；请先保存手眼样本")
            return
        mode = SOLVE_MODES[self.solve_mode_var.get()]
        self.tool_running = True
        self.solve_status.configure(text=f"正在运行 {name}…")

        def worker() -> None:
            code = run_algorithm(
                name,
                samples,
                mode,
                lambda text: self.events.put(("log", text)),
            )
            self.events.put(("tool_done", (name, code)))

        threading.Thread(target=worker, daemon=True).start()

    def run_all(self) -> None:
        if self.tool_running:
            return
        _, _, samples = self._paths()
        if not samples.exists():
            self._show_error("缺少 samples.yaml；请先保存手眼样本")
            return
        mode = SOLVE_MODES[self.solve_mode_var.get()]
        self.tool_running = True
        self.solve_status.configure(text="正在运行完整流程…")

        def worker() -> None:
            for name in ("diagnose", "solve", "verify"):
                self.events.put(("log", f"\n===== {name.upper()} =====\n"))
                code = run_algorithm(
                    name,
                    samples,
                    mode,
                    lambda text: self.events.put(("log", text)),
                )
                if code != 0:
                    self.events.put(("tool_done", (name, code)))
                    return
            self.events.put(("tool_done", ("完整流程", 0)))

        threading.Thread(target=worker, daemon=True).start()

    # ---------- event/render ----------
    def _tick(self) -> None:
        latest_image_event: RosImage | None = None
        for _ in range(200):
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "image":
                latest_image_event = (
                    payload  # render only the newest frame in this tick
                )
            elif kind == "pose":
                self.latest_pose = payload
                x, y, z, qx, qy, qz, qw = payload.values
                self.pose_status.configure(
                    text=f"Pose: ● {payload.frame_id or '(no frame)'}",
                    text_color="#34C759",
                )
                self.pose_value_label.configure(
                    text=(
                        f"frame: {payload.frame_id or '(empty)'}\n"
                        f"xyz [m] : {x: .5f}  {y: .5f}  {z: .5f}\n"
                        f"xyzw    : {qx: .5f}  {qy: .5f}  {qz: .5f}  {qw: .5f}"
                    )
                )
            elif kind == "camera_info":
                self.latest_camera_info = payload
                self.info_status.configure(
                    text=f"CameraInfo: ● {payload.width}×{payload.height}",
                    text_color="#34C759",
                )
            elif kind == "error":
                self.connection_status.configure(
                    text=str(payload), text_color="#FF3B30"
                )
            elif kind == "log":
                self._append_log(str(payload))
            elif kind == "tool_done":
                name, code = payload
                self.tool_running = False
                self.solve_status.configure(
                    text=f"{name} {'完成' if code == 0 else '失败'} (code={code})",
                    text_color="#34C759" if code == 0 else "#FF3B30",
                )
        if latest_image_event is not None:
            self.latest_image = latest_image_event
            self.image_status.configure(
                text=(
                    f"Image: ● {latest_image_event.width}×{latest_image_event.height} "
                    f"{latest_image_event.encoding}"
                ),
                text_color="#34C759",
            )
            now = time.monotonic()
            if now - self._last_preview_render >= 0.08:
                self._render_preview(latest_image_event.frame)
                self._last_preview_render = now
        self.after(50, self._tick)

    def _render_preview(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        max_w, max_h = 780, 330
        scale = min(max_w / image.width, max_h / image.height, 1.0)
        size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        image = image.resize(size, Image.Resampling.LANCZOS)
        for label in self._preview_labels:
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=size)
            self._preview_images[label] = ctk_image
            label.configure(image=ctk_image, text="")

    def _toast(self, text: str) -> None:
        self.connection_status.configure(text=text, text_color="#34C759")

    def _show_error(self, text: str) -> None:
        self.connection_status.configure(text=text, text_color="#FF3B30")
        messagebox.showerror(APP_TITLE, text)

    def on_close(self) -> None:
        try:
            self.ros.stop()
        finally:
            self.destroy()


def main() -> None:
    app = HandEyeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
