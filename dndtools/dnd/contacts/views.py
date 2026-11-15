from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from dnd.menu import menu_item, submenu_item, MenuItem
from dnd.models import StaticPage


@menu_item(MenuItem.CONTACTS)
@submenu_item(MenuItem.Contacts.CONTACT_US)
@require_GET
def contact(request):
    return render(request, 'dnd/contacts/contact.html')


@require_GET
def contact_sent(request):
    return redirect('contact')


@menu_item(MenuItem.CONTACTS)
@submenu_item(MenuItem.Contacts.STAFF)
def staff(request):
    return render(request, 'dnd/contacts/staff.html', {
        'page_body': get_object_or_404(StaticPage, name='staff'),
    })


@menu_item(MenuItem.ANDROID)
def android(request):
    page_body = StaticPage.objects.filter(name='android').first()
    return render(request, 'dnd/static/android.html', {
        'page_body': page_body,
    })
