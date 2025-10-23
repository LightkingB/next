import debug_toolbar
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('bsheet/', include('bsadmin.urls'), name='bsheet'),
    path('stepper/', include('stepper.urls'), name='stepper'),
    path('integrator/', include('integrator.urls'), name='integrator'),
    path('archive/', include('archives.urls'), name='archive'),
    path('', include('student.urls'), name='student'),
]

if settings.DEBUG:
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls)), ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
