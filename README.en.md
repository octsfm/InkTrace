# InkTrace

> A long-form fiction workspace where the author stays in control and AI prepares drafts, options, and consistency checks.

[中文 README](README.md)

Status: the V2.0 P2-04 Scheme A and the author-facing “Continue Writing” flow are locally sealed as of 2026-07-12. Remote CI verification is still pending.

## The key promise

- AI output is created as an isolated candidate draft.
- It never enters the manuscript until the author explicitly applies it.
- The system writes one chapter at a time and waits for the author before continuing.
- Continuing to the next chapter and applying the current draft are separate actions.
- Full manuscripts, candidate drafts, prompts, context packs, and API keys must not be written to ordinary logs.

## Continue Writing

Open a work and chapter, choose **AI → Continue Writing**, then:

1. Pick a plain-language direction, write one short instruction, or continue without extra guidance.
2. Ask InkTrace to prepare one chapter.
3. Review the new draft.
4. Decide separately whether to apply it and whether to continue.

Chinese author guide: [InkTrace Continue Writing Guide](docs/10_user_guide/InkTrace-接着写-使用说明.md).

## Quick start

Requirements:

- Python 3.11+
- Node.js 18+

```powershell
pip install -r requirements.txt
cd frontend
npm install
cd ..
.\start-all.bat
```

- Frontend: [http://localhost:3000](http://localhost:3000)
- API documentation: [http://127.0.0.1:9527/docs](http://127.0.0.1:9527/docs)

Stop all local services with `./stop.bat`.

## Local verification

| Check | Result |
|---|---|
| Backend | `839 passed, 1 skipped` |
| P2-04 focused backend tests | `60 passed` |
| Frontend | `443 passed` |
| Production build | Passed |
| Playwright visual QA | `2 passed` |
| Remote CI | Pending |

## Documentation

- [Seal summary](docs/07_overview/InkTrace-V2.0-P2-04-接着写封版总结.md)
- [Acceptance report](docs/09_acceptance/InkTrace-V2.0-P2-S2-P2-04-验收清单.md)
- [Current project status](docs/PROJECT_STATUS_CURRENT.md)
- [Requirements](docs/01_requirements/InkTrace-V2.0-需求规格说明书.md)
- [Architecture](docs/02_architecture/InkTrace-V2.0-架构设计说明书.md)

Historical redesign material under `docs/history_archive/`, `*_001.md` files, drafts, and backups are not current implementation sources.

## License

[MIT](LICENSE)
