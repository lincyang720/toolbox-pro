"""
图片批量压缩工具
本地压缩，不上传云端，支持 JPG/PNG/WEBP
支持拖拽、批量处理、自定义质量
"""

import os
import sys
import threading
import queue
from pathlib import Path

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    HAS_CTK = True
except ImportError:
    import tkinter as tk
    HAS_CTK = False

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as fd
import tkinter.messagebox as mb

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def format_bytes(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} GB"


def compress_image(src: Path, dst: Path, quality: int, max_width: int) -> tuple:
    """返回 (原始大小, 压缩后大小)"""
    orig_size = src.stat().st_size
    img = Image.open(src)

    # 转换模式
    if img.mode in ("RGBA", "P") and dst.suffix.lower() in (".jpg", ".jpeg"):
        img = img.convert("RGB")

    # 缩放
    if max_width > 0 and img.width > max_width:
        ratio = max_width / img.width
        new_h = int(img.height * ratio)
        img = img.resize((max_width, new_h), Image.LANCZOS)

    dst.parent.mkdir(parents=True, exist_ok=True)

    ext = dst.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        img.save(dst, "JPEG", quality=quality, optimize=True)
    elif ext == ".png":
        compress_level = max(0, min(9, int((100 - quality) / 11)))
        img.save(dst, "PNG", compress_level=compress_level, optimize=True)
    elif ext == ".webp":
        img.save(dst, "WEBP", quality=quality)
    else:
        img.save(dst, quality=quality, optimize=True)

    new_size = dst.stat().st_size
    return orig_size, new_size


