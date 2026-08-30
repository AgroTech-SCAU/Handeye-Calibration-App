from __future__ import annotations

import queue
import math
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import cv2
from PIL import Image, ImageTk

from algorithm_runner import joints_to_pose, run_algorithm
from calibration_engine import (
    CameraSession,
    HandEyeCollection,
    IntrinsicCalibration,
    detect_chessboard,
    rpy_to_quaternion,
)
from config import APP_DIR, PORTABLE_DIR, AppConfig
from ros_interface import RosInterface, RosJoints, RosPose


CONFIG_PATH = PORTABLE_DIR / "app_config.json"


class HandEyeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("手眼标定工作站")
        self.geometry("1240x820")
        self.minsize(1040, 720)
        self.configure(background="#EEF4F6")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.config_data = AppConfig.load(CONFIG_PATH)
        self.camera = CameraSession()
        self.intrinsic = IntrinsicCalibration()
        self.handeye = HandEyeCollection()
        self.current_frame = None
        self.preview_photo = None
        self.latest_pose: RosPose | None = None
        self.latest_robot_input: tuple[float, ...] | None = None
        self.latest_input_mode = "ros"
        self.robot_data_announced = False
        self.frame_counter = 0
        self.last_detection = (False, None)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.tool_running = False
        self.ros = RosInterface(
            self._ros_pose_callback,
            self._ros_joints_callback,
            self._ros_capture_callback,
            self._ros_error_callback,
        )

        self._setup_style()
        self._build_ui()
        self.after(30, self._tick)

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        font = ("Microsoft YaHei UI", 9)
        style.configure(".", font=font, background="#FFFFFF", foreground="#18323A")
        style.configure("TFrame", background="#FFFFFF")
        style.configure("Workspace.TFrame", background="#EFF3F5")
        style.configure("TLabel", background="#FFFFFF", foreground="#18323A")
        style.configure("TLabelframe", background="#FFFFFF")
        style.configure("TLabelframe.Label", background="#FFFFFF", foreground="#31505A")
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 20, "bold"), foreground="#102E38")
        style.configure(
            "Step.TLabel",
            font=("Microsoft YaHei UI", 15, "bold"),
            foreground="#102E38",
            background="#F3F7F8",
        )
        style.configure(
            "Eyebrow.TLabel",
            font=("Segoe UI", 8, "bold"),
            foreground="#168578",
            background="#F3F7F8",
        )
        style.configure(
            "TabMuted.TLabel",
            background="#F3F7F8",
            foreground="#60777E",
        )
        style.configure("TabBody.TFrame", background="#F3F7F8")
        style.configure(
            "Section.TFrame",
            background="#FFFFFF",
            bordercolor="#DDE7E9",
            lightcolor="#DDE7E9",
            darkcolor="#DDE7E9",
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Card.TLabelframe",
            background="#FFFFFF",
            bordercolor="#DCE5E8",
            lightcolor="#DCE5E8",
            darkcolor="#DCE5E8",
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Card.TLabelframe.Label",
            background="#FFFFFF",
            foreground="#244751",
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.configure("Card.TFrame", background="#FFFFFF")
        style.configure("Card.TLabel", background="#FFFFFF", foreground="#18323A")
        style.configure(
            "Accent.TButton",
            font=("Microsoft YaHei UI", 10, "bold"),
            foreground="#FFFFFF",
            background="#168578",
            bordercolor="#168578",
            padding=(14, 8),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#106F65"), ("pressed", "#0C5C54")],
            bordercolor=[("active", "#106F65")],
        )
        style.configure(
            "Capture.TButton",
            font=("Microsoft YaHei UI", 12, "bold"),
            foreground="#FFFFFF",
            background="#F06435",
            bordercolor="#F06435",
            padding=(18, 12),
        )
        style.map(
            "Capture.TButton",
            background=[("active", "#DB5127"), ("pressed", "#BF411D")],
            bordercolor=[("active", "#DB5127")],
        )
        style.configure(
            "Header.TButton",
            foreground="#FFFFFF",
            background="#1D4652",
            bordercolor="#4D6D76",
            font=("Microsoft YaHei UI", 9, "bold"),
            padding=(13, 7),
        )
        style.map("Header.TButton", background=[("active", "#285966")])
        style.configure(
            "TButton",
            padding=(10, 7),
            foreground="#294650",
            background="#F5F8F9",
            bordercolor="#CFDCE0",
            relief="flat",
        )
        style.map("TButton", background=[("active", "#E9F0F2"), ("pressed", "#DDE8EB")])
        style.configure("TEntry", fieldbackground="#FAFCFC", bordercolor="#CCDADD", padding=6)
        style.configure("TCombobox", fieldbackground="#FAFCFC", bordercolor="#CCDADD", padding=5)
        style.configure("TSpinbox", fieldbackground="#FAFCFC", bordercolor="#CCDADD", padding=5)
        style.configure("TNotebook", background="#EFF3F5", borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure(
            "TNotebook.Tab",
            background="#E4EBED",
            foreground="#587078",
            font=("Microsoft YaHei UI", 10, "bold"),
            padding=(18, 10),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#FFFFFF")],
            foreground=[("selected", "#14786E")],
        )
        style.configure(
            "Vertical.TScrollbar",
            background="#CBD8DC",
            troughcolor="#F4F7F8",
            bordercolor="#F4F7F8",
            arrowcolor="#61777E",
            width=12,
        )

    def _build_ui(self) -> None:
        self.configure(background="#EFF3F5")
        header = tk.Frame(self, background="#102E38", height=104)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(header, background="#24A293", height=3).pack(side="bottom", fill="x")

        brand = tk.Frame(header, background="#102E38")
        brand.pack(side="left", fill="y", padx=(22, 0))
        mascot_path = APP_DIR / "assets" / "turtle_mascot_v2.png"
        if not mascot_path.exists():
            mascot_path = APP_DIR / "assets" / "turtle_mascot.png"
        self.mascot_photo = None
        if mascot_path.exists():
            mascot = Image.open(mascot_path).convert("RGBA")
            alpha_box = mascot.getchannel("A").getbbox()
            if alpha_box:
                mascot = mascot.crop(alpha_box)
            mascot.thumbnail((70, 70), Image.Resampling.LANCZOS)
            self.mascot_photo = ImageTk.PhotoImage(mascot)
            mascot_panel = tk.Frame(
                brand,
                width=78, height=78,
                background="#183E48",
                highlightbackground="#315965",
                highlightthickness=1,
            )
            mascot_panel.pack(side="left", pady=11)
            mascot_panel.pack_propagate(False)
            mascot_label = tk.Label(
                mascot_panel, image=self.mascot_photo,
                background="#183E48", borderwidth=0,
            )
            mascot_label.pack(expand=True)
            self.iconphoto(True, self.mascot_photo)

        title_box = tk.Frame(brand, background="#102E38")
        title_box.pack(side="left", padx=(15, 0), pady=11)
        identity_row = tk.Frame(title_box, background="#102E38")
        identity_row.pack(anchor="w")
        tk.Label(
            identity_row,
            text="ROS 2",
            font=("Segoe UI", 8, "bold"),
            foreground="#71E1D3", background="#164651",
            padx=7, pady=2,
        ).pack(side="left")
        tk.Label(
            identity_row,
            text="HAND–EYE CALIBRATION",
            font=("Segoe UI", 8, "bold"),
            foreground="#8FAEB6", background="#102E38",
        ).pack(side="left", padx=(8, 0))
        tk.Label(
            title_box,
            text="小甲鱼 · 手眼标定工作站",
            font=("Microsoft YaHei UI", 18, "bold"),
            foreground="#FFFFFF", background="#102E38",
        ).pack(anchor="w", pady=(3, 0))
        tk.Label(
            title_box,
            text="01  内参标定    →    02  位姿采样    →    03  外参求解",
            font=("Microsoft YaHei UI", 9),
            foreground="#B5C9CE", background="#102E38",
        ).pack(anchor="w", pady=(3, 0))

        header_actions = tk.Frame(header, background="#102E38")
        header_actions.pack(side="right", padx=22)
        status_box = tk.Frame(header_actions, background="#102E38")
        status_box.pack(side="left", padx=(0, 15))
        tk.Label(
            status_box,
            text="SYSTEM STATUS",
            font=("Segoe UI", 7, "bold"),
            foreground="#77969E", background="#102E38",
        ).pack(anchor="w")
        self.workflow_status = tk.Label(
            status_box,
            text="●  工作流就绪",
            font=("Microsoft YaHei UI", 9, "bold"),
            foreground="#70E0B1", background="#102E38",
        )
        self.workflow_status.pack(anchor="w", pady=(2, 0))
        tk.Frame(
            header_actions, background="#36545D", width=1, height=38,
        ).pack(side="left", padx=(0, 15))
        ttk.Button(
            header_actions, text="保存全部设置", style="Header.TButton",
            command=self.save_config,
        ).pack(side="left")

        settings = tk.Frame(
            self,
            background="#FFFFFF",
            highlightbackground="#DCE5E8",
            highlightthickness=1,
        )
        settings.pack(fill="x", padx=20, pady=(14, 12))
        tk.Frame(settings, background="#168578", height=3).pack(fill="x")

        settings_head = tk.Frame(settings, background="#FFFFFF")
        settings_head.pack(fill="x", padx=14, pady=(10, 7))
        heading = tk.Frame(settings_head, background="#FFFFFF")
        heading.pack(side="left")
        tk.Label(
            heading, text="项目与设备设置",
            font=("Microsoft YaHei UI", 11, "bold"),
            foreground="#18323A", background="#FFFFFF",
        ).pack(anchor="w")
        tk.Label(
            heading, text="输出路径、相机分辨率与棋盘格规格",
            font=("Microsoft YaHei UI", 8),
            foreground="#758A91", background="#FFFFFF",
        ).pack(anchor="w", pady=(1, 0))
        self.camera_status = tk.Label(
            settings_head,
            text="●  相机未连接",
            font=("Microsoft YaHei UI", 9, "bold"),
            foreground="#A15C16", background="#FFF7E8",
            padx=10, pady=5,
        )
        self.camera_status.pack(side="right")

        self.vars: dict[str, tk.StringVar] = {}
        values = {
            "output_dir": self.config_data.output_dir,
            "camera_index": str(self.config_data.camera_index),
            "camera_width": str(self.config_data.camera_width),
            "camera_height": str(self.config_data.camera_height),
            "chessboard_cols": str(self.config_data.chessboard_cols),
            "chessboard_rows": str(self.config_data.chessboard_rows),
            "square_size_mm": str(self.config_data.square_size_mm),
        }
        for name, value in values.items():
            self.vars[name] = tk.StringVar(value=value)

        output_row = tk.Frame(settings, background="#FFFFFF")
        output_row.pack(fill="x", padx=14, pady=(0, 8))
        ttk.Label(output_row, text="输出目录", style="Card.TLabel").pack(side="left", padx=(0, 8))
        ttk.Entry(output_row, textvariable=self.vars["output_dir"]).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(output_row, text="浏览…", command=self.choose_output).pack(side="left", padx=(8, 0))

        device_row = tk.Frame(settings, background="#FFFFFF")
        device_row.pack(fill="x", padx=14, pady=(0, 11))

        def compact_field(label: str, name: str, width: int = 6) -> None:
            cell = tk.Frame(device_row, background="#FFFFFF")
            cell.pack(side="left", padx=(0, 12))
            tk.Label(
                cell, text=label, font=("Microsoft YaHei UI", 8),
                foreground="#6B8087", background="#FFFFFF",
            ).pack(anchor="w")
            ttk.Entry(cell, textvariable=self.vars[name], width=width).pack(pady=(2, 0))

        compact_field("相机编号", "camera_index", 6)
        compact_field("画面宽度", "camera_width", 8)
        compact_field("画面高度", "camera_height", 8)
        compact_field("角点列数", "chessboard_cols", 7)
        compact_field("角点行数", "chessboard_rows", 7)
        compact_field("方格边长 / mm", "square_size_mm", 9)
        camera_actions = tk.Frame(device_row, background="#FFFFFF")
        camera_actions.pack(side="right", pady=(13, 0))
        ttk.Button(camera_actions, text="关闭相机", command=self.close_camera).pack(side="right")
        ttk.Button(
            camera_actions, text="打开相机", style="Accent.TButton", command=self.open_camera,
        ).pack(side="right", padx=(0, 8))

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 18))
        left = ttk.Frame(body, padding=(0, 0, 12, 0), style="Workspace.TFrame")
        right = ttk.Frame(body, style="Workspace.TFrame")
        body.add(left, weight=3)
        body.add(right, weight=2)

        preview_box = tk.Frame(
            left, background="#FFFFFF",
            highlightbackground="#DCE5E8", highlightthickness=1,
        )
        preview_box.pack(fill="both", expand=True)
        tk.Frame(preview_box, background="#168578", height=3).pack(fill="x")
        preview_head = tk.Frame(preview_box, background="#F7FAFA")
        preview_head.pack(fill="x", padx=13, pady=10)
        tk.Label(
            preview_head, text="实时相机画面",
            font=("Microsoft YaHei UI", 11, "bold"),
            foreground="#18323A", background="#F7FAFA",
        ).pack(side="left")
        self.detect_status = tk.Label(
            preview_head, text="●  等待画面",
            font=("Microsoft YaHei UI", 9, "bold"),
            foreground="#60777E", background="#EDF2F3",
            padx=10, pady=5,
        )
        self.detect_status.pack(side="right")
        preview_surface = tk.Frame(preview_box, background="#0C2028")
        preview_surface.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.preview = tk.Label(
            preview_surface,
            text="打开相机后将在这里显示实时画面\n检测到棋盘角点时，状态将变为绿色",
            anchor="center",
            background="#102A2D",
            foreground="#AFC4CA",
            font=("Microsoft YaHei UI", 10),
            justify="center",
        )
        self.preview.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        self._build_intrinsic_tab()
        self._build_handeye_tab()
        self._build_solve_tab()

    def _create_scrollable_tab(self, title: str) -> ttk.Frame:
        """创建可用滚轮和滚动条浏览的页签内容区。"""
        page = ttk.Frame(self.notebook, style="Workspace.TFrame")
        self.notebook.add(page, text=title)

        canvas = tk.Canvas(
            page,
            background="#F3F7F8",
            highlightthickness=0,
            borderwidth=0,
        )
        scrollbar = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        content = ttk.Frame(canvas, padding=14, style="TabBody.TFrame")
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")

        def update_scroll_region(_event=None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def fit_content_width(event) -> None:
            canvas.itemconfigure(content_window, width=event.width)

        def scroll_windows(event) -> str:
            canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        def scroll_linux_up(_event) -> str:
            canvas.yview_scroll(-1, "units")
            return "break"

        def scroll_linux_down(_event) -> str:
            canvas.yview_scroll(1, "units")
            return "break"

        def enable_wheel(_event=None) -> None:
            canvas.bind_all("<MouseWheel>", scroll_windows)
            canvas.bind_all("<Button-4>", scroll_linux_up)
            canvas.bind_all("<Button-5>", scroll_linux_down)

        def disable_wheel(_event=None) -> None:
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        content.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", fit_content_width)
        page.bind("<Enter>", enable_wheel)
        page.bind("<Leave>", disable_wheel)

        # 保留引用，避免后续需要定位页签滚动区域时只能遍历控件树。
        if not hasattr(self, "tab_canvases"):
            self.tab_canvases: list[tk.Canvas] = []
        self.tab_canvases.append(canvas)
        return content

    def _build_intrinsic_tab(self) -> None:
        tab = self._create_scrollable_tab("① 内参标定")
        ttk.Label(tab, text="CALIBRATION  ·  STEP 01", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(tab, text="相机内参标定", style="Step.TLabel").pack(anchor="w", pady=(2, 0))
        ttk.Label(
            tab,
            text="移动棋盘覆盖画面中心、四角、远近与不同倾角。检测成功后采集，建议 20～30 张。",
            wraplength=410,
            style="TabMuted.TLabel",
        ).pack(anchor="w", pady=(6, 9))
        quality_row = ttk.Frame(tab, style="Section.TFrame", padding=(10, 8))
        quality_row.pack(fill="x", pady=(0, 8))
        ttk.Label(quality_row, text="采样质量").pack(side="left")
        self.intrinsic_quality_var = tk.StringVar(value="标准质量（推荐）")
        intrinsic_quality = ttk.Combobox(
            quality_row,
            textvariable=self.intrinsic_quality_var,
            values=("标准质量（推荐）", "严格质量", "极简采集"),
            state="readonly", width=18,
        )
        intrinsic_quality.pack(side="left", padx=8)
        intrinsic_quality.bind(
            "<<ComboboxSelected>>", lambda _event: self._update_intrinsic_quality_help()
        )
        intrinsic_feedback = tk.Frame(
            tab, background="#E7F6F2",
            highlightbackground="#B9E2D9", highlightthickness=1,
        )
        intrinsic_feedback.pack(fill="x", pady=(0, 9))
        self.intrinsic_feedback = tk.Label(
            intrinsic_feedback,
            text="标准质量：清晰度 ≥80、棋盘覆盖 ≥3%，至少 10 张。",
            background="#E7F6F2", foreground="#0F6F65",
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="w", padx=10, pady=7,
        )
        self.intrinsic_feedback.pack(fill="x")
        self.intrinsic_status = tk.Label(
            intrinsic_feedback, text="图片状态：已采集 0 张",
            background="#F5FBF9", foreground="#315B5D",
            anchor="w", padx=10, pady=4,
        )
        self.intrinsic_status.pack(fill="x")
        capture_panel = tk.Frame(
            tab, background="#FFF4EA",
            highlightbackground="#F5C3A6", highlightthickness=1,
        )
        capture_panel.pack(fill="x", pady=(0, 8))
        self.intrinsic_capture_btn = ttk.Button(
            capture_panel,
            text="拍摄当前棋盘图",
            style="Capture.TButton",
            command=self.capture_intrinsic,
        )
        self.intrinsic_capture_btn.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(
            capture_panel,
            text="每次点击只加入当前一张图片 · 请确认角点显示为绿色",
            background="#FFF4EA", foreground="#9A4A20",
            font=("Microsoft YaHei UI", 9),
        ).pack(pady=(0, 8))
        row = ttk.Frame(tab)
        row.pack(fill="x")
        ttk.Button(row, text="清空已拍图片", command=self.clear_intrinsic).pack(side="left")
        ttk.Button(row, text="计算并保存内参", command=self.solve_intrinsic).pack(side="left", padx=8)
        self.intrinsic_result = tk.Text(tab, height=10, wrap="word", state="disabled")
        self.intrinsic_result.configure(
            background="#F7FBFA", foreground="#173B3F",
            relief="flat", borderwidth=0, padx=10, pady=10,
            font=("Microsoft YaHei UI", 9),
        )
        self.intrinsic_result.pack(fill="both", expand=True, pady=(10, 0))

    def _build_handeye_tab(self) -> None:
        tab = self._create_scrollable_tab("② 外参采样")
        ttk.Label(tab, text="SAMPLING  ·  STEP 02", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(tab, text="手眼外参采样", style="Step.TLabel").pack(anchor="w", pady=(2, 0))
        feedback = tk.Frame(
            tab, background="#E7F6F2",
            highlightbackground="#B9E2D9", highlightthickness=1,
        )
        feedback.pack(fill="x", pady=(9, 5))
        self.feedback_banner = tk.Label(
            feedback,
            text="准备就绪 · 连接机器人数据后，点击“记录当前位姿样本”保存一组数据",
            background="#E7F6F2", foreground="#0F6F65",
            font=("Microsoft YaHei UI", 10, "bold"),
            anchor="w", padx=10, pady=7,
        )
        self.feedback_banner.pack(fill="x")
        self.pose_status = tk.Label(
            feedback, text="机器人数据：等待输入",
            background="#F5FBF9", foreground="#315B5D",
            anchor="w", padx=10, pady=4,
        )
        self.pose_status.pack(fill="x")
        self.sample_status = tk.Label(
            feedback, text="样本状态：已采集 0 组",
            background="#F5FBF9", foreground="#315B5D",
            anchor="w", padx=10, pady=4,
        )
        self.sample_status.pack(fill="x")
        mode_row = ttk.Frame(tab, style="Section.TFrame", padding=(10, 8))
        mode_row.pack(fill="x", pady=(10, 8))
        ttk.Label(mode_row, text="采样模式").pack(side="left")
        self.mode_var = tk.StringVar(value="ROS2 自动")
        mode = ttk.Combobox(
            mode_row,
            textvariable=self.mode_var,
            values=("ROS2 自动", "手动输入"),
            state="readonly",
            width=14,
        )
        mode.pack(side="left", padx=8)
        mode.bind("<<ComboboxSelected>>", lambda _event: self._update_mode())
        ttk.Label(mode_row, text="采样质量").pack(side="left", padx=(14, 0))
        self.handeye_quality_var = tk.StringVar(value="标准质量（推荐）")
        quality = ttk.Combobox(
            mode_row,
            textvariable=self.handeye_quality_var,
            values=("标准质量（推荐）", "严格质量", "极简采样"),
            state="readonly", width=18,
        )
        quality.pack(side="left", padx=8)
        quality.bind("<<ComboboxSelected>>", lambda _event: self._update_quality_help())

        self.ros_frame = ttk.LabelFrame(
            tab, text="ROS2 消息接口（请按机器人系统填写）",
            padding=9, style="Card.TLabelframe",
        )
        self.ros_frame.pack(fill="x", pady=4)
        default_auto_type = (
            "关节角（JointState）"
            if self.config_data.ros_input_type == "joints"
            else "末端位姿（PoseStamped）"
        )
        self.auto_input_type_var = tk.StringVar(value=default_auto_type)
        self.pose_topic_var = tk.StringVar(value=self.config_data.pose_topic)
        self.joint_dof_var = tk.StringVar(value=str(self.config_data.joint_dof))
        self.joint_names_var = tk.StringVar(value=self.config_data.joint_names)
        # 默认由界面按钮触发；空话题表示不创建 ROS2 采集订阅。
        self.capture_topic_var = tk.StringVar(value="")
        self.status_topic_var = tk.StringVar(value=self.config_data.status_topic)
        ttk.Label(self.ros_frame, text="输入数据").grid(row=0, column=0, sticky="w", pady=2)
        auto_type = ttk.Combobox(
            self.ros_frame,
            textvariable=self.auto_input_type_var,
            values=("末端位姿（PoseStamped）", "关节角（JointState）"),
            state="readonly",
            width=27,
        )
        auto_type.grid(row=0, column=1, sticky="ew", padx=8, pady=2)
        auto_type.bind("<<ComboboxSelected>>", lambda _event: self._update_auto_input_type())
        ttk.Label(self.ros_frame, text="输入话题").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(self.ros_frame, textvariable=self.pose_topic_var, width=29).grid(
            row=1, column=1, sticky="ew", padx=8, pady=2
        )

        self.auto_joint_frame = ttk.Frame(self.ros_frame)
        self.auto_joint_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Label(self.auto_joint_frame, text="关节自由度").pack(side="left")
        ttk.Spinbox(
            self.auto_joint_frame, from_=1, to=12,
            textvariable=self.joint_dof_var, width=5,
        ).pack(side="left", padx=(8, 14))
        ttk.Label(self.auto_joint_frame, text="关节顺序（可选）").pack(side="left")
        ttk.Entry(self.auto_joint_frame, textvariable=self.joint_names_var, width=29).pack(
            side="left", padx=8, fill="x", expand=True
        )

        ttk.Label(self.ros_frame, text="状态发布（可选）").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(self.ros_frame, textvariable=self.status_topic_var, width=29).grid(
            row=3, column=1, sticky="ew", padx=8, pady=2
        )
        self.ros_frame.columnconfigure(1, weight=1)
        self.auto_help = ttk.Label(
            self.ros_frame,
            wraplength=410,
            foreground="#4b5563",
        )
        self.auto_help.grid(row=4, column=0, columnspan=2, sticky="w", pady=(5, 0))
        ttk.Label(
            self.ros_frame,
            text=(
                "接口方向：① 输入话题＝机器人 → APP，提供当前末端位姿或关节角；  "
                "② 状态发布＝APP → 外部系统（可选）。采集不需要接口，直接点击下方按钮。"
            ),
            wraplength=410,
            foreground="#0F766E",
            style="Card.TLabel",
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(7, 0))
        ros_buttons = ttk.Frame(self.ros_frame)
        ros_buttons.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(ros_buttons, text="连接 ROS2", command=self.start_ros).pack(side="left")
        ttk.Button(ros_buttons, text="断开", command=self.stop_ros).pack(side="left", padx=8)
        ttk.Button(ros_buttons, text="查看接口说明", command=self._show_interface_help).pack(side="left")
        self.ros_status = ttk.Label(ros_buttons, text="未连接")
        self.ros_status.pack(side="left", padx=8)

        self.manual_frame = ttk.LabelFrame(
            tab, text="手动数据输入", padding=9, style="Card.TLabelframe"
        )
        manual_options = ttk.Frame(self.manual_frame)
        manual_options.pack(fill="x")
        self.manual_input_type_var = tk.StringVar(value="末端位姿（四元数）")
        manual_type = ttk.Combobox(
            manual_options,
            textvariable=self.manual_input_type_var,
            values=("末端位姿（四元数）", "末端位姿（RPY 欧拉角）", "关节角"),
            state="readonly",
            width=23,
        )
        manual_type.pack(side="left")
        manual_type.bind("<<ComboboxSelected>>", lambda _event: self._render_manual_fields())
        ttk.Label(manual_options, text="角度单位").pack(side="left", padx=(12, 3))
        self.manual_angle_unit_var = tk.StringVar(value="度 deg")
        ttk.Combobox(
            manual_options,
            textvariable=self.manual_angle_unit_var,
            values=("度 deg", "弧度 rad"),
            state="readonly", width=10,
        ).pack(side="left")
        ttk.Label(manual_options, text="自由度").pack(side="left", padx=(12, 3))
        self.manual_dof_var = tk.StringVar(value=str(self.config_data.joint_dof))
        ttk.Spinbox(
            manual_options, from_=1, to=12,
            textvariable=self.manual_dof_var, width=4,
        ).pack(side="left")
        ttk.Button(manual_options, text="更新输入框", command=self._render_manual_fields).pack(
            side="left", padx=6
        )
        self.manual_inputs = ttk.Frame(self.manual_frame)
        self.manual_inputs.pack(fill="x", pady=(8, 2))
        self.manual_help = ttk.Label(
            self.manual_frame, wraplength=410, foreground="#4b5563"
        )
        self.manual_help.pack(anchor="w", pady=(5, 0))
        self.manual_value_vars: list[tk.StringVar] = []
        self._render_manual_fields()

        action = tk.Frame(
            tab, background="#FFF4EA",
            highlightbackground="#F5C3A6", highlightthickness=1,
        )
        # 主操作固定在模式选择下方，避免较长的 ROS/手动参数区把它挤出窗口。
        action.pack(fill="x", pady=10, before=self.ros_frame)
        self.handeye_action_frame = action
        self.handeye_capture_btn = ttk.Button(
            action,
            text="记录当前位姿样本",
            style="Capture.TButton",
            command=self.capture_handeye,
        )
        self.handeye_capture_btn.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(
            action,
            text="每次点击只加入当前一组图像 + 机器人位姿",
            background="#FFF4EA", foreground="#9A4A20",
            font=("Microsoft YaHei UI", 9),
        ).pack(pady=(0, 5))
        secondary = tk.Frame(action, background="#FFF4EA")
        secondary.pack(pady=(0, 8))
        ttk.Button(secondary, text="保存全部样本", command=self.save_samples).pack(side="left")
        ttk.Button(secondary, text="清空已采样本", command=self.clear_samples).pack(side="left", padx=8)
        ttk.Label(
            tab,
            text="机械臂停稳且棋盘检测成功后，点击橙色主按钮记录样本。",
            wraplength=410,
            style="TabMuted.TLabel",
        ).pack(anchor="w", pady=(8, 0))
        self._update_auto_input_type(initial=True)
        self._update_quality_help()
        self._update_mode()

    def _build_solve_tab(self) -> None:
        tab = self._create_scrollable_tab("③ 求解验证")
        ttk.Label(tab, text="SOLVER  ·  STEP 03", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(tab, text="诊断、求解与验证", style="Step.TLabel").pack(anchor="w", pady=(2, 0))
        mode_row = ttk.Frame(tab, style="Section.TFrame", padding=(10, 8))
        mode_row.pack(fill="x", pady=(10, 2))
        ttk.Label(mode_row, text="求解模式").pack(side="left")
        self.solve_mode_var = tk.StringVar(value="标准鲁棒求解（推荐）")
        ttk.Combobox(
            mode_row,
            textvariable=self.solve_mode_var,
            values=(
                "标准鲁棒求解（推荐）",
                "极简 OpenCV 求解",
                "标准求解 + Bundle Adjustment",
            ),
            state="readonly",
            width=31,
        ).pack(side="left", padx=8)
        controls = ttk.Frame(tab, style="Section.TFrame", padding=(10, 8))
        controls.pack(fill="x", pady=10)
        ttk.Button(controls, text="运行诊断", command=lambda: self.run_tool("diagnose")).pack(side="left")
        ttk.Button(controls, text="求解外参", style="Accent.TButton", command=lambda: self.run_tool("solve")).pack(side="left", padx=8)
        ttk.Button(controls, text="验证结果", command=lambda: self.run_tool("verify")).pack(side="left")
        ttk.Button(controls, text="完整流程", command=self.run_all).pack(side="left", padx=8)
        self.solve_status = ttk.Label(tab, text="等待样本", padding=(0, 4))
        self.solve_status.pack(anchor="w")
        self.log = ScrolledText(tab, height=22, wrap="word", font=("Consolas", 9))
        self.log.configure(
            background="#102A2D", foreground="#D8F4EE",
            insertbackground="#FFFFFF", relief="flat",
            padx=9, pady=9,
        )
        self.log.pack(fill="both", expand=True, pady=(6, 0))

    def _numbers(self):
        return (
            int(self.vars["chessboard_cols"].get()),
            int(self.vars["chessboard_rows"].get()),
            float(self.vars["square_size_mm"].get()),
        )

    def _paths(self):
        output = Path(self.vars["output_dir"].get()).expanduser().resolve()
        return output, output / "camera_intrinsics.yaml", output / "samples.yaml"

    def save_config(self) -> None:
        try:
            self._validate_ros_topics()
            data = AppConfig(
                calib_dir=str((APP_DIR / "algorithms").resolve()),
                output_dir=self.vars["output_dir"].get(),
                camera_index=int(self.vars["camera_index"].get()),
                camera_width=int(self.vars["camera_width"].get()),
                camera_height=int(self.vars["camera_height"].get()),
                chessboard_cols=int(self.vars["chessboard_cols"].get()),
                chessboard_rows=int(self.vars["chessboard_rows"].get()),
                square_size_mm=float(self.vars["square_size_mm"].get()),
                ros_input_type=(
                    "joints" if self.auto_input_type_var.get().startswith("关节角")
                    else "pose"
                ),
                pose_topic=self.pose_topic_var.get(),
                joint_dof=int(self.joint_dof_var.get()),
                joint_names=self.joint_names_var.get(),
                capture_topic=self.capture_topic_var.get(),
                status_topic=self.status_topic_var.get(),
            )
            Path(data.output_dir).mkdir(parents=True, exist_ok=True)
            data.save(CONFIG_PATH)
            self.config_data = data
            self.workflow_status.configure(text="✓  设置已保存", foreground="#70E0B1")
        except Exception as exc:
            messagebox.showerror("设置错误", str(exc))

    def choose_output(self) -> None:
        path = filedialog.askdirectory(initialdir=self.vars["output_dir"].get())
        if path:
            self.vars["output_dir"].set(path)

    def open_camera(self) -> None:
        try:
            self.camera.open(
                int(self.vars["camera_index"].get()),
                int(self.vars["camera_width"].get()),
                int(self.vars["camera_height"].get()),
            )
            self.camera_status.configure(
                text="●  相机已连接", foreground="#0A7258", background="#E7F8F0"
            )
        except Exception as exc:
            messagebox.showerror("相机错误", str(exc))

    def close_camera(self) -> None:
        self.camera.close()
        self.current_frame = None
        self.camera_status.configure(
            text="●  相机未连接", foreground="#A15C16", background="#FFF7E8"
        )

    def _intrinsic_quality_mode(self) -> str:
        return {
            "标准质量（推荐）": "standard",
            "严格质量": "strict",
            "极简采集": "minimal",
        }[self.intrinsic_quality_var.get()]

    def _update_intrinsic_quality_help(self) -> None:
        descriptions = {
            "标准质量（推荐）": "标准质量：清晰度 ≥80、棋盘覆盖 ≥3%，至少 10 张。",
            "严格质量": "严格质量：清晰度 ≥120、棋盘覆盖 ≥6%，至少 15 张。",
            "极简采集": "极简采集：只要求检测到完整棋盘，至少 3 张；用于排障。",
        }
        self._set_intrinsic_feedback(
            descriptions[self.intrinsic_quality_var.get()], "info"
        )

    def _set_intrinsic_feedback(self, text: str, kind: str = "info") -> None:
        colors = {
            "info": ("#E7F6F2", "#0F6F65"),
            "success": ("#DCFCE7", "#166534"),
            "warning": ("#FEF3C7", "#92400E"),
            "error": ("#FEE2E2", "#B91C1C"),
        }
        background, foreground = colors.get(kind, colors["info"])
        self.intrinsic_feedback.configure(
            text=text, background=background, foreground=foreground
        )

    def capture_intrinsic(self) -> None:
        if self.current_frame is None:
            self._set_intrinsic_feedback("采集失败：请先打开相机", "error")
            return
        try:
            cols, rows, square = self._numbers()
            result = self.intrinsic.add(
                self.current_frame.copy(), cols, rows, square,
                quality_mode=self._intrinsic_quality_mode(),
            )
            count = len(self.intrinsic.image_sets)
            self.intrinsic_status.configure(
                text=(f"图片状态：已采集 {count} 张 | "
                      f"清晰度 {result.sharpness:.0f} | "
                      f"棋盘覆盖 {result.board_coverage_percent:.1f}%")
            )
            self._set_intrinsic_feedback(
                f"采集成功：第 {count} 张已加入；每次点击只保存一张", "success"
            )
        except Exception as exc:
            self._set_intrinsic_feedback(f"采集失败：{exc}", "error")

    def clear_intrinsic(self) -> None:
        self.intrinsic = IntrinsicCalibration()
        self.intrinsic_status.configure(text="图片状态：已采集 0 张")
        self._set_intrinsic_feedback("内参图片已清空，可以重新采集", "warning")

    def solve_intrinsic(self) -> None:
        try:
            output, intrinsics, _ = self._paths()
            output.mkdir(parents=True, exist_ok=True)
            cols, rows, square = self._numbers()
            result = self.intrinsic.solve(
                intrinsics, cols, rows, square,
                quality_mode=self._intrinsic_quality_mode(),
            )
            text = (
                f"保存：{intrinsics}\n"
                f"RMS：{result['reprojection_error_px']:.4f} px\n"
                f"中位单图误差：{result['reprojection_error_median_px']:.4f} px\n"
                f"最大单图误差：{result['reprojection_error_max_px']:.4f} px\n"
                f"图像尺寸：{result['image_width']} × {result['image_height']}"
            )
            self._set_text(self.intrinsic_result, text)
            self._set_intrinsic_feedback(
                f"内参计算完成：RMS {result['reprojection_error_px']:.4f}px", "success"
            )
            messagebox.showinfo("内参完成", "内参已保存，可以进入外参采样。")
            self.notebook.select(1)
        except Exception as exc:
            self._set_intrinsic_feedback(f"内参求解失败：{exc}", "error")

    def _update_auto_input_type(self, initial: bool = False) -> None:
        joint_mode = self.auto_input_type_var.get().startswith("关节角")
        if joint_mode:
            self.auto_joint_frame.grid()
            if not initial and self.pose_topic_var.get().strip() == "/arm/pose":
                self.pose_topic_var.set("/arm/joint_states")
            self.auto_help.configure(
                text=(
                    "JointState.position 为关节角，单位必须是 rad。自由度表示参与 FK 的关节数量；"
                    "当前 robot_params.yaml 示例为 5 自由度。关节顺序可填 joint1,joint2,...；"
                    "留空则按 position 数组前 N 项的顺序读取。"
                )
            )
        else:
            self.auto_joint_frame.grid_remove()
            if not initial and self.pose_topic_var.get().strip() == "/arm/joint_states":
                self.pose_topic_var.set("/arm/pose")
            self.auto_help.configure(
                text=(
                    "PoseStamped.pose.position: x/y/z 是末端在基座坐标系中的位置，单位 m；"
                    "orientation: x/y/z/w 是归一化四元数。header.frame_id 应是机械臂基座坐标系。"
                )
            )

    def _update_quality_help(self) -> None:
        descriptions = {
            "标准质量（推荐）": "标准质量：重投影 ≤0.40px、清晰度 ≥80、每格 ≥20px。",
            "严格质量": "严格质量：重投影 ≤0.25px、清晰度 ≥120、每格 ≥25px。",
            "极简采样": "极简采样：只检查棋盘和 PnP；用于排障，不建议作为最终标定数据。",
        }
        self._set_feedback(descriptions[self.handeye_quality_var.get()], "info")

    def _set_feedback(self, text: str, kind: str = "info") -> None:
        colors = {
            "info": ("#E7F6F2", "#0F6F65"),
            "success": ("#DCFCE7", "#166534"),
            "warning": ("#FEF3C7", "#92400E"),
            "error": ("#FEE2E2", "#B91C1C"),
        }
        background, foreground = colors.get(kind, colors["info"])
        self.feedback_banner.configure(
            text=text, background=background, foreground=foreground
        )

    def _render_manual_fields(self) -> None:
        for child in self.manual_inputs.winfo_children():
            child.destroy()
        selected = self.manual_input_type_var.get()
        if selected == "末端位姿（四元数）":
            labels = ("x", "y", "z", "qx", "qy", "qz", "qw")
            defaults = ("0", "0", "0", "0", "0", "0", "1")
            help_text = (
                "x/y/z：末端相对基座的位置，单位 m；qx/qy/qz/qw：末端姿态四元数 "
                "xyzw，必须非零。角度单位选项在此模式下不使用。"
            )
        elif selected == "末端位姿（RPY 欧拉角）":
            labels = ("x", "y", "z", "roll", "pitch", "yaw")
            defaults = ("0",) * 6
            help_text = (
                "x/y/z：末端相对基座的位置，单位 m；roll/pitch/yaw：绕 X/Y/Z 的固定轴欧拉角，"
                "采用 Rz(yaw)·Ry(pitch)·Rx(roll)，角度单位由上方选择。"
            )
        else:
            try:
                dof = int(self.manual_dof_var.get())
            except ValueError:
                dof = 5
                self.manual_dof_var.set("5")
            dof = max(1, min(12, dof))
            labels = tuple(f"q{i + 1}" for i in range(dof))
            defaults = ("0",) * dof
            help_text = (
                f"q1～q{dof}：按 robot_params.yaml MDH 顺序填写的 {dof} 个关节角；"
                "单位由上方选择。APP 先做正运动学得到末端位姿。当前随附机器人模型为 5 自由度，"
                "其他自由度必须同步修改 algorithms/robot_params.yaml。"
            )
        self.manual_value_vars = [tk.StringVar(value=value) for value in defaults]
        for column, (label, var) in enumerate(
            zip(labels, self.manual_value_vars, strict=True)
        ):
            ttk.Label(self.manual_inputs, text=label).grid(row=0, column=column)
            ttk.Entry(self.manual_inputs, textvariable=var, width=8).grid(
                row=1, column=column, padx=2
            )
        self.manual_help.configure(text=help_text)

    def _update_mode(self) -> None:
        if self.mode_var.get() == "ROS2 自动":
            self.manual_frame.pack_forget()
            if not self.ros_frame.winfo_ismapped():
                self.ros_frame.pack(fill="x", pady=4, after=self.handeye_action_frame)
            self.pose_status.configure(text="等待 ROS2 机器人数据")
        else:
            self.ros_frame.pack_forget()
            if not self.manual_frame.winfo_ismapped():
                self.manual_frame.pack(fill="x", pady=4, after=self.handeye_action_frame)
            self.pose_status.configure(text="请填写手动机器人数据")

    def _ros_pose_callback(self, pose: RosPose) -> None:
        self.events.put(("pose", pose))

    def _ros_joints_callback(self, joints: RosJoints) -> None:
        self.events.put(("joints", joints))

    def _ros_error_callback(self, error: str) -> None:
        self.events.put(("ros_error", error))

    def _ros_capture_callback(self) -> None:
        self.events.put(("capture", None))

    def _show_interface_help(self) -> None:
        messagebox.showinfo(
            "ROS2 接口作用与意义",
            "1. 输入话题（机器人 → APP）\n"
            "   作用：持续告诉 APP 机械臂当前状态。\n"
            "   PoseStamped：x/y/z 为基座到末端的位置，单位 m；四元数为 xyzw。\n"
            "   JointState：position 为关节角，单位 rad；APP 按关节顺序执行 FK。\n"
            "   意义：标定要求每张棋盘图像都和同一时刻的机器人位姿配对。\n\n"
            "2. 界面“记录当前位姿样本”按钮\n"
            "   作用：每点击一次，只保存一组当前图像和最新机器人数据。\n"
            "   意义：无需采集触发接口；请先确认机械臂停稳且棋盘检测成功。\n\n"
            "3. 状态发布话题（APP → 外部系统，可选）\n"
            "   类型：std_msgs/String，内容为 JSON。\n"
            "   事件：ros_started、sample_captured、capture_failed、samples_saved、input_error。\n"
            "   作用：外部程序可确认连接、样本数量、重投影误差、失败原因和保存路径。\n"
            "   意义：方便机器人流程自动等待结果、记录日志和处理异常。",
        )

    def start_ros(self) -> None:
        try:
            self._validate_ros_topics()
            if self.ros.running:
                raise RuntimeError("ROS2 已连接；修改接口后请先断开再重新连接")
            joint_names = tuple(
                name.strip() for name in self.joint_names_var.get().split(",")
                if name.strip()
            )
            self.latest_pose = None
            self.latest_robot_input = None
            self.robot_data_announced = False
            self.ros.start(
                "joints" if self.auto_input_type_var.get().startswith("关节角") else "pose",
                self.pose_topic_var.get().strip(),
                self.capture_topic_var.get().strip(),
                self.status_topic_var.get().strip(),
                int(self.joint_dof_var.get()),
                joint_names,
            )
            self.ros_status.configure(text="已连接", foreground="#047857")
            self._set_feedback("ROS2 已连接，等待机器人数据；收到后可点击“记录当前位姿样本”", "success")
        except Exception as exc:
            self._set_feedback(f"ROS2 连接失败：{exc}", "error")

    def _validate_ros_topics(self) -> None:
        topics = {
            "输入话题": self.pose_topic_var.get().strip(),
        }
        for label, topic in topics.items():
            if not topic:
                raise ValueError(f"请填写{label}")
            if not topic.startswith("/"):
                raise ValueError(f"{label}必须以 / 开头：{topic}")
        status_topic = self.status_topic_var.get().strip()
        if status_topic and not status_topic.startswith("/"):
            raise ValueError(f"状态话题必须以 / 开头：{status_topic}")
        dof = int(self.joint_dof_var.get())
        if not 1 <= dof <= 12:
            raise ValueError("关节自由度必须在 1～12 之间")
        joint_names = [
            name.strip() for name in self.joint_names_var.get().split(",")
            if name.strip()
        ]
        if joint_names and len(joint_names) != dof:
            raise ValueError(
                f"关节顺序填写了 {len(joint_names)} 个名称，但自由度设置为 {dof}"
            )

    def stop_ros(self) -> None:
        self.ros.stop()
        self.ros_status.configure(text="未连接", foreground="#b45309")
        self._set_feedback("ROS2 已断开", "warning")

    def _manual_sample(self) -> tuple[tuple[float, ...], tuple[float, ...], str]:
        values = tuple(float(var.get()) for var in self.manual_value_vars)
        selected = self.manual_input_type_var.get()
        if selected == "末端位姿（四元数）":
            return values, values, "pose"
        angle_scale = math.pi / 180.0 if self.manual_angle_unit_var.get() == "度 deg" else 1.0
        if selected == "末端位姿（RPY 欧拉角）":
            x, y, z, roll, pitch, yaw = values
            qx, qy, qz, qw = rpy_to_quaternion(
                roll * angle_scale, pitch * angle_scale, yaw * angle_scale
            )
            return (x, y, z, qx, qy, qz, qw), values, "pose_rpy"
        joints_rad = tuple(value * angle_scale for value in values)
        return joints_to_pose(joints_rad), joints_rad, "joints"

    def capture_handeye(self) -> None:
        if self.current_frame is None:
            self._set_feedback("采集失败：请先打开相机", "error")
            return
        if self.mode_var.get() == "ROS2 自动":
            if self.latest_pose is None:
                self._set_feedback("采集失败：尚未收到所选类型的 ROS2 机器人消息", "error")
                return
            pose = self.latest_pose.values
            robot_input = self.latest_robot_input or pose
            timestamp = self.latest_pose.timestamp
            input_mode = self.latest_input_mode
        else:
            try:
                pose, robot_input, input_mode = self._manual_sample()
            except Exception as exc:
                self._set_feedback(f"手动输入错误：{exc}", "error")
                return
            timestamp = time.time()
        try:
            _, intrinsics, _ = self._paths()
            if not intrinsics.exists():
                raise FileNotFoundError("请先完成内参标定，缺少 camera_intrinsics.yaml")
            cols, rows, square = self._numbers()
            quality_modes = {
                "标准质量（推荐）": "standard",
                "严格质量": "strict",
                "极简采样": "minimal",
            }
            result = self.handeye.add(
                self.current_frame.copy(), pose, intrinsics,
                cols, rows, square, input_mode, timestamp,
                robot_pose_input=robot_input,
                quality_mode=quality_modes[self.handeye_quality_var.get()],
            )
            self.sample_status.configure(
                text=(f"样本状态：已采集 {len(self.handeye.samples)} 组 | "
                      f"重投影 {result.reprojection_error_px:.3f}px | "
                      f"每格 {result.pixels_per_square:.1f}px | 清晰度 {result.sharpness:.0f}")
            )
            self._set_feedback(
                f"采集成功：第 {len(self.handeye.samples)} 组已加入，"
                f"重投影 {result.reprojection_error_px:.3f}px",
                "success",
            )
            self.ros.publish_status(
                "sample_captured",
                sample_count=len(self.handeye.samples),
                reprojection_error_px=result.reprojection_error_px,
            )
        except Exception as exc:
            self.ros.publish_status("capture_failed", error=str(exc))
            self._set_feedback(f"采集失败：{exc}", "error")

    def save_samples(self) -> None:
        try:
            _, intrinsics, samples = self._paths()
            cols, rows, square = self._numbers()
            self.handeye.save(samples, intrinsics, cols, rows, square)
            self.ros.publish_status("samples_saved", path=str(samples), count=len(self.handeye.samples))
            self._set_feedback(f"样本已保存：{samples}", "success")
            messagebox.showinfo("已保存", f"样本已保存：\n{samples}")
            self.notebook.select(2)
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))

    def clear_samples(self) -> None:
        self.handeye = HandEyeCollection()
        self.sample_status.configure(text="样本状态：已采集 0 组")
        self._set_feedback("样本已清空，可以重新开始采集", "warning")

    def _tool_request(self, name: str) -> tuple[Path, str]:
        calib_dir = (APP_DIR / "algorithms").resolve()
        _, _, samples = self._paths()
        result = samples.with_name(f"{samples.stem}_result.yaml")
        if name not in ("diagnose", "solve", "verify"):
            raise ValueError(f"未知任务：{name}")
        if not (calib_dir / "solve.py").exists():
            raise FileNotFoundError(f"内置算法目录不存在：{calib_dir}")
        if not samples.exists():
            raise FileNotFoundError("请先保存外参样本 samples.yaml")
        if name == "verify" and not result.exists():
            raise FileNotFoundError("请先求解，缺少 samples_result.yaml")
        solve_modes = {
            "标准鲁棒求解（推荐）": "robust",
            "极简 OpenCV 求解": "minimal",
            "标准求解 + Bundle Adjustment": "ba",
        }
        return samples, solve_modes[self.solve_mode_var.get()]

    def run_tool(self, name: str, on_done=None) -> None:
        if self.tool_running:
            messagebox.showwarning("算法正在运行", "请等待当前诊断、求解或验证任务完成")
            return
        try:
            samples, solve_mode = self._tool_request(name)
        except Exception as exc:
            messagebox.showerror("无法运行", str(exc))
            return
        self.tool_running = True
        self.solve_status.configure(text=f"正在运行 {name}…")
        self.log.insert(
            "end",
            f"\n[内置算法] {name} | 模式={self.solve_mode_var.get()} | {samples}\n",
        )
        self.log.see("end")

        def worker() -> None:
            code = run_algorithm(
                name,
                samples,
                solve_mode,
                lambda line: self.events.put(("log", line)),
            )
            self.events.put(("tool_done", (name, code, on_done)))

        threading.Thread(target=worker, daemon=True, name=f"tool-{name}").start()

    def run_all(self) -> None:
        self.run_tool("diagnose", on_done=lambda ok: self.run_tool(
            "solve", on_done=lambda ok2: self.run_tool("verify") if ok2 else None
        ) if ok else None)

    def _tick(self) -> None:
        frame = self.camera.read()
        if frame is not None:
            self.current_frame = frame
            self.frame_counter += 1
            if self.frame_counter % 5 == 0:
                try:
                    cols, rows, _ = self._numbers()
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    self.last_detection = detect_chessboard(gray, (cols, rows))
                except Exception:
                    self.last_detection = (False, None)
            display = frame.copy()
            found, corners = self.last_detection
            if found and corners is not None:
                try:
                    cols, rows, _ = self._numbers()
                    cv2.drawChessboardCorners(display, (cols, rows), corners, True)
                except Exception:
                    pass
                self.detect_status.configure(
                    text="●  棋盘检测成功", foreground="#087455", background="#E7F8F0"
                )
            else:
                self.detect_status.configure(
                    text="●  未检测到棋盘", foreground="#B33A3A", background="#FDECEC"
                )
            self._show_frame(display)

        while True:
            try:
                event, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if event == "pose":
                self.latest_pose = payload  # type: ignore[assignment]
                pose = self.latest_pose
                assert pose is not None
                self.latest_robot_input = pose.values
                self.latest_input_mode = "ros_pose"
                self.pose_status.configure(
                    text=(f"ROS 位姿：x={pose.values[0]:.4f} y={pose.values[1]:.4f} "
                          f"z={pose.values[2]:.4f} | frame={pose.frame_id or '-'}"),
                    foreground="#047857",
                )
                if not self.robot_data_announced:
                    self._set_feedback("已收到 ROS2 末端位姿，可以点击“记录当前位姿样本”", "info")
                    self.robot_data_announced = True
            elif event == "joints":
                joints = payload
                assert isinstance(joints, RosJoints)
                try:
                    pose_values = joints_to_pose(joints.values)
                    self.latest_pose = RosPose(
                        values=pose_values,
                        timestamp=joints.timestamp,
                        frame_id=joints.frame_id,
                    )
                    self.latest_robot_input = joints.values
                    self.latest_input_mode = "ros_joints"
                    names = ",".join(joints.names)
                    self.pose_status.configure(
                        text=(
                            f"ROS 关节角：{len(joints.values)} 自由度 [{names}] | "
                            f"FK 末端 x={pose_values[0]:.4f} y={pose_values[1]:.4f} "
                            f"z={pose_values[2]:.4f}m"
                        ),
                        foreground="#047857",
                    )
                    if not self.robot_data_announced:
                        self._set_feedback("已收到 ROS2 关节角并完成 FK，可以点击“记录当前位姿样本”", "info")
                        self.robot_data_announced = True
                except Exception as exc:
                    self.pose_status.configure(text=f"关节角/FK 错误：{exc}", foreground="#b91c1c")
                    self._set_feedback(f"关节角/FK 错误：{exc}", "error")
                    self.latest_pose = None
                    self.latest_robot_input = None
            elif event == "ros_error":
                self.pose_status.configure(text=f"ROS 输入错误：{payload}", foreground="#b91c1c")
                self._set_feedback(f"ROS 输入错误：{payload}", "error")
            elif event == "capture":
                self.capture_handeye()
            elif event == "log":
                self.log.insert("end", str(payload))
                self.log.see("end")
            elif event == "tool_done":
                name, code, callback = payload  # type: ignore[misc]
                self.tool_running = False
                ok = code == 0
                self.solve_status.configure(
                    text=f"{name} {'完成' if ok else '失败'}（退出码 {code}）",
                    foreground="#047857" if ok else "#b91c1c",
                )
                if callback is not None:
                    callback(ok)
        self.after(30, self._tick)

    def _show_frame(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        width = max(self.preview.winfo_width(), 320)
        height = max(self.preview.winfo_height(), 240)
        image = Image.fromarray(rgb)
        image.thumbnail((width - 8, height - 8), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview.configure(image=self.preview_photo, text="")

    @staticmethod
    def _set_text(widget: tk.Text, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def on_close(self) -> None:
        self.camera.close()
        self.ros.stop()
        self.destroy()


def main() -> None:
    HandEyeApp().mainloop()


if __name__ == "__main__":
    main()
