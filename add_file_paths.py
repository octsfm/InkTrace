"""
批量为Python文件添加实际文件路径脚本

作者：孔利群
"""

import os

PROJECT_ROOT = r"D:\Work\InkTrace\ink-trace"

def add_file_path_to_header(file_path: str) -> bool:
    """为文件添加实际文件路径到文件头"""
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有文件路径
        if "# 文件路径：" in content:
            return False
        
        # 生成相对文件路径
        rel_path = os.path.relpath(file_path, PROJECT_ROOT).replace("\\", "/")
        file_header = f"# 文件路径：{rel_path}\n"
        
        # 处理文件内容
        lines = content.split('\n')
        new_lines = []
        
        # 找到文档字符串开始位置
        docstring_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith('"""') or line.strip().startswith("'''"):
                docstring_start = i
                break
        
        # 如果有文档字符串，在文档字符串之后添加
        if docstring_start is not None:
            # 找到文档字符串结束
            docstring_end = None
            for i in range(docstring_start + 1, len(lines)):
                if lines[i].strip().startswith('"""') or lines[i].strip().startswith("'''"):
                    docstring_end = i
                    break
            
            # 在文档字符串结束后添加
            if docstring_end is not None:
                for i, line in enumerate(lines):
                    new_lines.append(line)
                    if i == docstring_end:
                        new_lines.append("")
                        new_lines.append(file_header)
        else:
            # 如果没有文档字符串，在文件开头添加
            new_lines.append(file_header)
            new_lines.extend(lines)
        
        # 写回文件
        new_content = '\n'.join(new_lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return True
    except Exception as e:
        print(f"处理文件 {file_path} 失败: {e}")
        return False

def main():
    """主函数"""
    python_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in ['__pycache__', 'node_modules', '.git']]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"找到 {len(python_files)} 个Python文件")
    
    success_count = 0
    skip_count = 0
    
    for file_path in python_files:
        if add_file_path_to_header(file_path):
            success_count += 1
            print(f"✓ {os.path.relpath(file_path, PROJECT_ROOT)}")
        else:
            skip_count += 1
    
    print(f"\n处理完成：成功 {success_count} 个，跳过 {skip_count} 个")

if __name__ == "__main__":
    main()
