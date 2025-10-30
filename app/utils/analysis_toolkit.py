"""
分析工具包
将各种分析能力封装为工具，供大模型调用
简洁、模块化的设计
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
from pathlib import Path
import logging

try:
    import numpy as np
    from sklearn.cluster import KMeans
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import LatentDirichletAllocation
    import jieba
    HAS_ML_LIBS = True
except ImportError:
    HAS_ML_LIBS = False

logger = logging.getLogger(__name__)


class AnalysisToolkit:
    """分析工具包 - 将所有分析能力封装为工具"""
    
    def __init__(self):
        """初始化工具包"""
        pass
    
    def tool_cluster_users(self, survey: Dict[str, Any], responses: List[Dict[str, Any]], n_clusters: int = 3) -> Dict[str, Any]:
        """
        工具：用户聚类分析
        对定量问题进行聚类，识别不同类型的用户群体
        
        Returns:
            {
                "clusters": [
                    {
                        "cluster_id": 1,
                        "size": 10,
                        "percentage": 33.3,
                        "characteristics": {"问题1": {"mean": 4.5, "std": 0.5}, ...},
                        "description": "高满意度群体..."
                    }
                ],
                "summary": "识别出3个用户群体..."
            }
        """
        if not HAS_ML_LIBS:
            return {"clusters": [], "summary": "需要sklearn库支持"}
        
        try:
            # 提取量表题
            scale_questions = [q for q in survey.get("questions", []) if q.get("type") == "量表题"]
            if len(scale_questions) < 2:
                return {"clusters": [], "summary": "量表题不足，无法聚类（至少需要2个）"}
            
            # 构建数据矩阵
            data_matrix = []
            question_ids = []
            
            for question in scale_questions:
                q_id = str(question.get("id", ""))
                question_ids.append(q_id)
                values = []
                
                for response in responses:
                    answers = response.get("answers", {})
                    if q_id in answers:
                        try:
                            val = float(answers[q_id])
                            values.append(val)
                        except (ValueError, TypeError):
                            values.append(None)
                    else:
                        values.append(None)
                
                # 用平均值填充缺失值
                valid_values = [v for v in values if v is not None]
                if valid_values:
                    avg = sum(valid_values) / len(valid_values)
                    values = [v if v is not None else avg for v in values]
                    data_matrix.append(values)
            
            if len(data_matrix) < 2:
                return {"clusters": [], "summary": "有效数据不足"}
            
            data_matrix = np.array(data_matrix).T
            
            # 确定聚类数
            n_clusters = min(n_clusters, len(responses) // 3) if len(responses) >= 6 else min(2, len(responses) // 2)
            if n_clusters < 2:
                return {"clusters": [], "summary": "回答数太少，无法聚类"}
            
            # KMeans聚类
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(data_matrix)
            
            # 分析聚类结果
            clusters = []
            for i in range(n_clusters):
                cluster_indices = np.where(cluster_labels == i)[0]
                cluster_data = data_matrix[cluster_indices]
                
                characteristics = {}
                for j, q_id in enumerate(question_ids):
                    question = next((q for q in scale_questions if str(q.get("id")) == q_id), None)
                    if question:
                        values = cluster_data[:, j]
                        characteristics[question.get("text", "")[:50]] = {
                            "mean": float(np.mean(values)),
                            "std": float(np.std(values))
                        }
                
                clusters.append({
                    "cluster_id": i + 1,
                    "size": len(cluster_indices),
                    "percentage": len(cluster_indices) / len(responses) * 100,
                    "characteristics": characteristics
                })
            
            summary = f"识别出{len(clusters)}个用户群体，最大群体占比{max(c['percentage'] for c in clusters):.1f}%"
            return {"clusters": clusters, "summary": summary}
            
        except Exception as e:
            logger.error(f"用户聚类分析失败: {e}")
            return {"clusters": [], "summary": f"聚类分析失败: {str(e)}"}
    
    def tool_extract_themes(self, responses: List[Dict[str, Any]], n_topics: int = 5) -> Dict[str, Any]:
        """
        工具：主题提取分析
        从文本回答中提取关键主题
        
        Returns:
            {
                "themes": [
                    {
                        "theme_name": "产品质量",
                        "keywords": ["质量", "产品", "满意"],
                        "description": "用户主要关注产品质量...",
                        "frequency": 15
                    }
                ],
                "summary": "识别出5个主要主题..."
            }
        """
        if not HAS_ML_LIBS:
            return {"themes": [], "summary": "需要sklearn库支持"}
        
        # 提取所有文本回答
        all_texts = []
        for response in responses:
            answers = response.get("answers", {})
            for answer in answers.values():
                if isinstance(answer, str) and answer.strip():
                    all_texts.append(answer.strip())
        
        if len(all_texts) < n_topics:
            return {"themes": [], "summary": f"文本数量不足（需要至少{n_topics}条）"}
        
        try:
            # 文本预处理
            processed_texts = []
            stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个'}
            
            for text in all_texts:
                words = jieba.lcut(text)
                filtered_words = [w for w in words if len(w) > 1 and w not in stop_words]
                processed_texts.append(' '.join(filtered_words))
            
            # TF-IDF向量化
            vectorizer = TfidfVectorizer(max_features=500, min_df=1)
            tfidf_matrix = vectorizer.fit_transform(processed_texts)
            
            # LDA主题建模
            actual_n_topics = min(n_topics, len(all_texts) // 2, 10)
            lda = LatentDirichletAllocation(n_components=actual_n_topics, random_state=42, max_iter=10)
            lda.fit(tfidf_matrix)
            
            # 提取主题
            feature_names = vectorizer.get_feature_names_out()
            themes = []
            
            for topic_idx, topic in enumerate(lda.components_):
                top_words_idx = topic.argsort()[-10:][::-1]
                top_words = [feature_names[i] for i in top_words_idx]
                
                themes.append({
                    "theme_name": f"主题 {topic_idx + 1}",
                    "keywords": top_words[:10].tolist() if hasattr(top_words, 'tolist') else top_words[:10],
                    "description": f"主要关键词: {', '.join(top_words[:5])}",
                    "frequency": len(all_texts) // actual_n_topics  # 估算频率
                })
            
            summary = f"识别出{len(themes)}个主要主题，共分析{len(all_texts)}条文本回答"
            return {"themes": themes, "summary": summary}
            
        except Exception as e:
            logger.error(f"主题提取失败: {e}")
            return {"themes": [], "summary": f"主题提取失败: {str(e)}"}
    
    def tool_analyze_sentiment(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        工具：情感倾向分析
        分析文本回答的情感倾向
        
        Returns:
            {
                "positive_percentage": 45.0,
                "negative_percentage": 20.0,
                "neutral_percentage": 35.0,
                "summary": "整体情感倾向：偏积极..."
            }
        """
        text_responses = []
        for response in responses:
            answers = response.get("answers", {})
            for answer in answers.values():
                if isinstance(answer, str) and answer.strip():
                    text_responses.append(answer.strip())
        
        if not text_responses:
            return {"positive_percentage": 0, "negative_percentage": 0, "neutral_percentage": 0, "summary": "没有文本回答"}
        
        positive_words = {'好', '喜欢', '满意', '不错', '棒', '优秀', '推荐', '赞', '支持', '同意'}
        negative_words = {'不好', '不喜欢', '不满意', '差', '糟糕', '反对', '问题', '困难', '拒绝', '麻烦'}
        
        positive_count = sum(1 for text in text_responses 
                           if any(word in text for word in positive_words))
        negative_count = sum(1 for text in text_responses 
                           if any(word in text for word in negative_words))
        
        total = len(text_responses)
        positive_pct = positive_count / total * 100
        negative_pct = negative_count / total * 100
        neutral_pct = (total - positive_count - negative_count) / total * 100
        
        if positive_pct > negative_pct:
            sentiment_summary = "整体情感倾向：偏积极"
        elif negative_pct > positive_pct:
            sentiment_summary = "整体情感倾向：偏消极"
        else:
            sentiment_summary = "整体情感倾向：中性"
        
        return {
            "positive_percentage": round(positive_pct, 1),
            "negative_percentage": round(negative_pct, 1),
            "neutral_percentage": round(neutral_pct, 1),
            "summary": f"{sentiment_summary}（积极{positive_pct:.1f}%，消极{negative_pct:.1f}%，中性{neutral_pct:.1f}%）"
        }
    
    def tool_extract_keywords(self, responses: List[Dict[str, Any]], top_k: int = 20) -> Dict[str, Any]:
        """
        工具：关键词提取
        提取文本回答中的高频关键词
        
        Returns:
            {
                "keywords": [
                    {"word": "质量", "count": 15},
                    {"word": "价格", "count": 12}
                ],
                "summary": "识别出20个高频关键词..."
            }
        """
        if not HAS_ML_LIBS:
            return {"keywords": [], "summary": "需要jieba库支持"}
        
        text_responses = []
        for response in responses:
            answers = response.get("answers", {})
            for answer in answers.values():
                if isinstance(answer, str) and answer.strip():
                    text_responses.append(answer.strip())
        
        if not text_responses:
            return {"keywords": [], "summary": "没有文本回答"}
        
        try:
            all_text = ' '.join(text_responses)
            words = jieba.lcut(all_text)
            stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个'}
            filtered_words = [w for w in words if len(w) > 1 and w not in stop_words]
            word_counts = Counter(filtered_words)
            keywords = [{"word": word, "count": count} for word, count in word_counts.most_common(top_k)]
            
            if keywords:
                summary = f"识别出{len(keywords)}个高频关键词，最高频词'{keywords[0]['word']}'出现{keywords[0]['count']}次"
            else:
                summary = "未识别出关键词"
            return {"keywords": keywords, "summary": summary}
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return {"keywords": [], "summary": f"关键词提取失败: {str(e)}"}
    
    def tool_statistics_summary(self, survey: Dict[str, Any], responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        工具：统计摘要
        生成问卷回答的基础统计信息
        
        Returns:
            {
                "total_responses": 50,
                "total_questions": 10,
                "question_types": {"单选题": 5, "量表题": 3, "开放式问题": 2},
                "answer_rate": 95.0,
                "summary": "共收集50份有效回答..."
            }
        """
        questions = survey.get("questions", [])
        question_types = Counter(q.get("type", "未知") for q in questions)
        
        # 计算回答率
        total_questions = len(questions)
        total_responses = len(responses)
        answered_total = 0
        
        for question in questions:
            q_id = str(question.get("id", ""))
            for response in responses:
                answers = response.get("answers", {})
                if q_id in answers and answers[q_id] is not None:
                    answered_total += 1
                    break
        
        answer_rate = (answered_total / (total_questions * total_responses) * 100) if total_responses > 0 else 0
        
        summary = f"共收集{total_responses}份有效回答，包含{total_questions}个问题，平均回答率{answer_rate:.1f}%"
        
        return {
            "total_responses": total_responses,
            "total_questions": total_questions,
            "question_types": dict(question_types),
            "answer_rate": round(answer_rate, 1),
            "summary": summary
        }

