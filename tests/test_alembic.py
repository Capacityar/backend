from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_config_and_migrations_exist() -> None:
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] is not None


def test_alembic_env_targets_all_models() -> None:
    from app.database import Base
    import app.modules.attempts.models
    import app.modules.gap_analysis.models
    import app.modules.job_descriptions.models
    import app.modules.learning_paths.models
    import app.modules.resources.models
    import app.modules.skills.models
    import app.modules.users.models
    import app.modules.user_skills.models  # noqa: F401

    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "users",
        "skills",
        "user_skills",
        "job_descriptions",
        "job_description_skills",
        "gap_analyses",
        "learning_paths",
        "attempts",
        "resources",
    }
    assert expected_tables.issubset(table_names)
