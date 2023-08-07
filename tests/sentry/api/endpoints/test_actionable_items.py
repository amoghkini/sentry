from django.utils import timezone
from rest_framework import status

from sentry.api.helpers.actionable_items_helper import get_file_extension, is_frame_filename_valid
from sentry.models import EventError, PromptsActivity, SourceMapProcessingIssue
from sentry.testutils.cases import APITestCase
from sentry.testutils.helpers import with_feature
from sentry.testutils.silo import region_silo_test


@region_silo_test
class ActionableItemsEndpointTestCase(APITestCase):
    # These tests will not focus on the actual source map debugging functionality as that is covered in
    # test_source_map_debug.py. Instead, these tests will focus on the unique parts of this endpoint including the responses,
    # and how event errors are handled.
    endpoint = "sentry-api-0-event-actionable-items"

    base_data = {
        "event_id": "a" * 32,
        "sdk": {
            "name": "sentry.javascript.browser",
            "version": "7.3.0",
        },
        "exception": {
            "values": [
                {
                    "type": "Error",
                    "stacktrace": {
                        "frames": [
                            {
                                "abs_path": "https://app.example.com/static/js/main.fa8fe19f.js",
                                "filename": "/static/js/main.fa8fe19f.js",
                                "lineno": 1,
                                "colno": 39,
                                "context_line": "function foo() {",
                                "in_app": True,
                            }
                        ]
                    },
                },
            ]
        },
    }

    class TestFrame:
        def __init__(self, abs_path, filename=None, in_app=None, function=None):
            self.abs_path = abs_path
            self.filename = filename
            self.in_app = in_app
            self.function = function

    def setUp(self) -> None:
        self.login_as(self.user)
        return super().setUp()

    def test_get_file_extension(self):
        cases = [("foo.js", "js"), ("foo.spec.js", "js"), ("foo", None)]
        for filename, expected in cases:
            assert get_file_extension(filename) == expected

    def test_is_frame_filename_valid(self):
        cases = [
            (
                self.TestFrame(
                    abs_path="https://app.example.com/static/js/main.fa8fe19f.js",
                    filename="<anonymous>",
                    in_app=True,
                ),
                False,
            ),
            (
                self.TestFrame(
                    abs_path="https://app.example.com/static/js/main.fa8fe19f.js",
                    function="@webkit-masked-url",
                    in_app=True,
                ),
                False,
            ),
            (
                self.TestFrame(
                    abs_path="https://app.example.com/static/js/main",
                ),
                False,
            ),
            (
                self.TestFrame(
                    abs_path="https://app.example.com/static/js/main.fa8fe19f.js",
                ),
                True,
            ),
        ]

        for frame, expected in cases:
            assert is_frame_filename_valid(frame) == expected

    def test_no_feature_flag(self):
        event = self.store_event(
            data={"event_id": "a" * 32},
            project_id=self.project.id,
        )
        resp = self.get_error_response(
            self.organization.slug,
            self.project.slug,
            event.event_id,
            status_code=status.HTTP_404_NOT_FOUND,
        )
        assert (
            resp.data["detail"]
            == "Endpoint not available without 'organizations:actionable-items' feature flag"
        )

    @with_feature("organizations:actionable-items")
    def test_missing_event(self):
        resp = self.get_error_response(
            self.organization.slug,
            self.project.slug,
            "invalid_id",
            status_code=status.HTTP_404_NOT_FOUND,
        )
        assert resp.data["detail"] == "Event not found"

    @with_feature("organizations:actionable-items")
    def test_event_is_not_javascript(self):
        data = {
            "event_id": "a" * 32,
            "sdk": {
                "name": "sentry.python",
                "version": "1.29.2",
            },
            "exception": {
                "values": [
                    {
                        "type": "Error",
                        "stacktrace": {
                            "frames": [
                                {
                                    "abs_path": "https://app.example.com/static/py/main.py",
                                    "filename": "/static/py/main.py",
                                    "lineno": 1,
                                    "colno": 39,
                                    "context_line": "return results",
                                    "in_app": True,
                                }
                            ]
                        },
                    },
                ]
            },
        }

        event = self.store_event(
            data=data,
            project_id=self.project.id,
        )

        resp = self.get_success_response(
            self.organization.slug,
            self.project.slug,
            event.event_id,
        )

        assert resp.data["errors"] == []

    @with_feature("organizations:actionable-items")
    def test_event_has_no_release(self):
        event = self.store_event(
            data=self.base_data,
            project_id=self.project.id,
        )

        # Dismiss from 2 weeks ago should be ignored
        PromptsActivity.objects.create(
            organization_id=self.organization.id,
            user_id=self.user.id,
            feature=SourceMapProcessingIssue.MISSING_RELEASE,
            project_id=self.project.id,
            data={"dismissed_ts": timezone.now().timestamp() - 60 * 60 * 24 * 14},
        )

        resp = self.get_success_response(
            self.organization.slug,
            self.project.slug,
            event.event_id,
        )

        error = resp.data["errors"][0]
        assert error["type"] == "no_release_on_event"
        assert error["message"] == "The event is missing a release"
        assert not error["dismissed"]

    @with_feature("organizations:actionable-items")
    def test_event_has_no_release_dismissed(self):
        event = self.store_event(
            data=self.base_data,
            project_id=self.project.id,
        )

        PromptsActivity.objects.create(
            organization_id=self.organization.id,
            user_id=self.user.id,
            feature=SourceMapProcessingIssue.MISSING_RELEASE,
            project_id=self.project.id,
            data={"dismissed_ts": timezone.now().timestamp() - 60 * 60 * 24 * 5},
        )

        resp = self.get_success_response(
            self.organization.slug,
            self.project.slug,
            event.event_id,
        )

        error = resp.data["errors"][0]
        assert error["type"] == "no_release_on_event"
        assert error["message"] == "The event is missing a release"
        assert error["dismissed"]

    @with_feature("organizations:actionable-items")
    def test_multiple_source_map_errors(self):
        data = {
            "event_id": "a" * 32,
            "sdk": {
                "name": "sentry.javascript.browser",
                "version": "7.3.0",
            },
            "exception": {
                "values": [
                    {
                        "type": "Error",
                        "stacktrace": {
                            "frames": [
                                {
                                    "abs_path": "https://app.example.com/static/js/main.fa8fe19f.js",
                                    "filename": "/static/js/main.fa8fe19f.js",
                                    "lineno": 1,
                                    "colno": 39,
                                    "context_line": "function foo() {",
                                    "in_app": True,
                                },
                                {
                                    "abs_path": "https://app.example.com/static/js/main.fa8fe19f.js",
                                    "filename": "/static/js/main.fa8fe19f.js",
                                    "lineno": 10,
                                    "colno": 15,
                                    "context_line": "function baz() {",
                                    "in_app": True,
                                },
                                {
                                    "abs_path": "https://app.example.com/static/js/main.a1b2c3.js",
                                    "filename": "/static/js/main.a1b2c3.js",
                                    "lineno": 2,
                                    "colno": 50,
                                    "context_line": "function bar() {",
                                    "in_app": True,
                                },
                            ]
                        },
                    },
                ]
            },
        }
        event = self.store_event(
            data=data,
            project_id=self.project.id,
        )

        resp = self.get_success_response(
            self.organization.slug,
            self.project.slug,
            event.event_id,
        )

        errors = resp.data["errors"]

        # Should have 2 errors, one path is repeated so it shouldn't have an error
        assert len(errors) == 2

        assert errors[0]["type"] == "no_release_on_event"
        assert errors[1]["type"] == "no_release_on_event"

    @with_feature("organizations:actionable-items")
    def test_event_has_no_release_with_event_error(self):
        data = {
            "event_id": "a" * 32,
            "sdk": {
                "name": "sentry.javascript.browser",
                "version": "7.3.0",
            },
            "exception": {
                "values": [
                    {
                        "type": "Error",
                        "stacktrace": {
                            "frames": [
                                {
                                    "abs_path": "https://app.example.com/static/js/main.fa8fe19f.js",
                                    "filename": "/static/js/main.fa8fe19f.js",
                                    "lineno": 1,
                                    "colno": 39,
                                    "context_line": "function foo() {",
                                    "in_app": True,
                                }
                            ]
                        },
                    },
                ]
            },
            "errors": [{"type": EventError.JS_SCRAPING_DISABLED, "url": "http://example.com"}],
        }

        event = self.store_event(
            data=data,
            project_id=self.project.id,
            assert_no_errors=False,
        )

        resp = self.get_success_response(
            self.organization.slug,
            self.project.slug,
            event.event_id,
        )

        errors = resp.data["errors"]

        assert len(errors) == 2

        # Sourcemap error should be first
        sourcemap_error = errors[0]
        event_error = errors[1]

        assert sourcemap_error["type"] == SourceMapProcessingIssue.MISSING_RELEASE
        assert event_error["type"] == EventError.JS_SCRAPING_DISABLED

    @with_feature("organizations:actionable-items")
    def test_orders_event_errors_by_priority(self):
        event = self.store_event(
            data={
                "event_id": "a" * 32,
                "sdk": {
                    "name": "sentry.javascript.browser",
                    "version": "7.3.0",
                },
                "exception": {
                    "values": [
                        {
                            "type": "Error",
                            "stacktrace": {
                                "frames": [
                                    {
                                        "abs_path": "https://app.example.com/static/js/main.fa8fe19f.js",
                                        "filename": "/static/js/main.fa8fe19f.js",
                                        "lineno": 1,
                                        "colno": 39,
                                        "context_line": "function foo() {",
                                        "in_app": True,
                                        "data": {
                                            "sourcemap": "https://media.sentry.io/_static/29e365f8b0d923bc123e8afa38d890c3/sentry/dist/vendor.js.map",
                                            "symbolicated": True,
                                        },
                                    }
                                ]
                            },
                        },
                    ]
                },
                "errors": [
                    {"type": EventError.INVALID_DATA, "name": "foo"},
                    {"type": EventError.JS_SCRAPING_DISABLED, "url": "http://example.com"},
                    {"type": EventError.UNKNOWN_ERROR, "name": "bar"},
                ],
            },
            project_id=self.project.id,
            assert_no_errors=False,
        )

        resp = self.get_success_response(
            self.organization.slug,
            self.project.slug,
            event.event_id,
        )

        errors = resp.data["errors"]

        # Unknown error should be hidden
        assert len(errors) == 2

        # Scraping Error should be first by priority
        scraping_error = errors[0]
        invalid_data = errors[1]

        assert scraping_error["type"] == EventError.JS_SCRAPING_DISABLED
        assert invalid_data["type"] == EventError.INVALID_DATA
