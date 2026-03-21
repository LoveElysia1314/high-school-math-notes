from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PLACEHOLDER = "__INPUT_TEX__"
INPUT_PATTERN = re.compile(r"\\input\{[^}]*\}")


def render_wrapper(template_text: str, input_tex: Path) -> str:
    input_path = input_tex.resolve().as_posix()
    if PLACEHOLDER in template_text:
        return template_text.replace(PLACEHOLDER, input_path, 1)

    replacement = rf"\input{{{input_path}}}"
    if INPUT_PATTERN.search(template_text):
        return INPUT_PATTERN.sub(replacement, template_text, count=1)

    raise ValueError("模板中没有可替换的 \\input{...} 或占位符 __INPUT_TEX__")


def run_xelatex(
    wrapper_path: Path, output_dir: Path, jobname: str, xelatex_cmd: str
) -> subprocess.CompletedProcess[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        xelatex_cmd,
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-jobname={jobname}",
        f"-output-directory={output_dir.resolve().as_posix()}",
        str(wrapper_path),
    ]
    return subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )


def clean_auxiliary_files(build_dir: Path, jobname: str) -> None:
    for candidate in build_dir.glob(f"{jobname}.*"):
        if candidate.suffix == ".tex":
            continue
        if candidate.suffix == ".gz" and candidate.name.endswith(".synctex.gz"):
            continue
        candidate.unlink(missing_ok=True)


def move_pdf(build_dir: Path, pdf_dir: Path, jobname: str) -> Path:
    pdf_dir.mkdir(parents=True, exist_ok=True)
    source_pdf = build_dir / f"{jobname}.pdf"
    target_pdf = pdf_dir / f"{jobname}.pdf"
    if target_pdf.exists():
        target_pdf.unlink()
    source_pdf.replace(target_pdf)
    return target_pdf


def build_one(
    template_path: Path, input_tex: Path, pdf_dir: Path, xelatex_cmd: str
) -> tuple[bool, str]:
    template_text = template_path.read_text(encoding="utf-8-sig")
    wrapper_text = render_wrapper(template_text, input_tex)
    build_dir = input_tex.parent
    jobname = input_tex.stem

    with tempfile.NamedTemporaryFile(
        "w", suffix=".tex", encoding="utf-8", delete=False
    ) as temp_file:
        wrapper_path = Path(temp_file.name)
        temp_file.write(wrapper_text)

    try:
        result = run_xelatex(wrapper_path, build_dir, jobname, xelatex_cmd)
        if result.returncode != 0:
            message = [f"[{input_tex.name}] xelatex 失败，退出码 {result.returncode}"]
            if result.stdout:
                message.append(result.stdout.strip())
            if result.stderr:
                message.append(result.stderr.strip())
            return False, "\n".join(message)

        pdf_path = move_pdf(build_dir, pdf_dir, jobname)
        clean_auxiliary_files(build_dir, jobname)
        return True, f"[{input_tex.name}] 已生成 {pdf_path}"
    finally:
        wrapper_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="批量用模板和 xelatex 生成 tex 文件对应的 PDF"
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=Path(__file__).with_name("tex模板.tex"),
        help="模板 tex 文件路径",
    )
    parser.add_argument(
        "--tex-dir",
        type=Path,
        default=Path(__file__).with_name("tex"),
        help="待处理的 tex 目录",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).with_name("pdf"),
        help="PDF 输出目录，默认是根目录下的 pdf",
    )
    parser.add_argument("--xelatex", default="xelatex", help="xelatex 命令名或完整路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    template_path = args.template.resolve()
    tex_dir = args.tex_dir.resolve()
    pdf_dir = args.output_dir.resolve()

    if not template_path.exists():
        print(f"找不到模板文件: {template_path}", file=sys.stderr)
        return 1

    if not tex_dir.exists():
        print(f"找不到 tex 目录: {tex_dir}", file=sys.stderr)
        return 1

    tex_files = sorted(
        path for path in tex_dir.rglob("*.tex") if path.resolve() != template_path
    )

    if not tex_files:
        print(f"在 {tex_dir} 中没有找到可处理的 .tex 文件")
        return 0

    failures: list[str] = []
    for tex_file in tex_files:
        success, message = build_one(template_path, tex_file, pdf_dir, args.xelatex)
        print(message)
        if not success:
            failures.append(tex_file.name)

    if failures:
        print("以下文件生成失败: " + ", ".join(failures), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
