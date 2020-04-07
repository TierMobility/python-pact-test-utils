from collections import namedtuple
from contextlib import contextmanager

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from pactman import Consumer, Provider
from requests import Request

ResponseDTO = namedtuple("ResponseDTO", ["status", "headers", "body"])
WithRequestDTO = namedtuple(
    "WithRequestDTO", ["method", "path", "body", "headers", "query"]
)


class PactRequestMimic:
    # mimics the behavior of the `requests` module for pact tests
    @classmethod
    def request(cls, method, url, **kwargs) -> WithRequestDTO:
        # pact requires the query to be built by themselves, so let's move the "params"
        # (which is the "query" for requests) to the side instead of using the requests module to do it for us
        query = kwargs.pop("params", None)
        # now let's use all the convenience of requests, so that we have to do as little as possible ourselves!
        # NOTE: The pact server wants a relative URL and requests needs a absolute URL, so to make it absolute, we just
        # throw in a dummy url
        r = Request(method=method, url="http://dummy", **kwargs)
        prepared_request = r.prepare()
        # the prepared request should now contain all the things we need for the pact's "with_request" method.
        # The returned DTO contains all args for the "with_request" method.
        headers = dict(prepared_request.headers)
        # remove the Content-Length header added by requests
        headers.pop("Content-Length", "")
        return WithRequestDTO(
            method=prepared_request.method,
            path=url,
            body=prepared_request.body,
            headers=headers,
            query=query,
        )

    @classmethod
    def get(cls, url, params=None, **kwargs):
        return cls.request("get", url, params=params, **kwargs)

    @classmethod
    def options(cls, url, **kwargs):
        return cls.request("options", url, **kwargs)

    @classmethod
    def head(cls, url, **kwargs):
        return cls.request("head", url, **kwargs)

    @classmethod
    def post(cls, url, data=None, json=None, **kwargs):
        return cls.request("post", url, data=data, json=json, **kwargs)

    @classmethod
    def put(cls, url, data=None, **kwargs):
        return cls.request("put", url, data=data, **kwargs)

    @classmethod
    def patch(cls, url, data=None, **kwargs):
        return cls.request("patch", url, data=data, **kwargs)

    @classmethod
    def delete(cls, url, **kwargs):
        return cls.request("delete", url, **kwargs)


class ConsumerPactTest(TestCase):
    """
    The ConsumerPactTest is a wrapper around the pactman which is more pythonic; You can inherit and
    use mixins to reduce your clutter using this class-based approach. Also, instead of using the
    weird pact-syntax to define API requests, it contains a compatibility layer which translates the
    behavior of the `requests` module to the pact-style automatically.

        # you can use `self.requests` to construct a virtual request which is pact compatible
        request = self.requests.delete(f'/manage/customer/123', headers={'x-api-key': 'api-key'})

    This means that you should be able to go from making a single test-api call to production-ready
    much faster.

    Secondly there is `self.response` which can be used to construct the expected response from
    the producer:

        response = self.response(200, body='lol')

    Now these two can be used with the `self.pact_mock_server` context manager, which brings all of
    these together:

        with self.pact_mock_server(request, response):
            # perform your actual api call here, e.g. using the requests module
            SERVICE = 'localhost:8155'  # pact mock server
            requests.delete(f'{SERVICE}/manage/customer/123', headers={'x-api-key': 'api-key'})

    The only part that isn't fully aligned between the `requests` module and the
    `requests-pact-compat` module, is that requests needs a absolute URL with protocol etc while
    pact needs a url relative to the server.

    The remaining magic parts are the class-attributes that are used instruct which service talks to
    which and also why.

    consumer_name:
        e.g. "RequestSenderService"
    provider_name:
        e.g. "RequestReceiverService"
    provider_state_description:
        e.g. "a user with the id 123 exists"
    provider_request_description:
        e.g. "deletion request for user 123"
    """

    consumer_name = None  # name of the consumer as string
    provider_name = None  # name of the provider as string
    provider_state_description = None
    provider_request_description = None

    _pact = None

    requests = PactRequestMimic

    @classmethod
    def response(self, status, headers=None, body=None):
        return ResponseDTO(status=status, headers=headers, body=body)

    def get_pact(self):
        if not self.__class__._pact:
            self.__class__._pact = Consumer(self.consumer_name).has_pact_with(
                Provider(self.provider_name), version="3.0.0", port=8155
            )
        return self.__class__._pact

    def __init__(self, *args, **kwargs):
        if self.consumer_name is None:
            raise ImproperlyConfigured(
                f'You need to set "consumer_name" e.g. "RequestSenderService"'
            )
        if self.provider_name is None:
            raise ImproperlyConfigured(
                f'You need to set "provider_name" e.g. "RequestReceiverService"'
            )
        if self.provider_state_description is None:
            raise ImproperlyConfigured(
                f'You need to set "provider_state_description" e.g. "a user with the id 123 exists" '
            )
        if self.provider_request_description is None:
            raise ImproperlyConfigured(
                f'You need to set "provider_request_description" e.g. "deletion request for user 123"'
            )
        super().__init__(*args, **kwargs)

    @contextmanager
    def pact_mock_server(self, request: WithRequestDTO, response: ResponseDTO):
        pact = self.get_pact()
        pact.given(self.provider_state_description).upon_receiving(
            self.provider_request_description
        ).with_request(**request._asdict()).will_respond_with(**response._asdict())
        with pact:
            yield
