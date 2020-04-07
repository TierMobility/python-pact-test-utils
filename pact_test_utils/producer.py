from contextlib import ExitStack
import logging
from functools import wraps
from pactman.verifier.verify import ProviderStateError

logger = logging.getLogger(__name__)


class PactRegistry:
    def __init__(self):
        self.state_registry = {}

    def add(self, consumer, state_name, state_func, mocks=None):
        if mocks is None:
            mocks = []
        self.state_registry[(consumer, state_name)] = (state_func, mocks)

    def get(self, consumer, state_name):
        try:
            return self.state_registry[(consumer, state_name)]
        except KeyError:
            raise ProviderStateError(
                f"Missing state provider for consumer:\n@pact_state('{consumer}', '{state_name}')"
            )

    def prepare_state(self, consumer, state_name):
        func, mocks = self.get(consumer, state_name)
        func()

    def get_mocks(self, consumer, state_name):
        func, mocks = self.get(consumer, state_name)
        return mocks

    def state(self, consumer, state_name, mocks=None):
        def outer(func):
            self.add(consumer, state_name, func, mocks=mocks)

            @wraps(func)
            def inner(*args, **kwds):
                return func(*args, **kwds)

            return inner

        return outer


def _make_provider_state(pact_registry):
    def provider_state(interaction, name, **params):
        pact_registry.prepare_state(interaction.pact.consumer, name)

    return provider_state


def verify_pacts(pact_verifier, live_server, pact_registry):
    if pact_verifier.interaction.providerState:
        state_name = pact_verifier.interaction.providerState
    else:
        assert (
            len(pact_verifier.interaction.providerStates) == 1
        ), "Pact interaction must have exactly one state!"
        state_name = pact_verifier.interaction.providerStates[0]["name"]
    consumer_name = pact_verifier.interaction.pact.consumer
    mocks = pact_registry.get_mocks(consumer_name, state_name)

    with ExitStack() as stack:
        for mock in mocks:
            stack.enter_context(mock())
        pact_verifier.verify(live_server.url, _make_provider_state(pact_registry))
