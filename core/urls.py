import debug_toolbar
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from bsadmin.views import auth_required_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('bsheet/', include('bsadmin.urls'), name='bsheet'),
    path('stepper/', include('stepper.urls'), name='stepper'),
    path('integrator/', include('integrator.urls'), name='integrator'),
    path('archive/', include('archives.urls'), name='archive'),
    # path('minio/', include('djminio.urls'), name='minio'),
    path('', include('student.urls'), name='student'),
    path('auth-required/', auth_required_view, name='auth_required'),
]
# urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]
if settings.DEBUG:
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls)), ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler400 = 'bsadmin.views.handler400'
handler403 = 'bsadmin.views.handler403'
handler404 = 'bsadmin.views.handler404'
handler500 = 'bsadmin.views.handler500'
