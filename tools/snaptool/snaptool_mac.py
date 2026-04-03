"""
截图工具 - SnapTool (macOS 版)
功能：区域截图、标注（箭头/文字/矩形/模糊/画笔）、贴图到桌面、保存
快捷键：F1 截图，ESC 取消，Ctrl+Z 撤销，Ctrl+S 保存
"""
import tkinter as tk
from tkinter import ttk, colorchooser, simpledialog
import os, sys, math
from PIL import Image, ImageTk, ImageGrab, ImageFilter, ImageDraw

try:
    from pynput import keyboard as kb
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "pynput", "-q"])
    from pynput import keyboard as kb

# ── 主题色 ──
BG    = "#1e1f22"
BG2   = "#2b2d30"
BG3   = "#3c3f41"
ACCENT= "#4f8ef7"
GREEN = "#3dba78"
RED   = "#e05c5c"
BORDER= "#444"
FG    = "#e0e0e0"
FG_DIM= "#888"
FONT  = ("Helvetica", 10)
FONT_B= ("Helvetica", 10, "bold")


def make_round_btn(parent, text, bg, fg, command, padx=14, pady=5):
    btn = tk.Label(parent, text=text, bg=bg, fg=fg,
                   font=FONT_B, padx=padx, pady=pady, cursor="hand2")
    btn.bind("<Button-1>", lambda e: command())
    btn.bind("<Enter>", lambda e: btn.config(bg=_lighten(bg)))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def _lighten(hex_color):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"#{min(255,r+30):02x}{min(255,g+30):02x}{min(255,b+30):02x}"


