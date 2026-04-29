# collect_code.py
"""
一键收集多个 Python 文件内容，格式化为可粘贴的 Markdown 代码块
作者：为您定制
使用方法：
  1. 创建 files.txt，每行一个文件路径
  2. 运行 python collect_code.py
  3. 复制输出内容发给 AI 助手
"""

import os
from pathlib import Path

def read_files_from_list(file_list_path: str = "files.txt"):
    """从 files.txt 读取文件路径列表"""
    if not os.path.exists(file_list_path):
        print(f"❌ 错误: 找不到文件列表 '{file_list_path}'")
        print("请先创建 files.txt，每行写一个文件路径")
        return []

    with open(file_list_path, "r", encoding="utf-8") as f:
        paths = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return paths

def main():
    file_paths = read_files_from_list()
    if not file_paths:
        return

    output_lines = []
    for path in file_paths:
        p = Path(path)
        if not p.exists():
            print(f"⚠️ 警告: 文件不存在 - {path}")
            continue

        try:
            with open(p, "r", encoding="utf-8") as f:
                code = f.read()
        except Exception as e:
            print(f"❌ 读取失败: {path} - {e}")
            continue

        # 格式化输出
        output_lines.append(f"### File: {path}")
        output_lines.append("```python")
        output_lines.append(code)
        output_lines.append("```")
        output_lines.append("")  # 空行分隔

    # 输出到控制台
    print("\n" + "="*60)
    print("✅ 以下是可直接复制粘贴的内容（发给 AI 助手）:")
    print("="*60 + "\n")

    full_output = "\n".join(output_lines)
    print(full_output)

    # 可选：保存到文件
    with open("collected_code.md", "w", encoding="utf-8") as f:
        f.write(full_output)
    print(f"\n📝 同时已保存到: collected_code.md")

if __name__ == "__main__":
    main()