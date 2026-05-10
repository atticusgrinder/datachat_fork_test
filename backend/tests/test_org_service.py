"""Tests for the org service: domain classification, assignment, invites."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.organization import Organization
from app.models.user import User
from app.services import org_service
from app.core.email_domains import is_generic_domain, domain_from_email


class TestDomainHelpers:
    def test_generic_match(self):
        assert is_generic_domain("gmail.com")
        assert is_generic_domain("Outlook.com")
        assert is_generic_domain("ICLOUD.COM")

    def test_work_domain(self):
        assert not is_generic_domain("gazerlabs.com")
        assert not is_generic_domain("synapsedata.ai")

    def test_domain_from_email(self):
        assert domain_from_email("a@gazerlabs.com") == "gazerlabs.com"
        assert domain_from_email("a@FOO.COM") == "foo.com"
        assert domain_from_email("nope") == ""
        assert domain_from_email("") == ""


class TestOrgAssignment:
    def test_work_users_share_one_org(self, db_session):
        a = User(id="u1", email="a@gazerlabs.com", name="A")
        b = User(id="u2", email="b@gazerlabs.com", name="B")
        db_session.add_all([a, b])
        db_session.commit()
        org_a = org_service.get_or_create_org_for_user(db_session, a)
        org_b = org_service.get_or_create_org_for_user(db_session, b)
        assert org_a.id == org_b.id
        assert org_a.domain == "gazerlabs.com"
        assert not org_a.is_personal

    def test_generic_domain_creates_solo_org(self, db_session):
        a = User(id="u1", email="me@gmail.com", name="Me")
        b = User(id="u2", email="other@gmail.com", name="Other")
        db_session.add_all([a, b])
        db_session.commit()
        org_a = org_service.get_or_create_org_for_user(db_session, a)
        org_b = org_service.get_or_create_org_for_user(db_session, b)
        assert org_a.id != org_b.id
        assert org_a.is_personal
        assert org_b.is_personal
        assert org_a.domain is None
        assert org_b.domain is None

    def test_idempotent(self, db_session):
        a = User(id="u1", email="a@example.org", name="A")
        db_session.add(a)
        db_session.commit()
        org1 = org_service.get_or_create_org_for_user(db_session, a)
        org2 = org_service.get_or_create_org_for_user(db_session, a)
        assert org1.id == org2.id
        assert a.organization_id == org1.id

    def test_can_invite(self, db_session):
        work = Organization(name="ex", domain="example.org", is_personal=False)
        personal = Organization(name="me", domain=None, is_personal=True)
        db_session.add_all([work, personal])
        db_session.commit()
        assert org_service.can_invite(work)
        assert not org_service.can_invite(personal)


class TestInvite:
    @pytest.mark.asyncio
    async def test_personal_org_cannot_invite(self, db_session):
        u = User(id="u1", email="me@gmail.com", name="Me")
        db_session.add(u)
        db_session.commit()
        org = org_service.get_or_create_org_for_user(db_session, u)
        with pytest.raises(ValueError, match="personal workspace"):
            await org_service.send_invite(
                db_session, inviter=u, org=org, invitee_email="x@gmail.com",
            )

    @pytest.mark.asyncio
    async def test_domain_mismatch_blocked(self, db_session):
        u = User(id="u1", email="me@gazerlabs.com", name="Me")
        db_session.add(u)
        db_session.commit()
        org = org_service.get_or_create_org_for_user(db_session, u)
        with pytest.raises(ValueError, match="@gazerlabs.com"):
            await org_service.send_invite(
                db_session, inviter=u, org=org, invitee_email="x@otherco.com",
            )

    @pytest.mark.asyncio
    async def test_self_invite_blocked(self, db_session):
        u = User(id="u1", email="me@gazerlabs.com", name="Me")
        db_session.add(u)
        db_session.commit()
        org = org_service.get_or_create_org_for_user(db_session, u)
        with pytest.raises(ValueError, match="invite yourself"):
            await org_service.send_invite(
                db_session, inviter=u, org=org, invitee_email="me@gazerlabs.com",
            )

    @pytest.mark.asyncio
    async def test_already_member_blocked(self, db_session):
        a = User(id="u1", email="a@gazerlabs.com")
        b = User(id="u2", email="b@gazerlabs.com")
        db_session.add_all([a, b])
        db_session.commit()
        org = org_service.get_or_create_org_for_user(db_session, a)
        org_service.get_or_create_org_for_user(db_session, b)
        with pytest.raises(ValueError, match="already a member"):
            await org_service.send_invite(
                db_session, inviter=a, org=org, invitee_email="b@gazerlabs.com",
            )

    @pytest.mark.asyncio
    async def test_happy_path_sends_email(self, db_session):
        u = User(id="u1", email="me@gazerlabs.com", name="Me")
        db_session.add(u)
        db_session.commit()
        org = org_service.get_or_create_org_for_user(db_session, u)

        sent = AsyncMock(return_value="msg-id")
        with patch("app.services.org_service.email_service.send_html", new=sent):
            await org_service.send_invite(
                db_session, inviter=u, org=org, invitee_email="newteammate@gazerlabs.com",
            )
        sent.assert_called_once()
        kwargs = sent.call_args.kwargs
        assert kwargs["to"] == "newteammate@gazerlabs.com"
        assert "gazerlabs.com" in kwargs["html"]
