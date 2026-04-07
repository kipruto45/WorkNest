from __future__ import annotations

import re
from collections import OrderedDict

from django.utils.text import slugify

from apps.memberships.models import Membership

MENTION_PATTERN = re.compile(r"(?<![\w@])@([A-Za-z0-9._-]{2,50})")


def extract_mention_handles(content: str) -> list[str]:
    if not content:
        return []
    matches = [match.lower() for match in MENTION_PATTERN.findall(content)]
    return list(OrderedDict.fromkeys(matches))


def _build_user_handles(user) -> set[str]:
    handles: set[str] = set()

    if user.email:
        handles.add(user.email.split("@", 1)[0].lower())

    for value in (user.name, getattr(user, "first_name", ""), getattr(user, "last_name", "")):
        if not value:
            continue
        normalized = slugify(value)
        if not normalized:
            continue
        handles.add(normalized)
        handles.add(normalized.replace("-", ""))
        handles.add(normalized.replace("-", "."))
        handles.add(normalized.replace("-", "_"))

    first_name = slugify(getattr(user, "first_name", ""))
    last_name = slugify(getattr(user, "last_name", ""))
    if first_name and last_name:
        handles.add(f"{first_name}.{last_name}")
        handles.add(f"{first_name}_{last_name}")
        handles.add(f"{first_name}{last_name}")

    return {handle for handle in handles if handle}


def resolve_mentions_for_team(*, content: str, team) -> list:
    handles = extract_mention_handles(content)
    if not handles:
        return []

    memberships = (
        Membership.objects.filter(team=team, status=Membership.Status.ACTIVE)
        .select_related("user")
        .order_by("user__name", "user__email")
    )

    matched_users = []
    remaining_handles = set(handles)
    for membership in memberships:
        user = membership.user
        user_handles = _build_user_handles(user)
        if remaining_handles.intersection(user_handles):
            matched_users.append(user)
            remaining_handles.difference_update(user_handles)
        if not remaining_handles:
            break

    return matched_users
