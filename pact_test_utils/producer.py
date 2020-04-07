from contextlib import ExitStack, contextmanager
import logging
from functools import wraps
from pactman.verifier.verify import ProviderStateError

logger = logging.getLogger(__name__)


class PactStates:
    def __init__(self):
        self.state_registry = {}

    def _get(self, consumer, state_name):
        try:
            return self.state_registry[(consumer, state_name)]
        except KeyError:
            raise ProviderStateError(
                f"Missing state provider for consumer:\n@pact_state('{consumer}', '{state_name}')"
            )

    def _set(self, consumer, state_name, func, mocks):
        self.state_registry[(consumer, state_name)] = (func, mocks)

    def prepare_state(self, consumer, state_name):
        func, mocks = self._get(consumer, state_name)
        func()

    def get_mocks(self, consumer, state_name):
        func, mocks = self._get(consumer, state_name)
        return mocks

    @contextmanager
    def enable_mocks(self, consumer_name, state_name):
        with ExitStack() as stack:
            for mock in self.get_mocks(consumer_name, state_name):
                stack.enter_context(mock())
            yield

    def add(self, consumer, state_name, mocks=None):
        if mocks is None:
            mocks = []

        def outer(func):
            self._set(consumer, state_name, func, mocks)

            @wraps(func)
            def inner(*args, **kwds):
                return func(*args, **kwds)

            return inner

        return outer


def _make_provider_state(pact_registry):
    def provider_state(interaction, name, **params):
        pact_registry.prepare_state(interaction.pact.consumer, name)

    return provider_state


def verify_pacts(pact_verifier, live_server, states):
    if pact_verifier.interaction.providerState:
        state_name = pact_verifier.interaction.providerState
    else:
        assert (
            len(pact_verifier.interaction.providerStates) == 1
        ), "Pact interaction must have exactly one state!"
        state_name = pact_verifier.interaction.providerStates[0]["name"]
    consumer_name = pact_verifier.interaction.pact.consumer

    with states.enable_mocks(consumer_name, state_name):
        pact_verifier.verify(live_server.url, _make_provider_state(states))
