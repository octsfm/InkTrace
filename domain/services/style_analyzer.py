"""
文风分析领域服务模块

作者：孔利群
"""

import re
from typing import List, Dict
from collections import Counter

from domain.entities.chapter import Chapter
from domain.value_objects.style_profile import StyleProfile


class StyleAnalyzer:
    """
    文风分析领域服务
    
    分析小说文本的语言特征，生成文风特征报告。
    """

    def analyze(self, chapters: List[Chapter]) -> StyleProfile:
        """
        分析章节文风，生成文风特征
        
        Args:
            chapters: 章节列表
            
        Returns:
            文风特征值对象
        """
        if not chapters:
            return StyleProfile(
                vocabulary_stats={},
                sentence_patterns=[],
                rhetoric_stats={},
                dialogue_style="未知",
                narrative_voice="未知",
                pacing="未知",
                sample_sentences=[]
            )
        
        all_content = '\n'.join(ch.content for ch in chapters)
        
        vocabulary_stats = self.analyze_vocabulary(all_content)
        sentence_patterns = self.analyze_sentence_patterns(all_content)
        rhetoric_stats = self.analyze_rhetoric(all_content)
        dialogue_style = self.extract_dialogue_style(all_content)
        narrative_voice = self.detect_narrative_voice(all_content)
        pacing = self.analyze_pacing(all_content)
        sample_sentences = self.extract_sample_sentences(all_content)
        
        return StyleProfile(
            vocabulary_stats=vocabulary_stats,
            sentence_patterns=sentence_patterns,
            rhetoric_stats=rhetoric_stats,
            dialogue_style=dialogue_style,
            narrative_voice=narrative_voice,
            pacing=pacing,
            sample_sentences=sample_sentences
        )

    def analyze_vocabulary(self, text: str) -> Dict[str, float]:
        """
        分析词汇特征
        
        Args:
            text: 文本内容
            
        Returns:
            词汇统计字典
        """
        words = re.findall(r'[\u4e00-\u9fa5]+', text)
        
        if not words:
            return {"高频词": [], "平均词长": 0, "词汇丰富度": 0}
        
        word_freq = Counter(words)
        high_freq_words = word_freq.most_common(20)
        
        total_words = len(words)
        unique_words = len(word_freq)
        avg_length = sum(len(w) for w in words) / total_words if total_words > 0 else 0
        richness = unique_words / total_words if total_words > 0 else 0
        
        return {
            "高频词": high_freq_words,
            "平均词长": round(avg_length, 2),
            "词汇丰富度": round(richness, 4),
            "总词数": total_words,
            "独立词数": unique_words
        }

    def analyze_sentence_patterns(self, text: str) -> List[str]:
        """
        分析句式模板
        
        Args:
            text: 文本内容
            
        Returns:
            句式模板列表
        """
        sentences = re.split(r'[。！？\n]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        
        patterns = []
        
        for sentence in sentences[:50]:
            if "，" in sentence:
                parts = sentence.split("，")
                if len(parts) >= 2:
                    pattern = f"{len(parts[0])}字+，+{len(parts[1])}字+..."
                    if pattern not in patterns:
                        patterns.append(pattern)
        
        return patterns[:10]

    def analyze_rhetoric(self, text: str) -> Dict[str, int]:
        """
        分析修辞手法
        
        Args:
            text: 文本内容
            
        Returns:
            修辞统计字典
        """
        rhetoric_stats = {}
        
        metaphor_patterns = [
            r'如[^，。！？]+[般一般]',
            r'像[^，。！？]+[样一般]',
            r'仿佛[^，。！？]+'
        ]
        metaphor_count = 0
        for pattern in metaphor_patterns:
            metaphor_count += len(re.findall(pattern, text))
        rhetoric_stats["比喻"] = metaphor_count
        
        personification_patterns = [
            r'[他她它][^，。！？]{0,5}(说|想|看|听|感觉)',
            r'风[^，。！？]{0,5}(吹|呼啸|低语)',
            r'光[^，。！？]{0,5}(照耀|闪烁)'
        ]
        personification_count = 0
        for pattern in personification_patterns:
            personification_count += len(re.findall(pattern, text))
        rhetoric_stats["拟人"] = personification_count
        
        parallelism_count = len(re.findall(r'[^，。！？]+，[^，。！？]+，[^，。！？]+', text))
        rhetoric_stats["排比"] = parallelism_count
        
        exaggeration_patterns = [
            r'遮天蔽日',
            r'惊天动地',
            r'翻天覆地',
            r'无尽',
            r'无穷'
        ]
        exaggeration_count = 0
        for pattern in exaggeration_patterns:
            exaggeration_count += len(re.findall(pattern, text))
        rhetoric_stats["夸张"] = exaggeration_count
        
        return rhetoric_stats

    def extract_dialogue_style(self, text: str) -> str:
        """
        提取对话风格
        
        Args:
            text: 文本内容
            
        Returns:
            对话风格描述
        """
        dialogues = re.findall(r'"([^"]+)"', text)
        
        if not dialogues:
            return "无对话"
        
        avg_length = sum(len(d) for d in dialogues) / len(dialogues)
        
        exclamation_count = sum(1 for d in dialogues if '！' in d)
        question_count = sum(1 for d in dialogues if '？' in d)
        
        if avg_length < 10:
            length_style = "简洁"
        elif avg_length < 20:
            length_style = "适中"
        else:
            length_style = "详细"
        
        if exclamation_count > len(dialogues) * 0.3:
            emotion_style = "情感强烈"
        elif question_count > len(dialogues) * 0.2:
            emotion_style = "疑问较多"
        else:
            emotion_style = "平和"
        
        return f"{length_style}，{emotion_style}"

    def detect_narrative_voice(self, text: str) -> str:
        """
        检测叙述视角
        
        Args:
            text: 文本内容
            
        Returns:
            叙述视角描述
        """
        first_person = len(re.findall(r'[我咱]', text))
        third_person = len(re.findall(r'[他她它]', text))
        
        if first_person > third_person * 1.5:
            return "第一人称"
        elif third_person > first_person * 1.5:
            return "第三人称"
        else:
            return "混合视角"

    def analyze_pacing(self, text: str) -> str:
        """
        分析节奏特点
        
        Args:
            text: 文本内容
            
        Returns:
            节奏描述
        """
        sentences = re.split(r'[。！？]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return "未知"
        
        avg_length = sum(len(s) for s in sentences) / len(sentences)
        
        short_sentences = sum(1 for s in sentences if len(s) < 15)
        ratio = short_sentences / len(sentences)
        
        if ratio > 0.5:
            return "快节奏"
        elif ratio > 0.3:
            return "中等节奏"
        else:
            return "慢节奏"

    def extract_sample_sentences(self, text: str, count: int = 10) -> List[str]:
        """
        提取示例句子
        
        Args:
            text: 文本内容
            count: 提取数量
            
        Returns:
            示例句子列表
        """
        sentences = re.split(r'[。！？]', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        return sentences[:count]
