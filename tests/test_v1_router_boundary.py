from pathlib import Path


def test_v1_routers_do_not_import_infrastructure_repositories_directly():
    router_dir = Path(__file__).resolve().parents[1] / "presentation" / "api" / "routers" / "v1"
    offenders = []

    for path in sorted(router_dir.glob("*.py")):
        source = path.read_text(encoding="utf-8-sig")
        if "from infrastructure.database.repositories import" in source:
            offenders.append(path.name)

    assert offenders == []
