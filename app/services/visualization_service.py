"""
问卷分析可视化服务
生成词云图、主题分布图、情感分布图等可视化内容
"""

import base64
import io
import logging
from typing import List, Dict, Any
from collections import Counter

logger = logging.getLogger(__name__)


class VisualizationService:
    """可视化服务 - 生成各类图表"""
    
    def __init__(self):
        """初始化可视化服务"""
        self.has_wordcloud = False
        self.has_matplotlib = False
        
        # 尝试导入可视化库
        try:
            from wordcloud import WordCloud
            self.WordCloud = WordCloud
            self.has_wordcloud = True
        except ImportError:
            logger.warning("wordcloud 未安装，词云功能将不可用")
        
        try:
            import matplotlib
            matplotlib.use('Agg')  # 使用非GUI后端
            import matplotlib.pyplot as plt
            import matplotlib.font_manager as fm
            self.plt = plt
            self.fm = fm
            self.has_matplotlib = True
        except ImportError:
            logger.warning("matplotlib 未安装，图表功能将不可用")
    
    def generate_wordcloud(
        self, 
        texts: List[str], 
        title: str = "主题词云"
    ) -> str:
        """
        生成词云图
        
        Args:
            texts: 文本列表
            title: 词云标题
            
        Returns:
            Base64编码的图片字符串
        """
        if not self.has_wordcloud or not self.has_matplotlib:
            return ""
        
        try:
            # 合并所有文本
            all_text = " ".join(texts)
            
            if not all_text.strip():
                return ""
            
            # 创建词云
            wordcloud = self.WordCloud(
                width=800,
                height=400,
                background_color='white',
                font_path=self._get_chinese_font(),
                max_words=100,
                relative_scaling=0.5,
                colormap='viridis'
            ).generate(all_text)
            
            # 绘制图形
            fig, ax = self.plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            ax.set_title(title, fontsize=16, fontproperties=self._get_chinese_font_prop())
            
            # 转换为Base64
            buffer = io.BytesIO()
            self.plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            self.plt.close(fig)
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"生成词云失败: {e}")
            return ""
    
    def generate_theme_distribution_chart(
        self,
        themes: List[Dict[str, Any]],
        title: str = "主题分布"
    ) -> str:
        """
        生成主题分布柱状图
        
        Args:
            themes: 主题列表，每个主题包含 theme 和 count
            title: 图表标题
            
        Returns:
            Base64编码的图片字符串
        """
        if not self.has_matplotlib:
            return ""
        
        try:
            if not themes:
                return ""
            
            # 取前10个主题
            top_themes = sorted(themes, key=lambda x: x.get('count', 0), reverse=True)[:10]
            
            theme_names = [t.get('theme', '') for t in top_themes]
            counts = [t.get('count', 0) for t in top_themes]
            
            # 创建图表
            fig, ax = self.plt.subplots(figsize=(10, 6))
            bars = ax.barh(range(len(theme_names)), counts, color='skyblue')
            
            # 设置标签
            ax.set_yticks(range(len(theme_names)))
            ax.set_yticklabels(theme_names, fontproperties=self._get_chinese_font_prop())
            ax.set_xlabel('提及次数', fontproperties=self._get_chinese_font_prop())
            ax.set_title(title, fontsize=16, fontproperties=self._get_chinese_font_prop())
            
            # 在柱子上显示数值
            for i, (bar, count) in enumerate(zip(bars, counts)):
                ax.text(count + 0.1, i, str(count), va='center')
            
            # 反转y轴，使最大值在上面
            ax.invert_yaxis()
            
            self.plt.tight_layout()
            
            # 转换为Base64
            buffer = io.BytesIO()
            self.plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            self.plt.close(fig)
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"生成主题分布图失败: {e}")
            return ""
    
    def generate_sentiment_pie_chart(
        self,
        themes: List[Dict[str, Any]],
        title: str = "情感分布"
    ) -> str:
        """
        生成情感分布饼图
        
        Args:
            themes: 主题列表，每个主题包含 sentiment 和 count
            title: 图表标题
            
        Returns:
            Base64编码的图片字符串
        """
        if not self.has_matplotlib:
            return ""
        
        try:
            if not themes:
                return ""
            
            # 统计情感分布
            sentiment_counts = Counter()
            for theme in themes:
                sentiment = theme.get('sentiment', 'neutral')
                count = theme.get('count', 1)
                sentiment_counts[sentiment] += count
            
            # 情感标签映射
            sentiment_labels = {
                'positive': '积极',
                'negative': '消极',
                'neutral': '中性'
            }
            
            labels = [sentiment_labels.get(s, s) for s in sentiment_counts.keys()]
            sizes = list(sentiment_counts.values())
            colors = []
            for s in sentiment_counts.keys():
                if s == 'positive':
                    colors.append('#4CAF50')
                elif s == 'negative':
                    colors.append('#F44336')
                else:
                    colors.append('#9E9E9E')
            
            # 创建饼图
            fig, ax = self.plt.subplots(figsize=(8, 6))
            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=labels,
                colors=colors,
                autopct='%1.1f%%',
                startangle=90
            )
            
            # 设置字体
            for text in texts:
                text.set_fontproperties(self._get_chinese_font_prop())
            
            ax.set_title(title, fontsize=16, fontproperties=self._get_chinese_font_prop())
            
            self.plt.tight_layout()
            
            # 转换为Base64
            buffer = io.BytesIO()
            self.plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            self.plt.close(fig)
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"生成情感分布图失败: {e}")
            return ""
    
    def generate_scale_distribution_chart(
        self,
        data: Dict[str, int],
        question_title: str,
        scale_range: str = "1-5"
    ) -> str:
        """
        生成量表题分布图
        
        Args:
            data: 分数分布字典，如 {1: 5, 2: 10, 3: 20, 4: 15, 5: 8}
            question_title: 问题标题
            scale_range: 量表范围
            
        Returns:
            Base64编码的图片字符串
        """
        if not self.has_matplotlib:
            return ""
        
        try:
            if not data:
                return ""
            
            # 处理键的格式，统一转换为浮点数后再转回字符串进行匹配
            scores = sorted([float(k) for k in data.keys()])
            counts = []
            for s in scores:
                # 尝试多种键格式：整数字符串、浮点数字符串
                count = None
                for key_format in [str(int(s)), str(s), f"{int(s)}.0", f"{s:.1f}"]:
                    if key_format in data:
                        count = data[key_format]
                        break
                if count is None:
                    # 如果所有格式都找不到，尝试直接匹配最接近的键
                    closest_key = min(data.keys(), key=lambda x: abs(float(x) - s))
                    count = data[closest_key]
                counts.append(count)
            
            # 创建柱状图
            fig, ax = self.plt.subplots(figsize=(8, 5))
            bars = ax.bar(scores, counts, color='#667eea', width=0.6)
            
            # 设置标签
            ax.set_xlabel(f'分数 ({scale_range})', fontproperties=self._get_chinese_font_prop())
            ax.set_ylabel('回答数', fontproperties=self._get_chinese_font_prop())
            ax.set_title(f'{question_title}\n分数分布', fontsize=14, fontproperties=self._get_chinese_font_prop())
            ax.set_xticks(scores)
            
            # 在柱子上显示数值
            for bar, count in zip(bars, counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{count}',
                       ha='center', va='bottom')
            
            self.plt.tight_layout()
            
            # 转换为Base64
            buffer = io.BytesIO()
            self.plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            self.plt.close(fig)
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            # 静默处理错误，不显示错误提示
            return ""
    
    def generate_choice_distribution_chart(
        self,
        data: Dict[str, int],
        question_title: str,
        max_items: int = 10
    ) -> str:
        """
        生成选择题分布图
        
        Args:
            data: 选项分布字典
            question_title: 问题标题
            max_items: 最多显示的选项数
            
        Returns:
            Base64编码的图片字符串
        """
        if not self.has_matplotlib:
            return ""
        
        try:
            if not data:
                return ""
            
            # 按count排序，取前max_items个
            sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:max_items]
            options = [item[0] for item in sorted_items]
            counts = [item[1] for item in sorted_items]
            
            # 截断过长的选项名
            options = [opt[:20] + '...' if len(opt) > 20 else opt for opt in options]
            
            # 创建横向柱状图
            fig, ax = self.plt.subplots(figsize=(10, max(6, len(options) * 0.5)))
            bars = ax.barh(range(len(options)), counts, color='#764ba2')
            
            # 设置标签
            ax.set_yticks(range(len(options)))
            ax.set_yticklabels(options, fontproperties=self._get_chinese_font_prop())
            ax.set_xlabel('选择次数', fontproperties=self._get_chinese_font_prop())
            ax.set_title(f'{question_title}\n选项分布', fontsize=14, fontproperties=self._get_chinese_font_prop())
            
            # 在柱子上显示数值
            for i, (bar, count) in enumerate(zip(bars, counts)):
                ax.text(count + max(counts) * 0.02, i, str(count), va='center')
            
            # 反转y轴
            ax.invert_yaxis()
            
            self.plt.tight_layout()
            
            # 转换为Base64
            buffer = io.BytesIO()
            self.plt.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            self.plt.close(fig)
            
            return f"data:image/png;base64,{image_base64}"
            
        except Exception as e:
            logger.error(f"生成选择题分布图失败: {e}")
            return ""
    
    def _get_chinese_font(self) -> str:
        """
        获取中文字体路径
        
        Returns:
            字体文件路径
        """
        try:
            # Windows系统字体
            import platform
            if platform.system() == 'Windows':
                return 'C:\\Windows\\Fonts\\simhei.ttf'  # 黑体
            # 其他系统可以添加更多选项
            return None
        except Exception:
            return None
    
    def _get_chinese_font_prop(self):
        """
        获取中文字体属性对象
        
        Returns:
            FontProperties对象
        """
        try:
            font_path = self._get_chinese_font()
            if font_path and self.has_matplotlib:
                return self.fm.FontProperties(fname=font_path)
            return None
        except Exception:
            return None
    
    def check_availability(self) -> Dict[str, bool]:
        """
        检查可视化功能可用性
        
        Returns:
            功能可用性字典
        """
        return {
            "wordcloud": self.has_wordcloud and self.has_matplotlib,
            "charts": self.has_matplotlib
        }

