import debug_toolbar
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from bsadmin.views import sign_in_view, sign_out_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', sign_in_view, name='login'),
    path('logout/', sign_out_view, name='logout'),
    path('', include('bsadmin.urls'), name='bsadmin'),
]

if settings.DEBUG:
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls)), ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
