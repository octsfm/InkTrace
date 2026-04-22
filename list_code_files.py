# list_code_files.py (最终稳定版 - 排除虚拟环境)
"""
从 dirs.txt 读取目录列表，
扫描 .py/.html/.js/.css 文件（排除 __init__.py 和虚拟环境目录），
输出到 files.txt，完全兼容软链接和复杂路径。
"""

import os
from pathlib import Path


def read_dirs_from_file(file_path: str = "dirs.txt") -> list:
    """读取要扫描的目录列表"""
    if not Path(file_path).exists():
        print(f"❌ 错误: 找不到 '{file_path}'")
        print("请创建 dirs.txt，每行一个目录名（如 'edge'）")
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def collect_files_in_dir(dir_name: str, extensions: set) -> list:
    """
    扫描指定目录，返回文件的逻辑路径（如 edge/app.py）
    排除虚拟环境目录（.venv, venv, env 等）
    """
    dir_path = Path(dir_name)
    if not dir_path.exists():
        print(f"⚠️ 警告: 目录不存在 - {dir_name}")
        return []

    # 定义要排除的目录名（大小写敏感，通常小写）
    excluded_dirs = {'.venv', 'venv', 'env', '.git', '__pycache__', '.mypy_cache', '.pytest_cache'}

    file_paths = []
    for file in dir_path.rglob('*'):
        if not file.is_file():
            continue

        # 跳过 __init__.py
        if file.name == '__init__.py':
            continue

        # 检查文件路径中是否包含任何排除目录
        # 将路径拆分为各部分，检查是否有 part 在 excluded_dirs 中
        try:
            parts = file.relative_to(dir_path).parts
        except ValueError:
            # fallback：用字符串分割（应对软链接等边缘情况）
            rel_str = str(file).replace(str(dir_path), "", 1).lstrip('\\').lstrip('/')
            parts = tuple(rel_str.split(os.sep))

        if any(part in excluded_dirs for part in parts):
            continue

        # 检查扩展名
        if file.suffix.lower() in extensions:
            try:
                rel_part = file.relative_to(dir_path)
                logical_path = Path(dir_name) / rel_part
                file_paths.append(str(logical_path).replace(os.sep, '/'))
            except ValueError:
                rel_str = str(file).replace(str(dir_path), "", 1).lstrip('\\').lstrip('/')
                file_paths.append(f"{dir_name}/{rel_str}")

    return file_paths


def main():
    extensions = {'.py', '.html', '.js', '.css'}
    dir_names = read_dirs_from_file()
    if not dir_names:
        return

    all_files = []
    for dir_name in dir_names:
        print(f"🔍 扫描目录: {dir_name}")
        files = collect_files_in_dir(dir_name, extensions)
        all_files.extend(files)
        print(f"   → 找到 {len(files)} 个文件")

    # 去重 + 排序
    all_files = sorted(set(all_files))

    output_file = "files.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        for path in all_files:
            f.write(path + "\n")

    print(f"\n✅ 完成！共 {len(all_files)} 个文件")
    print(f"📄 输出: {output_file}")


if __name__ == "__main__":
    main()