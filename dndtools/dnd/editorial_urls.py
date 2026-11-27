from django.urls import path
from dnd import editorial_views as views
from dnd.item_requirement_editorial import item_requirements_editor

urlpatterns = [
    path('', views.dashboard, name='editorial_dashboard'),
    path('switch-account/', views.switch_account, name='editorial_switch_account'),
    path('invite/', views.invite, name='editorial_invite'),
    path('activate/', views.activate, name='editorial_activate'),
    path('invite/<int:invite_id>/revoke/', views.revoke, name='editorial_revoke'),
    path('catalog/<str:resource>/', views.catalog, name='editorial_catalog'),
    path('catalog/<str:resource>/import/', views.import_catalog, name='editorial_import'),
    path('catalog/Item/creation-requirements/import/', item_requirements_editor,
         name='editorial_item_requirements_import'),
    path('catalog/Item/<int:target_pk>/creation-requirements/', item_requirements_editor,
         name='editorial_item_requirements'),
    path('imports/<int:batch_id>/', views.import_batch, name='editorial_import_batch'),
    path('catalog/<str:resource>/create/', views.propose, {'action': 'create'}, name='editorial_create'),
    path('catalog/<str:resource>/<int:target_pk>/correct/', views.propose,
         {'action': 'correct'}, name='editorial_correct'),
    path('catalog/<str:resource>/<int:target_pk>/translate/', views.propose,
         {'action': 'translate'}, name='editorial_translate'),
    path('catalog/<str:resource>/<int:target_pk>/remove/', views.propose,
         {'action': 'delete'}, name='editorial_delete'),
    path('review/<int:proposal_id>/', views.review, name='editorial_review'),
    path('review/<int:proposal_id>/decide/', views.decide, name='editorial_decide'),
]
