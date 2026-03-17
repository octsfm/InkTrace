"""
批量为Python文件添加文件路径描述脚本 - 修复版

作者：孔利群
"""

# 文件路径：add_file_descriptions_v2.py


import os
import re

PROJECT_ROOT = r"D:\Work\InkTrace\ink-trace"

def get_file_description(file_path: str) -> str:
    """根据文件路径生成文件描述"""
    rel_path = os.path.relpath(file_path, PROJECT_ROOT)
    
    if "domain/entities" in rel_path:
        entity_name = os.path.basename(file_path).replace(".py", "")
        return f"领域实体：{entity_name}实体"
    elif "domain/value_objects" in rel_path:
        vo_name = os.path.basename(file_path).replace(".py", "")
        return f"领域值对象：{vo_name}值对象"
    elif "domain/services" in rel_path:
        service_name = os.path.basename(file_path).replace(".py", "")
        return f"领域服务：{service_name}服务"
    elif "domain/repositories" in rel_path:
        repo_name = os.path.basename(file_path).replace(".py", "")
        return f"领域仓储：{repo_name}仓储接口"
    elif "application/services" in rel_path:
        service_name = os.path.basename(file_path).replace(".py", "")
        return f"应用服务：{service_name}应用服务"
    elif "application/dto" in rel_path:
        dto_name = os.path.basename(file_path).replace(".py", "")
        return f"应用DTO：{dto_name}数据传输对象"
    elif "infrastructure/llm" in rel_path:
        client_name = os.path.basename(file_path).replace(".py", "")
        return f"基础设施层：LLM{client_name}客户端"
    elif "infrastructure/persistence" in rel_path:
        repo_name = os.path.basename(file_path).replace(".py", "")
        return f"基础设施层：{repo_name}持久化"
    elif "infrastructure/security" in rel_path:
        sec_name = os.path.basename(file_path).replace(".py", "")
        return f"基础设施层：{sec_name}安全组件"
    elif "infrastructure/file" in rel_path:
        file_name = os.path.basename(file_path).replace(".py", "")
        return f"基础设施层：{file_name}文件处理"
    elif "presentation/api/routers" in rel_path:
        router_name = os.path.basename(file_path).replace(".py", "")
        return f"接口层：{router_name}路由"
    elif "presentation/api" in rel_path:
        api_name = os.path.basename(file_path).replace(".py", "")
        return f"接口层：{api_name}API"
    elif "tests/unit" in rel_path:
        test_name = os.path.basename(file_path).replace(".py", "")
        return f"单元测试：{test_name}测试"
    else:
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
        file_header = f"# 文件：{description}\n"
        
        # 在文件开头添加描述
        new_content = file_header + content
        
        # 写回文件
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
        if process_file(file_path):
            success_count += 1
            print(f"✓ {os.path.relpath(file_path, PROJECT_ROOT)}")
        else:
            skip_count += 1
    
    print(f"\n处理完成：成功 {success_count} 个，跳过 {skip_count} 个")

if __name__ == "__main__":
    main()
