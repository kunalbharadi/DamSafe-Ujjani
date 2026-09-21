import pytest
from damsafe.contracts import RunRequest
from damsafe.db import engine_for, metadata, projects, scenarios
from damsafe.numerics.service import submit
from fastapi import HTTPException
from sqlalchemy import insert


def test_custom_site_cannot_silently_execute_default_case(tmp_path):
    engine = engine_for(f'sqlite:///{(tmp_path / "guard.db").as_posix()}')
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(insert(projects).values(id='site', body={'site_key': 'ujjani-bhima', 'synthetic': False}))
        conn.execute(insert(scenarios).values(id='scenario', project_id='site', body={'snapshot': {'scenario': {'forcing': {'mode': 'computed_breach'}}}}))

    # Valid site scenario now successfully enters QUEUED state with bound scenario snapshot
    run = submit(engine, 'site', RunRequest(engine='dflowfm', case_kind='SITE_SCENARIO', scenario_id='scenario', idempotency_key='valid-custom-site'))
    assert run["state"] == "QUEUED"
    assert run["input"]["request"]["case_kind"] == "SITE_SCENARIO"
    assert run["input"]["site_key"] == "ujjani-bhima"
    assert "scenario_snapshot" in run["input"]

    # Missing scenario is rejected with 422
    with pytest.raises(HTTPException) as error:
        submit(engine, 'site', RunRequest(engine='dflowfm', case_kind='SITE_SCENARIO', scenario_id='missing-scenario', idempotency_key='missing-scenario-key'))
    assert error.value.status_code == 422
    assert "scenario" in error.value.detail.lower()

    engine.dispose()

