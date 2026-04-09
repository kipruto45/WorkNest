from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.memberships.models import Membership
from apps.teams.models import Team
from apps.teams.services import create_team_with_owner, generate_unique_team_slug
from apps.users.models import User


DEFAULT_PASSWORD = "LocalDemo123!"
DEFAULT_TEAM_NAME = "Role Demo Workspace"


ROLE_USERS = [
    {
        "role": Membership.Role.ADMIN,
        "email": "admin@worknest.local",
        "name": "Admin User",
        "first_name": "Admin",
        "last_name": "User",
        "is_staff": True,
    },
    {
        "role": Membership.Role.MANAGER,
        "email": "manager@worknest.local",
        "name": "Manager User",
        "first_name": "Manager",
        "last_name": "User",
        "is_staff": False,
    },
    {
        "role": Membership.Role.MEMBER,
        "email": "member@worknest.local",
        "name": "Member User",
        "first_name": "Member",
        "last_name": "User",
        "is_staff": False,
    },
]


class Command(BaseCommand):
    help = "Create three local users mapped to admin, manager, and member roles."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help=f"Password to assign to every generated user. Defaults to {DEFAULT_PASSWORD}.",
        )
        parser.add_argument(
            "--team",
            default=DEFAULT_TEAM_NAME,
            help=f"Team name to use for the generated memberships. Defaults to {DEFAULT_TEAM_NAME}.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        team_name = options["team"].strip() or DEFAULT_TEAM_NAME

        users_by_role: dict[str, User] = {}

        for payload in ROLE_USERS:
            user, created = User.objects.get_or_create(
                email=payload["email"],
                defaults={
                    "name": payload["name"],
                    "first_name": payload["first_name"],
                    "last_name": payload["last_name"],
                    "is_staff": payload["is_staff"],
                    "email_verified": True,
                },
            )
            updated_fields: list[str] = []
            for field in ("name", "first_name", "last_name", "is_staff"):
                if getattr(user, field) != payload[field]:
                    setattr(user, field, payload[field])
                    updated_fields.append(field)
            if not user.email_verified:
                user.email_verified = True
                updated_fields.append("email_verified")
            user.set_password(password)
            updated_fields.append("password")
            if created or updated_fields:
                user.save(update_fields=list(dict.fromkeys(updated_fields + ["updated_at"])))
            users_by_role[payload["role"]] = user

        admin_user = users_by_role[Membership.Role.ADMIN]
        team = Team.objects.filter(name=team_name, created_by=admin_user).first()
        if not team:
            team = create_team_with_owner(
                created_by=admin_user,
                name=team_name,
                description="Seeded workspace for admin, manager, and member role testing.",
                allow_manager_invites=True,
            )
        else:
            team.slug = team.slug or generate_unique_team_slug(name=team_name)
            team.description = "Seeded workspace for admin, manager, and member role testing."
            team.allow_manager_invites = True
            team.is_archived = False
            team.archived_at = None
            team.save(update_fields=["slug", "description", "allow_manager_invites", "is_archived", "archived_at", "updated_at"])

        for role, user in users_by_role.items():
            membership, _ = Membership.objects.get_or_create(
                team=team,
                user=user,
                defaults={
                    "role": role,
                    "status": Membership.Status.ACTIVE,
                    "invited_by": admin_user,
                    "joined_at": timezone.now(),
                },
            )
            membership.role = role
            membership.status = Membership.Status.ACTIVE
            membership.invited_by = admin_user
            membership.joined_at = membership.joined_at or timezone.now()
            membership.save(update_fields=["role", "status", "invited_by", "joined_at", "updated_at"])

        self.stdout.write(self.style.SUCCESS("Generated local role users successfully."))
        self.stdout.write("")
        self.stdout.write(f"Team: {team.name}")
        self.stdout.write(f"Password: {password}")
        self.stdout.write("")
        for payload in ROLE_USERS:
            self.stdout.write(f"{payload['role']}: {payload['email']}")
