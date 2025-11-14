"""
问卷服务模块

提供问卷生成和分析的高级服务接口
"""

import json
from typing import Dict, Any, Optional, Tuple, List
from dotenv import load_dotenv

from app.core.vector_store import SurveyVectorStore
from app.chains.survey_creation_chain import SurveyCreationChain
from langchain_core.documents import Document


class SurveyService:
    """问卷服务类
    
    提供问卷生成和分析的业务逻辑
    """
    
    def __init__(
        self,
        vector_store_dir: str = "./data/chroma_db",
        llm_model: str = "qwen-max",
        temperature: float = 0.7,
        retrieval_k: int = 3
    ):
        """
        初始化问卷服务
        
        Args:
            vector_store_dir: 向量数据库目录
            llm_model: LLM模型名称
            temperature: 温度参数
            retrieval_k: RAG检索返回的文档数量
        """
        # 初始化向量存储
        self.vector_store = SurveyVectorStore(
            persist_directory=vector_store_dir,
            collection_name="exemplary_surveys"
        )
        
        # 尝试加载向量存储
        try:
            self.vector_store.create_vector_store()
            print("Success: Vector store loaded successfully")
            self.has_vector_store = True
        except Exception as e:
            print(f"Warning: Vector store loading failed: {e}")
            print("Note: Vector database is not initialized, RAG feature will not be used")
            print("To enable RAG, run: python init_vector_store.py")
            self.has_vector_store = False
        
        # 初始化问卷创建链
        # 使用更快的模型进行生成
        generation_model = "qwen-flash" if llm_model == "qwen-max" else llm_model
        self.chain = SurveyCreationChain(
            vector_store=self.vector_store,
            llm_model=generation_model,
            temperature=temperature,
            retrieval_k=retrieval_k
        )
        
        # 初始化需求扩写链
        from langchain_dashscope import ChatDashScope
        self.enhancement_llm = ChatDashScope(
            model=llm_model,
            temperature=0.5  # 较低温度确保扩写更稳定
        )
    
    def enhance_requirement(self, user_input: str) -> str:
        """
        需求扩写：作为行业专家帮助用户改写和完善需求
        
        Args:
            user_input: 用户的原始需求
            
        Returns:
            扩写后的需求
        """
        print(f"\n开始需求扩写...")
        print(f"原始需求: {user_input}")
        
        from langchain_core.prompts import ChatPromptTemplate
        
        enhancement_prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一位资深的调查问卷设计专家。

请将用户的问卷需求改写并优化，使其：
1. 更加专业和严谨
2. 突出调查的核心目标和价值
3. 清晰定义目标受众和调查范围
4. 保持简洁（1-3句话）

