from rest_framework import serializers

from .models import Membership, Workspace


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ("id", "name", "created_at", "updated_at")


class MembershipSerializer(serializers.ModelSerializer):
    # Read-only convenience field — testui (and any real client) wants a
    # name to show, not just the user's id.
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "user", "username", "workspace", "role", "created_at")
        # user/workspace are set by the view (from the URL + resolved
        # username), never client-writable on an existing membership — same
        # reasoning as `workspace` being read-only on Board/Task.
        read_only_fields = ("user", "workspace")


class AddMemberSerializer(serializers.Serializer):
    """Input shape for WorkspaceViewSet.members' POST branch — add an
    existing user to a workspace by username, admin/owner only."""

    username = serializers.CharField()
    role = serializers.ChoiceField(choices=Membership.Role.choices, default=Membership.Role.MEMBER)
