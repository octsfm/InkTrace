"""
批量为Python文件添加文件路径描述脚本

作者：孔利群
"""

# 文件路径：add_file_descriptions.py


import os
import re

# 项目根目录
PROJECT_ROOT = r"D:\Work\InkTrace\ink-trace"

def get_file_description(file_path: str) -> str:
    """根据文件路径生成文件描述"""
    # 移除根目录和.py扩展名
    rel_path = os.path.relpath(file_path, PROJECT_ROOT)
    module_path = rel_path.replace("\\", "/").replace("/", ".").replace(".py", "")
    
    # 根据目录生成描述
    if "domain/entities" in module_path:
        entity_name = os.path.basename(file_path).replace(".py", "")
        return f"领域实体：{entity_name}实体"
    elif "domain/value_objects" in module_path:
        vo_name = os.path.basename(file_path).replace(".py", "")
        return f"领域值对象：{vo_name}值对象"
    elif "domain/services" in module_path:
        service_name = os.path.basename(file_path).replace(".py", "")
        return f"领域服务：{service_name}服务"
    elif "domain/repositories" in module_path:
        repo_name = os.path.basename(file_path).replace(".py", "")
        return f"领域仓储：{repo_name}仓储"
    elif "application/services" in module_path:
        service_name = os.path.basename(file_path).replace(".py", "")
        return f"应用服务：{service_name}应用服务"
    elif "application/dto" in module_path:
        dto_name = os.path.basename(file_path).replace(".py", "")
        return f"应用DTO：{dto_name}数据传输对象"
    elif "infrastructure/llm" in module_path:
        client_name = os.path.basename(file_path).replace(".py", "")
        return f"基础设施层：LLM{client_name}客户端"
    elif "infrastructure/persistence" in module_path:
        repo_name = os.path.basename(file_path).replace(".py", "")
        return f"基础设施层：{repo_name}持久化"
    elif "infrastructure/security" in module_path:
        sec_name = os.path.basename(file_path).replace(".py", "")
        return f"基础设施层：{sec_name}安全组件"
    elif "infrastructure/file" in module_path:
        file_name = os.path.basename(file_path).replace(".py", "")
        return f"基础设施层：{file_name}文件处理"
    elif "presentation/api/routers" in module_path:
        router_name = os.path.basename(file_path).replace(".py", "")
        return f"接口层：{router_name}路由"
    elif "presentation/api" in module_path:
        api_name = os.path.basename(file_path).replace(".py", "")
        return f"接口层：{api_name}API"
    elif "tests/unit" in module_path:
        test_name = os.path.basename(file_path).replace(".py", "")
        return f"单元测试：{test_name}测试"
    elif "desktop" in module_path:
        desktop_name = os.path.basename(file_path).replace(".py", "")
        return f"桌面应用：{desktop_name}桌面组件"
    else:
        # 使用文件名作为描述
        name = os.path.basename(file_path).replace(".py", "")
        return f"模块：{name}"

def process_file(file_path: str) -> bool:
    """处理单个文件，添加文件路径描述"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经有文件路径描述
        if "# 文件：" in content:
            return False
        
        # 生成文件描述
        description = get_file_description(file_path)
        
        # 添加文件路径描述（在文档字符串之后或开头）
        lines = content.split('\n')
        
        # 找到文档字符串结束位置
        new_lines = []
        in_docstring = False
        docstring_start = None
        docstring_end = None
        
        for i, line in enumerate(lines):
            if '"""' in line or "'''" in line:
                if not in_docstring:
                    in_docstring = True
                    docstring_start = i
                else:
                    in_docstring = False
                    docstring_end = i
                    
            # 在文档字符串之后添加文件路径描述
            if not in_docstring and docstring_end is not None and i == docstring_end + 1:
                # 检查是否为空行
                if line.strip():
                    new_lines.append(f"# 文件：{description}")
                    new_lines.append("")
            
            new_lines.append(line)
        
        # 如果没有文档字符串，在文件开头添加
        if docstring_end is None:
            new_lines.insert(0, f"# 文件：{description}")
            new_lines.insert(1, "")
        
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
    # 获取所有Python文件
    python_files = []
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # 跳过__pycache__和node_modules
        dirs[:] = [d for d in dirs if d not in ['__pycache__', 'node_modules', '.git']]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"找到 {len(python_files)} 个Python文件")
    
    # 处理每个文件
    success_count = 0
    skip_count = 0
    
    for file_path in python_files:
        if process_file(file_path):
            success_count += 1
        else:
            skip_count += 1
    
    print(f"处理完成：成功 {success_count} 个，跳过 {skip_count} 个")

if __name__ == "__main__":
    main()