class ImageCompressorApp:
    def __init__(self):
        if HAS_CTK:
            self.root = ctk.CTk()
        else:
            self.root = tk.Tk()

        self.root.title("图片批量压缩工具")
        self.root.geometry("900x640")
        self.root.minsize(700, 500)
        self.files: list[Path] = []
        self.q = queue.Queue()
        self._build_ui()
        self.root.after(100, self._poll)

    def _build_ui(self):
        if HAS_CTK:
            self._build_ctk()
        else:
            self._build_tk()

    def _build_ctk(self):
        root = self.root

        # 顶部标题
        header = ctk.CTkFrame(root, fg_color="#4f8ef7", corner_radius=0, height=70)
        header.pack(fill="x"); header.pack_propagate(False)
        ctk.CTkLabel(header, text="🖼 图片批量压缩工具",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color="white").pack(side="left", padx=20)
        ctk.CTkLabel(header, text="本地处理 · 隐私安全 · 不上传云端",
                     font=ctk.CTkFont(size=11), text_color="#cce0ff").pack(side="left")

        body = ctk.CTkFrame(root, fg_color="#f5f6f8")
        body.pack(fill="both", expand=True)

        # 左侧设置面板
        left = ctk.CTkFrame(body, width=220, fg_color="white",
                             border_width=1, border_color="#e8e8e8")
        left.pack(side="left", fill="y", padx=(12, 6), pady=12)
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="压缩设置",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(16, 8))

        # 质量滑块
        ctk.CTkLabel(left, text="压缩质量", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16)
        self.quality_var = tk.IntVar(value=80)
        self.quality_label = ctk.CTkLabel(left, text="80%", font=ctk.CTkFont(size=11, weight="bold"))
        self.quality_label.pack()
        self.quality_slider = ctk.CTkSlider(left, from_=10, to=99, number_of_steps=89,
                                             variable=self.quality_var,
                                             command=self._on_quality)
        self.quality_slider.pack(padx=16, fill="x", pady=(0, 12))

        # 最大宽度
        ctk.CTkLabel(left, text="最大宽度 (0=不限制)",
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16)
        self.max_width_var = tk.StringVar(value="0")
        ctk.CTkEntry(left, textvariable=self.max_width_var,
                     width=80, height=28).pack(padx=16, pady=(4, 12), anchor="w")

        # 输出格式
        ctk.CTkLabel(left, text="输出格式",
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16)
        self.fmt_var = tk.StringVar(value="保持原格式")
        fmt_menu = ctk.CTkOptionMenu(left, variable=self.fmt_var,
                                      values=["保持原格式", "JPG", "PNG", "WEBP"],
                                      width=160)
        fmt_menu.pack(padx=16, pady=(4, 12))

        # 输出目录
        ctk.CTkLabel(left, text="输出目录",
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16)
        self.out_var = tk.StringVar(value="原目录/compressed")
        ctk.CTkEntry(left, textvariable=self.out_var,
                     width=180, height=28).pack(padx=16, pady=(4, 4))
        ctk.CTkButton(left, text="选择目录", height=28, width=160,
                      command=self._pick_outdir).pack(padx=16, pady=(0, 16))

        ctk.CTkFrame(left, height=1, fg_color="#e8e8e8").pack(fill="x", padx=16, pady=4)

        # 操作按钮
        ctk.CTkButton(left, text="添加图片", height=36,
                      command=self._add_files).pack(padx=16, pady=(12, 4), fill="x")
        ctk.CTkButton(left, text="添加文件夹", height=36,
                      command=self._add_folder).pack(padx=16, pady=4, fill="x")
        ctk.CTkButton(left, text="清空列表", height=36,
                      fg_color="#e8e8e8", text_color="#333", hover_color="#ddd",
                      command=self._clear).pack(padx=16, pady=4, fill="x")

        # 右侧
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side="right", fill="both", expand=True, padx=(0, 12), pady=12)

        # 文件列表
        list_frame = ctk.CTkFrame(right, fg_color="white",
                                   border_width=1, border_color="#e8e8e8")
        list_frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", rowheight=26, font=("Microsoft YaHei", 10),
                        background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=("Microsoft YaHei", 10, "bold"))

        cols = ("name", "orig", "new", "ratio", "status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings")
        self.tree.heading("name",   text="文件名")
        self.tree.heading("orig",   text="原始大小")
        self.tree.heading("new",    text="压缩后")
        self.tree.heading("ratio",  text="压缩率")
        self.tree.heading("status", text="状态")

        self.tree.column("name",   width=280, minwidth=150)
        self.tree.column("orig",   width=90,  minwidth=70,  anchor="e")
        self.tree.column("new",    width=90,  minwidth=70,  anchor="e")
        self.tree.column("ratio",  width=80,  minwidth=60,  anchor="center")
        self.tree.column("status", width=90,  minwidth=70,  anchor="center")

        self.tree.tag_configure("done",  foreground="#27ae60")
        self.tree.tag_configure("error", foreground="#e74c3c")
        self.tree.tag_configure("wait",  foreground="#999")

        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # 底部
        bottom = ctk.CTkFrame(right, fg_color="white",
                               border_width=1, border_color="#e8e8e8", height=70)
        bottom.pack(fill="x", pady=(8, 0)); bottom.pack_propagate(False)

        self.progress = ctk.CTkProgressBar(bottom)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=16, pady=(10, 4))

        btn_row = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_row.pack(fill="x", padx=16)

        self.status_label = ctk.CTkLabel(btn_row, text="添加图片后点击「开始压缩」",
                                          font=ctk.CTkFont(size=11), text_color="gray")
        self.status_label.pack(side="left")

        self.compress_btn = ctk.CTkButton(
            btn_row, text="开始压缩", height=32, width=100,
            fg_color="#4f8ef7", hover_color="#3a7de0",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_compress
        )
        self.compress_btn.pack(side="right")

    def _build_tk(self):
        # 极简 tk 备用界面
        root = self.root
        root.configure(bg="#f5f6f8")
        tk.Label(root, text="图片批量压缩工具", bg="#4f8ef7", fg="white",
                 font=("Microsoft YaHei", 14, "bold"), pady=12).pack(fill="x")

        self.quality_var  = tk.IntVar(value=80)
        self.max_width_var = tk.StringVar(value="0")
        self.fmt_var       = tk.StringVar(value="保持原格式")
        self.out_var       = tk.StringVar(value="原目录/compressed")

        ctrl = tk.Frame(root, bg="#f5f6f8")
        ctrl.pack(fill="x", padx=12, pady=8)
        tk.Button(ctrl, text="添加图片",   command=self._add_files,  bg="#4f8ef7", fg="white", relief="flat").pack(side="left", padx=4)
        tk.Button(ctrl, text="添加文件夹", command=self._add_folder, bg="#4f8ef7", fg="white", relief="flat").pack(side="left", padx=4)
        tk.Button(ctrl, text="清空",       command=self._clear,      bg="#e8e8e8", relief="flat").pack(side="left", padx=4)
        tk.Button(ctrl, text="开始压缩",   command=self._start_compress, bg="#27ae60", fg="white", relief="flat").pack(side="right", padx=4)

        cols = ("name", "orig", "new", "ratio", "status")
        self.tree = ttk.Treeview(root, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(fill="both", expand=True, padx=12, pady=4)

        self.status_label = tk.Label(root, text="添加图片后点击「开始压缩」",
                                      bg="#f5f6f8", fg="gray", font=("Microsoft YaHei", 10))
        self.status_label.pack(pady=4)
        self.progress = None
        self.compress_btn = None

    def _on_quality(self, val):
        self.quality_label.configure(text=f"{int(float(val))}%")

    def _pick_outdir(self):
        d = fd.askdirectory()
        if d:
            self.out_var.set(d)

    def _add_files(self):
        files = fd.askopenfilenames(
            title="选择图片",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.webp *.bmp"), ("全部", "*.*")]
        )
        for f in files:
            p = Path(f)
            if p not in self.files and p.suffix.lower() in SUPPORTED:
                self.files.append(p)
        self._refresh_tree_files()

    def _add_folder(self):
        d = fd.askdirectory(title="选择文件夹")
        if not d:
            return
        for f in Path(d).rglob("*"):
            if f.suffix.lower() in SUPPORTED and f not in self.files:
                self.files.append(f)
        self._refresh_tree_files()

    def _clear(self):
        self.files.clear()
        self.tree.delete(*self.tree.get_children())
        self.status_label.configure(text="已清空")
        if self.progress:
            self.progress.set(0)

    def _refresh_tree_files(self):
        self.tree.delete(*self.tree.get_children())
        for p in self.files:
            size = format_bytes(p.stat().st_size)
            self.tree.insert("", "end", iid=str(p),
                             values=(p.name, size, "-", "-", "等待"),
                             tags=("wait",))
        self.status_label.configure(text=f"已添加 {len(self.files)} 张图片")

    def _start_compress(self):
        if not HAS_PIL:
            mb.showerror("缺少依赖",
                         "请先安装 Pillow 库：\npip install Pillow")
            return
        if not self.files:
            mb.showinfo("提示", "请先添加图片")
            return

        quality   = self.quality_var.get()
        max_width = int(self.max_width_var.get() or 0)
        fmt       = self.fmt_var.get()
        out_base  = self.out_var.get()

        if self.compress_btn:
            self.compress_btn.configure(state="disabled")

        def run():
            total  = len(self.files)
            saved  = 0
            orig_t = 0
            new_t  = 0

            for i, src in enumerate(self.files):
                # 决定输出路径
                if out_base == "原目录/compressed":
                    out_dir = src.parent / "compressed"
                else:
                    out_dir = Path(out_base)

                # 决定输出格式
                if fmt == "保持原格式":
                    out_ext = src.suffix
                else:
                    out_ext = "." + fmt.lower()

                dst = out_dir / (src.stem + out_ext)

                self.q.put(("row_status", str(src), "压缩中..."))
                try:
                    orig, new = compress_image(src, dst, quality, max_width)
                    ratio = (1 - new / orig) * 100 if orig > 0 else 0
                    orig_t += orig
                    new_t  += new
                    saved  += (orig - new)
                    self.q.put(("row_done", str(src), orig, new, ratio))
                except Exception as e:
                    self.q.put(("row_error", str(src), str(e)))

                self.q.put(("progress", (i + 1) / total))

            self.q.put(("all_done", orig_t, new_t, saved))

        threading.Thread(target=run, daemon=True).start()

    def _poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                kind = msg[0]
                if kind == "row_status":
                    _, iid, status = msg
                    vals = list(self.tree.item(iid, "values"))
                    vals[4] = status
                    self.tree.item(iid, values=vals)
                elif kind == "row_done":
                    _, iid, orig, new, ratio = msg
                    vals = list(self.tree.item(iid, "values"))
                    vals[1] = format_bytes(orig)
                    vals[2] = format_bytes(new)
                    vals[3] = f"-{ratio:.1f}%"
                    vals[4] = "✓ 完成"
                    self.tree.item(iid, values=vals, tags=("done",))
                elif kind == "row_error":
                    _, iid, err = msg
                    vals = list(self.tree.item(iid, "values"))
                    vals[4] = "✗ 失败"
                    self.tree.item(iid, values=vals, tags=("error",))
                elif kind == "progress":
                    pct = msg[1]
                    if self.progress and HAS_CTK:
                        self.progress.set(pct)
                    self.status_label.configure(text=f"压缩中 {int(pct*100)}%...")
                elif kind == "all_done":
                    _, orig_t, new_t, saved = msg
                    ratio = (1 - new_t / orig_t) * 100 if orig_t > 0 else 0
                    self.status_label.configure(
                        text=f"✅ 全部完成！共节省 {format_bytes(saved)}（压缩率 {ratio:.1f}%）"
                    )
                    if self.compress_btn and HAS_CTK:
                        self.compress_btn.configure(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def mainloop(self):
        self.root.mainloop()


if __name__ == "__main__":
    if not HAS_PIL:
        import subprocess
        print("正在安装 Pillow...")
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow", "-q"])
        print("安装完成，请重新运行程序")
        input("按回车退出...")
        sys.exit(0)

    app = ImageCompressorApp()
    app.mainloop()
