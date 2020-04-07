# python-pact-test-utils
A wrapper for pact tests to make them more pythonic

The `ConsumerPactTest` is a wrapper around the `pactman` which makes it more
pythonic. You can inherit and use mixins to reduce your clutter using this
class-based approach. Also, instead of using the special pact-syntax to define
API requests, it contains a compatibility layer which translates the behavior of
the well-known requests module.

This means that you should be able to go from making a single test-api call to
production-ready and pact-tested much faster.


Usage Example
-------------

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
            with self.pact_mock_server(request, response):
                # You should call your integration here instead of a plain requests call
                requests.delete(
                    f"http://fakeservice/manage/customer/123", headers={"x-api-key": "consumer-api-key"}
                )
