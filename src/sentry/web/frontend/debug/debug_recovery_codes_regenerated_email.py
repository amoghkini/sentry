import datetime

from django.http import HttpResponse
from django.views.generic import View

from sentry.security.emails import generate_security_email
from sentry.users.models.authenticator import Authenticator
from sentry.utils.auth import AuthenticatedHttpRequest

from .mail import MailPreview


class DebugRecoveryCodesRegeneratedEmailView(View):
    def get(self, request: AuthenticatedHttpRequest) -> HttpResponse:
        authenticator = Authenticator(id=0, type=3, user_id=request.user.id)  # u2f

        email = generate_security_email(
            account=request.user,
            actor=request.user,
            type="recovery-codes-regenerated",
            ip_address=request.META["REMOTE_ADDR"],
            context={"authenticator": authenticator},
            # make this consistent for acceptance tests
            current_datetime=datetime.datetime(2017, 1, 20, 21, 39, 23, 30723),
        )
        return MailPreview(
            html_template=email.html_template, text_template=email.template, context=email.context
        ).render(request)
