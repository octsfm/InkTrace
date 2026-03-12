"""
值对象单元测试

作者：孔利群
"""

import unittest

from domain.value_objects.style_profile import StyleProfile
from domain.value_objects.character_state import CharacterState
from domain.value_objects.writing_config import WritingConfig
from domain.types import CharacterId, ChapterId


class TestStyleProfile(unittest.TestCase):
    """测试StyleProfile值对象"""

    def test_create_style_profile(self):
        """测试创建文风特征"""
        profile = StyleProfile(
            vocabulary_stats={"常用词": 100, "生僻词": 10},
            sentence_patterns=["主谓宾", "倒装句"],
            rhetoric_stats={"比喻": 50, "拟人": 30},
            dialogue_style="简洁有力",
            narrative_voice="第三人称",
            pacing="快节奏",
            sample_sentences=["示例句子1", "示例句子2"]
        )
        self.assertEqual(profile.vocabulary_stats["常用词"], 100)
        self.assertEqual(len(profile.sentence_patterns), 2)
        self.assertEqual(profile.dialogue_style, "简洁有力")

    def test_style_profile_immutable(self):
        """测试文风特征不可变"""
        profile = StyleProfile(
            vocabulary_stats={},
            sentence_patterns=[],
            rhetoric_stats={},
            dialogue_style="",
            narrative_voice="",
            pacing="",
            sample_sentences=[]
        )
        with self.assertRaises(AttributeError):
            profile.dialogue_style = "新风格"


class TestCharacterState(unittest.TestCase):
    """测试CharacterState值对象"""

    def test_create_character_state(self):
        """测试创建人物状态"""
        state = CharacterState(
            character_id=CharacterId("char-001"),
            location="蓝星龙国春泽市",
            cultivation_level="筑基期",
            health_status="健康",
            emotional_state="平静",
            possessions=["金箍棒", "菩提手串"],
            active_goals=["突破金丹期"],
            chapter_id=ChapterId("chapter-001")
        )
        self.assertEqual(state.character_id.value, "char-001")
        self.assertEqual(state.cultivation_level, "筑基期")
        self.assertEqual(len(state.possessions), 2)

    def test_character_state_immutable(self):
        """测试人物状态不可变"""
        state = CharacterState(
            character_id=CharacterId("char-001"),
            location="",
            cultivation_level="",
            health_status="",
            emotional_state="",
            possessions=[],
            active_goals=[],
            chapter_id=ChapterId("chapter-001")
        )
        with self.assertRaises(AttributeError):
            state.cultivation_level = "金丹期"


class TestWritingConfig(unittest.TestCase):
    """测试WritingConfig值对象"""

    def test_create_writing_config(self):
        """测试创建写作配置"""
        config = WritingConfig(
            target_word_count=2100,
            style_intensity=0.8,
            temperature=0.7,
            max_context_chapters=5,
            enable_consistency_check=True,
            enable_style_mimicry=True
        )
        self.assertEqual(config.target_word_count, 2100)
        self.assertEqual(config.style_intensity, 0.8)
        self.assertTrue(config.enable_consistency_check)

    def test_writing_config_immutable(self):
        """测试写作配置不可变"""
        config = WritingConfig(
            target_word_count=2000,
            style_intensity=0.5,
            temperature=0.7,
            max_context_chapters=3,
            enable_consistency_check=True,
            enable_style_mimicry=True
        )
        with self.assertRaises(AttributeError):
            config.target_word_count = 3000

    def test_default_values(self):
        """测试默认值"""
        config = WritingConfig()
        self.assertEqual(config.target_word_count, 2100)
        self.assertEqual(config.style_intensity, 0.8)
        self.assertEqual(config.temperature, 0.7)
        self.assertEqual(config.max_context_chapters, 5)
        self.assertTrue(config.enable_consistency_check)
        self.assertTrue(config.enable_style_mimicry)


if __name__ == '__main__':
    unittest.main()
