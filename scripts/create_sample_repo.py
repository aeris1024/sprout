"""Create a sample Sprout repository for trying the CLI and GUI.

Usage: uv run python scripts/create_sample_repo.py <empty-or-new-folder>
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

GUIDE = Path(__file__).with_name("sample_repo_guide.md")
SPROUT = "import sys; from sprout.cli import main; sys.exit(main())"
POSTER_SIZE = (600, 800)
THUMBNAIL_SIZE = (240, 320)
SPRING = {"sky": "#f4e8c8", "ground": "#8a6a4a", "leaf": "#6f9e4f", "text": "#3d4a2c"}
BRIGHT = {"sky": "#cdeaf2", "ground": "#a5784c", "leaf": "#5fb54a", "text": "#27502c"}
NIGHT = {"sky": "#1f2a52", "ground": "#3b3350", "leaf": "#8fd07a", "text": "#f2eeb8"}
BRIEF = """# 春の芽吹きマルシェ ポスター

- サイズ: A2 縦
- 掲出: 3月1日から駅前掲示板
- 必須要素: イベント名、芽のモチーフ、ロゴ
"""
FEEDBACK = """# クライアントからの修正依頼

- タイトルをもう少し大きく
- 芽をひとまわり大きく
"""
STL = """solid stand
facet normal 0 0 1
outer loop
vertex 0 0 0
vertex 40 0 0
vertex 0 60 0
endloop
endfacet
endsolid stand
"""


@dataclass
class Sprout:
    root: Path

    def run(self, *args: str) -> str:
        env = {**os.environ, "PYTHONUTF8": "1"}
        result = subprocess.run(
            [sys.executable, "-c", SPROUT, *args],
            cwd=self.root,
            env=env,
            capture_output=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"sprout {' '.join(args)} failed: {result.stderr or result.stdout}"
            )
        return result.stdout

    def json(self, *args: str) -> Any:
        return json.loads(self.run(*args, "--json"))


def font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    return ImageFont.load_default(size=size)


def draw_poster(
    colors: dict[str, str],
    title: str | None = None,
    title_size: int = 56,
    leaf_scale: float = 1.0,
    logo: bool = False,
    stars: bool = False,
) -> Image.Image:
    width, height = POSTER_SIZE
    image = Image.new("RGB", POSTER_SIZE, colors["sky"])
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, height - 180, width, height), fill=colors["ground"])
    center = width // 2
    stem_top = height - 180 - int(190 * leaf_scale)
    draw.line((center, height - 180, center, stem_top), fill=colors["leaf"], width=14)
    leaf_width = int(150 * leaf_scale)
    leaf_height = int(80 * leaf_scale)
    draw.ellipse(
        (center - leaf_width, stem_top - leaf_height, center, stem_top + leaf_height // 2),
        fill=colors["leaf"],
    )
    draw.ellipse(
        (center, stem_top - leaf_height, center + leaf_width, stem_top + leaf_height // 2),
        fill=colors["leaf"],
    )
    if stars:
        for index in range(24):
            x = (index * 97 + 31) % width
            y = (index * 53 + 17) % (height - 400)
            draw.ellipse((x, y, x + 5, y + 5), fill=colors["text"])
    if title:
        draw.text((center, 90), title, fill=colors["text"], font=font(title_size), anchor="mm")
    if logo:
        image.paste(draw_logo(colors), (width - 110, height - 110))
    return image


def draw_logo(colors: dict[str, str]) -> Image.Image:
    image = Image.new("RGB", (80, 80), colors["leaf"])
    ImageDraw.Draw(image).text(
        (40, 40), "S", fill="#ffffff", font=font(52), anchor="mm"
    )
    return image


def write_wav(path: Path, notes: tuple[float, ...]) -> None:
    rate = 8000
    frames = bytearray()
    for frequency in notes:
        for sample in range(rate // 5):
            value = math.sin(2 * math.pi * frequency * sample / rate)
            frames += struct.pack("<h", int(value * 12000))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(bytes(frames))


class SampleBuilder:
    def __init__(self, root: Path, attachments: Path) -> None:
        self.root = root
        self.attachments = attachments
        self.sprout = Sprout(root)

    def write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_palette(self, colors: dict[str, str]) -> None:
        self.write("palette.json", json.dumps(colors, indent=2) + "\n")

    def save_poster(self, image: Image.Image) -> Path:
        image.save(self.root / "poster.png")
        thumbnail = self.attachments / "thumbnail.png"
        image.resize(THUMBNAIL_SIZE).save(thumbnail)
        return thumbnail

    def commit(self, message: str, thumbnail: Path | None = None) -> str:
        args = ["commit", "-m", message]
        if thumbnail:
            args += ["--thumbnail", str(thumbnail)]
        return self.sprout.json(*args)["id"]

    def build(self) -> None:
        sprout = self.sprout
        sprout.run("init")
        palette_commit, reviewed = self.build_main()
        self.add_previews(reviewed)
        self.build_side_branches(palette_commit, reviewed)
        sprout.run("switch", "main")
        self.leave_working_state()

    def build_main(self) -> tuple[str, str]:
        sprout = self.sprout
        self.write(".sproutignore", "# 生成物とガイドは追跡しない\ncache/\n*.tmp\nGUIDE.md\n")
        self.write("brief.md", BRIEF)
        self.write_palette(SPRING)
        thumbnail = self.save_poster(draw_poster(SPRING))
        sprout.run("track", ".sproutignore", "brief.md", "palette.json", "poster.png")
        draft = self.commit("ラフ案を作成", thumbnail)
        sprout.run("tag", "first-draft", draft, "-m", "初稿")

        self.write_palette(BRIGHT)
        palette_commit = self.commit(
            "配色を春らしく調整", self.save_poster(draw_poster(BRIGHT))
        )

        logo = self.root / "assets" / "logo.png"
        logo.parent.mkdir()
        draw_logo(BRIGHT).save(logo)
        write_wav(self.root / "audio" / "jingle.wav", (523.25, 659.25, 783.99))
        sprout.run("track", "assets", "audio")
        added = self.commit(
            "ロゴとジングルを追加",
            self.save_poster(draw_poster(BRIGHT, "SPRING MARKET", logo=True)),
        )
        sprout.run("label", added, "wip")

        self.write("notes/feedback.md", FEEDBACK)
        sprout.run("track", "notes/feedback.md")
        reviewed = self.commit(
            "クライアント修正を反映",
            self.save_poster(
                draw_poster(BRIGHT, "SPRING MARKET", 72, 1.25, logo=True)
            ),
        )
        sprout.run("tag", "submitted", reviewed, "-m", "提出版")
        sprout.run("label", reviewed, "submitted")
        sprout.run("note", reviewed, "クライアント確認済み。印刷所へ入稿した版。")

        sprout.run("move", "assets/logo.png", "assets/brand/logo.png")
        self.commit("ロゴを assets/brand へ整理")
        return palette_commit, reviewed

    def add_previews(self, commit: str) -> None:
        sprout = self.sprout
        large = self.attachments / "poster-large.png"
        draw_poster(BRIGHT, "SPRING MARKET", 72, 1.25, logo=True).resize((1200, 1600)).save(large)
        jingle = self.attachments / "jingle-preview.wav"
        write_wav(jingle, (523.25, 659.25, 783.99, 1046.5))
        stand = self.attachments / "stand.stl"
        stand.write_text(STL, encoding="ascii")
        previews = sprout.json("preview", "add", commit, str(large), str(jingle), str(stand))

        files = sprout.json("show", commit)["files"]
        poster_id = next(item["file_id"] for item in files if item["path"] == "poster.png")
        sprout.run(
            "preview", "metadata", commit, previews[0]["id"],
            "--name=印刷確認用", "--description=入稿データを2倍で書き出した確認用画像",
            "--file-id", poster_id,
        )
        sprout.run("preview", "metadata", commit, previews[1]["id"], "--name=ジングル試聴")
        sprout.run("preview", "metadata", commit, previews[2]["id"], "--name=掲示スタンドの3Dモデル")

    def build_side_branches(self, palette_commit: str, reviewed: str) -> None:
        sprout = self.sprout
        # 過去のコミットから分岐した別案
        sprout.run("branch", "night", palette_commit, "--switch", "-m", "夜祭り版の案")
        self.write_palette(NIGHT)
        self.commit("夜祭り版の配色を試す", self.save_poster(draw_poster(NIGHT)))
        self.commit(
            "星空とタイトルを追加",
            self.save_poster(draw_poster(NIGHT, "NIGHT MARKET", stars=True)),
        )

        sprout.run("branch", "logo-test", reviewed, "--switch", "-m", "ロゴ差し替えの検討")
        draw_logo(NIGHT).save(self.root / "assets" / "logo.png")
        self.commit("ロゴの配色を試す")

        # 枝を消してもコミットはtreeに残る
        sprout.run("branch", "abandoned", reviewed, "--switch")
        self.write("brief.md", BRIEF + "- 没案: 横長レイアウト\n")
        self.commit("横長レイアウトの没案")
        sprout.run("switch", "main")
        sprout.run("branch", "--delete", "abandoned")

    def leave_working_state(self) -> None:
        sprout = self.sprout
        # つぼみを1つ残してから、追跡ファイルは先端の内容へ戻す
        self.write("brief.md", BRIEF + "- 検討中: 配布用チラシも作る？\n")
        sprout.run("bud", "--save")
        sprout.run("restore", "main", "--discard")

        # 現在位置が変わるとゴミ箱から復旧できないため、葉の削除は最後に行う
        self.write("notes/feedback.md", FEEDBACK + "\n- （書きかけ）\n")
        mistake = self.commit("誤って保存した版")
        sprout.run("delete-commit", mistake, "--yes")
        sprout.run("restore", "main", "--discard")
        # 準備で破棄した変更や枝は残さず、ゴミ箱には削除した葉だけを置く
        for item in sprout.json("trash", "list"):
            if item["kind"] != "commit":
                sprout.run("trash", "purge", item["id"], "--yes")

        self.write("scratch-idea.txt", "まだ追跡していないアイデアのメモ\n")
        self.write("cache/render.tmp", "無視パターンの確認用\n")
        shutil.copyfile(GUIDE, self.root / "GUIDE.md")

        doctor = sprout.json("doctor")
        if not doctor["ok"]:
            raise RuntimeError(f"sample repository is unhealthy: {doctor['issues']}")


def prepare_output(path: Path) -> None:
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise SystemExit(f"Output must be a new or empty folder: {path}")
    path.mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path, help="New or empty folder to create")
    output = parser.parse_args().output.resolve()
    prepare_output(output)
    with tempfile.TemporaryDirectory() as attachments:
        SampleBuilder(output, Path(attachments)).build()
    print(f"Created sample repository: {output}")
    print(f"Next: open {output / 'GUIDE.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
