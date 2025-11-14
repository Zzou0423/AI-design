"""
通用问卷答案批量生成脚本
自动为任意主题的问卷生成符合真实场景的测试答案

功能：
1. 自动列出所有可用问卷
2. 让用户选择要生成答案的问卷
3. 自定义生成数量
4. 根据问卷主题智能生成多样化的身份设定
5. 批量生成高质量的测试答案
6. 支持并发生成，大幅提升速度

使用场景：
- 问卷测试：在问卷发布前进行功能测试
- 分析演示：生成样本数据用于展示分析功能
- 压力测试：测试系统对大量数据的处理能力
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# 加载环境变量
load_dotenv()

# 导入DashScope
import dashscope
from dashscope import Generation


class ResponseGenerator:
    """通用答案生成器 - 支持并发生成"""
    
    def __init__(self, llm_model: str = "qwen-flash", temperature: float = 0.8, max_workers: int = 5):
        """
        初始化答案生成器
        
        Args:
            llm_model: LLM模型名称（默认：qwen-flash）
            temperature: 温度参数（默认：0.8，越高越多样化）
            max_workers: 最大并发数（默认：5）
        """
        self.model = llm_model
        self.temperature = temperature
        self.max_workers = max_workers
    
    def generate_response(
        self, 
        survey_title: str,
        questions: List[Dict], 
        identity: str,
        tendency: str = "neutral"
    ) -> Dict[str, Any]:
        """
        生成一个问卷回答
        
        Args:
            survey_title: 问卷标题
            questions: 问卷问题列表
            identity: 身份设定
            tendency: 回答倾向（positive/negative/neutral/mixed）
            
        Returns:
            答案字典
        """
        # 准备问题JSON（精简版，只包含必要信息）
        simplified_questions = []
        for q in questions:
            simplified_q = {
                "id": q.get("id"),
                "type": q.get("type"),
                "text": q.get("text"),
            }
            if "options" in q:
                simplified_q["options"] = q["options"]
            if q.get("type") == "量表题":
                simplified_q["scale_range"] = f"{q.get('scale_min', 1)}-{q.get('scale_max', 5)}"
            simplified_questions.append(simplified_q)
        
        questions_json = json.dumps(simplified_questions, ensure_ascii=False, indent=2)
        
        # 根据倾向生成指导语
        tendency_instructions = {
            "positive": """
【回答倾向】：整体积极正面
- 量表题：倾向于打4-5分（高分）
- 选择题：选择正面、满意、认可的选项
- 开放题：表达满意、赞赏、积极的观点，可以提一些小建议但整体语气积极""",
            "negative": """
【回答倾向】：整体消极负面
- 量表题：倾向于打1-2分（低分）
- 选择题：选择负面、不满、批评的选项
- 开放题：表达不满、失望、批评的观点，具体指出问题和不足""",
            "neutral": """
【回答倾向】：中立客观
- 量表题：倾向于打3分左右（中等）
- 选择题：选择中立、客观的选项
- 开放题：平衡地表达优缺点，既有肯定也有建议""",
            "mixed": """
【回答倾向】：褒贬参半
- 量表题：分数分布在2-4分之间，有高有低
- 选择题：既选正面也选负面的选项
- 开放题：既表达满意的地方，也指出不满的地方，真实反映复杂感受"""
        }
        
        tendency_guide = tendency_instructions.get(tendency, tendency_instructions["neutral"])
        
        # 构建带倾向的prompt
        full_prompt = f"""你是{identity}，正在填写一份「{survey_title}」调查问卷。

{tendency_guide}

问卷问题：
{questions_json}

请根据你的身份背景和指定的回答倾向，填写完整的问卷答案。以JSON格式返回，使用问题的id作为key。

答题规则：
- 单选题：返回单个选项字符串（从options中选择一个）
- 多选题：返回选项数组（从options中选择多个）
- 量表题：返回数值（在指定的scale_range范围内）
- 开放式问题：返回文本（50-200字的真实感受和具体描述）

