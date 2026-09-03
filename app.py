from __future__ import annotations

import queue
import tkinter as tk
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter.font as tkfont

import cv2
import customtkinter as ctk
from PIL import Image

from algorithm_runner import run_algorithm
from calibration_engine import HandEyeCollection, IntrinsicCalibration
from camera_info_utils import save_camera_info_intrinsics
from config import AppConfig
from ros_interface import ContractTopics, RosCameraInfo, RosImage, RosInterface, RosPose

APP_TITLE = "HandEye Calibration"

UI_COLORS = {
    "bg": "#F5F5F7",
    "sidebar": "#F2F2F5",
    "card": "#FFFFFF",
    "card_alt": "#FAFAFC",
    "border": "#E5E5EA",
    "text": "#1D1D1F",
    "secondary": "#6E6E73",
    "accent": "#007AFF",
    "accent_hover": "#0A84FF",
    "success": "#34C759",
    "warning": "#FF9500",
    "danger": "#FF3B30",
    "muted": "#8E8E93",
    "preview": "#ECECF0",
}

QUALITY_LABELS = {
    "标准": "standard",
    "严格": "strict",
    "极简": "minimal",
}
QUALITY_DEFAULT = "标准"

SOLVE_MODES = {
    "鲁棒": "robust",
    "OpenCV": "minimal",
    "BA": "ba",
}
SOLVE_DEFAULT = "鲁棒"


class AnimatedSegmentedControl(tk.Frame):
    """Lightweight canvas based segmented control.

    Intentionally uses plain tkinter.Frame/Canvas instead of CTkFrame.
    CustomTkinter's internal _draw lifecycle conflicts with custom drawing.
    """
    def __init__(self, master, values, variable, command=None, **kwargs):
        super().__init__(master, bg="#EAF1FB", height=44, **kwargs)
        self.values = list(values)
        self.variable = variable
        self.command = command
        self.height = 44
        self.canvas = tk.Canvas(
            self,
            height=self.height,
            highlightthickness=0,
            bd=0,
            bg="#EAF1FB",
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._click)
        self._slider_x = 0
        self._target_x = 0
        self.item_w = 60
        self._draw()

    def _on_resize(self, event=None):
        self._draw()

    def _draw(self):
        self.canvas.delete("all")
        w = max(self.canvas.winfo_width(), 180)
        h = self.height
        self.item_w = w / max(len(self.values), 1)

        # background
        self.canvas.create_round_rect = None
        self.canvas.create_rectangle(
            0, 0, w, h,
            fill="#EAF1FB",
            outline="",
        )

        idx = self.values.index(self.variable.get()) if self.variable.get() in self.values else 0
        self._slider_x = idx * self.item_w
        self._target_x = self._slider_x
        self._paint()

    def _paint(self):
        self.canvas.delete("slider")
        self.canvas.delete("text")

        x = self._slider_x
        self.canvas.create_rectangle(
            x + 3, 4,
            x + self.item_w - 3, self.height - 4,
            fill="#007AFF",
            outline="",
            tags="slider",
        )

        selected = self.variable.get()
        for i, value in enumerate(self.values):
            self.canvas.create_text(
                (i + 0.5) * self.item_w,
                self.height / 2,
                text=value,
                fill="#FFFFFF" if value == selected else "#007AFF",
                font=("TkDefaultFont", 12),
                tags="text",
            )

    def _click(self, event):
        if not self.values:
            return
        idx = min(len(self.values)-1, max(0, int(event.x / self.item_w)))
        value = self.values[idx]
        self.variable.set(value)
        self._animate(idx * self.item_w)
        if self.command:
            self.command(value)

    def _animate(self, target):
        self._target_x = target

        def step():
            diff = self._target_x - self._slider_x
            if abs(diff) < 1:
                self._slider_x = self._target_x
                self._paint()
                return
            self._slider_x += diff * 0.22
            self._paint()
            self.after(12, step)

        step()

