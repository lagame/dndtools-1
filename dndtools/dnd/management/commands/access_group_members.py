"""Emit the exact Access group membership desired by the editorial system."""

import json

from django.conf import settings
from django.core.management.base import BaseCommand

from dnd.models import CollaboratorInvite


class Command(BaseCommand):
    help = 'List invited or active editorial emails for the private Access sync helper.'

    def handle(self, *args, **options):
        emails = {settings.ADMINS[0][1].casefold()}
        invites = CollaboratorInvite.objects.select_related('user').filter(
            access_state__in=('pending', 'active'))
        for invite in invites:
            if invite.access_state == 'pending' or invite.user.is_active:
                emails.add(invite.user.email.casefold())
        self.stdout.write(json.dumps({'emails': sorted(emails)}))
