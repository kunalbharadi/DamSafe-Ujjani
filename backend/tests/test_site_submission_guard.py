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
    with pytest.raises(HTTPException) as error:
        submit(engine, 'site', RunRequest(engine='dflowfm', case_kind='SITE_SCENARIO', scenario_id='scenario', idempotency_key='blocked-custom-site'))
    assert error.value.status_code == 422
    assert 'worker binds' in error.value.detail
    engine.dispose()
