from django.contrib.auth.models import AbstractUser

from apps.core.models import BaseModel


class User(AbstractUser, BaseModel):
    """
    Custom user model so the project isn't locked into Django's default
    integer-pk auth.User from day one — swapping AUTH_USER_MODEL after the
    fact is a painful migration, so it's decided up front even though the
    fields are otherwise identical to AbstractUser for now.

    id / created_at / updated_at come from BaseModel (UUID pk); username,
    email, password, etc. come from AbstractUser.
    """