class HandEyeApp(ctk.CTk):
    def __init__(self) -> None:
        self.config_data = AppConfig.load()
        ctk.set_appearance_mode(self.config_data.appearance_mode)
        ctk.set_default_color_theme("blue")
        ctk.set_widget_scaling(1.35)
        ctk.set_window_scaling(1.0)
        super().__init__()
        self._init_fonts()

        self.title(APP_TITLE)
        self.geometry("1480x940")
        self.minsize(1260, 820)
        self.configure(fg_color=UI_COLORS["bg"])
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

    def _init_fonts(self) -> None:
        families = set(tkfont.families())
        preferred = [
            "SF Pro Text",
            "SF Pro Display",
            "PingFang SC",
            "Noto Sans CJK SC",
            "Noto Sans SC",
            "Microsoft YaHei UI",
            "Segoe UI",
            "Helvetica",
            "Arial",
        ]
        family = next((name for name in preferred if name in families), "TkDefaultFont")
        mono = next((name for name in ["JetBrains Mono", "Cascadia Mono", "Consolas", "Menlo", "Monaco", "DejaVu Sans Mono"] if name in families), "TkFixedFont")
        self.font_family = family
        self.font_sm = ctk.CTkFont(family=family, size=13)
        self.font_md = ctk.CTkFont(family=family, size=15)
        self.font_md_bold = ctk.CTkFont(family=family, size=15, weight="bold")
        self.font_lg = ctk.CTkFont(family=family, size=18, weight="bold")
        self.font_xl = ctk.CTkFont(family=family, size=30, weight="bold")
        self.font_header = ctk.CTkFont(family=family, size=28, weight="bold")
        self.font_code = ctk.CTkFont(family=mono, size=14)

    # ---------- shell ----------
    def _build_shell(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color=UI_COLORS["sidebar"])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(
            sidebar,
            corner_radius=18,
            fg_color="#FFF4E5",
            border_width=1,
            border_color="#F1D1A3",
        )
        brand.pack(fill="x", padx=16, pady=(18, 22))

        ctk.CTkLabel(
            brand,
            text="HandEye",
            font=self.font_xl,
            text_color=UI_COLORS["text"],
        ).pack(anchor="w", padx=18, pady=(16, 0))

        ctk.CTkLabel(
            brand,
            text="ROS2 Calibration Workstation",
            font=self.font_sm,
            text_color=UI_COLORS["secondary"],
        ).pack(anchor="w", padx=18, pady=(6, 16))

        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for key, text in (
            ("connect", "01  Connect"),
            ("intrinsics", "02  Intrinsics"),
            ("handeye", "03  Hand-Eye"),
            ("solve", "04  Solve"),
        ):
            button = ctk.CTkButton(
                sidebar,
                text=text,
                anchor="w",
                height=46,
                corner_radius=14,
                fg_color="transparent",
                hover_color="#E9F2FF",
                text_color=UI_COLORS["text"],
                font=self.font_md_bold,
                border_width=0,
                command=lambda page=key: self._show_page(page),
            )
            button.pack(fill="x", padx=16, pady=4)
            self.nav_buttons[key] = button

        ctk.CTkFrame(sidebar, height=1, fg_color=UI_COLORS["border"]).pack(fill="x", padx=18, pady=(20, 14))

        note = ctk.CTkFrame(sidebar, fg_color=UI_COLORS["card"], corner_radius=16, border_width=1, border_color=UI_COLORS["border"])
        note.pack(fill="x", padx=18, pady=(0, 12))
        ctk.CTkLabel(note, text="接入约定", font=self.font_md_bold, text_color=UI_COLORS["text"]).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(
            note,
            text="Pose 使用 geometry_msgs/msg/PoseStamped\nImage 使用 sensor_msgs/msg/Image\nCameraInfo 可选导入",
            font=self.font_sm,
            justify="left",
            text_color=UI_COLORS["secondary"],
        ).pack(anchor="w", padx=14, pady=(0, 12))

        self.sidebar_status = self._status_pill(sidebar, "ROS2 未启动", "warning")
        self.sidebar_status.pack(side="bottom", anchor="w", padx=24, pady=24)

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=UI_COLORS["bg"])
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.content, corner_radius=20, fg_color=UI_COLORS["card"], border_width=1, border_color=UI_COLORS["border"])
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 10))
        header.grid_columnconfigure(0, weight=1)
        self.page_title = ctk.CTkLabel(header, text="", font=self.font_header, text_color=UI_COLORS["text"])
        self.page_title.grid(row=0, column=0, sticky="w", padx=20, pady=16)

        pill_row = ctk.CTkFrame(header, fg_color="transparent")
        pill_row.grid(row=0, column=1, sticky="e", padx=(0, 14), pady=12)
        self.ros_header_pill = self._status_pill(pill_row, "ROS2", "warning")
        self.ros_header_pill.pack(side="left", padx=4)
        self.pose_header_pill = self._status_pill(pill_row, "Pose", "neutral")
        self.pose_header_pill.pack(side="left", padx=4)
        self.image_header_pill = self._status_pill(pill_row, "Image", "neutral")
        self.image_header_pill.pack(side="left", padx=4)
        self.info_header_pill = self._status_pill(pill_row, "Info", "neutral")
        self.info_header_pill.pack(side="left", padx=4)
        self._ghost_button(header, "保存设置", self.save_config, width=112).grid(row=0, column=2, sticky="e", padx=(0, 18), pady=12)

        self.page_host = ctk.CTkFrame(self.content, fg_color="transparent")
        self.page_host.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 24))
        self.page_host.grid_columnconfigure(0, weight=1)
        self.page_host.grid_rowconfigure(0, weight=1)

        self.bind_all("<Button-4>", self._mousewheel_linux)
        self.bind_all("<Button-5>", self._mousewheel_linux)
        self.bind_all("<MouseWheel>", self._mousewheel_windows)

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
            scrollbar_button_color="#D5D5DA",
            scrollbar_button_hover_color="#C5C5CB",
        )
        page.grid_columnconfigure(0, weight=1)
        return page

    def _card(self, parent, title: str, subtitle: str = "") -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            corner_radius=18,
            fg_color=UI_COLORS["card"],
            border_width=1,
            border_color=UI_COLORS["border"],
        )
        card.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 10))
        ctk.CTkLabel(head, text=title, font=self.font_lg, text_color=UI_COLORS["text"]).pack(anchor="w")
        if subtitle:
            ctk.CTkLabel(
                head,
                text=subtitle,
                font=self.font_sm,
                text_color=UI_COLORS["secondary"],
                wraplength=980,
                justify="left",
            ).pack(anchor="w", pady=(5, 0))
        return card

    def _status_pill(self, parent, text: str, tone: str) -> ctk.CTkLabel:
        styles = {
            "success": ("#EAF8EF", "#1E8E4E", "#B8E0C8"),
            "warning": ("#FFF4E5", "#B86B00", "#F1D1A3"),
            "danger": ("#FFE9E7", "#C2382A", "#F4C0BA"),
            "neutral": ("#F2F2F7", "#6E6E73", "#E0E0E6"),
        }
        bg, fg, border = styles[tone]
        return ctk.CTkLabel(
            parent,
            text=f"  ● {text}  ",
            font=self.font_sm,
            text_color=fg,
            fg_color=bg,
            corner_radius=999,
            border_width=1,
            border_color=border,
            height=34,
        )

    def _button(self, parent, text: str, command, kind: str = "primary", width: int = 120):
        if kind == "primary":
            return ctk.CTkButton(
                parent,
                text=text,
                command=command,
                height=42,
                width=width,
                corner_radius=12,
                font=self.font_md_bold,
                fg_color=UI_COLORS["accent"],
                hover_color=UI_COLORS["accent_hover"],
                text_color="#FFFFFF",
            )
        if kind == "secondary":
            return ctk.CTkButton(
                parent,
                text=text,
                command=command,
                height=42,
                width=width,
                corner_radius=12,
                font=self.font_md_bold,
                fg_color="#ECF4FF",
                hover_color="#DCEBFF",
                text_color=UI_COLORS["accent"],
                border_width=1,
                border_color="#CFE2FF",
            )
        if kind == "danger":
            return ctk.CTkButton(
                parent,
                text=text,
                command=command,
                height=42,
                width=width,
                corner_radius=12,
                font=self.font_md_bold,
                fg_color=UI_COLORS["danger"],
                hover_color="#E03528",
                text_color="#FFFFFF",
            )
        return self._ghost_button(parent, text, command, width)

    def _ghost_button(self, parent, text: str, command, width: int = 120):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            height=42,
            width=width,
            corner_radius=12,
            font=self.font_md_bold,
            fg_color=UI_COLORS["card"],
            hover_color="#F2F7FF",
            text_color=UI_COLORS["text"],
            border_width=1,
            border_color=UI_COLORS["border"],
        )

    def _entry(self, parent, textvariable=None, width: int = 300) -> ctk.CTkEntry:
        return ctk.CTkEntry(
            parent,
            textvariable=textvariable,
            height=46,
            width=width,
            corner_radius=14,
            border_width=1,
            border_color=UI_COLORS["border"],
            fg_color=UI_COLORS["card_alt"],
            text_color=UI_COLORS["text"],
            font=self.font_md,
        )

    def _combo(self, parent, variable, values) -> ctk.CTkComboBox:
        return ctk.CTkComboBox(
            parent,
            variable=variable,
            values=list(values) if values else [""],
            state="normal",
            height=46,
            corner_radius=14,
            border_width=1,
            border_color=UI_COLORS["border"],
            button_color="#D9DDE6",
            button_hover_color="#C9D4E5",
            fg_color=UI_COLORS["card_alt"],
            dropdown_fg_color=UI_COLORS["card"],
            dropdown_hover_color="#EEF5FF",
            dropdown_text_color=UI_COLORS["text"],
            font=self.font_md,
            dropdown_font=self.font_md,
        )

    def _segmented(self, parent, variable, values) -> AnimatedSegmentedControl:
        return AnimatedSegmentedControl(
            parent,
            values,
            variable,
        )

    def _form_topic_row(self, parent, row: int, label: str, variable, type_name: str):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=22, pady=(0, 10))
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(frame, text=label, font=self.font_md_bold, text_color=UI_COLORS["text"], anchor="w").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(frame, text=type_name, font=self.font_sm, text_color=UI_COLORS["secondary"], anchor="w").grid(row=1, column=0, sticky="w", pady=(2, 8))
        combo = self._combo(frame, variable, [variable.get()] if variable.get() else [""])
        combo.grid(row=2, column=0, sticky="ew")
        return combo

    def _build_preview(self, parent, row: int) -> ctk.CTkLabel:
        box = self._card(parent, "RGB Preview", "实时显示当前选择的 sensor_msgs/msg/Image")
        box.grid(row=row, column=0, sticky="ew", pady=(12, 0))
        label = ctk.CTkLabel(
            box,
            text="等待 ROS 图像…",
            height=360,
            corner_radius=14,
            fg_color=UI_COLORS["preview"],
            text_color=UI_COLORS["secondary"],
            font=self.font_md,
        )
        label.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 22))
        self._preview_labels.append(label)
        return label

    # ---------- Connect ----------
    def _build_connect_page(self):
        page = self._new_page()

        project = self._card(page, "Project", "输出文件统一保存在该目录")
        project.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        row = ctk.CTkFrame(project, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 22))
        row.grid_columnconfigure(0, weight=1)
        self.output_var = ctk.StringVar(value=self.config_data.output_dir)
        self._entry(row, textvariable=self.output_var).grid(row=0, column=0, sticky="ew")
        self._ghost_button(row, "浏览", self.choose_output, width=86).grid(row=0, column=1, padx=(10, 0))

        ros_card = self._card(
            page,
            "ROS2 Sources",
            "Topic 名称不固定；刷新后从当前 ROS graph 选择，也可以直接输入自己的话题",
        )
        ros_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ros_card.grid_columnconfigure(0, weight=1)

        self.pose_topic_var = ctk.StringVar(value=self.config_data.pose_topic)
        self.image_topic_var = ctk.StringVar(value=self.config_data.image_topic)
        self.camera_info_topic_var = ctk.StringVar(value=self.config_data.camera_info_topic)
        self.topic_boxes = [
            self._form_topic_row(ros_card, 1, "Robot Pose", self.pose_topic_var, "geometry_msgs/msg/PoseStamped"),
            self._form_topic_row(ros_card, 2, "RGB Image", self.image_topic_var, "sensor_msgs/msg/Image"),
            self._form_topic_row(ros_card, 3, "Camera Info（可选）", self.camera_info_topic_var, "sensor_msgs/msg/CameraInfo"),
        ]

        actions = ctk.CTkFrame(ros_card, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=22, pady=(6, 8))
        self._button(actions, "启动 / 刷新 ROS2", self.start_or_refresh_ros, "secondary", width=154).pack(side="left")
        self._button(actions, "应用订阅", self.apply_ros_topics, "primary", width=118).pack(side="left", padx=10)
        self.connection_status = ctk.CTkLabel(actions, text="未连接", font=self.font_md, text_color=UI_COLORS["warning"])
        self.connection_status.pack(side="left", padx=12)

        status_row = ctk.CTkFrame(ros_card, fg_color="transparent")
        status_row.grid(row=5, column=0, sticky="ew", padx=22, pady=(0, 18))
        self.pose_status = self._status_pill(status_row, "Pose 等待", "neutral")
        self.pose_status.pack(side="left", padx=(0, 8))
        self.image_status = self._status_pill(status_row, "Image 等待", "neutral")
        self.image_status.pack(side="left", padx=(0, 8))
        self.info_status = self._status_pill(status_row, "CameraInfo 可选", "neutral")
        self.info_status.pack(side="left")

        guide = self._card(page, "接入约定", "机械臂控制、拖拽和正运动学由用户自己的机器人程序负责")
        guide.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        guide_text = (
            "机械臂只需持续发布 geometry_msgs/msg/PoseStamped，语义为 ^base T_gripper；position 单位 m，orientation 为 xyzw 四元数。\n"
            "相机只需发布 sensor_msgs/msg/Image；支持 mono8 / bgr8 / rgb8 / bgra8 / rgba8。\n"
            "如果已有可靠内参，可额外发布 sensor_msgs/msg/CameraInfo，并在 Intrinsics 页直接导入。"
        )
        ctk.CTkLabel(guide, text=guide_text, font=self.font_md, justify="left", anchor="w", wraplength=980, text_color=UI_COLORS["secondary"]).grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 22))

        self._build_preview(page, 3)
        return page

    # ---------- Intrinsics ----------
    def _build_intrinsics_page(self):
        page = self._new_page()
        board = self._card(page, "Calibration Board", "角点列/行填写内角点数量，方格边长单位 mm")
        board.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        grid = ctk.CTkFrame(board, fg_color="transparent")
        grid.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 22))

        self.cols_var = ctk.StringVar(value=str(self.config_data.chessboard_cols))
        self.rows_var = ctk.StringVar(value=str(self.config_data.chessboard_rows))
        self.square_var = ctk.StringVar(value=str(self.config_data.square_size_mm))
        for col, (label, variable) in enumerate((("角点列数", self.cols_var), ("角点行数", self.rows_var), ("方格边长 / mm", self.square_var))):
            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=0, column=col, sticky="w", padx=(0, 20))
            ctk.CTkLabel(cell, text=label, font=self.font_md_bold, text_color=UI_COLORS["text"]).pack(anchor="w")
            self._entry(cell, textvariable=variable, width=170).pack(anchor="w", pady=(6, 0))

        capture = self._card(page, "Camera Intrinsics", "已有 CameraInfo 可直接导入；否则使用当前 ROS RGB 图像采集棋盘并求解")
        capture.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        quality_row = ctk.CTkFrame(capture, fg_color="transparent")
        quality_row.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 10))
        ctk.CTkLabel(quality_row, text="采样质量", font=self.font_md_bold, text_color=UI_COLORS["text"]).pack(side="left")
        self.intrinsic_quality_var = ctk.StringVar(value=QUALITY_DEFAULT)
        self._segmented(quality_row, self.intrinsic_quality_var, QUALITY_LABELS.keys()).pack(side="left", padx=(12, 0))

        line = ctk.CTkFrame(capture, fg_color="transparent")
        line.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 12))
        self._button(line, "从 CameraInfo 导入", self.import_camera_info, "secondary", width=158).pack(side="left")
        self._button(line, "采集当前图像", self.capture_intrinsic, "primary", width=144).pack(side="left", padx=10)
        self._ghost_button(line, "计算并保存内参", self.solve_intrinsic, width=154).pack(side="left")
        self._ghost_button(line, "清空", self.clear_intrinsic, width=82).pack(side="right")

        self.intrinsic_status = ctk.CTkLabel(capture, text="已采集 0 张；标准模式建议 20～30 张", anchor="w", font=self.font_md, text_color=UI_COLORS["secondary"])
        self.intrinsic_status.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 20))
        self._build_preview(page, 2)
        return page

    # ---------- HandEye ----------
    def _build_handeye_page(self):
        page = self._new_page()
        pose_card = self._card(page, "Current Robot Pose", "读取当前选择的 PoseStamped；APP 不计算机械臂 FK")
        pose_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.pose_value_label = ctk.CTkLabel(
            pose_card,
            text="等待 PoseStamped…",
            font=self.font_code,
            justify="left",
            anchor="w",
            text_color=UI_COLORS["text"],
            fg_color=UI_COLORS["card_alt"],
            corner_radius=14,
            height=96,
        )
        self.pose_value_label.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 22))

        sample = self._card(page, "Hand-Eye Sampling", "固定棋盘，手动拖拽机械臂到不同位置与姿态；停稳后记录当前 Image + Pose")
        sample.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        quality_row = ctk.CTkFrame(sample, fg_color="transparent")
        quality_row.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 10))
        ctk.CTkLabel(quality_row, text="采样质量", font=self.font_md_bold, text_color=UI_COLORS["text"]).pack(side="left")
        self.handeye_quality_var = ctk.StringVar(value=QUALITY_DEFAULT)
        self._segmented(quality_row, self.handeye_quality_var, QUALITY_LABELS.keys()).pack(side="left", padx=(12, 0))

        actions = ctk.CTkFrame(sample, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 12))
        self._button(actions, "记录当前样本", self.capture_handeye, "primary", width=148).pack(side="left")
        self._button(actions, "保存 samples.yaml", self.save_samples, "secondary", width=166).pack(side="left", padx=10)
        self._ghost_button(actions, "清空", self.clear_samples, width=82).pack(side="right")

        self.sample_status = ctk.CTkLabel(sample, text="已采集 0 组；建议 20～30 组", anchor="w", font=self.font_md, text_color=UI_COLORS["secondary"])
        self.sample_status.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 20))
        self._build_preview(page, 2)
        return page

    # ---------- Solve ----------
    def _build_solve_page(self):
        page = self._new_page()
        solve = self._card(page, "Diagnose · Solve · Verify", "直接调用仓库内已经验证的 algorithms，不改变求解数学实现")
        solve.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        mode_row = ctk.CTkFrame(solve, fg_color="transparent")
        mode_row.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 10))
        ctk.CTkLabel(mode_row, text="求解模式", font=self.font_md_bold, text_color=UI_COLORS["text"]).pack(side="left")
        self.solve_mode_var = ctk.StringVar(value=SOLVE_DEFAULT)
        self._segmented(mode_row, self.solve_mode_var, SOLVE_MODES.keys()).pack(side="left", padx=(12, 0))

        controls = ctk.CTkFrame(solve, fg_color="transparent")
        controls.grid(row=2, column=0, sticky="ew", padx=22, pady=(0, 12))
        self._ghost_button(controls, "诊断", lambda: self.run_tool("diagnose"), width=88).pack(side="left")
        self._ghost_button(controls, "求解", lambda: self.run_tool("solve"), width=88).pack(side="left", padx=(10, 0))
        self._ghost_button(controls, "验证", lambda: self.run_tool("verify"), width=88).pack(side="left", padx=(10, 0))
        self._button(controls, "完整流程", self.run_all, "primary", width=120).pack(side="left", padx=(10, 0))

        self.solve_status = ctk.CTkLabel(solve, text="等待 samples.yaml", anchor="w", font=self.font_md, text_color=UI_COLORS["secondary"])
        self.solve_status.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 12))
        self.log = ctk.CTkTextbox(
            solve,
            height=480,
            corner_radius=14,
            border_width=1,
            border_color=UI_COLORS["border"],
            fg_color=UI_COLORS["card_alt"],
            text_color=UI_COLORS["text"],
            font=self.font_code,
        )
        self.log.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 22))
        return page


    def _mousewheel_linux(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget:
            if hasattr(widget, "_parent_canvas"):
                widget._parent_canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
                return
            widget = getattr(widget, "master", None)

    def _mousewheel_windows(self, event):
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget:
            if hasattr(widget, "_parent_canvas"):
                widget._parent_canvas.yview_scroll(int(-event.delta / 120), "units")
                return
            widget = getattr(widget, "master", None)

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
            if key == name:
                button.configure(fg_color="#EAF4FF", hover_color="#EAF4FF", text_color=UI_COLORS["accent"])
            else:
                button.configure(fg_color="transparent", hover_color="#E9F2FF", text_color=UI_COLORS["text"])

    def choose_output(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.output_var.get() or str(Path.home()))
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
                self._set_ros_running(True)
                self.after(250, self._refresh_topics)
            else:
                self._refresh_topics()
        except Exception as exc:
            self._show_error(str(exc))

    def _set_ros_running(self, running: bool) -> None:
        if running:
            self.sidebar_status.configure(text="  ● ROS2 已启动  ", fg_color="#EAF8EF", text_color="#1E8E4E", border_color="#B8E0C8")
            self.ros_header_pill.configure(text="  ● ROS2 已启动  ", fg_color="#EAF8EF", text_color="#1E8E4E", border_color="#B8E0C8")
            self.connection_status.configure(text="ROS2 已启动", text_color=UI_COLORS["success"])
        else:
            self.sidebar_status.configure(text="  ● ROS2 未启动  ", fg_color="#FFF4E5", text_color="#B86B00", border_color="#F1D1A3")
            self.ros_header_pill.configure(text="  ● ROS2  ", fg_color="#FFF4E5", text_color="#B86B00", border_color="#F1D1A3")

    def _refresh_topics(self) -> None:
        try:
            topics = self.ros.discover_topics()
            self._set_topic_values(topics)
            self.connection_status.configure(text="话题列表已刷新", text_color=UI_COLORS["success"])
        except Exception as exc:
            self._show_error(str(exc))

    def _set_topic_values(self, topics: ContractTopics) -> None:
        values = (topics.pose_topics, topics.image_topics, ("",) + topics.camera_info_topics)
        variables = (self.pose_topic_var, self.image_topic_var, self.camera_info_topic_var)
        for combo, variable, options in zip(self.topic_boxes, variables, values, strict=True):
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
                self._set_ros_running(True)
            self.ros.subscribe(self.pose_topic_var.get(), self.image_topic_var.get(), self.camera_info_topic_var.get())
            self.connection_status.configure(text="已订阅", text_color=UI_COLORS["success"])
            self.save_config()
        except Exception as exc:
            self._show_error(str(exc))

    # ---------- intrinsics ----------
    def import_camera_info(self) -> None:
        if self.latest_camera_info is None:
            self._show_error("尚未收到 CameraInfo；请先在 Connect 页选择并应用 CameraInfo topic")
            return
        try:
            _, intrinsics_path, _ = self._paths()
            payload = save_camera_info_intrinsics(intrinsics_path, self.latest_camera_info)
            self.intrinsic_status.configure(text=f"已从 CameraInfo 保存内参：{payload['image_width']}×{payload['image_height']} → {intrinsics_path}")
        except Exception as exc:
            self._show_error(str(exc))

    def capture_intrinsic(self) -> None:
        if self.latest_image is None:
            self._show_error("尚未收到 RGB 图像")
            return
        try:
            cols, rows, square = self._numbers()
            mode = QUALITY_LABELS[self.intrinsic_quality_var.get()]
            result = self.intrinsic.add(self.latest_image.frame.copy(), cols, rows, square, quality_mode=mode)
            self.intrinsic_status.configure(text=f"已采集 {len(self.intrinsic.image_sets)} 张 · 清晰度 {result.sharpness:.0f} · 棋盘覆盖 {result.board_coverage_percent:.1f}%")
        except Exception as exc:
            self._show_error(str(exc))

    def solve_intrinsic(self) -> None:
        try:
            cols, rows, square = self._numbers()
            mode = QUALITY_LABELS[self.intrinsic_quality_var.get()]
            _, path, _ = self._paths()
            payload = self.intrinsic.solve(path, cols, rows, square, quality_mode=mode)
            self.intrinsic_status.configure(text=f"内参已保存 · RMS {payload['reprojection_error_px']:.3f}px · {path}")
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
                raise ValueError("缺少 camera_intrinsics.yaml；请先完成 Intrinsics 或导入 CameraInfo")
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
            self.sample_status.configure(text=f"已采集 {len(self.handeye.samples)} 组 · 重投影 {result.reprojection_error_px:.3f}px · 清晰度 {result.sharpness:.0f} · 方格 {result.pixels_per_square:.1f}px")
        except Exception as exc:
            self._show_error(str(exc))

    def save_samples(self) -> None:
        try:
            cols, rows, square = self._numbers()
            _, intrinsics_path, samples_path = self._paths()
            self.handeye.save(samples_path, intrinsics_path, cols, rows, square)
            self.sample_status.configure(text=f"已保存 {len(self.handeye.samples)} 组样本 → {samples_path}")
        except Exception as exc:
            self._show_error(str(exc))

    def clear_samples(self) -> None:
        self.handeye = HandEyeCollection()
        self.sample_status.configure(text="已采集 0 组；建议 20～30 组")

    # ---------- algorithms ----------
    def _append_log(self, text: str) -> None:
        self.log.insert("end", text)
        self.log.see("end")

    def _set_busy(self, busy: bool) -> None:
        self.tool_running = busy

    def run_tool(self, name: str) -> None:
        if self.tool_running:
            return
        _, _, samples = self._paths()
        if not samples.exists():
            self._show_error("缺少 samples.yaml；请先保存手眼样本")
            return
        mode = SOLVE_MODES[self.solve_mode_var.get()]
        self._set_busy(True)
        self.solve_status.configure(text=f"正在运行 {name}…", text_color=UI_COLORS["accent"])

        def worker() -> None:
            code = run_algorithm(name, samples, mode, lambda text: self.events.put(("log", text)))
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
        self._set_busy(True)
        self.solve_status.configure(text="正在运行完整流程…", text_color=UI_COLORS["accent"])

        def worker() -> None:
            for name in ("diagnose", "solve", "verify"):
                self.events.put(("log", f"\n===== {name.upper()} =====\n"))
                code = run_algorithm(name, samples, mode, lambda text: self.events.put(("log", text)))
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
                latest_image_event = payload
            elif kind == "pose":
                self.latest_pose = payload
                x, y, z, qx, qy, qz, qw = payload.values
                self.pose_status.configure(text=f"  ● Pose {payload.frame_id or '(no frame)'}  ", fg_color="#EAF8EF", text_color="#1E8E4E", border_color="#B8E0C8")
                self.pose_header_pill.configure(text="  ● Pose 已连接  ", fg_color="#EAF8EF", text_color="#1E8E4E", border_color="#B8E0C8")
                self.pose_value_label.configure(text=(f"frame: {payload.frame_id or '(empty)'}\nxyz [m] : {x: .5f}  {y: .5f}  {z: .5f}\nxyzw    : {qx: .5f}  {qy: .5f}  {qz: .5f}  {qw: .5f}"))
            elif kind == "camera_info":
                self.latest_camera_info = payload
                self.info_status.configure(text=f"  ● CameraInfo {payload.width}×{payload.height}  ", fg_color="#EAF8EF", text_color="#1E8E4E", border_color="#B8E0C8")
                self.info_header_pill.configure(text="  ● Info 已连接  ", fg_color="#EAF8EF", text_color="#1E8E4E", border_color="#B8E0C8")
            elif kind == "error":
                self.connection_status.configure(text=str(payload), text_color=UI_COLORS["danger"])
            elif kind == "log":
                self._append_log(str(payload))
            elif kind == "tool_done":
                name, code = payload
                self._set_busy(False)
                self.solve_status.configure(text=f"{name} {'完成' if code == 0 else '失败'} (code={code})", text_color=UI_COLORS["success"] if code == 0 else UI_COLORS["danger"])

        if latest_image_event is not None:
            self.latest_image = latest_image_event
            self.image_status.configure(text=f"  ● Image {latest_image_event.width}×{latest_image_event.height} {latest_image_event.encoding}  ", fg_color="#EAF8EF", text_color="#1E8E4E", border_color="#B8E0C8")
            self.image_header_pill.configure(text="  ● Image 已连接  ", fg_color="#EAF8EF", text_color="#1E8E4E", border_color="#B8E0C8")
            now = time.monotonic()
            if now - self._last_preview_render >= 0.08:
                self._render_preview(latest_image_event.frame)
                self._last_preview_render = now
        self.after(50, self._tick)

    def _render_preview(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        max_w, max_h = 900, 360
        scale = min(max_w / image.width, max_h / image.height, 1.0)
        size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        image = image.resize(size, Image.Resampling.LANCZOS)
        for label in self._preview_labels:
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=size)
            self._preview_images[label] = ctk_image
            label.configure(image=ctk_image, text="")

    def _toast(self, text: str) -> None:
        self.connection_status.configure(text=text, text_color=UI_COLORS["success"])

    def _show_error(self, text: str) -> None:
        self.connection_status.configure(text=text, text_color=UI_COLORS["danger"])
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
