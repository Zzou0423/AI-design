"""
问卷创建链模块

使用 RAG + LLM 生成高质量问卷
"""

import json
import os
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 使用 dashscope SDK 直接调用
import dashscope
from dashscope import Generation

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_dashscope import ChatDashScope

from app.core.vector_store import SurveyVectorStore


class SurveyCreationChain:
    """问卷创建链
    
    使用RAG检索相关问卷案例，然后使用LLM生成新问卷
    """
    
    def __init__(
        self,
        vector_store: Optional[SurveyVectorStore] = None,
        llm_model: str = "qwen-turbo",
        temperature: float = 0.7,
        retrieval_k: int = 3
    ):
        """
        初始化问卷创建链
        
        Args:
            vector_store: 向量存储实例（如果不提供，将使用默认配置创建）
            llm_model: LLM模型名称
            temperature: 温度参数
            retrieval_k: RAG检索返回的文档数量
        """
        # 初始化向量存储
        if vector_store is None:
            self.vector_store = SurveyVectorStore()
            try:
                # 尝试加载已有的向量存储
                self.vector_store.create_vector_store()
            except Exception as e:
                print(f"Warning: Unable to load vector store: {e}")
                print("Please run python init_vector_store.py to initialize vector database")
        else:
            self.vector_store = vector_store
        
        # 初始化DashScope LLM
        self.llm = ChatDashScope(
            model=llm_model,
            temperature=temperature
        )
        
        self.retrieval_k = retrieval_k
        
        # 创建输出解析器和自定义解析器
        self.output_parser = JsonOutputParser()
        self.custom_parser = self._create_custom_parser()
        
        # 创建提示词模板
        self.prompt_template = self._create_prompt_template()
        
        # 创建链
        self.chain = self._create_chain()
    
    def _create_prompt_template(self) -> ChatPromptTemplate:
        """创建提示词模板"""
        
        system_role = """你是一位经验丰富的问卷设计专家，擅长创建高质量、科学严谨的调查问卷。

你的职责：
1. 深入理解用户的问卷需求
2. 结合专业知识库中的优秀问卷案例
3. 设计符合最佳实践的问卷
4. 确保问题逻辑清晰、表述精准

你的专业领域包括：
- 市场调研问卷设计
- 用户满意度调查
- 产品体验评估
- 学术研究问卷
- 员工调研问卷
- 客户需求分析

你的设计原则：
1. 问题清晰明确，避免歧义
2. 逻辑严谨，问题排序合理
3. 避免引导性和诱导性问题
4. 考虑受访者的认知负担
5. 遵循问卷设计最佳实践
6. 根据用户的具体需求定制问卷内容"""

        human_template = """请根据以下信息为我创建一个专业的调查问卷：

**用户需求描述：**
{user_input}

**参考案例（从知识库检索）：**
{retrieved_context}

**任务要求：**
1. 仔细分析用户的问卷需求和场景
2. 如果提供了参考案例，请参考其设计思路
3. 设计问卷时要考虑用户的具体场景和目的
4. 问题数量控制在8-12个，确保受访者能在合理时间内完成
5. 根据场景选择合适的题型（单选、多选、量表、开放等）
6. 对于选择题，必须确保选项完整且合理，可以添加"其他"选项
7. 确保每个问题都有明确的可交互元素（选项、输入框等），避免生成无效问题

**输出格式（JSON）：**
{{
    "title": "问卷标题（根据需求定制）",
    "description": "问卷描述和目的（说明调查的具体目的）",
    "target_audience": "目标受众说明（清晰定义目标人群）",
    "estimated_time": "预计完成时间（如：5-10分钟）",
    "questions": [
        {{
            "id": 1,
            "type": "单选题|多选题|量表题|开放式问题",
            "text": "问题题干（清晰、明确）",
            "required": true,
            "options": ["选项1", "选项2", ...],  # 仅选择题需要
            "scale_min": 1,  # 仅量表题需要
            "scale_max": 5,  # 仅量表题需要
            "scale_labels": {{"1": "完全不满意", "5": "完全满意"}}  # 仅量表题需要
        }}
    ],
    "design_notes": "设计说明和注意事项（说明设计思路和关键考虑）"
}}

{format_instructions}"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_role),
            ("human", human_template)
        ])
        
        return prompt
    
    def _create_custom_parser(self):
        """创建自定义JSON解析器，处理LLM可能输出的额外文本"""
        import json
        import re
        
        class CustomJsonParser:
            def __init__(self):
                self.original_parser = JsonOutputParser()
            
            def get_format_instructions(self):
                return self.original_parser.get_format_instructions()
            
            def parse(self, text: str) -> Dict[str, Any]:
                # 尝试提取JSON部分
                json_text = self._extract_json(text)
                
                # 修复常见JSON错误
                json_text = self._fix_json_errors(json_text)
                
                # 解析JSON
                try:
                    result = json.loads(json_text)
                    return result
                except json.JSONDecodeError as e:
                    # 尝试更激进的修复
                    json_text_fixed = self._try_aggressive_fix(json_text)
                    try:
                        result = json.loads(json_text_fixed)
                        return result
                    except Exception as e2:
                        # 保存问题 JSON 用于调试
                        with open("debug_failed_json.txt", "w", encoding="utf-8") as f:
                            f.write(json_text)
                        raise
            
            def invoke(self, input, config=None):
                """适配LangChain的输出解析器接口"""
                # 输入可能是一个包含多个生成结果的列表
                if isinstance(input, list):
                    # 获取第一个结果的内容
                    result_text = input[0].text if hasattr(input[0], 'text') else str(input[0])
                elif hasattr(input, 'content'):
                    result_text = input.content
                else:
                    result_text = str(input)
                
                return self.parse(result_text)
            
            def _extract_json(self, text: str) -> str:
                """从文本中提取JSON部分"""
                # 尝试找到 ```json ... ``` 模式
                json_pattern = r'```json\s*(.*?)\s*```'
                match = re.search(json_pattern, text, re.DOTALL)
                if match:
                    return match.group(1).strip()
                
                # 尝试找到完整的 JSON 对象（智能括号匹配）
                start = text.find('{')
                if start == -1:
                    return text.strip()
                
                # 从第一个 { 开始，智能找到匹配的最后一个 }
                brace_count = 0
                i = start
                while i < len(text):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return text[start:i+1].strip()
                    i += 1
                
                # 如果没找到完整的 JSON，返回从 { 到末尾的内容
                return text[start:].strip()
            
            def _fix_json_errors(self, json_text: str) -> str:
                """修复常见的JSON错误"""
                print(f"[DEBUG] Before fixing: {json_text[:100]}...")
                
                # 1. 修复所有罗马数字和特殊字符为数字
                json_text = json_text.replace('Ⅰ', '0')  # 罗马数字 1
                json_text = json_text.replace('Ⅱ', '2')
                json_text = json_text.replace('Ⅲ', '3')
                json_text = json_text.replace('Ⅳ', '4')
                json_text = json_text.replace('Ⅴ', '5')
                json_text = json_text.replace('–', '-')  # 特殊破折号
                json_text = json_text.replace('—', '-')  # em 破折号
                
                # 2. 替换所有非标准空白字符为空格
                # 包括全角空格、不间断空格等
                json_text = re.sub(r'[\u00A0\u2000-\u200B\uFEFF]', ' ', json_text)
                
                # 3. 修复前导零的数字（如 01 → 1）
                # 匹配 ": 01," 或 ": 01}" 这样的模式
                json_text = re.sub(r':\s+0+(\d+)', r': \1', json_text)
                print(f"[DEBUG] After leading zero fix: {json_text[:100]}...")
                
                # 4. 修复问题字段（移除未闭合的值）
                # 查找 scale_min: 后面跟非数字的情况（但不影响正常的数字）
                print(f"[DEBUG] Before regex 276: {json_text[:100]}...")
                # 只匹配 scale_min: 后面跟非数字的情况，比如 "scale_min": abc 或 "scale_min": 
                # 使用更精确的正则表达式，避免匹配正常的数字
                # 修复：使用更精确的正则表达式，只匹配非数字的情况
                # 匹配 "scale_min": 后面跟非数字的情况，比如 "scale_min": abc 或 "scale_min": 
                # 使用更精确的正则表达式，避免匹配正常的数字
                # 修复：使用更精确的正则表达式，只匹配非数字的情况
                # 匹配 "scale_min": 后面跟非数字的情况，比如 "scale_min": abc 或 "scale_min": 
                # 使用更精确的正则表达式，避免匹配正常的数字
                # 修复：使用更精确的正则表达式，只匹配非数字的情况
                # 匹配 "scale_min": 后面跟非数字的情况，比如 "scale_min": abc 或 "scale_min": 
                # 使用更精确的正则表达式，避免匹配正常的数字
                # 修复：只匹配真正的非数字值，不匹配空格
                json_text = re.sub(r'"scale_min":\s*[a-zA-Z_]+', r'"scale_min": 0', json_text)
                print(f"[DEBUG] After regex 276: {json_text[:100]}...")
                json_text = re.sub(r'"scale_max":\s*[a-zA-Z_]+', r'"scale_max": 5', json_text)
                
                # 5. 修复值中的特殊空白字符
                json_text = re.sub(r':\s+(\d)', r': \1', json_text)  # 修复非标准空格后的数字
                
                # 3. 修复注释：移除 // 和 /* */ 注释
                json_text = re.sub(r'//.*', '', json_text)
                json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)
                
                # 4. 修复未转义的引号和特殊字符
                # 在值中的 & 符号
                json_text = re.sub(r'(["\'])(.*?)(&)(.*?)\1', r'\1\2&amp;\4\1', json_text)
                
                # 5. 移除末尾的多余说明
                last_brace = json_text.rfind('}')
                if last_brace > 0:
                    after_brace = json_text[last_brace + 1:].strip()
                    if after_brace and not after_brace.startswith(','):
                        json_text = json_text[:last_brace + 1]
                
                # 6. 清理多余的空行和空格
                lines = json_text.split('\n')
                cleaned_lines = []
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('//'):
                        cleaned_lines.append(line)
                
                json_text = '\n'.join(cleaned_lines)
                
                return json_text
            
            def _try_fix_json(self, json_text: str, error_line: int, error_col: int) -> str:
                """尝试修复 JSON 错误"""
                # 移除末尾的逗号（在最后一个数组/对象元素之后）
                json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
                
                return json_text
            
            def _try_aggressive_fix(self, json_text: str) -> str:
                """尝试激进的 JSON 修复"""
                # 1. 移除末尾的逗号
                json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
                
                # 2. 尝试找到完整的 JSON（更智能的括号匹配）
                brace_count = 0
                bracket_count = 0
                in_string = False
                escape_next = False
                
                end_pos = len(json_text)
                for i, char in enumerate(json_text):
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"':
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                        elif char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                    
                    # 如果所有括号都闭合了，且后面还有内容，说明有额外文本
                    if brace_count == 0 and bracket_count == 0 and not in_string and char in [',', '\n', ' ', '\t']:
                        # 寻找下一个非空白字符
                        j = i + 1
                        while j < len(json_text) and json_text[j] in [' ', '\t', '\n']:
                            j += 1
                        if j < len(json_text) and json_text[j] not in ['{', '[', '(', '[', '<']:
                            end_pos = i + 1
                            break
                
                json_text = json_text[:end_pos].rstrip()
                
                # 3. 修复未闭合的字符串
                if json_text.count('"') % 2 != 0:
                    json_text += '"'
                
                # 4. 确保 JSON 以 } 结束
                while brace_count > 0:
                    json_text += '}'
                    brace_count -= 1
                
                # 5. 确保数组以 ] 结束
                while bracket_count > 0:
                    json_text += ']'
                    bracket_count -= 1
                
                return json_text
        
        return CustomJsonParser()
    
    def _create_chain(self):
        """创建RAG链"""
        
        def format_context(docs: List[Document]) -> str:
            """格式化检索到的文档为上下文"""
            if not docs:
                return "（未找到相关案例，将基于通用最佳实践设计问卷）"
            
            context = "以下是相似主题的优秀问卷案例，请参考其设计思路：\n\n"
            for i, doc in enumerate(docs, 1):
                context += f"案例 {i}:\n{doc.page_content}\n"
                if doc.metadata:
                    context += f"元数据: {doc.metadata}\n"
                context += "\n---\n\n"
            
            return context
        
        def retrieve_context(user_input: str) -> str:
            """从向量库检索相关上下文"""
            try:
                # 检查向量存储是否初始化
                if not self.vector_store.vector_store:
                    return "（向量库未初始化，未提供参考案例）"
                
                results = self.vector_store.similarity_search(
                    query=user_input,
                    k=self.retrieval_k
                )
                return format_context(results)
            except ValueError as e:
                # 向量库未初始化
                return "（向量库未初始化，未提供参考案例）"
            except Exception as e:
                print(f"Warning: Error retrieving context: {e}")
                return "Retrieval failed, will continue to generate survey using general knowledge"
        
        # 获取格式指令
        format_instructions = self.output_parser.get_format_instructions()
        
        # 创建Runnable链
        chain = (
            RunnablePassthrough.assign(
                retrieved_context=lambda x: retrieve_context(x["user_input"]),
            )
            | RunnablePassthrough.assign(
                format_instructions=lambda x: format_instructions
            )
            | self.prompt_template
            | self.llm
            | self.output_parser
        )
        
        return chain
    
    def generate_survey(
        self,
        user_input: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成问卷
        
        Args:
            user_input: 用户输入的主题和需求
            additional_context: 额外的上下文信息（可选）
            
        Returns:
            生成的问卷（字典格式）
        """
        # 准备输入
        input_data = {
            "user_input": user_input
        }
        
        # 添加额外的上下文
        if additional_context:
            context_str = "\n**额外需求：**\n"
            for key, value in additional_context.items():
                context_str += f"- {key}: {value}\n"
            input_data["user_input"] += context_str
        
        try:
            # 运行链
            print("执行生成链...")
            result = self.chain.invoke(input_data)
            
            # 验证结果
            if not result or not isinstance(result, dict):
                raise ValueError("链返回结果不是有效的字典")
            
            # 确保有必需的字段
            if 'questions' not in result:
                raise ValueError("结果中缺少 'questions' 字段")
            
            print(f"[OK] 链执行成功，生成了 {len(result.get('questions', []))} 个问题")
            return result
            
        except Exception as e:
            print(f"\n[ERROR] 链执行错误: {e}")
            print("尝试备用方案...")
            
            try:
                # 如果链执行失败，尝试直接调用LLM并手动解析
                llm_chain = (
                    RunnablePassthrough.assign(
                        retrieved_context=lambda x: self._retrieve_context(x["user_input"]),
                    )
                    | RunnablePassthrough.assign(
                        format_instructions=lambda x: self.output_parser.get_format_instructions()
                    )
                    | self.prompt_template
                    | self.llm
                )
                
                print("调用备用LLM链...")
                response = llm_chain.invoke(input_data)
                
                if hasattr(response, 'content'):
                    result = self.custom_parser.parse(response.content)
                else:
                    result = self.custom_parser.parse(str(response))
                
                print(f"[OK] 备用方案成功，生成了 {len(result.get('questions', []))} 个问题")
                return result
                
            except Exception as e2:
                print(f"\n[ERROR] 备用方案也失败了: {e2}")
                raise
    
    def _retrieve_context(self, user_input: str) -> str:
        """从向量库检索相关上下文"""
        try:
            # 检查向量存储是否初始化
            if not self.vector_store.vector_store:
                return "Vector database not initialized, no reference cases available"
            
            results = self.vector_store.similarity_search(
                query=user_input,
                k=self.retrieval_k
            )
            return self._format_context(results)
        except ValueError as e:
            return "Vector database not initialized, no reference cases available"
        except Exception as e:
            print(f"Warning: Error retrieving context: {e}")
            return "Retrieval failed, will continue to generate survey using general knowledge"
    
    def _format_context(self, docs: List[Document]) -> str:
        """格式化检索到的文档为上下文"""
        if not docs:
            return "No relevant cases found, will design based on general best practices"
        
        context = "Here are excellent survey case examples for similar topics, please refer to their design approach:\n\n"
        for i, doc in enumerate(docs, 1):
            context += f"Example {i}:\n{doc.page_content}\n"
            if doc.metadata:
                context += f"Metadata: {doc.metadata}\n"
            context += "\n---\n\n"
        
        return context
    
    def generate_with_rag(
        self,
        topic: str,
        context_info: Optional[Dict[str, Any]] = None
    ) -> tuple[Dict[str, Any], List[Document]]:
        """
        使用RAG生成问卷，并返回检索到的参考文档
        
        Args:
            topic: 调查主题
            context_info: 额外的上下文信息
            
        Returns:
            (生成的问卷, 检索到的参考文档)
        """
        # 检索相关文档
        retrieved_docs = self.vector_store.similarity_search(
            query=topic,
            k=self.retrieval_k
        )
        
        # 生成问卷
        survey = self.generate_survey(topic, context_info)
        
        return survey, retrieved_docs
    
    def format_survey_output(self, survey: Dict[str, Any]) -> str:
        """
        格式化问卷输出为可读文本
        
        Args:
            survey: 问卷字典
            
        Returns:
            格式化的文本
        """
        output = []
        output.append("=" * 60)
        output.append(f"问卷标题: {survey.get('title', 'N/A')}")
        output.append("=" * 60)
        output.append(f"\n描述: {survey.get('description', 'N/A')}")
        output.append(f"目标受众: {survey.get('target_audience', 'N/A')}")
        output.append(f"预计完成时间: {survey.get('estimated_time', 'N/A')} 分钟")
        
        output.append("\n" + "-" * 60)
        output.append("问题列表")
        output.append("-" * 60)
        
        questions = survey.get('questions', [])
        for q in questions:
            q_id = q.get('id', 'N/A')
            q_type = q.get('type', 'N/A')
            q_text = q.get('text', 'N/A')
            q_required = "【必填】" if q.get('required', False) else "【选填】"
            
            output.append(f"\n问题 {q_id}. {q_text} ({q_type}) {q_required}")
            
            # 处理选项
            if q_type in ['单选题', '多选题']:
                options = q.get('options', [])
                for i, opt in enumerate(options, 1):
                    output.append(f"  {i}. {opt}")
            
            # 处理量表
            elif q_type == '量表题':
                scale_min = q.get('scale_min', 1)
                scale_max = q.get('scale_max', 5)
                output.append(f"  量表范围: {scale_min} - {scale_max}")
                scale_labels = q.get('scale_labels', {})
                if scale_labels:
                    for scale, label in scale_labels.items():
                        output.append(f"    {scale}: {label}")
        
        # 设计说明
        design_notes = survey.get('design_notes')
        if design_notes:
            output.append("\n" + "-" * 60)
            output.append("设计说明")
            output.append("-" * 60)
            output.append(design_notes)
        
        output.append("\n" + "=" * 60)
        
        return "\n".join(output)


def main():
    """测试和演示使用"""
    import sys
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # 测试主题
    test_topic = "用户满意度调查"
    if len(sys.argv) > 1:
        test_topic = sys.argv[1]
    
    print(f"正在生成问卷: {test_topic}\n")
    
    try:
        # 创建链
        chain = SurveyCreationChain(
            llm_model="qwen-max",
            temperature=0.7,
            retrieval_k=3
        )
        
        # 生成问卷
        print("生成中...")
        survey, retrieved_docs = chain.generate_with_rag(test_topic)
        
        # 显示检索到的参考文档
        print(f"\n检索到 {len(retrieved_docs)} 个相关案例\n")
        
        # 显示生成的问卷
        formatted_output = chain.format_survey_output(survey)
        print(formatted_output)
        
        # 保存为JSON
        output_file = "generated_survey.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(survey, f, ensure_ascii=False, indent=2)
        print(f"\n问卷已保存到: {output_file}")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

