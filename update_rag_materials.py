#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG 语料更新脚本

扫描 rag_materials/ 文件夹中的PDF文件，并更新向量数据库
支持增量更新：只处理新增或修改的文件
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json
import hashlib
from dotenv import load_dotenv

# Windows终端编码修复
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.core.vector_store import SurveyVectorStore

# 加载环境变量
load_dotenv()

# 配置文件路径
INDEX_FILE = project_root / "rag_materials" / ".rag_index.json"


def get_file_hash(file_path: Path) -> str:
    """计算文件MD5哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def load_index() -> dict:
    """加载文件索引"""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_index(index: dict):
    """保存文件索引"""
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # 更新处理时间戳
    index["_last_updated"] = datetime.now().isoformat()
    
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def scan_pdf_files(materials_dir: Path) -> list:
    """扫描文件夹中的PDF文件"""
    pdf_files = []
    
    if not materials_dir.exists():
        print(f"[警告] 语料文件夹不存在: {materials_dir}")
        return pdf_files
    
    # 支持嵌套文件夹
    for pdf_file in materials_dir.rglob("*.pdf"):
        if pdf_file.is_file():
            pdf_files.append(pdf_file)
    
    return sorted(pdf_files)


def main():
    """主函数"""
    print("=" * 70)
    print("RAG 语料更新工具")
    print("=" * 70)
    
    # 检查API Key
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("\n[错误] DASHSCOPE_API_KEY 未设置")
        print("请在 .env 文件中配置您的 DashScope API Key")
        return 1
    
    # 语料文件夹路径
    materials_dir = project_root / "rag_materials"
    
    # 扫描PDF文件
    print(f"\n📂 扫描语料文件夹: {materials_dir}")
    pdf_files = scan_pdf_files(materials_dir)
    
    if not pdf_files:
        print("\n[警告] 未找到PDF文件")
        print(f"请将问卷样例PDF文件放入: {materials_dir}")
        print("\n支持的格式:")
        print("  - PDF文件 (.pdf)")
        print("  - 支持嵌套文件夹")
        return 0
    
    print(f"[成功] 找到 {len(pdf_files)} 个PDF文件:\n")
    for i, pdf_file in enumerate(pdf_files, 1):
        rel_path = pdf_file.relative_to(materials_dir)
        print(f"  {i}. {rel_path}")
    
    # 加载文件索引
    index = load_index()
    
    # 检查需要处理的文件（新增或修改）
    files_to_process = []
    for pdf_file in pdf_files:
        rel_path = str(pdf_file.relative_to(materials_dir))
        file_hash = get_file_hash(pdf_file)
        file_stat = pdf_file.stat()
        
        if rel_path not in index:
            # 新文件
            files_to_process.append((pdf_file, rel_path, "新增"))
            index[rel_path] = {
                "hash": file_hash,
                "size": file_stat.st_size,
                "modified": file_stat.st_mtime,
                "processed_at": None
            }
        elif index[rel_path]["hash"] != file_hash:
            # 修改过的文件
            files_to_process.append((pdf_file, rel_path, "更新"))
            index[rel_path]["hash"] = file_hash
            index[rel_path]["size"] = file_stat.st_size
            index[rel_path]["modified"] = file_stat.st_mtime
    
    if not files_to_process:
        print("\n[信息] 所有文件都已处理，无需更新")
        return 0
    
    print(f"\n[处理] 需要处理 {len(files_to_process)} 个文件:\n")
    for pdf_file, rel_path, status in files_to_process:
        print(f"  [{status}] {rel_path}")
    
    # 初始化向量存储
    print("\n[初始化] 初始化向量数据库...")
    vector_store = SurveyVectorStore(
        persist_directory="./data/chroma_db",
        collection_name="exemplary_surveys"
    )
    
    # 尝试加载现有向量存储，如果不存在则创建新的
    try:
        vector_store.create_vector_store()
        print("[成功] 向量数据库加载成功")
        is_new = False
    except Exception as e:
        print(f"[信息] 向量数据库不存在，将创建新的数据库")
        print(f"       错误信息: {e}")
        is_new = True
    
    # 处理每个文件
    print("\n[处理] 开始处理文件...\n")
    processed_count = 0
    failed_files = []
    
    for pdf_file, rel_path, status in files_to_process:
        try:
            print(f"[{status}] 处理文件: {rel_path}")
            
            # 加载PDF并切分
            documents = vector_store.load_and_split_pdf(str(pdf_file))
            
            if is_new and processed_count == 0:
                # 第一个文件，创建新的向量存储
                vector_store.create_vector_store(documents)
                vector_store.persist()
                is_new = False
                print(f"  [成功] 向量数据库已创建，包含 {len(documents)} 个文档块")
            else:
                # 后续文件，添加到现有向量存储
                if not vector_store.vector_store:
                    vector_store.create_vector_store()
                vector_store.add_documents(documents)
                vector_store.persist()
                print(f"  [成功] 已添加到向量数据库，包含 {len(documents)} 个文档块")
            
            # 更新索引
            index[rel_path]["processed_at"] = datetime.now().isoformat()
            processed_count += 1
            
        except Exception as e:
            print(f"  [失败] 处理失败: {e}")
            failed_files.append((rel_path, str(e)))
    
    # 保存索引
    save_index(index)
    
    # 显示结果
    print("\n" + "=" * 70)
    print("处理完成")
    print("=" * 70)
    print(f"[成功] 成功处理: {processed_count}/{len(files_to_process)} 个文件")
    
    if failed_files:
        print(f"\n[失败] 失败文件 ({len(failed_files)} 个):")
        for rel_path, error in failed_files:
            print(f"  - {rel_path}: {error}")
    
    # 显示向量数据库统计信息
    if processed_count > 0:
        print("\n[统计] 向量数据库统计:")
        stats = vector_store.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    print("\n[提示]")
    print("  - 向量数据库已更新，下次生成问卷时将使用新的语料")
    print("  - 如需重新构建向量数据库，删除 data/chroma_db 文件夹后重新运行此脚本")
    
    return 0 if not failed_files else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[取消] 操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