注意事项：
1. **严格遵循指定的回答倾向**，确保答案整体基调一致
2. 答案要符合你的身份设定，逻辑连贯
3. 开放题要写得具体、真实、有细节，符合指定倾向
4. 量表打分要符合倾向要求
5. 只返回JSON格式的答案，不要任何其他说明文字

返回格式示例：
{{
  "1": "选项A",
  "2": ["选项1", "选项2"],
  "3": 4,
  "4": "这是一段详细的文字回答，包含具体的例子和感受..."
}}
"""
        
        try:
            # 调用DashScope API
            response = Generation.call(
                model=self.model,
                prompt=full_prompt,
                temperature=self.temperature,
                result_format='message'
            )
            
            if response.status_code == 200:
                # 提取答案内容
                content = response.output.choices[0].message.content
                
                # 清理可能的markdown代码块标记
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    parts = content.split("```")
                    if len(parts) > 1:
                        content = parts[1].strip()
                
                # 尝试解析JSON
                answers = json.loads(content)
                return answers
            else:
                print(f"       [ERROR] API调用失败: {response.message}")
                return {}
        except json.JSONDecodeError as e:
            print(f"       [ERROR] JSON解析失败: {e}")
            if 'content' in locals():
                print(f"       [DEBUG] 响应内容: {content[:200]}")
            return {}
        except Exception as e:
            print(f"       [ERROR] 调用失败: {e}")
            return {}
    
    def generate_identities(self, survey_title: str, count: int = 10) -> List[str]:
        """
        根据问卷主题智能生成多样化的身份设定
        
        Args:
            survey_title: 问卷标题
            count: 要生成的身份数量
            
        Returns:
            身份设定列表
        """
        print(f"\n[INFO] 正在为「{survey_title}」生成身份设定...")
        
        # 使用LLM生成符合主题的身份
        prompt = f"""请为「{survey_title}」这个调研问卷，生成{count}个多样化的受访者身份设定。

要求：
1. 身份要符合该调研的目标受众
2. 每个身份要有明确的特征（年龄/职业/背景/经验等）
3. 身份之间要有差异性，覆盖不同类型的受访者
4. 每个身份用一句话描述（30-60字）
5. 返回JSON数组格式

示例格式：
[
  "一位25岁的互联网产品经理，工作3年，经常需要加班但热爱自己的工作",
  "一位35岁的全职妈妈，有两个孩子，注重家庭生活质量",
  ...
]

