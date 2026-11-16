from django.urls import path

from dnd.supplemental import views

urlpatterns = [
    path('<slug:kind>/', views.index, name='supplemental_index'),
    path('<slug:kind>/<slug:slug>--<int:entry_id>/', views.detail, name='supplemental_detail'),
]
