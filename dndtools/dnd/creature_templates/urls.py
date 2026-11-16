from django.urls import path

from dnd.creature_templates import views


urlpatterns = [
    path('', views.index, name='creature_template_index'),
    path('<slug:slug>--<int:template_id>/', views.detail, name='creature_template_detail'),
]
