"""
Exercises IsWorkspaceAdmin end to end via the real Workspace endpoints —
renaming/deleting a workspace and managing its membership are owner/admin
only; plain members can view but not mutate; non-members can't even see it.
See notes/current_progress.md "Next course of action" #3.
"""

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from apps.workspaces.models import Membership, Workspace

User = get_user_model()


class WorkspaceAdminPermissionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pw")
        self.admin = User.objects.create_user(username="admin", password="pw")
        self.member = User.objects.create_user(username="member", password="pw")
        self.outsider = User.objects.create_user(username="outsider", password="pw")

        self.workspace = Workspace.objects.create(name="Acme")
        Membership.objects.create(user=self.owner, workspace=self.workspace, role=Membership.Role.OWNER)
        Membership.objects.create(user=self.admin, workspace=self.workspace, role=Membership.Role.ADMIN)
        Membership.objects.create(user=self.member, workspace=self.workspace, role=Membership.Role.MEMBER)

    def as_(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    # ---- rename / delete the workspace itself ----

    def test_member_cannot_rename_workspace(self):
        res = self.as_(self.member).patch(f"/api/workspaces/{self.workspace.id}/", {"name": "Hacked"})
        self.assertEqual(res.status_code, 403)

    def test_admin_can_rename_workspace(self):
        res = self.as_(self.admin).patch(f"/api/workspaces/{self.workspace.id}/", {"name": "Renamed"})
        self.assertEqual(res.status_code, 200)

    def test_member_cannot_delete_workspace(self):
        res = self.as_(self.member).delete(f"/api/workspaces/{self.workspace.id}/")
        self.assertEqual(res.status_code, 403)
        self.assertTrue(Workspace.objects.filter(id=self.workspace.id).exists())

    def test_owner_can_delete_workspace(self):
        res = self.as_(self.owner).delete(f"/api/workspaces/{self.workspace.id}/")
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Workspace.objects.filter(id=self.workspace.id).exists())

    def test_non_member_gets_404_not_403(self):
        # Not a member at all — get_queryset scopes to real memberships, so
        # they shouldn't even learn the workspace exists.
        res = self.as_(self.outsider).delete(f"/api/workspaces/{self.workspace.id}/")
        self.assertEqual(res.status_code, 404)

    def test_admin_elsewhere_has_no_rights_here(self):
        # Being owner/admin of a *different* workspace must not grant any
        # rights on this one.
        other = Workspace.objects.create(name="Other")
        Membership.objects.create(user=self.outsider, workspace=other, role=Membership.Role.OWNER)
        res = self.as_(self.outsider).delete(f"/api/workspaces/{self.workspace.id}/")
        self.assertEqual(res.status_code, 404)

    # ---- membership management ----

    def test_member_can_view_member_list(self):
        res = self.as_(self.member).get(f"/api/workspaces/{self.workspace.id}/members/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 3)

    def test_member_cannot_add_member(self):
        res = self.as_(self.member).post(
            f"/api/workspaces/{self.workspace.id}/members/",
            {"username": "outsider", "role": "member"},
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_can_add_member(self):
        res = self.as_(self.admin).post(
            f"/api/workspaces/{self.workspace.id}/members/",
            {"username": "outsider", "role": "member"},
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(Membership.objects.filter(user=self.outsider, workspace=self.workspace).exists())

    def test_cannot_add_same_member_twice(self):
        res = self.as_(self.admin).post(
            f"/api/workspaces/{self.workspace.id}/members/",
            {"username": "member", "role": "admin"},
        )
        self.assertEqual(res.status_code, 400)

    def test_admin_can_promote_member(self):
        res = self.as_(self.admin).patch(
            f"/api/workspaces/{self.workspace.id}/members/{self.member.id}/",
            {"role": "admin"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            Membership.objects.get(user=self.member, workspace=self.workspace).role,
            Membership.Role.ADMIN,
        )

    def test_member_cannot_change_roles(self):
        res = self.as_(self.member).patch(
            f"/api/workspaces/{self.workspace.id}/members/{self.admin.id}/",
            {"role": "member"},
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_can_remove_member(self):
        res = self.as_(self.admin).delete(f"/api/workspaces/{self.workspace.id}/members/{self.member.id}/")
        self.assertEqual(res.status_code, 204)
        self.assertFalse(Membership.objects.filter(user=self.member, workspace=self.workspace).exists())

    def test_cannot_demote_last_owner(self):
        res = self.as_(self.owner).patch(
            f"/api/workspaces/{self.workspace.id}/members/{self.owner.id}/",
            {"role": "member"},
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(
            Membership.objects.get(user=self.owner, workspace=self.workspace).role,
            Membership.Role.OWNER,
        )

    def test_cannot_remove_last_owner(self):
        res = self.as_(self.owner).delete(f"/api/workspaces/{self.workspace.id}/members/{self.owner.id}/")
        self.assertEqual(res.status_code, 400)
        self.assertTrue(Membership.objects.filter(user=self.owner, workspace=self.workspace).exists())
