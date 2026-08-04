import os

from django.conf import settings
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import StaticFilesStorage


class VersionedStaticFilesStorage(StaticFilesStorage):
    """Добавляет ?v=<mtime> к URL статики — браузер подтягивает CSS/JS после правок."""

    def url(self, name):
        url = super().url(name)
        version = self._file_version(name)
        if version:
            separator = '&' if '?' in url else '?'
            return f'{url}{separator}v={version}'
        return url

    def _file_version(self, name):
        path = finders.find(name)
        if path:
            try:
                return int(os.path.getmtime(path))
            except OSError:
                return None

        if not settings.DEBUG and self.exists(name):
            try:
                return int(os.path.getmtime(self.path(name)))
            except OSError:
                return None

        return None
