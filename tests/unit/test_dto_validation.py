"""
DTO输入校验单元测试模块

作者：孔利群
"""

# 文件路径：tests/unit/test_dto_validation.py


import pytest
from pydantic import ValidationError

from application.dto.request_dto import (
    BaseRequest,
    CreateNovelRequest,
    ImportNovelRequest,
    AnalyzeNovelRequest,
    GenerateChapterRequest,
    PlanPlotRequest,
    ExportNovelRequest,
    UpdateChapterRequest,
    CreateCharacterRequest
)


class TestBaseRequest:
    """基础请求DTO测试"""
    
    def test_base_request_with_context(self):
        """测试带上下文的基础请求"""
        request = BaseRequest(
            user_id="user123",
            session_id="session456",
            trace_id="trace789"
        )
        assert request.user_id == "user123"
        assert request.session_id == "session456"
        assert request.trace_id == "trace789"
    
    def test_base_request_without_context(self):
        """测试不带上下文的基础请求"""
        request = BaseRequest()
        assert request.user_id is None
        assert request.session_id is None
        assert request.trace_id is None


class TestCreateNovelRequest:
    """创建小说请求测试"""
    
    def test_valid_request(self):
        """测试有效请求"""
        request = CreateNovelRequest(
            title="测试小说",
            author="测试作者",
            genre="玄幻",
            target_word_count=100000
        )
        assert request.title == "测试小说"
        assert request.author == "测试作者"
        assert request.genre == "玄幻"
        assert request.target_word_count == 100000
    
    def test_empty_title_validation(self):
        """测试空标题验证"""
        with pytest.raises(ValidationError):
            CreateNovelRequest(
                title="",
                author="测试作者",
                genre="玄幻",
                target_word_count=100000
            )
    
    def test_negative_word_count_validation(self):
        """测试负数字数验证"""
        with pytest.raises(ValidationError):
            CreateNovelRequest(
                title="测试小说",
                author="测试作者",
                genre="玄幻",
                target_word_count=-100
            )
    
    def test_with_context(self):
        """测试带上下文的请求"""
        request = CreateNovelRequest(
            title="测试小说",
            author="测试作者",
            genre="玄幻",
            target_word_count=100000,
            user_id="user123",
            session_id="session456"
        )
        assert request.user_id == "user123"
        assert request.session_id == "session456"


class TestGenerateChapterRequest:
    """生成章节请求测试"""
    
    def test_valid_request(self):
        """测试有效请求"""
        request = GenerateChapterRequest(
            novel_id="novel123",
            goal="提升冲突",
            constraints=["主角不能死亡"],
            context_summary="当前剧情紧张",
            chapter_count=3,
            target_word_count=3000
        )
        assert request.novel_id == "novel123"
        assert request.goal == "提升冲突"
        assert request.constraints == ["主角不能死亡"]
        assert request.chapter_count == 3
    
    def test_default_values(self):
        """测试默认值"""
        request = GenerateChapterRequest(
            novel_id="novel123",
            goal="测试目标"
        )
        assert request.chapter_count == 1
        assert request.target_word_count == 2100
        assert request.constraints is None
        assert request.options is None
    
    def test_invalid_chapter_count(self):
        """测试无效章节数"""
        with pytest.raises(ValidationError):
            GenerateChapterRequest(
                novel_id="novel123",
                goal="测试目标",
                chapter_count=0
            )
    
    def test_with_options(self):
        """测试带选项的请求"""
        request = GenerateChapterRequest(
            novel_id="novel123",
            goal="测试目标",
            options={"style": "紧张", "tone": "悬疑"}
        )
        assert request.options == {"style": "紧张", "tone": "悬疑"}


class TestImportNovelRequest:
    """导入小说请求测试"""
    
    def test_valid_request(self):
        """测试有效请求"""
        request = ImportNovelRequest(
            novel_id="novel123",
            file_path="/path/to/file.txt"
        )
        assert request.novel_id == "novel123"
        assert request.file_path == "/path/to/file.txt"
    
    def test_empty_novel_id_validation(self):
        """测试空小说ID验证"""
        with pytest.raises(ValidationError):
            ImportNovelRequest(
                novel_id="",
                file_path="/path/to/file.txt"
            )


class TestAnalyzeNovelRequest:
    """分析小说请求测试"""
    
    def test_valid_request(self):
        """测试有效请求"""
        request = AnalyzeNovelRequest(
            novel_id="novel123",
            analyze_style=True,
            analyze_plot=False
        )
        assert request.novel_id == "novel123"
        assert request.analyze_style is True
        assert request.analyze_plot is False


class TestPlanPlotRequest:
    """规划剧情请求测试"""
    
    def test_valid_request(self):
        """测试有效请求"""
        request = PlanPlotRequest(
            novel_id="novel123",
            goal="增加冲突",
            chapter_count=5
        )
        assert request.novel_id == "novel123"
        assert request.goal == "增加冲突"
        assert request.chapter_count == 5


class TestExportNovelRequest:
    """导出小说请求测试"""
    
    def test_valid_request(self):
        """测试有效请求"""
        request = ExportNovelRequest(
            novel_id="novel123",
            output_path="/path/to/output",
            format="markdown"
        )
        assert request.novel_id == "novel123"
        assert request.output_path == "/path/to/output"
        assert request.format == "markdown"


class TestUpdateChapterRequest:
    """更新章节请求测试"""
    
    def test_valid_request(self):
        """测试有效请求"""
        request = UpdateChapterRequest(
            chapter_id="chapter123",
            content="新内容",
            title="新标题"
        )
        assert request.chapter_id == "chapter123"
        assert request.content == "新内容"
        assert request.title == "新标题"
    
    def test_partial_update(self):
        """测试部分更新"""
        request = UpdateChapterRequest(
            chapter_id="chapter123",
            content="新内容"
        )
        assert request.content == "新内容"
        assert request.title is None


class TestCreateCharacterRequest:
    """创建人物请求测试"""
    
    def test_valid_request(self):
        """测试有效请求"""
        request = CreateCharacterRequest(
            novel_id="novel123",
            name="张三",
            role="主角",
            background="孤儿",
            personality="勇敢"
        )
        assert request.novel_id == "novel123"
        assert request.name == "张三"
        assert request.role == "主角"
    
    def test_empty_name_validation(self):
        """测试空名字验证"""
        with pytest.raises(ValidationError):
            CreateCharacterRequest(
                novel_id="novel123",
                name="",
                role="主角"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