# ── 全屏选区遮罩 ──
class SelectionOverlay:
    def __init__(self, on_selected):
        self.on_selected = on_selected
        self.start_x = self.start_y = 0
        self.cur_x = self.cur_y = 0
        self.dragging = False

        self.screen_img = ImageGrab.grab()
        self.screen_w, self.screen_h = self.screen_img.size

        dim = self.screen_img.copy().convert("RGBA")
        overlay = Image.new("RGBA", dim.size, (0, 0, 0, 150))
        self.dim_img = Image.alpha_composite(dim, overlay).convert("RGB")

        self.root = tk.Toplevel()
        self.root.attributes("-fullscreen", True)
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.configure(cursor="crosshair")

        self.canvas = tk.Canvas(self.root, bg="black",
                                highlightthickness=0,
                                width=self.screen_w, height=self.screen_h)
        self.canvas.pack(fill="both", expand=True)

        self.bg_photo = ImageTk.PhotoImage(self.dim_img)
        self.bg_item = self.canvas.create_image(0, 0, anchor="nw", image=self.bg_photo)

        self.root.attributes("-alpha", 1.0)
        self.canvas.bind("<ButtonPress-1>",   self.on_press)
        self.canvas.bind("<B1-Motion>",        self.on_drag)
        self.canvas.bind("<ButtonRelease-1>",  self.on_release)
        self.root.bind("<Escape>", lambda e: self.cancel())
        self.root.focus_force()

    def on_press(self, e):
        self.start_x, self.start_y = e.x, e.y
        self.cur_x,   self.cur_y   = e.x, e.y
        self.dragging = True

    def on_drag(self, e):
        if not self.dragging:
            return
        self.cur_x, self.cur_y = e.x, e.y
        x1 = min(self.start_x, e.x)
        y1 = min(self.start_y, e.y)
        x2 = max(self.start_x, e.x)
        y2 = max(self.start_y, e.y)

        composite = self.dim_img.copy()
        if x2 > x1 and y2 > y1:
            clear_patch = self.screen_img.crop((x1, y1, x2, y2))
            composite.paste(clear_patch, (x1, y1))

        draw = ImageDraw.Draw(composite)
        draw.rectangle([x1, y1, x2, y2], outline="#4f8ef7", width=2)
        draw.rectangle([x1-1, y1-1, x2+1, y2+1], outline="#ffffff", width=1)

        w, h = x2 - x1, y2 - y1
        label = f" {w} × {h} "
        tx = x1 + 4
        ty = y1 - 22 if y1 > 70 else y2 + 6
        draw.rectangle([tx-2, ty-2, tx + len(label)*7, ty+16], fill="#1e1f22")
        draw.text((tx, ty), label, fill="#4f8ef7")
        draw.rectangle([0, 0, self.screen_w, 44], fill="#1e1f22")
        draw.text((self.screen_w // 2, 12),
                  "拖拽选择截图区域    |    ESC 取消",
                  fill="#e0e0e0", anchor="mt")

        self.bg_photo = ImageTk.PhotoImage(composite)
        self.canvas.itemconfig(self.bg_item, image=self.bg_photo)

    def on_release(self, e):
        self.dragging = False
        x1 = min(self.start_x, self.cur_x)
        y1 = min(self.start_y, self.cur_y)
        x2 = max(self.start_x, self.cur_x)
        y2 = max(self.start_y, self.cur_y)
        if x2 - x1 < 5 or y2 - y1 < 5:
            self.cancel()
            return
        region = self.screen_img.crop((x1, y1, x2, y2))
        self.root.destroy()
        self.on_selected(region)

    def cancel(self):
        self.root.destroy()


# ── 标注编辑器 ──
class AnnotationEditor:
    TOOLS = [
        ("rect",  "▭", "矩形"),
        ("arrow", "↗", "箭头"),
        ("pen",   "✏", "画笔"),
        ("text",  "T",  "文字"),
        ("blur",  "⬜", "模糊"),
    ]

    def __init__(self, image: Image.Image, app):
        self.app         = app
        self.orig        = image.copy()
        self.base        = image.copy()
        self.annotations = []
        self.tool        = "rect"
        self.color       = RED
        self.line_width  = 3
        self.drag_start  = None
        self.preview_ids = []
        self.pen_points  = []
        self._build_window()

    def _build_window(self):
        self.win = tk.Toplevel()
        self.win.title("SnapTool")
        self.win.configure(bg=BG)
        self.win.attributes("-topmost", True)
        self.win.resizable(True, True)
        self._build_toolbar()
        self._build_canvas()
        self.win.bind("<Command-z>", lambda e: self.undo())
        self.win.bind("<Control-z>", lambda e: self.undo())
        self.win.bind("<Command-s>", lambda e: self.save())
        self.win.bind("<Control-s>", lambda e: self.save())
        self.win.bind("<Escape>",    lambda e: self.win.destroy())
        self._refresh_canvas()
        self.set_tool("rect")
        self.win.update_idletasks()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        ww = self.win.winfo_width()
        wh = self.win.winfo_height()
        self.win.geometry(f"+{(sw-ww)//2}+{(sh-wh)//2}")

    def _build_toolbar(self):
        bar = tk.Frame(self.win, bg=BG2, pady=0)
        bar.pack(fill="x", side="top")
        tk.Label(bar, text="✂ SnapTool", bg=BG2, fg=ACCENT,
                 font=("Helvetica", 11, "bold"), padx=14).pack(side="left")
        tk.Frame(bar, bg=BORDER, width=1).pack(side="left", fill="y", pady=6, padx=4)

        self.tool_btns = {}
        for key, icon, label in self.TOOLS:
            f = tk.Frame(bar, bg=BG2)
            f.pack(side="left", padx=1, pady=6)
            btn = tk.Label(f, text=f"{icon} {label}", bg=BG3, fg=FG,
                           font=FONT, padx=10, pady=5, cursor="hand2")
            btn.pack()
            btn.bind("<Button-1>", lambda e, k=key: self.set_tool(k))
            btn.bind("<Enter>",    lambda e, b=btn, k=key: b.config(
                bg=GREEN if self.tool==k else _lighten(BG3)))
            btn.bind("<Leave>",    lambda e, b=btn, k=key: b.config(
                bg=GREEN if self.tool==k else BG3))
            self.tool_btns[key] = btn

        tk.Frame(bar, bg=BORDER, width=1).pack(side="left", fill="y", pady=6, padx=6)
        for c in [RED, "#f0a500", GREEN, ACCENT, "#ffffff"]:
            dot = tk.Label(bar, bg=c, width=2, cursor="hand2", relief="flat", pady=10)
            dot.pack(side="left", padx=2)
            dot.bind("<Button-1>", lambda e, col=c: self._set_color(col))

        self.color_preview = tk.Label(bar, bg=self.color, text=" 自定义 ",
                                      fg="white", font=FONT, cursor="hand2", pady=5, padx=6)
        self.color_preview.pack(side="left", padx=(4, 8))
        self.color_preview.bind("<Button-1>", lambda e: self.pick_color())

        tk.Frame(bar, bg=BORDER, width=1).pack(side="left", fill="y", pady=6, padx=4)
        tk.Label(bar, text="线宽", bg=BG2, fg=FG_DIM, font=FONT, padx=4).pack(side="left")
        self.width_var = tk.IntVar(value=3)
        for w in [1, 2, 3, 5, 8]:
            rb = tk.Radiobutton(bar, text=str(w), variable=self.width_var,
                                value=w, bg=BG2, fg=FG, selectcolor=BG2,
                                activebackground=BG2, activeforeground=ACCENT,
                                font=FONT, indicatoron=False, relief="flat", padx=6, pady=5)
            rb.pack(side="left", padx=1)

        tk.Frame(bar, bg=BORDER, width=1).pack(side="left", fill="y", pady=6, padx=6)
        undo_btn = tk.Label(bar, text="↩ 撤销", bg=BG2, fg=FG_DIM,
                            font=FONT, padx=10, pady=5, cursor="hand2")
        undo_btn.pack(side="left", padx=2)
        undo_btn.bind("<Button-1>", lambda e: self.undo())
        undo_btn.bind("<Enter>", lambda e: undo_btn.config(fg=FG))
        undo_btn.bind("<Leave>", lambda e: undo_btn.config(fg=FG_DIM))

        for text, bg, cmd in [
            ("📋 复制", BG3,   self.copy_to_clipboard),
            ("💾 保存", GREEN,  self.save),
            ("📌 贴图", ACCENT, self.pin),
        ]:
            btn = make_round_btn(bar, text, bg, "white", cmd, padx=12, pady=5)
            btn.pack(side="right", padx=3, pady=6)

    def _build_canvas(self):
        img_w, img_h = self.base.size
        canvas_w = min(img_w, self.win.winfo_screenwidth() - 60)
        canvas_h = min(img_h, self.win.winfo_screenheight() - 120)
        frame = tk.Frame(self.win, bg=BG, padx=8, pady=8)
        frame.pack(fill="both", expand=True)
        border = tk.Frame(frame, bg=BORDER, padx=1, pady=1)
        border.pack(fill="both", expand=True)
        inner = tk.Frame(border, bg=BG)
        inner.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(inner, bg="#111", highlightthickness=0,
                                width=canvas_w, height=canvas_h, cursor="crosshair")
        sx = ttk.Scrollbar(inner, orient="horizontal", command=self.canvas.xview)
        sy = ttk.Scrollbar(inner, orient="vertical",   command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=sx.set, yscrollcommand=sy.set,
                              scrollregion=(0, 0, img_w, img_h))
        sy.pack(side="right", fill="y")
        sx.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>",   self.on_press)
        self.canvas.bind("<B1-Motion>",        self.on_drag)
        self.canvas.bind("<ButtonRelease-1>",  self.on_release)
        status = tk.Frame(self.win, bg=BG2, pady=3)
        status.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(
            value=f"图片尺寸：{img_w} × {img_h}  |  F1 新截图  |  ⌘Z 撤销  |  ⌘S 保存")
        tk.Label(status, textvariable=self.status_var, bg=BG2, fg=FG_DIM,
                 font=("Helvetica", 9), padx=12).pack(side="left")

    def set_tool(self, t):
        self.tool = t
        for key, btn in self.tool_btns.items():
            btn.config(bg=GREEN if key == t else BG3,
                       fg="white" if key == t else FG)

    def _set_color(self, c):
        self.color = c
        self.color_preview.config(bg=c)

    def pick_color(self):
        c = colorchooser.askcolor(color=self.color, title="选择颜色")[1]
        if c:
            self._set_color(c)

    def _canvas_xy(self, e):
        return int(self.canvas.canvasx(e.x)), int(self.canvas.canvasy(e.y))

    def _ask_text(self):
        result = [None, 24]
        dlg = tk.Toplevel(self.win)
        dlg.title("输入文字")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.grab_set()
        tk.Label(dlg, text="文字内容", bg=BG, fg=FG, font=FONT).grid(
            row=0, column=0, padx=12, pady=(14,4), sticky="w")
        entry = tk.Entry(dlg, font=("Helvetica", 12), bg=BG3, fg=FG,
                         insertbackground=FG, relief="flat", width=24, bd=6)
        entry.grid(row=1, column=0, columnspan=2, padx=12, pady=(0,10), sticky="ew")
        entry.focus_set()
        tk.Label(dlg, text="字号", bg=BG, fg=FG, font=FONT).grid(
            row=2, column=0, padx=12, pady=(0,4), sticky="w")
        size_frame = tk.Frame(dlg, bg=BG)
        size_frame.grid(row=3, column=0, columnspan=2, padx=12, pady=(0,12), sticky="w")
        size_var = tk.IntVar(value=24)
        for s in [14, 18, 24, 32, 48]:
            tk.Radiobutton(size_frame, text=str(s), variable=size_var, value=s,
                           bg=BG, fg=FG, selectcolor=BG, activebackground=BG,
                           activeforeground=ACCENT, font=FONT, indicatoron=False,
                           relief="flat", padx=8, pady=4, cursor="hand2").pack(side="left", padx=2)

        def confirm():
            txt = entry.get().strip()
            if txt:
                result[0] = txt
                result[1] = size_var.get()
            dlg.destroy()

        btn_row = tk.Frame(dlg, bg=BG)
        btn_row.grid(row=4, column=0, columnspan=2, pady=(0,12))
        make_round_btn(btn_row, "确认", GREEN, "white", confirm, padx=20, pady=5).pack(side="left", padx=6)
        make_round_btn(btn_row, "取消", BG3,   FG,      dlg.destroy, padx=20, pady=5).pack(side="left", padx=6)
        entry.bind("<Return>", lambda e: confirm())
        entry.bind("<Escape>", lambda e: dlg.destroy())
        dlg.update_idletasks()
        pw = self.win.winfo_x() + self.win.winfo_width()  // 2
        ph = self.win.winfo_y() + self.win.winfo_height() // 2
        dlg.geometry(f"+{pw - dlg.winfo_width()//2}+{ph - dlg.winfo_height()//2}")
        dlg.wait_window()
        return result[0], result[1]

    def on_press(self, e):
        self.drag_start = self._canvas_xy(e)
        self.pen_points = [self.drag_start]

    def on_drag(self, e):
        if not self.drag_start:
            return
        for pid in self.preview_ids:
            self.canvas.delete(pid)
        self.preview_ids = []
        cur  = self._canvas_xy(e)
        x1, y1 = self.drag_start
        x2, y2 = cur
        lw = self.width_var.get()
        if self.tool == "rect":
            self.preview_ids.append(self.canvas.create_rectangle(
                x1, y1, x2, y2, outline=self.color, width=lw))
        elif self.tool == "arrow":
            self.preview_ids.append(self.canvas.create_line(
                x1, y1, x2, y2, fill=self.color, width=lw,
                arrow=tk.LAST, arrowshape=(14, 16, 6)))
        elif self.tool == "blur":
            self.preview_ids.append(self.canvas.create_rectangle(
                x1, y1, x2, y2, outline="#aaa", width=1, dash=(5, 3)))
        elif self.tool == "pen":
            self.pen_points.append(cur)
            if len(self.pen_points) >= 2:
                p1, p2 = self.pen_points[-2], self.pen_points[-1]
                self.preview_ids.append(self.canvas.create_line(
                    p1[0], p1[1], p2[0], p2[1],
                    fill=self.color, width=lw, capstyle="round", joinstyle="round"))

    def on_release(self, e):
        if not self.drag_start:
            return
        for pid in self.preview_ids:
            self.canvas.delete(pid)
        self.preview_ids = []
        cur  = self._canvas_xy(e)
        x1, y1 = self.drag_start
        x2, y2 = cur
        lw = self.width_var.get()
        if self.tool == "text":
            txt, size = self._ask_text()
            if txt:
                self.annotations.append({
                    "type": "text", "x": x1, "y": y1,
                    "text": txt, "color": self.color, "lw": lw, "size": size})
                self._redraw()
        elif self.tool == "blur":
            rx1, ry1 = min(x1,x2), min(y1,y2)
            rx2, ry2 = max(x1,x2), max(y1,y2)
            if rx2-rx1 > 4 and ry2-ry1 > 4:
                self.annotations.append({
                    "type": "blur", "x1": rx1, "y1": ry1, "x2": rx2, "y2": ry2})
                self._redraw()
        elif self.tool == "pen":
            if len(self.pen_points) >= 2:
                self.annotations.append({
                    "type": "pen", "points": list(self.pen_points),
                    "color": self.color, "lw": lw})
                self._redraw()
        else:
            if abs(x2-x1) > 2 or abs(y2-y1) > 2:
                self.annotations.append({
                    "type": self.tool, "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "color": self.color, "lw": lw})
                self._redraw()
        self.drag_start = None
        self.pen_points = []

    def _redraw(self):
        img  = self.orig.copy()
        draw = ImageDraw.Draw(img)
        for ann in self.annotations:
            t = ann["type"]
            if t == "rect":
                for i in range(ann["lw"]):
                    draw.rectangle([ann["x1"]-i, ann["y1"]-i,
                                    ann["x2"]+i, ann["y2"]+i], outline=ann["color"])
            elif t == "arrow":
                self._pil_arrow(draw, ann)
            elif t == "text":
                try:
                    from PIL import ImageFont
                    font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",
                                             ann.get("size", 24))
                except Exception:
                    font = None
                draw.text((ann["x"], ann["y"]), ann["text"],
                          fill=ann["color"], font=font)
            elif t == "blur":
                region  = img.crop((ann["x1"], ann["y1"], ann["x2"], ann["y2"]))
                blurred = region.filter(ImageFilter.GaussianBlur(12))
                img.paste(blurred, (ann["x1"], ann["y1"]))
                draw = ImageDraw.Draw(img)
            elif t == "pen":
                pts = ann["points"]
                for i in range(len(pts)-1):
                    draw.line([pts[i], pts[i+1]], fill=ann["color"], width=ann["lw"])
        self.base = img
        self._refresh_canvas()

    def _pil_arrow(self, draw, ann):
        x1, y1, x2, y2 = ann["x1"], ann["y1"], ann["x2"], ann["y2"]
        lw, color = ann["lw"], ann["color"]
        draw.line([(x1,y1),(x2,y2)], fill=color, width=lw)
        angle = math.atan2(y2-y1, x2-x1)
        size  = max(12, lw * 4)
        for da in (0.4, -0.4):
            ex = x2 - size * math.cos(angle - da)
            ey = y2 - size * math.sin(angle - da)
            draw.line([(x2,y2),(int(ex),int(ey))], fill=color, width=lw)

    def _refresh_canvas(self):
        self.photo = ImageTk.PhotoImage(self.base)
        self.canvas.delete("img")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo, tags="img")

    def undo(self):
        if self.annotations:
            self.annotations.pop()
            self._redraw()

    def save(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")],
            title="保存截图")
        if not path:
            return
        self.base.save(path)
        self._toast(f"已保存：{os.path.basename(path)}", GREEN)

    def copy_to_clipboard(self):
        import subprocess, tempfile
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                tmp = f.name
            self.base.save(tmp)
            subprocess.run(
                ["osascript", "-e",
                 f'set the clipboard to (read (POSIX file "{tmp}") as «class PNGf»)'],
                check=True)
            os.unlink(tmp)
            self._toast("已复制到剪贴板", ACCENT)
        except Exception as ex:
            self._toast(f"复制失败：{ex}", RED)

    def pin(self):
        img = self.base.copy()
        self.win.destroy()
        PinWindow(img)

    def _toast(self, msg, color=GREEN):
        t = tk.Toplevel(self.win)
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        t.configure(bg=BG2)
        tk.Label(t, text=f"  {msg}  ", bg=color, fg="white",
                 font=FONT_B, pady=8, padx=4).pack()
        wx = self.win.winfo_x() + 20
        wy = self.win.winfo_y() + self.win.winfo_height() - 60
        t.geometry(f"+{wx}+{wy}")
        t.after(2200, t.destroy)


# ── 贴图悬浮窗 ──
class PinWindow:
    def __init__(self, image: Image.Image):
        self.image = image
        self.scale = 1.0
        self.win = tk.Toplevel()
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        outer = tk.Frame(self.win, bg=BORDER, padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(outer, highlightthickness=0, cursor="fleur")
        self.canvas.pack(fill="both", expand=True)
        self._render()
        self.canvas.bind("<ButtonPress-1>",  self._drag_start)
        self.canvas.bind("<B1-Motion>",       self._drag_move)
        self.canvas.bind("<ButtonPress-2>",   self._context)
        self.canvas.bind("<ButtonPress-3>",   self._context)
        self.canvas.bind("<MouseWheel>",      self._on_scroll)
        self.canvas.bind("<Double-Button-1>", lambda e: self._reset_scale())
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        w, h = image.size
        self.win.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    def _render(self):
        w = max(10, int(self.image.width  * self.scale))
        h = max(10, int(self.image.height * self.scale))
        resized    = self.image.resize((w, h), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)
        self.canvas.config(width=w, height=h)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        self.win.geometry(f"{w+2}x{h+2}")

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag_move(self, e):
        x = self.win.winfo_x() + e.x - self._dx
        y = self.win.winfo_y() + e.y - self._dy
        self.win.geometry(f"+{x}+{y}")

    def _on_scroll(self, e):
        self.scale = min(4.0, self.scale * 1.1) if e.delta > 0 \
                     else max(0.1, self.scale / 1.1)
        self._render()

    def _reset_scale(self):
        self.scale = 1.0
        self._render()

    def _context(self, e):
        menu = tk.Menu(self.win, tearoff=0, bg=BG2, fg=FG,
                       activebackground=ACCENT, activeforeground="white")
        menu.add_command(label="关闭贴图",    command=self.win.destroy)
        menu.add_command(label="恢复原始大小", command=self._reset_scale)
        menu.add_separator()
        for label, val in [("不透明 100%", 1.0), ("半透明 75%", 0.75),
                            ("半透明 50%", 0.5),  ("半透明 25%", 0.25)]:
            menu.add_command(label=label,
                             command=lambda v=val: self.win.attributes("-alpha", v))
        try:
            menu.tk_popup(e.x_root, e.y_root)
        finally:
            menu.grab_release()


# ── 主程序 ──
class SnapToolApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self._capturing = False
        self._hint_win  = None
        self._show_hint()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.mainloop()

    def _show_hint(self):
        if self._hint_win and self._hint_win.winfo_exists():
            self._hint_win.deiconify()
            self._hint_win.lift()
            return
        win = tk.Toplevel(self.root)
        self._hint_win = win
        win.title("SnapTool")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.attributes("-topmost", True)

        header = tk.Frame(win, bg=ACCENT, pady=16)
        header.pack(fill="x")
        tk.Label(header, text="✂  SnapTool", bg=ACCENT, fg="white",
                 font=("Helvetica", 18, "bold")).pack()
        tk.Label(header, text="轻量截图 · 标注 · 贴图工具",
                 bg=ACCENT, fg="#d0e8ff", font=("Helvetica", 10)).pack()

        shortcuts = tk.Frame(win, bg=BG, padx=24, pady=16)
        shortcuts.pack(fill="x")
        rows = [
            ("F1",    "区域截图"),
            ("ESC",   "取消截图"),
            ("⌘Z",    "撤销标注"),
            ("⌘S",    "保存截图"),
            ("滚轮",  "缩放贴图"),
            ("右键贴图", "菜单（关闭/透明度）"),
        ]
        for i, (k, v) in enumerate(rows):
            row = tk.Frame(shortcuts, bg=BG2 if i%2==0 else BG, pady=7, padx=12)
            row.pack(fill="x")
            tk.Label(row, text=k, bg=row["bg"], fg=ACCENT,
                     font=("Courier", 10, "bold"), width=12, anchor="w").pack(side="left")
            tk.Label(row, text=v, bg=row["bg"], fg=FG, font=FONT).pack(side="left")

        btn_frame = tk.Frame(win, bg=BG, pady=16)
        btn_frame.pack(fill="x", padx=24)

        def start_and_close():
            self._start_hotkeys()
            win.destroy()

        btn = make_round_btn(btn_frame, "开始使用  →", ACCENT, "white",
                             start_and_close, padx=30, pady=8)
        btn.pack()
        win.protocol("WM_DELETE_WINDOW", start_and_close)

        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        w  = win.winfo_width()
        h  = win.winfo_height()
        win.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    def _start_hotkeys(self):
        import threading, time

        def listen():
            def on_press(key):
                try:
                    if key == kb.Key.f1 and not self._capturing:
                        self.root.after(0, self.start_capture)
                except Exception:
                    pass
            with kb.Listener(on_press=on_press) as listener:
                listener.join()

        t = threading.Thread(target=listen, daemon=True)
        t.start()
        import time
        time.sleep(0.05)

    def start_capture(self):
        self._capturing = True
        self.root.after(150, self._open_overlay)

    def _open_overlay(self):
        try:
            SelectionOverlay(self._on_captured)
        except Exception:
            self._capturing = False

    def _on_captured(self, region):
        self._capturing = False
        self.root.after(0, lambda: AnnotationEditor(region, self))

    def quit(self):
        self.root.destroy()


if __name__ == "__main__":
    SnapToolApp()
