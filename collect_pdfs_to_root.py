from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path


def build_flat_name(source_root: Path, pdf_path: Path) -> str:
    relative_path = pdf_path.relative_to(source_root)
    parts = list(relative_path.parts)
    if len(parts) == 1:
        return parts[0]

    flattened_stem = "__".join(
        part.replace(" ", "_") for part in parts[:-1] + [pdf_path.stem]
    )
    return f"{flattened_stem}{pdf_path.suffix}"


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def unique_target_path(output_dir: Path, file_name: str) -> Path:
    candidate = output_dir / file_name
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        next_candidate = output_dir / f"{stem}_{index}{suffix}"
        if not next_candidate.exists():
            return next_candidate
        index += 1


def collect_pdfs(
    source_dir: Path, output_dir: Path, move_files: bool = False
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[Path] = []
    pdf_files = sorted(
        path
        for path in source_dir.rglob("*.pdf")
        if path.is_file()
        and (output_dir == source_dir or not is_within(path, output_dir))
    )

    for pdf_path in pdf_files:
        flat_name = build_flat_name(source_dir, pdf_path)
        target_path = unique_target_path(output_dir, flat_name)

        if move_files:
            shutil.move(str(pdf_path), str(target_path))
        else:
            shutil.copy2(pdf_path, target_path)

        copied_files.append(target_path)

    return copied_files


def create_archive(pdf_files: list[Path], archive_path: Path) -> Path:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive_file:
        for pdf_file in pdf_files:
            archive_file.write(pdf_file, arcname=pdf_file.name)
    return archive_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="递归提取目录中的 PDF，并扁平化复制或移动到目标根目录"
    )
    parser.add_argument("source_dir", type=Path, help="要扫描的源文件夹")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="PDF 输出根目录，默认是当前工作目录",
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="将 PDF 移动到目标目录而不是复制",
    )
    parser.add_argument(
        "--archive",
        type=Path,
        default=None,
        help="可选：在输出目录中额外生成一个 zip 压缩包",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not source_dir.exists() or not source_dir.is_dir():
        print(f"找不到源文件夹: {source_dir}", file=sys.stderr)
        return 1

    pdf_files = collect_pdfs(source_dir, output_dir, move_files=args.move)
    if not pdf_files:
        print(f"在 {source_dir} 中没有找到 PDF 文件")
        return 0

    print(f"已处理 {len(pdf_files)} 个 PDF 到 {output_dir}")
    for pdf_file in pdf_files:
        print(f"- {pdf_file.name}")

    if args.archive is not None:
        archive_path = args.archive
        if not archive_path.is_absolute():
            archive_path = output_dir / archive_path
        archive_path = archive_path.resolve()
        created_archive = create_archive(pdf_files, archive_path)
        print(f"已生成压缩包: {created_archive}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
