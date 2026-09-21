from unittest.mock import Mock

from damsafe.observation import gee


def test_service_account_is_used_without_exposing_provider_error(monkeypatch):
    from google.oauth2 import service_account

    credentials = object()
    load = Mock(return_value=credentials)
    initialize = Mock(side_effect=RuntimeError("sensitive-provider-detail"))
    monkeypatch.setenv("EE_PROJECT", "test-project")
    monkeypatch.setenv("EE_SERVICE_ACCOUNT_JSON", "/outside/repo/test-account.json")
    monkeypatch.setattr(gee, "HAS_EE", True)
    monkeypatch.setattr(gee.ee, "Initialize", initialize)
    monkeypatch.setattr(service_account.Credentials, "from_service_account_file", load)
    service = gee.EarthEngineService()
    initialize.assert_called_once_with(credentials=credentials, project="test-project")
    assert load.call_args.args == ("/outside/repo/test-account.json",)
    assert service.get_readiness_state() == gee.ObservationState.AUTHENTICATION_FAILED
    assert "sensitive-provider-detail" not in service.auth_error


def test_oauth_uses_project_and_default_credentials(monkeypatch):
    monkeypatch.setenv("EE_PROJECT", "test-project")
    monkeypatch.delenv("EE_SERVICE_ACCOUNT_JSON", raising=False)
    initialize = Mock()
    monkeypatch.setattr(gee.ee, "Initialize", initialize)
    service = gee.EarthEngineService()
    initialize.assert_called_once_with(project="test-project")
    assert service.get_readiness_state() == gee.ObservationState.AUTHENTICATED
