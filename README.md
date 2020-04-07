# python-pact-test-utils
A wrapper for pact tests to make them more pythonic

The `ConsumerPactTest` is a wrapper around the `pactman` which makes it more
pythonic. You can inherit and use mixins to reduce your clutter using this
class-based approach. Also, instead of using the special pact-syntax to define
API requests, it contains a compatibility layer which translates the behavior of
the well-known requests module.

This means that you should be able to go from making a single test-api call to
production-ready and pact-tested much faster.


Creating Pacts as Consumer
--------------------------

    import requests
    from pact_test_utils.testcase import ConsumerPactTest
    
    
    class TestDummyPact(ConsumerPactTest):
        consumer_name = "InAppShopServices"
        provider_name = "FakeDummyService"
        provider_state_description = 'has a customer with the id "123"'
        provider_request_description = 'a request to delete customer with id "123"'
    
        def test_delete_customer(self):
            # prepare the request using the fake requests module (`self.requests`)
            request = self.requests.delete(
                f"/manage/customer/123", headers={"x-api-key": "consumer-api-key"}
            )
            # prepare the response
            response = self.response(204)
    
            # kick off the pact server in a context-manager
            with self.pact_mock_server(request, response) as server:
                # You should call your integration here instead of a plain requests call
                requests.delete(
                    f"{server.url}/manage/customer/123",
                    headers={"x-api-key": "consumer-api-key"},
                )

The magic parts here are the class-attributes that are used to initialize the pact server thingy.
Other three things are:
 - `self.requests` which is the pact-requests-translation layer
 - `self.response` which is a thin layer around the `pact.with_response` call
    and finally
 - the context manager `self.pact_mock_server` which brings all of these together.

Verifying pacts as Producer
---------------------------

To verify pacts you need to reproduce the correct state for the consumer.
All of these instructions how to produce a certain state are kept in a registry
for the tests to run in, called `PactStates`.

    import os
    import pytest
    from pact_test_utils.producer import PactStates, verify_pacts
    
    # create a new registry for pact states to be referenced in
    states = PactStates()
    
    # you can mark functions that reproduce a certain state using the `states.add`
    # decorator.
    @states.add("OtherService", "the in app shop service is e.g. drinking milk")
    def in_app_shop_service_drinks_milk():
        from unittest.mock import MagicMock
    
        cow = MagicMock()
        milk = cow.spin()
        milk.drink()
    

    # This part is the only one required to be copied into your test-suite
    # for all pact tests to be executed.    
    @pytest.mark.usefixtures("live_server", "pact_verifier")
    def test_pacts(live_server, pact_verifier):
        verify_pacts(live_server, pact_verifier, states)
