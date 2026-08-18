from rest_framework import generics

from .models import User
from .serializers import RegisterSerializer

# Login and token refresh reuse simplejwt's built-in TokenObtainPairView /
# TokenRefreshView directly in urls.py — no need to wrap them here unless the
# response shape needs to change later.


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = []  # anyone can register; tighten if invite-only later
