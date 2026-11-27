from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from dnd.catalog_ordering import order_catalog, search_book_names
from dnd.editorial import source_digest
from dnd.models import DndEdition, Item, PublishedTranslation, Rulebook


class CatalogOrderingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        edition = DndEdition.objects.create(name='Edition', system='DnD 3.5', slug='edition', core=True)
        cls.book = Rulebook.objects.create(dnd_edition=edition, name='Book', abbr='BK', slug='book')
        cls.other = Rulebook.objects.create(dnd_edition=edition, name='Other', abbr='OT', slug='other')
        cls.apple = Item.objects.create(rulebook=cls.book, type='ENH', name='Apple', slug='apple-sort',
                                        price_gp=1000, description='Apple rules.')
        cls.zebra = Item.objects.create(rulebook=cls.book, type='ENH', name='Zebra', slug='zebra-sort',
                                        price_gp=500, description='Zebra rules.')
        cls.lemon = Item.objects.create(rulebook=cls.book, type='ENH', name='Lemon', slug='lemon-sort',
                                        price_bonus=2, description='Lemon rules.')
        cls.blank = Item.objects.create(rulebook=cls.book, type='ENH', name='Blank', slug='blank-sort',
                                        description='Blank rules.')
        cls.foreign = Item.objects.create(rulebook=cls.other, type='ENH', name='Other item',
                                          slug='other-sort', description='Other rules.')
        user = User.objects.create(username='translator')
        for item, name in ((cls.apple, 'Gato'), (cls.zebra, 'Bola'), (cls.foreign, 'Bola distante')):
            PublishedTranslation.objects.create(
                resource='Item', target_pk=item.pk, locale='pt-br',
                payload={'name': name, 'description': item.description},
                source_digest=source_digest(item, translation=True), author=user, reviewer=user)

    def request(self, params, language='pt-br'):
        request = RequestFactory().get('/', params)
        request.LANGUAGE_CODE = language
        request.session = {}
        return request

    def test_name_sort_uses_current_translation_before_pagination(self):
        rows = Item.objects.filter(rulebook=self.book)
        sorted_rows, key = order_catalog(rows, self.request({'order': 'name'}))
        self.assertEqual(key, 'name')
        self.assertEqual(list(sorted_rows.values_list('name', flat=True)),
                         ['Blank', 'Zebra', 'Apple', 'Lemon'])
        english, _ = order_catalog(rows, self.request({'order': 'name'}, 'en-us'))
        self.assertEqual(list(english.values_list('name', flat=True)),
                         ['Apple', 'Blank', 'Lemon', 'Zebra'])
        descending, _ = order_catalog(rows, self.request({'order': '-name'}))
        self.assertEqual(list(descending.values_list('name', flat=True))[0], 'Lemon')

    def test_cost_sort_groups_gp_bonus_and_empty(self):
        rows = Item.objects.filter(rulebook=self.book)
        asc, _ = order_catalog(rows, self.request({'order': 'cost'}))
        desc, _ = order_catalog(rows, self.request({'order': '-cost'}))
        self.assertEqual(list(asc.values_list('name', flat=True)),
                         ['Zebra', 'Apple', 'Lemon', 'Blank'])
        self.assertEqual(list(desc.values_list('name', flat=True)),
                         ['Apple', 'Zebra', 'Lemon', 'Blank'])

    def test_stale_translation_falls_back_and_unknown_order_is_ignored(self):
        Item.objects.filter(pk=self.zebra.pk).update(name='Aardvark')
        rows = Item.objects.filter(rulebook=self.book)
        sorted_rows, _ = order_catalog(rows, self.request({'order': 'name'}))
        self.assertEqual(sorted_rows.first().name, 'Aardvark')
        untouched, key = order_catalog(rows, self.request({'order': 'rulebook__id;drop'}))
        self.assertEqual(key, '')
        self.assertEqual(untouched.query.order_by, rows.query.order_by)

    def test_book_search_is_scoped_and_language_aware(self):
        rows = Item.objects.filter(rulebook=self.book)
        portuguese = search_book_names(rows, self.request({'q': 'Bola'}))
        self.assertEqual(list(portuguese.values_list('name', flat=True)), ['Zebra'])
        english = search_book_names(rows, self.request({'q': 'Bola'}, 'en-us'))
        self.assertFalse(english.exists())

    def test_header_keeps_search_and_page_size_but_resets_page(self):
        response = self.client.get('/pt-br/items/book--%s/' % self.book.pk,
                                   {'q': 'Bola', 'order': 'name', 'page_size': '50', 'page': '2'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'order=-name')
        self.assertContains(response, 'page_size=50')
        self.assertContains(response, 'q=Bola')
        self.assertNotContains(response, 'order=-name&amp;page=2')

    def test_book_search_is_available_across_catalogs(self):
        routes = ('items/book--{id}/', 'spells/book--{id}/', 'feats/book--{id}/',
                  'monsters/book--{id}/', 'races/book--{id}/',
                  'classes/rulebook/book--{id}/', 'skills/rulebook/book--{id}/')
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get('/pt-br/' + route.format(id=self.book.pk),
                                           {'q': 'Bola', 'order': 'name'})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'name="q"')
