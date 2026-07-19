#!/usr/bin/env python3
"""Seed-VC のリアルタイム用ボイスクローン・プロファイル選択 GUI。

プロファイルは config/voice_clone_profiles.json で定義する。checkpoint_path と
config_path が両方 null のプロファイルは Seed-VC 公式のゼロショット tiny モデルを使う。
両方を指定したプロファイルは、実在する real-time tiny の fine-tune 成果物だけを起動する。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

REPO_DIR = Path(__file__).resolve().parent.parent
PROFILE_PATH = REPO_DIR / "config" / "voice_clone_profiles.json"
ZERO_SHOT_RUNNER_PATH = REPO_DIR / "scripts" / "run_seedvc_zero_shot.sh"
FINETUNED_RUNNER_PATH = REPO_DIR / "scripts" / "run_seedvc_finetuned.sh"


class ProfileError(ValueError):
    """プロファイル定義または選択内容が起動条件を満たさない。"""


def load_profile_document(path: Path = PROFILE_PATH) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProfileError(f"プロファイル設定が見つかりません: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProfileError(f"プロファイル設定の JSON が不正です: {exc}") from exc

    profiles = document.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ProfileError("profiles は空でない配列である必要があります。")
    if not isinstance(document.get("active_profile"), str):
        raise ProfileError("active_profile は文字列である必要があります。")
    return document


def profile_by_id(document: dict[str, Any], profile_id: str) -> dict[str, Any]:
    for profile in document["profiles"]:
        if isinstance(profile, dict) and profile.get("id") == profile_id:
            return profile
    raise ProfileError(f"未知のプロファイルです: {profile_id}")


def resolve_profile_command(profile: dict[str, Any]) -> list[str]:
    """検証済みプロファイルから shell を介さない起動コマンドを作る。"""
    profile_id = profile.get("id")
    name = profile.get("name")
    pipeline = profile.get("pipeline")
    checkpoint = profile.get("checkpoint_path")
    config = profile.get("config_path")
    reference_audio = profile.get("reference_audio_path")
    if not isinstance(profile_id, str) or not profile_id:
        raise ProfileError("各プロファイルには空でない id が必要です。")
    if not isinstance(name, str) or not name:
        raise ProfileError(f"{profile_id}: name が必要です。")
    if pipeline == "v1-zero-shot-realtime":
        if checkpoint is not None or config is not None or reference_audio is not None:
            raise ProfileError(
                f"{profile_id}: zero-shot pipeline には custom model や固定 reference を指定できません．"
            )
        return [
            str(ZERO_SHOT_RUNNER_PATH),
            "--profile-name", name,
            "--profile-source", "Built-in zero-shot checkpoint",
        ]
    if pipeline != "v1-finetuned-realtime":
        raise ProfileError(f"{profile_id}: 未対応の pipeline です: {pipeline}")
    if checkpoint is None or config is None:
        raise ProfileError(
            f"{profile_id}: fine-tuned pipeline には checkpoint と config が必要です．"
        )
    if not isinstance(checkpoint, str) or not isinstance(config, str):
        raise ProfileError(f"{profile_id}: モデルパスは文字列で指定してください。")
    if reference_audio is not None and not isinstance(reference_audio, str):
        raise ProfileError(f"{profile_id}: reference_audio_path は文字列または null で指定してください．")

    checkpoint_path = (REPO_DIR / checkpoint).resolve()
    config_path = (REPO_DIR / config).resolve()
    required_paths = [
        ("checkpoint", checkpoint_path),
        ("config", config_path),
    ]
    reference_audio_path = None
    if reference_audio is not None:
        reference_audio_path = (REPO_DIR / reference_audio).resolve()
        required_paths.append(("reference audio", reference_audio_path))
    for label, path in required_paths:
        try:
            path.relative_to(REPO_DIR)
        except ValueError as exc:
            raise ProfileError(f"{profile_id}: {label} はリポジトリ内のパスにしてください。") from exc
        if not path.is_file():
            raise ProfileError(
                f"{profile_id}: {label} が未配置です: {path.relative_to(REPO_DIR)}\n"
                "fine-tune 完了後に ft_model.pth と対応する YAML を配置してください。"
            )
    command = [
        str(FINETUNED_RUNNER_PATH),
        "--checkpoint-path", str(checkpoint_path),
        "--config-path", str(config_path),
        "--profile-name", name,
        "--profile-source", f"Loaded fine-tuned checkpoint: {checkpoint_path.relative_to(REPO_DIR)}",
    ]
    if reference_audio_path is not None:
        command.extend(["--reference-audio-path", str(reference_audio_path)])
    return command


def save_active_profile(document: dict[str, Any], profile_id: str) -> None:
    document["active_profile"] = profile_id
    PROFILE_PATH.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def list_profiles(document: dict[str, Any]) -> str:
    lines = []
    for profile in document["profiles"]:
        marker = "*" if profile.get("id") == document["active_profile"] else " "
        lines.append(f"{marker} {profile.get('id')}: {profile.get('name')}")
    return "\n".join(lines)


class LauncherGUI:
    def __init__(self, document: dict[str, Any]):
        self.document = document
        self.root = tk.Tk()
        self.root.title("Voice Changer - Clone Profile")
        self.root.resizable(False, False)
        self.profile_ids = [profile["id"] for profile in document["profiles"]]
        self.profile_var = tk.StringVar(value=document["active_profile"])
        self.description_var = tk.StringVar()
        self.status_var = tk.StringVar()

        frame = ttk.Frame(self.root, padding=16)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="Voice clone profile").grid(row=0, column=0, sticky="w")
        self.selector = ttk.Combobox(
            frame, state="readonly", values=self.profile_ids, textvariable=self.profile_var, width=42
        )
        self.selector.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.selector.bind("<<ComboboxSelected>>", self.on_profile_changed)
        ttk.Label(frame, textvariable=self.description_var, wraplength=420, justify="left").grid(
            row=2, column=0, sticky="w", pady=(0, 10)
        )
        ttk.Label(frame, textvariable=self.status_var, foreground="#9c0006", wraplength=420).grid(
            row=3, column=0, sticky="w", pady=(0, 12)
        )
        ttk.Button(frame, text="Start Voice Changer", command=self.start).grid(
            row=4, column=0, sticky="e"
        )
        self.on_profile_changed()

    def selected_profile(self) -> dict[str, Any]:
        return profile_by_id(self.document, self.profile_var.get())

    def on_profile_changed(self, _event: object | None = None) -> None:
        try:
            profile = self.selected_profile()
            self.description_var.set(profile.get("description", ""))
            resolve_profile_command(profile)
            self.status_var.set("このプロファイルは起動できます。")
        except ProfileError as exc:
            self.status_var.set(str(exc))

    def start(self) -> None:
        try:
            profile = self.selected_profile()
            command = resolve_profile_command(profile)
            save_active_profile(self.document, profile["id"])
            subprocess.Popen(command, cwd=REPO_DIR)
        except (ProfileError, OSError) as exc:
            messagebox.showerror("起動できません", str(exc), parent=self.root)
            return
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed-VC のボイスクローン・プロファイルを選択して起動する")
    parser.add_argument("--profile", help="GUI を開かずに指定プロファイルを選ぶ")
    parser.add_argument("--list", action="store_true", help="利用可能なプロファイルを表示する")
    parser.add_argument("--dry-run", action="store_true", help="起動せず、検証済みコマンドを表示する")
    args = parser.parse_args()

    try:
        document = load_profile_document()
        if args.list:
            print(list_profiles(document))
            return 0
        if args.profile or args.dry_run:
            profile = profile_by_id(document, args.profile or document["active_profile"])
            command = resolve_profile_command(profile)
            print(json.dumps({"profile": profile["id"], "command": command}, ensure_ascii=False))
            if args.dry_run:
                return 0
            save_active_profile(document, profile["id"])
            return subprocess.call(command, cwd=REPO_DIR)
        LauncherGUI(document).run()
        return 0
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
