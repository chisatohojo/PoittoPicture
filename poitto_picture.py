# -*- coding: utf-8 -*-
from __future__ import annotations

import shutil
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import Image, ImageOps, ImageTk, UnidentifiedImageError

try:
    from send2trash import send2trash
except Exception:  # pragma: no cover - optional dependency fallback
    send2trash = None


APP_NAME = "ぽいっとピクチャ"
HELP_TEXT = "操作:  ← / A：前へ    → / D / Enter：次へ    Backspace / Delete：ぽいっと削除"
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


def collect_image_paths(folder: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in folder.iterdir()
            if path.is_file() and path.suffix.casefold() in SUPPORTED_EXTENSIONS
        ),
        key=lambda path: path.name.casefold(),
    )


def unique_deleted_path(deleted_dir: Path, source: Path) -> Path:
    candidate = deleted_dir / source.name
    if not candidate.exists():
        return candidate

    stem = source.stem
    suffix = source.suffix
    counter = 1
    while True:
        candidate = deleted_dir / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


class PoittoPictureApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("980x700")
        self.root.minsize(520, 360)
        self.root.configure(bg="#15171d")

        self.folder: Path | None = None
        self.images: list[Path] = []
        self.index = 0
        self.tk_image: ImageTk.PhotoImage | None = None
        self.resize_job: str | None = None

        self._set_window_icon()
        self._build_ui()
        self._bind_keys()

        self.root.withdraw()
        self.root.after(100, self.choose_folder_on_start)

    def _set_window_icon(self) -> None:
        icon_path = resource_path("assets/app_icon.ico")
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except tk.TclError:
                pass

    def _build_ui(self) -> None:
        self.canvas = tk.Canvas(
            self.root,
            bg="#101216",
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._schedule_render)

        footer = tk.Frame(self.root, bg="#20242d", padx=14, pady=10)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.bind("<Configure>", self._update_footer_wrap)

        self.info_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="")

        self.info_label = tk.Label(
            footer,
            textvariable=self.info_var,
            fg="#f4f6fb",
            bg="#20242d",
            anchor="w",
            justify=tk.LEFT,
            font=("Yu Gothic UI", 11),
        )
        self.info_label.pack(fill=tk.X)

        self.help_label = tk.Label(
            footer,
            text=HELP_TEXT,
            fg="#ffe8f3",
            bg="#2a303b",
            anchor="w",
            justify=tk.LEFT,
            font=("Yu Gothic UI", 10, "bold"),
            padx=10,
            pady=6,
        )
        self.help_label.pack(fill=tk.X, pady=(7, 0))

        self.status_label = tk.Label(
            footer,
            textvariable=self.status_var,
            fg="#aeb7c6",
            bg="#20242d",
            anchor="w",
            justify=tk.LEFT,
            font=("Yu Gothic UI", 9),
        )
        self.status_label.pack(fill=tk.X, pady=(4, 0))

    def _update_footer_wrap(self, event: tk.Event) -> None:
        wrap_width = max(event.width - 28, 240)
        self.info_label.configure(wraplength=wrap_width)
        self.help_label.configure(wraplength=wrap_width)
        self.status_label.configure(wraplength=wrap_width)

    def _bind_keys(self) -> None:
        for key in ("<Right>", "<Return>", "<Key-d>", "<Key-D>"):
            self.root.bind(key, self.show_next)
        for key in ("<Left>", "<Key-a>", "<Key-A>"):
            self.root.bind(key, self.show_previous)
        for key in ("<BackSpace>", "<Delete>"):
            self.root.bind(key, self.delete_current)

    def choose_folder_on_start(self) -> None:
        folder = filedialog.askdirectory(title="画像フォルダを選択")
        if not folder:
            self.root.destroy()
            return

        self.folder = Path(folder)
        self.images = collect_image_paths(self.folder)
        self.index = 0

        self.root.deiconify()
        self.root.focus_force()
        self.root.after(20, self.render_current)

        if not self.images:
            self.status_var.set("画像がありません")
        else:
            self.status_var.set(str(self.folder))

    def show_next(self, event: tk.Event | None = None) -> str:
        if self.images and self.index < len(self.images) - 1:
            self.index += 1
            self.render_current()
        return "break"

    def show_previous(self, event: tk.Event | None = None) -> str:
        if self.images and self.index > 0:
            self.index -= 1
            self.render_current()
        return "break"

    def delete_current(self, event: tk.Event | None = None) -> str:
        if not self.images:
            return "break"

        path = self.images[self.index]
        moved = False
        error_message = ""

        if not path.exists():
            moved = True
            error_message = "ファイルが見つからないため一覧から外しました"
        else:
            if send2trash is not None:
                try:
                    send2trash(str(path))
                    moved = True
                except Exception as exc:
                    error_message = f"ゴミ箱へ移動できませんでした: {exc}"

            if not moved:
                try:
                    moved = self._move_to_deleted_folder(path)
                except Exception as exc:
                    error_message = f"_deleted への移動に失敗しました: {exc}"

        if moved or not path.exists():
            deleted_name = path.name
            del self.images[self.index]
            if self.index >= len(self.images):
                self.index = max(0, len(self.images) - 1)

            self.status_var.set(f"ぽいっとしました: {deleted_name}")
            if error_message and self.images:
                self.status_var.set(f"ぽいっとしました: {deleted_name} / {error_message}")
            self.render_current()
        else:
            messagebox.showerror(APP_NAME, error_message or "削除できませんでした")
            self.status_var.set(error_message or "削除できませんでした")

        return "break"

    def _move_to_deleted_folder(self, path: Path) -> bool:
        if self.folder is None:
            raise RuntimeError("フォルダが選択されていません")

        deleted_dir = self.folder / "_deleted"
        deleted_dir.mkdir(exist_ok=True)
        destination = unique_deleted_path(deleted_dir, path)
        shutil.move(str(path), str(destination))
        return True

    def _schedule_render(self, event: tk.Event | None = None) -> None:
        if self.resize_job is not None:
            self.root.after_cancel(self.resize_job)
        self.resize_job = self.root.after(80, self.render_current)

    def render_current(self) -> None:
        self.resize_job = None
        self.canvas.delete("all")
        self.tk_image = None

        if not self.images:
            self.info_var.set("0 / 0")
            self._draw_center_text("画像がありません")
            if not self.status_var.get():
                self.status_var.set("画像がありません")
            return

        self.index = min(max(self.index, 0), len(self.images) - 1)
        path = self.images[self.index]
        self.info_var.set(f"{self.index + 1} / {len(self.images)}    {path.name}")

        try:
            image = self._load_image(path)
        except (OSError, UnidentifiedImageError, ValueError) as exc:
            self._draw_center_text("画像を読み込めません")
            self.status_var.set(f"{path.name}: {exc}")
            return

        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)
        target_width, target_height = self._fit_size(
            image.width,
            image.height,
            canvas_width,
            canvas_height,
        )

        if (target_width, target_height) != image.size:
            image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

        self.tk_image = ImageTk.PhotoImage(image)
        self.canvas.create_image(
            canvas_width // 2,
            canvas_height // 2,
            image=self.tk_image,
            anchor=tk.CENTER,
        )

    def _load_image(self, path: Path) -> Image.Image:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA")
            else:
                image = image.copy()
        return image

    def _fit_size(
        self,
        image_width: int,
        image_height: int,
        canvas_width: int,
        canvas_height: int,
    ) -> tuple[int, int]:
        padding = 24
        available_width = max(canvas_width - padding, 1)
        available_height = max(canvas_height - padding, 1)
        scale = min(
            available_width / image_width,
            available_height / image_height,
            2.0,
        )
        scale = max(scale, 0.01)
        return max(int(image_width * scale), 1), max(int(image_height * scale), 1)

    def _draw_center_text(self, text: str) -> None:
        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)
        self.canvas.create_text(
            canvas_width // 2,
            canvas_height // 2,
            text=text,
            fill="#d8dde8",
            font=("Yu Gothic UI", 18, "bold"),
            anchor=tk.CENTER,
        )


def main() -> None:
    root = tk.Tk()
    PoittoPictureApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