请只返回JSON数组，不要其他说明。"""

        try:
            response = Generation.call(
                model=self.model,
                prompt=prompt,
                temperature=0.8,
                result_format='message'
            )
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                
                # 清理markdown代码块
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    parts = content.split("```")
                    if len(parts) > 1:
                        content = parts[1].strip()
                
                identities = json.loads(content)
                print(f"[OK] 已生成 {len(identities)} 个身份设定")
                return identities
            else:
                print(f"[WARN] LLM生成身份失败，使用通用身份模板")
                return self._get_generic_identities(count)
                
        except Exception as e:
            print(f"[WARN] 生成身份时出错: {e}，使用通用身份模板")
            return self._get_generic_identities(count)
    
    def _get_generic_identities(self, count: int) -> List[str]:
        """
        获取通用身份模板（fallback）
        
        Args:
            count: 身份数量
            
        Returns:
            通用身份列表
        """
        generic_identities = [
            "一位25岁的年轻上班族，对新鲜事物充满好奇",
            "一位35岁的中年职场人士，有丰富的生活经验",
            "一位20岁的大学生，思维活跃，关注潮流",
            "一位45岁的资深从业者，专业知识丰富",
            "一位30岁的自由职业者，生活方式灵活",
            "一位40岁的企业管理者，注重效率和品质",
            "一位28岁的创业者，充满激情和想法",
            "一位50岁的行业专家，见解独到",
            "一位22岁的应届毕业生，刚步入社会",
            "一位38岁的家庭主要成员，注重家庭和工作平衡",
            "一位32岁的技术工作者，善于分析和思考",
            "一位26岁的设计师，追求美感和创意",
            "一位42岁的教育工作者，有耐心和责任心",
            "一位29岁的销售人员，善于沟通和交流",
            "一位36岁的公务员，工作稳定，注重规范"
        ]
        return generic_identities[:count]
    
    def generate_response_batch(
        self,
        survey_title: str,
        questions: List[Dict],
        identities: List[str],
        tendencies: List[str],
        start_index: int = 0
    ) -> List[Tuple[int, Dict[str, Any], str, str]]:
        """
        并发批量生成答案
        
        Args:
            survey_title: 问卷标题
            questions: 问题列表
            identities: 身份列表
            tendencies: 倾向列表（与identities对应）
            start_index: 起始索引（用于显示进度）
            
        Returns:
            [(索引, 答案, 身份, 倾向), ...]
        """
        results = []
        
        def generate_single(idx: int, identity: str, tendency: str):
            """生成单个答案的包装函数"""
            try:
                answers = self.generate_response(survey_title, questions, identity, tendency)
                return (idx, answers, identity, tendency, True)
            except Exception as e:
                return (idx, None, identity, tendency, False)
        
        # 使用线程池并发生成
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_idx = {
                executor.submit(generate_single, i, identities[i], tendencies[i]): i
                for i in range(len(identities))
            }
            
            # 收集结果
            for future in as_completed(future_to_idx):
                result = future.result()
                results.append(result)
        
        # 按索引排序
        results.sort(key=lambda x: x[0])
        return results


def list_available_surveys() -> List[Tuple[str, str, Path]]:
    """
    列出所有可用的问卷
    
    Returns:
        (问卷标题, 问卷ID, 文件路径) 的列表
    """
    surveys_dir = Path("data/surveys")
    if not surveys_dir.exists():
        return []
    
    surveys = []
    for survey_file in surveys_dir.glob("*.json"):
        try:
            with open(survey_file, 'r', encoding='utf-8') as f:
                survey_data = json.load(f)
            surveys.append((
                survey_data.get("title", "未命名问卷"),
                survey_data.get("id", ""),
                survey_file
            ))
        except Exception:
            continue
    
    return sorted(surveys, key=lambda x: x[0])


def select_survey() -> Tuple[Dict[str, Any], Path]:
    """
    让用户选择要生成答案的问卷
    
    Returns:
        (问卷数据, 文件路径)
    """
    surveys = list_available_surveys()
    
    if not surveys:
        print("\n[ERROR] 未找到任何问卷文件")
        print("请先在系统中创建问卷，问卷会保存在 data/surveys/ 目录下")
        return None, None
    
    print("\n可用的问卷：")
    print("-" * 70)
    for idx, (title, survey_id, _) in enumerate(surveys, 1):
        # 检查现有答案数
        responses_dir = Path("data/responses") / f"{title}_{survey_id}"
        existing_count = len(list(responses_dir.glob("*.json"))) if responses_dir.exists() else 0
        print(f"{idx}. {title}")
        print(f"   ID: {survey_id} | 现有答案: {existing_count} 份")
    print("-" * 70)
    
    while True:
        try:
            choice = input("\n请选择问卷编号 (输入 q 退出): ").strip()
            if choice.lower() == 'q':
                return None, None
            
            idx = int(choice)
            if 1 <= idx <= len(surveys):
                selected_title, selected_id, selected_path = surveys[idx - 1]
                
                # 加载问卷数据
                with open(selected_path, 'r', encoding='utf-8') as f:
                    survey_data = json.load(f)
                
                print(f"\n✓ 已选择: {selected_title}")
                return survey_data, selected_path
            else:
                print(f"[ERROR] 请输入 1-{len(surveys)} 之间的数字")
        except ValueError:
            print("[ERROR] 请输入有效的数字")
        except Exception as e:
            print(f"[ERROR] 读取问卷失败: {e}")


def main():
    """主函数"""
    print("=" * 80)
    print("🤖 AI 问卷答案批量生成工具")
    print("=" * 80)
    print("\n功能说明：")
    print("  - 自动为任意主题的问卷生成高质量测试答案")
    print("  - 根据问卷主题智能生成多样化的受访者身份")
    print("  - 支持所有题型（单选、多选、量表、开放题）")
    print("  - 生成的答案逻辑一致、真实自然")
    
    # 检查API Key
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("\n" + "=" * 80)
        print("[ERROR] DASHSCOPE_API_KEY 未配置")
        print("\n请执行以下步骤：")
        print("1. 在项目根目录创建 .env 文件")
        print("2. 添加内容：DASHSCOPE_API_KEY=你的API密钥")
        print("3. 保存后重新运行此脚本")
        print("=" * 80)
        return
    
    # 让用户选择问卷
    survey_data, survey_file = select_survey()
    if not survey_data:
        print("\n[INFO] 已退出")
        return
    
    survey_id = survey_data["id"]
    survey_title = survey_data["title"]
    questions = survey_data["questions"]
    
    print(f"\n问卷信息：")
    print(f"  - 标题: {survey_title}")
    print(f"  - 问题数量: {len(questions)}")
    
    # 统计题型
    question_types = {}
    for q in questions:
        q_type = q.get("type", "未知")
        question_types[q_type] = question_types.get(q_type, 0) + 1
    
    print(f"  - 题型分布: ", end="")
    print(" | ".join([f"{t}×{c}" for t, c in question_types.items()]))
    
    # 询问生成数量
    print("\n" + "-" * 80)
    while True:
        try:
            count_input = input("请输入要生成的答案数量 (默认 30，推荐 30-100): ").strip()
            if not count_input:
                total_responses = 30
                break
            total_responses = int(count_input)
            if total_responses <= 0:
                print("[ERROR] 数量必须大于0")
                continue
            if total_responses > 200:
                confirm = input(f"⚠️  生成 {total_responses} 份答案可能需要较长时间，确认继续？(y/n): ")
                if confirm.lower() != 'y':
                    continue
            break
        except ValueError:
            print("[ERROR] 请输入有效的数字")
    
    print(f"\n✓ 将生成 {total_responses} 份答案")
    
    # 选择回答倾向
    print("\n" + "-" * 80)
    print("选择回答倾向（用于验证分析结果的准确性）：")
    print("  1. 积极正面 (positive) - 高满意度、正面评价")
    print("  2. 消极负面 (negative) - 低满意度、负面评价")  
    print("  3. 中立客观 (neutral) - 中等评价、平衡反馈")
    print("  4. 褒贬参半 (mixed) - 混合评价、有好有坏")
    print("  5. 随机分布 (random) - 自动按比例分配不同倾向")
    print("-" * 80)
    
    tendency_map = {
        "1": ("positive", "积极正面"),
        "2": ("negative", "消极负面"),
        "3": ("neutral", "中立客观"),
        "4": ("mixed", "褒贬参半"),
        "5": ("random", "随机分布")
    }
    
    while True:
        tendency_choice = input("请选择倾向 (1-5, 默认5): ").strip()
        if not tendency_choice:
            tendency_choice = "5"
        
        if tendency_choice in tendency_map:
            tendency_mode, tendency_desc = tendency_map[tendency_choice]
            print(f"\n✓ 已选择: {tendency_desc}")
            break
        else:
            print("[ERROR] 请输入 1-5 之间的数字")
    
    # 如果选择随机分布，设置各倾向的比例
    if tendency_mode == "random":
        print("\n[INFO] 随机分布模式：")
        print("  - 40% 积极正面")
        print("  - 30% 中立客观")
        print("  - 20% 褒贬参半")
        print("  - 10% 消极负面")
    
    # 询问并发数
    print("\n" + "-" * 80)
    while True:
        try:
            workers_input = input("并发数 (默认 5，推荐 3-10，越大越快但需要更多API配额): ").strip()
            if not workers_input:
                max_workers = 5
                break
            max_workers = int(workers_input)
            if max_workers <= 0:
                print("[ERROR] 并发数必须大于0")
                continue
            if max_workers > 20:
                print("[WARN] 并发数过大可能导致API限流")
                confirm = input("确认继续？(y/n): ")
                if confirm.lower() != 'y':
                    continue
            break
        except ValueError:
            print("[ERROR] 请输入有效的数字")
    
    print(f"✓ 并发数: {max_workers}")
    
    # 初始化生成器
    print("\n" + "=" * 80)
    print("[1/4] 初始化生成器...")
    generator = ResponseGenerator(llm_model="qwen-flash", temperature=0.8, max_workers=max_workers)
    print(f"✓ 初始化完成（并发数: {max_workers}）")
    
    # 生成身份设定
    print("\n[2/4] 生成受访者身份设定...")
    identity_count = min(15, total_responses)  # 最多生成15个不同身份
    identities = generator.generate_identities(survey_title, identity_count)
    
    # 创建答案保存目录
    responses_dir = Path("data/responses")
    survey_dir = responses_dir / f"{survey_title}_{survey_id}"
    survey_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ 答案将保存到: {survey_dir}")
    
    # 生成答案
    print(f"\n[3/4] 开始生成 {total_responses} 份答案（并发模式）...")
    print("-" * 80)
    
    successful = 0
    failed = 0
    tendency_stats = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
    
    # 预计算随机分布的倾向序列
    if tendency_mode == "random":
        import random
        tendency_sequence = (
            ["positive"] * int(total_responses * 0.4) +
            ["neutral"] * int(total_responses * 0.3) +
            ["mixed"] * int(total_responses * 0.2) +
            ["negative"] * int(total_responses * 0.1)
        )
        # 补足到total_responses
        while len(tendency_sequence) < total_responses:
            tendency_sequence.append("neutral")
        random.shuffle(tendency_sequence)
    
    # 准备所有任务的身份和倾向
    all_identities = []
    all_tendencies = []
    for i in range(total_responses):
        identity = identities[i % len(identities)]
        if tendency_mode == "random":
            current_tendency = tendency_sequence[i]
        else:
            current_tendency = tendency_mode
        all_identities.append(identity)
        all_tendencies.append(current_tendency)
    
    # 倾向标签
    tendency_labels = {
        "positive": "😊",
        "negative": "😞",
        "neutral": "😐",
        "mixed": "🤔"
    }
    
    # 分批并发生成（每批max_workers个）
    batch_size = max_workers * 2  # 每批处理并发数的2倍
    total_batches = (total_responses + batch_size - 1) // batch_size
    
    print(f"💡 使用 {max_workers} 个并发线程，分 {total_batches} 批处理")
    print(f"⏱️  预计耗时: {total_responses / max_workers / 2:.1f}-{total_responses / max_workers:.1f} 分钟")
    print()
    
    start_time = time.time()
    
    try:
        for batch_idx in range(total_batches):
            batch_start = batch_idx * batch_size
            batch_end = min((batch_idx + 1) * batch_size, total_responses)
            batch_count = batch_end - batch_start
            
            print(f"📦 批次 {batch_idx + 1}/{total_batches}: 生成 {batch_start + 1}-{batch_end} 份...")
            
            # 准备当前批次的数据
            batch_identities = all_identities[batch_start:batch_end]
            batch_tendencies = all_tendencies[batch_start:batch_end]
            
            # 并发生成当前批次
            batch_results = generator.generate_response_batch(
                survey_title,
                questions,
                batch_identities,
                batch_tendencies,
                batch_start
            )
            
            # 处理结果并保存
            for idx, answers, identity, current_tendency, success in batch_results:
                global_idx = batch_start + idx
                
                if not success or not answers:
                    failed += 1
                    print(f"  [{global_idx + 1}/{total_responses}] {tendency_labels.get(current_tendency, '')} ✗ 失败")
                    continue
                
                tendency_stats[current_tendency] += 1
                
                # 生成用户ID
                user_id = f"user_{uuid.uuid4().hex[:10]}"
                
                # 构建答案数据
                response_data = {
                    "survey_id": survey_id,
                    "survey_info": {
                        "title": survey_title,
                        "description": survey_data.get("description", "")
                    },
                    "submitted_at": datetime.now().isoformat(),
                    "answers": answers,
                    "user_identity": identity,
                    "response_tendency": current_tendency
                }
                
                # 保存答案
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"{timestamp}_{user_id}_{survey_id}.json"
                filepath = survey_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(response_data, f, ensure_ascii=False, indent=2)
                
                successful += 1
                print(f"  [{global_idx + 1}/{total_responses}] {tendency_labels.get(current_tendency, '')} ✓")
            
            # 显示批次统计
            elapsed = time.time() - start_time
            avg_time = elapsed / (batch_end) if batch_end > 0 else 0
            remaining = (total_responses - batch_end) * avg_time
            print(f"  ⏱️  已用时: {elapsed:.1f}秒 | 预计剩余: {remaining:.1f}秒")
            print()
    
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断，正在保存已生成的答案...")
    except Exception as e:
        print(f"\n[ERROR] 批量生成出错: {e}")
        import traceback
        traceback.print_exc()
    
    # 统计结果
    print("\n" + "=" * 80)
    print("[4/4] 生成完成!")
    print("-" * 80)
    print(f"✓ 成功: {successful} 份")
    if failed > 0:
        print(f"✗ 失败: {failed} 份")
    print(f"📁 保存位置: {survey_dir}")
    print("=" * 80)
    
    # 显示倾向分布统计
    print("\n📊 答案倾向分布统计：")
    print("-" * 80)
    total_actual = sum(tendency_stats.values())
    if total_actual > 0:
        print(f"😊 积极正面: {tendency_stats['positive']} 份 ({tendency_stats['positive']/total_actual*100:.1f}%)")
        print(f"😞 消极负面: {tendency_stats['negative']} 份 ({tendency_stats['negative']/total_actual*100:.1f}%)")
        print(f"😐 中立客观: {tendency_stats['neutral']} 份 ({tendency_stats['neutral']/total_actual*100:.1f}%)")
        print(f"🤔 褒贬参半: {tendency_stats['mixed']} 份 ({tendency_stats['mixed']/total_actual*100:.1f}%)")
        print("-" * 80)
        
        # 预期分析结果提示
        print("\n🔍 预期分析结果：")
        if tendency_mode == "positive":
            print("  ✓ 分析报告应显示：高满意度、积极主题占主导、情感倾向偏正面")
        elif tendency_mode == "negative":
            print("  ✓ 分析报告应显示：低满意度、负面主题占主导、情感倾向偏负面")
        elif tendency_mode == "neutral":
            print("  ✓ 分析报告应显示：中等评价、客观主题、情感倾向中性")
        elif tendency_mode == "mixed":
            print("  ✓ 分析报告应显示：褒贬参半、正负主题混合、情感倾向混合")
        elif tendency_mode == "random":
            print("  ✓ 分析报告应显示：多样化评价、正面主题为主、情感分布较均衡")
        
        print("\n💡 使用建议：")
        print("  1. 在系统中对该问卷进行分析")
        print("  2. 对比分析结果与预期倾向")
        print("  3. 验证分析引擎的准确性")
        print("  4. 检查可视化图表是否符合数据分布")
    
    # 统计总回答数
    existing_responses = len(list(survey_dir.glob("*.json")))
    print(f"\n📊 该问卷现共有 {existing_responses} 份答案")
    print("=" * 80)


if __name__ == "__main__":
    main()

