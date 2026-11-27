import json

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from dnd.item_requirement_editorial import PREVIEW_SESSION_KEY
from dnd.models import DndEdition, EditorialGrant, EditorialProposal, Item, ItemCreationRequirements, Rulebook


class ItemRequirementEditorialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_superuser(settings.ADMINS[0][0], settings.ADMINS[0][1])
        cls.editor = User.objects.create_user('requirements-editor', is_staff=True)
        cls.creator = User.objects.create_user('item-creator', is_staff=True)
        EditorialGrant.objects.create(user=cls.editor, resource='Item', can_correct=True)
        EditorialGrant.objects.create(user=cls.creator, resource='Item', can_create=True)
        edition = DndEdition.objects.create(name='3.5 Core', slug='core-35', system='DnD 3.5', core=True)
        cls.book = Rulebook.objects.create(name='Example Handbook', slug='example-handbook', abbr='EH', dnd_edition=edition)
        cls.first = Item.objects.create(name='First Shield', slug='first-shield', rulebook=cls.book, page=12,
                                        type=Item.ItemType.ENHANCEMENT, description='A shield property.',
                                        required_extra='One legacy requirement.')
        cls.second = Item.objects.create(name='Second Shield', slug='second-shield', rulebook=cls.book, page=13,
                                         type=Item.ItemType.ENHANCEMENT, description='Another shield property.')

    def _row(self, item):
        return {
            'item_id': item.pk, 'original_name': item.name, 'rulebook_id': self.book.pk, 'page': item.page,
            'source': {'rulebook_id': self.book.pk, 'pages': [item.page]},
            'requirements': {'kind': 'condition', 'en': 'A reviewed requirement.',
                             'pt_br': 'Um requisito conferido.'},
        }

    def _preview(self, *items):
        raw = {'resource': 'ItemCreationRequirements', 'version': 1, 'items': [self._row(item) for item in items]}
        return self._upload(raw)

    def _upload(self, raw):
        file = SimpleUploadedFile('requirements.json', json.dumps(raw).encode('utf-8'), content_type='application/json')
        return self.client.post(reverse('editorial_item_requirements_import'), {'action': 'preview', 'file': file})

    def _submit(self, preview_url, response):
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['token'], response.context['errors'])
        response = self.client.post(preview_url, {'action': 'submit', 'token': response.context['token']})
        self.assertRedirects(response, reverse('editorial_dashboard'), fetch_redirect_response=False)
        return EditorialProposal.objects.get(action='item_reqs')

    def test_individual_requires_correction_permission_and_owner_approval(self):
        url = reverse('editorial_item_requirements', args=[self.first.pk])
        self.client.force_login(self.creator)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.get(reverse('editorial_item_requirements_import')).status_code, 403)

        self.client.force_login(self.editor)
        response = self.client.post(url, {'action': 'preview', 'source_book_id': self.book.pk,
                                          'source_pages': '12, 13',
                                          'requirements': json.dumps(self._row(self.first)['requirements'])})
        self.assertContains(response, 'A reviewed requirement.')
        self.assertContains(response, 'Um requisito conferido.')
        self.assertFalse(EditorialProposal.objects.exists())
        proposal = self._submit(url, response)
        self.assertEqual(proposal.author, self.editor)
        self.assertEqual(proposal.target_pk, self.first.pk)
        self.assertFalse(ItemCreationRequirements.objects.exists())

        decision_url = reverse('editorial_decide', args=[proposal.pk])
        self.assertEqual(self.client.post(decision_url, {'decision': 'approve'}).status_code, 403)
        self.assertFalse(ItemCreationRequirements.objects.exists())
        self.client.force_login(self.owner)
        review = self.client.get(reverse('editorial_review', args=[proposal.pk]))
        self.assertContains(review, 'One legacy requirement.')
        self.assertContains(review, 'Um requisito conferido.')
        self.assertRedirects(self.client.post(decision_url, {'decision': 'approve'}),
                             reverse('editorial_dashboard'), fetch_redirect_response=False)
        published = ItemCreationRequirements.objects.get(item=self.first)
        proposal.refresh_from_db()
        self.first.refresh_from_db()
        self.assertEqual(proposal.status, 'approved')
        self.assertEqual(proposal.reviewer, self.owner)
        self.assertEqual(published.source['pages'], [12, 13])
        self.assertEqual(self.first.required_extra, 'One legacy requirement.')

    def test_batch_preview_expires_and_rejects_other_resources(self):
        self.client.force_login(self.editor)
        url = reverse('editorial_item_requirements_import')
        example = self.client.get(url, {'template': 'json'}).json()
        self.assertEqual(example['resource'], 'ItemCreationRequirements')
        wrong = {'resource': 'Spell', 'version': 1, 'items': [self._row(self.first)]}
        response = self._upload(wrong)
        self.assertFalse(response.context['token'])
        self.assertTrue(response.context['errors'])

        response = self._preview(self.first)
        token = response.context['token']
        session = self.client.session
        preview = session[PREVIEW_SESSION_KEY]
        preview['created'] = 0
        session[PREVIEW_SESSION_KEY] = preview
        session.save()
        expired = self.client.post(url, {'action': 'submit', 'token': token})
        self.assertTrue(expired.context['errors'])
        self.assertFalse(EditorialProposal.objects.exists())
        self.assertFalse(ItemCreationRequirements.objects.exists())

    def test_batch_is_atomic_on_stale_item(self):
        self.client.force_login(self.editor)
        url = reverse('editorial_item_requirements_import')
        proposal = self._submit(url, self._preview(self.first, self.second))
        self.assertIsNone(proposal.target_pk)

        Item.objects.filter(pk=self.second.pk).update(required_extra='A newer requirement.')
        self.client.force_login(self.owner)
        approve = reverse('editorial_decide', args=[proposal.pk])
        review = reverse('editorial_review', args=[proposal.pk])
        self.assertRedirects(self.client.post(approve, {'decision': 'approve'}), review, fetch_redirect_response=False)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, 'pending')
        self.assertFalse(ItemCreationRequirements.objects.exists())

        latest = self._preview(self.first, self.second)
        response = self.client.post(url, {'action': 'submit', 'token': latest.context['token']})
        self.assertRedirects(response, reverse('editorial_dashboard'), fetch_redirect_response=False)
        fresh = EditorialProposal.objects.exclude(pk=proposal.pk).get()
        self.assertRedirects(self.client.post(reverse('editorial_decide', args=[fresh.pk]), {'decision': 'approve'}),
                             reverse('editorial_dashboard'), fetch_redirect_response=False)
        self.assertCountEqual(ItemCreationRequirements.objects.filter(proposal=fresh).values_list('item_id', flat=True),
                              [self.first.pk, self.second.pk])