用专业且易懂的语言重述需求。"""),
            ("user", "用户需求：{user_input}")
        ])
        
        try:
            messages = enhancement_prompt.format_messages(user_input=user_input)
            result = self.enhancement_llm.invoke(messages)
            
            enhanced_text = result.content if hasattr(result, 'content') else str(result)
            print(f"[OK] 扩写完成")
            print(f"扩写结果: {enhanced_text}")
            
            return enhanced_text
            
        except Exception as e:
            print(f"[ERROR] 需求扩写失败，使用原始输入: {e}")
            return user_input
    
    def create_survey(
        self,
        user_input: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建问卷
        
        Args:
            user_input: 用户输入的主题和需求
            additional_context: 额外的上下文信息（可选）
            
        Returns:
            生成的问卷（字典格式）
        """
        print(f"\n开始生成问卷...")
        print(f"主题: {user_input}")
        
        try:
            # 使用链生成问卷
            survey = self.chain.generate_survey(
                user_input=user_input,
                additional_context=additional_context
            )
            
            # 验证生成的问卷格式
            if not survey or not isinstance(survey, dict):
                raise ValueError("返回的问卷格式不正确")
            
            if 'questions' not in survey or not survey.get('questions'):
                raise ValueError("问卷中没有包含任何问题")
            
            # 验证每个问题的有效性
            valid_questions = []
            for q in survey.get('questions', []):
                if not q.get('text'):
                    print(f"警告: 跳过无效问题（无文本）")
                    continue
                
                qtype = q.get('type', '')
                # 验证选择题必须有选项
                if qtype in ['单选题', '多选题']:
                    if not q.get('options') or len(q.get('options', [])) < 2:
                        print(f"警告: 跳过无效问题 {q.get('text', '')[:50]}...（选项不足）")
                        continue
                
                # 验证量表题必须有范围
                if qtype == '量表题':
                    if not q.get('scale_min') or not q.get('scale_max'):
                        print(f"警告: 跳过无效问题 {q.get('text', '')[:50]}...（量表范围未定义）")
                        continue
                
                valid_questions.append(q)
            
            if not valid_questions:
                raise ValueError("所有生成的问题都无效")
            
            # 重新分配连续的题号
            for i, question in enumerate(valid_questions):
                question['id'] = i + 1
            
            survey['questions'] = valid_questions
            print(f"[OK] 问卷生成完成，包含 {len(valid_questions)} 个有效问题")
            
            return survey
            
        except Exception as e:
            print(f"\n[ERROR] 生成问卷时发生错误: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def create_survey_with_refs(
        self,
        user_input: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Dict[str, Any], List[Document]]:
        """
        创建问卷并返回参考文档
        
        Args:
            user_input: 用户输入的主题和需求
            additional_context: 额外的上下文信息
            
        Returns:
            (生成的问卷, 检索到的参考文档)
        """
        print(f"\n开始生成问卷并检索参考文档...")
        print(f"主题: {user_input}")
        
        # 使用RAG生成问卷并获取参考文档
        survey, retrieved_docs = self.chain.generate_with_rag(
            topic=user_input,
            context_info=additional_context
        )
        
        print(f"检索到 {len(retrieved_docs)} 个参考案例")
        print("问卷生成完成")
        
        return survey, retrieved_docs
    
    def format_survey_json(self, survey: Dict[str, Any], indent: int = 2) -> str:
        """
        格式化问卷为JSON字符串
        
        Args:
            survey: 问卷字典
            indent: JSON缩进
            
        Returns:
            格式化的JSON字符串
        """
        return json.dumps(survey, ensure_ascii=False, indent=indent)
    
    def save_survey_to_file(
        self,
        survey: Dict[str, Any],
        filepath: str = "generated_survey.json"
    ) -> str:
        """
        保存问卷到JSON文件
        
        Args:
            survey: 问卷字典
            filepath: 保存路径
            
        Returns:
            保存的文件路径
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(survey, f, ensure_ascii=False, indent=2)
        
        return filepath


def main():
    """测试和演示"""
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    print("=" * 60)
    print("问卷生成服务测试")
    print("=" * 60)
    
    try:
        # 创建服务实例
        print("\n初始化服务...")
        service = SurveyService(
            llm_model="qwen-max",
            temperature=0.7,
            retrieval_k=3
        )
        
        # 测试数据
        test_topics = [
            "用户满意度调查",
            "产品功能需求调研"
        ]
        
        for topic in test_topics:
            print("\n" + "=" * 60)
            print(f"测试主题: {topic}")
            print("=" * 60)
            
            # 生成问卷
            survey, refs = service.create_survey_with_refs(topic)
            
            # 显示参考文档
            print(f"\n【参考文档】")
            for i, doc in enumerate(refs, 1):
                print(f"\n参考 {i}:")
                print(f"内容: {doc.page_content[:150]}...")
            
            # 显示问卷JSON
            print(f"\n【生成的问卷】")
            formatted_json = service.format_survey_json(survey)
            print(formatted_json)
            
            # 保存到文件
            filename = f"survey_{topic.replace(' ', '_')}.json"
            saved_path = service.save_survey_to_file(survey, filename)
            print(f"\n问卷已保存到: {saved_path}")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

