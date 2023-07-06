from sentry.models import AuthIdentity, AuthProvider
from sentry.silo import SiloMode
from sentry.testutils import AuthProviderTestCase
from sentry.testutils.silo import assume_test_silo_mode
from sentry.utils.auth import SsoSession


# @control_silo_test(stable=True)
class OrganizationAuthLoginTest(AuthProviderTestCase):
    def test_sso_auth_required(self):
        user = self.create_user("foo@example.com", is_superuser=False)
        organization = self.create_organization(name="foo")
        member = self.create_member(user=user, organization=organization)

        with assume_test_silo_mode(SiloMode.REGION):
            setattr(member.flags, "sso:linked", True)
            member.save()

        auth_provider = AuthProvider.objects.create(
            organization_id=organization.id, provider="dummy", flags=0
        )

        AuthIdentity.objects.create(auth_provider=auth_provider, user=user)

        self.login_as(user)

        path = f"/{organization.slug}/"
        redirect_uri = f"/auth/login/{organization.slug}/?next=%2Ffoo%2F"

        # we should be redirecting the user to the authentication form as they
        # haven't verified this specific organization
        resp = self.client.get(path)
        self.assertRedirects(resp, redirect_uri)

        # superuser should still require SSO as they're a member of the org
        user.update(is_superuser=True)
        resp = self.client.get(path)
        self.assertRedirects(resp, redirect_uri)

        # XXX(dcramer): using internal API as exposing a request object is hard
        sso_session = SsoSession.create(organization.id)
        self.session[sso_session.session_key] = sso_session.to_dict()
        self.save_session()

        # now that SSO is marked as complete, we should be able to access dash
        resp = self.client.get(path)
        assert resp.status_code == 200
