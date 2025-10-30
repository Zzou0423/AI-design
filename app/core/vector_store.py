"""
向量数据库管理模块

使用 LangChain 的 Chroma 向量数据库和 DashScope Embeddings
实现问卷知识库的存储和检索功能
"""

import os
from typing import List, Optional
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class SurveyVectorStore:
    """问卷向量存储类
    
    用于管理优秀问卷知识库的向量存储和检索
    """
    
    def __init__(
        self,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "exemplary_surveys",
        embedding_model: str = "text-embedding-v3"
    ):
        """
        初始化向量存储
        
        Args:
            persist_directory: 向量数据库持久化目录
            collection_name: 集合名称
            embedding_model: 嵌入模型名称
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        
        # 初始化 DashScope Embeddings
        self.embeddings = DashScopeEmbeddings(model=embedding_model)
        
        # 初始化文本切分器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,           # 每个chunk的最大字符数
            chunk_overlap=200,         # chunk之间的重叠字符数
            length_function=len,
            separators=["\n\n", "\n", "。", "；", " ", ""]
        )
        
        self.vector_store: Optional[Chroma] = None
        
    def load_document_from_pdf(self, pdf_path: str) -> List[Document]:
        """
        从PDF文件加载文档
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            文档列表
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
        
        print(f"正在加载PDF文档: {pdf_path}")
        
        # 使用 PyPDFLoader 加载PDF
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        
        print(f"成功加载 {len(documents)} 页文档")
        return documents
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        切分文档为较小的文本块
        
        Args:
            documents: 原始文档列表
            
        Returns:
            切分后的文档列表
        """
        print(f"开始切分文档，原始文档数: {len(documents)}")
        
        # 切分文档
        split_docs = self.text_splitter.split_documents(documents)
        
        print(f"切分完成，共生成 {len(split_docs)} 个文本块")
        
        return split_docs
    
    def load_and_split_pdf(self, pdf_path: str) -> List[Document]:
        """
        从PDF加载文档并进行切分
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            切分后的文档列表
        """
        # 加载PDF
        documents = self.load_document_from_pdf(pdf_path)
        
        # 切分文档
        split_docs = self.split_documents(documents)
        
        return split_docs
    
    def create_vector_store(self, documents: Optional[List[Document]] = None) -> Chroma:
        """
        创建向量存储
        
        Args:
            documents: 要存储的文档列表，如果为None则从持久化目录加载
            
        Returns:
            Chroma向量存储实例
        """
        if documents:
            print("创建新的向量存储...")
            self.vector_store = Chroma.from_documents(
                documents=documents,
                embedding=self.embeddings,
                collection_name=self.collection_name,
                persist_directory=self.persist_directory
            )
            print(f"向量存储已创建，包含 {len(documents)} 个文档块")
        else:
            print("从持久化目录加载向量存储...")
            self.vector_store = Chroma(
                persist_directory=self.persist_directory,
                collection_name=self.collection_name,
                embedding_function=self.embeddings
            )
            print("向量存储加载完成")
        
        return self.vector_store
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        向已有的向量存储添加文档
        
        Args:
            documents: 要添加的文档列表
        """
        if not self.vector_store:
            raise ValueError("向量存储未初始化，请先调用 create_vector_store")
        
        print(f"添加 {len(documents)} 个文档到向量存储...")
        
        # 切分文档
        split_docs = self.split_documents(documents)
        
        # 添加到向量存储
        self.vector_store.add_documents(split_docs)
        
        print(f"文档添加完成")
    
    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None
    ) -> List[Document]:
        """
        语义相似度搜索
        
        Args:
            query: 查询文本
            k: 返回最相似的文档数量
            filter: 过滤条件
            
        Returns:
            相似的文档列表
        """
        if not self.vector_store:
            raise ValueError("向量存储未初始化，请先调用 create_vector_store")
        
        results = self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=filter
        )
        
        return results
    
    def similarity_search_with_score(
        self,
        query: str,
        k: int = 4
    ) -> List[tuple]:
        """
        语义相似度搜索（带分数）
        
        Args:
            query: 查询文本
            k: 返回最相似的文档数量
            
        Returns:
            (文档, 相似度分数) 元组列表
        """
        if not self.vector_store:
            raise ValueError("向量存储未初始化，请先调用 create_vector_store")
        
        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=k
        )
        
        return results
    
    def persist(self) -> None:
        """持久化向量存储"""
        if not self.vector_store:
            raise ValueError("向量存储未初始化")
        
        self.vector_store.persist()
        print(f"向量存储已持久化到: {self.persist_directory}")
    
    def init_from_pdf(self, pdf_path: str) -> None:
        """
        从PDF文件初始化向量存储
        
        这是一个便捷方法，一次性完成加载、切分和创建向量存储
        
        Args:
            pdf_path: PDF文件路径
        """
        # 加载和切分PDF
        documents = self.load_and_split_pdf(pdf_path)
        
        # 创建向量存储
        self.create_vector_store(documents)
        
        # 持久化
        self.persist()
        
        print(f"向量存储初始化完成！")
    
    def get_stats(self) -> dict:
        """
        获取向量存储统计信息
        
        Returns:
            统计信息字典
        """
        if not self.vector_store:
            return {
                "status": "未初始化",
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory
            }
        
        # 获取向量存储中的文档数量
        try:
            count = self.vector_store._collection.count()
            return {
                "status": "已初始化",
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory,
                "document_count": count,
                "embedding_model": self.embedding_model
            }
        except Exception as e:
            return {
                "status": "错误",
                "error": str(e),
                "collection_name": self.collection_name,
                "persist_directory": self.persist_directory
            }


def main():
    """测试和演示使用"""
    import sys
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # 检查是否提供了PDF路径
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/exemplary_surveys.pdf"
    
    # 创建向量存储实例
    vector_store = SurveyVectorStore(
        persist_directory="./data/chroma_db",
        collection_name="exemplary_surveys"
    )
    
    # 初始化向量存储
    print("\n开始初始化向量存储...")
    vector_store.init_from_pdf(pdf_path)
    
    # 显示统计信息
    print("\n向量存储统计信息:")
    stats = vector_store.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 测试搜索
    test_query = "用户满意度调查"
    print(f"\n测试搜索: '{test_query}'")
    results = vector_store.similarity_search(test_query, k=3)
    
    print(f"\n找到 {len(results)} 个相关文档:")
    for i, doc in enumerate(results, 1):
        print(f"\n文档 {i}:")
        print(f"  内容: {doc.page_content[:200]}...")
        if doc.metadata:
            print(f"  元数据: {doc.metadata}")


if __name__ == "__main__":
    main()

