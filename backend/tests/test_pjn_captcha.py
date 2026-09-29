import anthropic
import httpx
import pytest

from scripts.scrapers.pjn_tribunales import CaptchaSolver, client_kwargs


class FakeMessages:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def create(self, **_):
        self.calls += 1
        raise self.error


def solver_with(error) -> tuple[CaptchaSolver, FakeMessages]:
    solver = CaptchaSolver.__new__(CaptchaSolver)
    solver.calls, solver.cost = 0, 0.0
    messages = FakeMessages(error)
    solver.client = type("Client", (), {"messages": messages})()
    return solver, messages


def test_bad_request_stops_immediately():
    response = httpx.Response(400, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    solver, messages = solver_with(anthropic.BadRequestError("needs anthropic-workspace-id", response=response, body=None))
    with pytest.raises(anthropic.BadRequestError):
        solver.solve(b"png")
    assert messages.calls == 1


def test_workspace_id_is_sent_as_header():
    assert client_kwargs("sk-ant-x", "") == {"api_key": "sk-ant-x"}
    assert client_kwargs("sk-ant-x", "wrkspc_123") == {
        "api_key": "sk-ant-x",
        "default_headers": {"anthropic-workspace-id": "wrkspc_123"},
    }


def test_invalid_api_key_stops_immediately():
    response = httpx.Response(401, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
    solver, messages = solver_with(anthropic.AuthenticationError("invalid x-api-key", response=response, body=None))
    with pytest.raises(anthropic.AuthenticationError):
        solver.solve(b"png")
    assert messages.calls == 1
