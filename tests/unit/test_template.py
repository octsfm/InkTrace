"""
模板实体单元测试

作者：孔利群
"""

# 文件路径：tests/unit/test_template.py


import unittest
from datetime import datetime

from domain.entities.template import Template, CharacterTemplate, PlotTemplate
from domain.types import TemplateId, GenreType


class TestCharacterTemplate(unittest.TestCase):
    """人物模板测试"""
    
    def test_create_character_template(self):
        """测试创建人物模板"""
# 文件：模块：test_template

        template = CharacterTemplate(
            role="protagonist",
            name_pattern="姓+名",
            traits=["坚韧", "智慧"],
            background_template="出身{出身地}",
            abilities=["剑法", "内功"]
        )
        self.assertEqual(template.role, "protagonist")
        self.assertEqual(template.name_pattern, "姓+名")
        self.assertEqual(len(template.traits), 2)
        self.assertEqual(len(template.abilities), 2)
    
    def test_character_template_to_dict(self):
        """测试人物模板转字典"""
        template = CharacterTemplate(role="antagonist", name_pattern="霸气名字")
        data = template.to_dict()
        self.assertEqual(data["role"], "antagonist")
        self.assertEqual(data["name_pattern"], "霸气名字")
    
    def test_character_template_from_dict(self):
        """测试从字典创建人物模板"""
# 文件：模块：test_template

        data = {
            "role": "supporting",
            "name_pattern": "普通名字",
            "traits": ["忠诚"],
            "background_template": "背景模板",
            "abilities": ["辅助技能"]
        }
        template = CharacterTemplate.from_dict(data)
        self.assertEqual(template.role, "supporting")
        self.assertEqual(len(template.traits), 1)


class TestPlotTemplate(unittest.TestCase):
    """剧情模板测试"""
    
    def test_create_plot_template(self):
        """测试创建剧情模板"""
# 文件：模块：test_template

        template = PlotTemplate(
            name="开局觉醒",
            description="主角获得金手指",
            stages=["测试", "觉醒", "成长"],
            key_events=["事件1", "事件2"]
        )
        self.assertEqual(template.name, "开局觉醒")
        self.assertEqual(len(template.stages), 3)
        self.assertEqual(len(template.key_events), 2)
    
    def test_plot_template_to_dict(self):
        """测试剧情模板转字典"""
        template = PlotTemplate(name="测试剧情", description="描述")
        data = template.to_dict()
        self.assertEqual(data["name"], "测试剧情")
        self.assertEqual(data["description"], "描述")
    
    def test_plot_template_from_dict(self):
        """测试从字典创建剧情模板"""
# 文件：模块：test_template

        data = {
            "name": "宗门试炼",
            "description": "宗门历练",
            "stages": ["入门", "考核"],
            "key_events": ["试炼"]
        }
        template = PlotTemplate.from_dict(data)
        self.assertEqual(template.name, "宗门试炼")
        self.assertEqual(len(template.stages), 2)


class TestTemplate(unittest.TestCase):
    """模板实体测试"""
    
    def setUp(self):
        """测试前置"""
# 文件：模块：test_template

        self.template_id = TemplateId("tpl_001")
        self.template = Template(
            id=self.template_id,
            name="玄幻模板",
            genre=GenreType.XUANHUAN,
            description="玄幻小说模板"
        )
    
    def test_create_template(self):
        """测试创建模板"""
        self.assertEqual(str(self.template.id), "tpl_001")
        self.assertEqual(self.template.name, "玄幻模板")
        self.assertEqual(self.template.genre, GenreType.XUANHUAN)
        self.assertFalse(self.template.is_builtin)
    
    def test_add_character_template(self):
        """测试添加人物模板"""
# 文件：模块：test_template

        char_template = CharacterTemplate(role="protagonist", name_pattern="测试")
        self.template.add_character_template(char_template)
        self.assertEqual(len(self.template.character_templates), 1)
    
    def test_add_plot_template(self):
        """测试添加剧情模板"""
        plot_template = PlotTemplate(name="测试剧情", description="描述")
        self.template.add_plot_template(plot_template)
        self.assertEqual(len(self.template.plot_templates), 1)
    
    def test_update_worldview_framework(self):
        """测试更新世界观框架"""
# 文件：模块：test_template

        framework = {
            "power_system": {"name": "修炼境界", "levels": ["练气", "筑基"]},
            "currency_system": {"primary": "灵石"}
        }
        self.template.update_worldview_framework(framework)
        self.assertEqual(self.template.worldview_framework["power_system"]["name"], "修炼境界")
    
    def test_update_style_reference(self):
        """测试更新文风参考"""
        style = {
            "vocabulary": ["灵气", "法力"],
            "sentence_patterns": ["只见{人物}"]
        }
        self.template.update_style_reference(style)
        self.assertEqual(len(self.template.style_reference["vocabulary"]), 2)
    
    def test_template_to_dict(self):
        """测试模板转字典"""
# 文件：模块：test_template

        data = self.template.to_dict()
        self.assertEqual(data["id"], "tpl_001")
        self.assertEqual(data["name"], "玄幻模板")
        self.assertEqual(data["genre"], "xuanhuan")
        self.assertFalse(data["is_builtin"])
    
    def test_template_from_dict(self):
        """测试从字典创建模板"""
        data = {
            "id": "tpl_002",
            "name": "仙侠模板",
            "genre": "xianxia",
            "description": "仙侠小说模板",
            "worldview_framework": {"test": "value"},
            "character_templates": [
                {"role": "protagonist", "name_pattern": "清雅名字"}
            ],
            "plot_templates": [
                {"name": "求仙之路", "description": "修仙故事"}
            ],
            "style_reference": {"vocabulary": ["道友"]},
            "is_builtin": True,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00"
        }
        template = Template.from_dict(data)
        self.assertEqual(str(template.id), "tpl_002")
        self.assertEqual(template.genre, GenreType.XIANXIA)
        self.assertTrue(template.is_builtin)
        self.assertEqual(len(template.character_templates), 1)
        self.assertEqual(len(template.plot_templates), 1)


if __name__ == "__main__":
    unittest.main()
