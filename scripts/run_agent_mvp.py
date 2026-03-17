import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.agent_mvp import (
    AgentOrchestrator,
    ExecutionContext,
    RAGSearchTool,
    TaskContext,
    WritingGenerateTool
)


def main() -> None:
    task_context = TaskContext(
        novel_id="novel-mvp-001",
        goal="主角在古城遗迹中发现身世线索，并引出新的对手",
        target_word_count=320
    )
    execution_context = ExecutionContext(timeout_seconds=10, max_steps=2)
    orchestrator = AgentOrchestrator(
        tools={
            "RAGSearchTool": RAGSearchTool(),
            "WritingGenerateTool": WritingGenerateTool()
        }
    )
    result = orchestrator.run(task_context, execution_context)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
