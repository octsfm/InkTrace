#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跨语言有效代码行统计报告生成器
自动生成结构化报告，按目录组织，适合工作量汇报
✅ 仅将 /tests/ 目录视为测试代码
✅ 其他所有代码（包括 test_xxx 命名）均视为生产代码
"""

import re
from pathlib import Path
from datetime import datetime


def is_effective_line(line: str, lang: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    patterns = {
        'python': r'^\s*#',
        'javascript': r'^\s*(//|/\*)',
        'typescript': r'^\s*(//|/\*)',
        'html': r'^\s*<!--',
        'css': r'^\s*/\*|^\s*//',
        'default': r'^\s*//|^\s*/\*|^\s*<!--|^\s*#'
    }
    pattern = patterns.get(lang, patterns['default'])
    return not re.match(pattern, stripped)


def detect_language(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    mapping = {
        '.py': 'python',
        '.js': 'javascript', '.jsx': 'javascript',
        '.ts': 'typescript', '.tsx': 'typescript',
        '.html': 'html', '.htm': 'html',
        '.css': 'css', '.scss': 'css', '.sass': 'css', '.less': 'css',
        '.vue': 'html',
        '.json': 'default', '.yaml': 'default', '.yml': 'default'
    }
    return mapping.get(ext, 'default')


def count_eloc_in_file(file_path: Path) -> int:
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        lang = detect_language(file_path)
        return sum(1 for line in lines if is_effective_line(line, lang))
    except Exception:
        return 0


def should_exclude(path: Path) -> bool:
    exclude_parts = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'dist', 'build', '.idea', '.vscode'}
    return any(part in exclude_parts for part in path.parts)


def is_test_file(file_path: Path, root_dir: Path) -> bool:
    """仅当文件位于 tests 目录下时，才视为测试代码"""
    try:
        rel_path = file_path.relative_to(root_dir)
        return 'tests' in [p.lower() for p in rel_path.parts]
    except ValueError:
        return False


def generate_report(root_dir: Path, extensions: list):
    current_script = Path(__file__).resolve()
    all_files = []

    # 收集所有有效文件并标记是否为测试
    for file_path in root_dir.rglob('*'):
        if (
            file_path.is_file()
            and file_path.suffix in extensions
            and not should_exclude(file_path)
            and file_path.resolve() != current_script
        ):
            eloc = count_eloc_in_file(file_path)
            is_test = is_test_file(file_path, root_dir)
            all_files.append((file_path, eloc, is_test))

    # 分离
    prod_files = [(fp, eloc) for fp, eloc, is_test in all_files if not is_test]
    test_files = [(fp, eloc) for fp, eloc, is_test in all_files if is_test]

    total_all = len(all_files)
    total_prod = len(prod_files)
    total_test = len(test_files)

    eloc_all = sum(eloc for _, eloc, _ in all_files)
    eloc_prod = sum(eloc for _, eloc in prod_files)
    eloc_test = sum(eloc for _, eloc in test_files)

    # === 生成报告头部 ===
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_lines = [
        "=" * 70,
        "✅ 有效代码行数统计报告 (ELOC)",
        "=" * 70,
        f"📊 项目根目录: {root_dir.resolve()}",
        f"📅 生成时间: {timestamp}",
        f"🧩 扩展名: {', '.join(extensions)}",
        "",
        "📈 总览（含生产 + 测试）:",
        f"   📁 总文件数: {total_all}",
        f"   🔢 有效代码行数: {eloc_all:,}",
        "",
        "🏭 生产代码（非 tests/ 目录）:",
        f"   📁 文件数: {total_prod}",
        f"   🔢 有效代码行数: {eloc_prod:,}",
        "",
        "🧪 测试代码（仅 tests/ 目录）:",
        f"   📁 文件数: {total_test}",
        f"   🔢 有效代码行数: {eloc_test:,}",
        "-" * 70,
        "📂 文件详情（按目录结构缩进，含标识）:",
        ""
    ]

    # === 树形输出（带 [PROD] / [TEST] 标签）===
    rel_entries = []
    for file_path, eloc, is_test in all_files:
        rel_path = file_path.relative_to(root_dir)
        rel_entries.append((rel_path.parts, eloc, is_test))
    rel_entries.sort()

    last_parts = ()
    for parts, eloc, is_test in rel_entries:
        common_len = 0
        for a, b in zip(last_parts, parts[:-1]):
            if a == b:
                common_len += 1
            else:
                break

        for i in range(common_len, len(parts) - 1):
            indent = "    " * i
            report_lines.append(f"{indent}📁 {parts[i]}")

        indent = "    " * (len(parts) - 1)
        tag = "[TEST]" if is_test else "[PROD]"
        report_lines.append(f"{indent}    {eloc:5d} | {parts[-1]} {tag}")

        last_parts = parts

    # 写入文件
    report_filename = f"codeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path = root_dir / report_filename

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))

    print(f"✅ 报告已生成: {report_path}")
    print(f"🏭 生产代码: {eloc_prod:,} 行 | 🧪 测试代码: {eloc_test:,} 行")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="统计代码行数（仅 tests/ 目录视为测试）")
    parser.add_argument("path", nargs="?", default=None, help="项目根目录（默认：脚本所在目录）")
    parser.add_argument(
        "-e", "--extensions",
        nargs="+",
        default=[".py", ".js", ".ts", ".html", ".css"],
        help="要统计的文件扩展名"
    )
    args = parser.parse_args()

    root_dir = Path(args.path) if args.path else Path(__file__).parent
    root_dir = root_dir.resolve()

    if not root_dir.exists():
        print(f"❌ 目录不存在: {root_dir}")
        return

    print(f"🔍 正在分析目录: {root_dir}")
    generate_report(root_dir, args.extensions)


if __name__ == "__main__":
    main()