from django.core.paginator import Paginator


class Pagination:
    def __init__(self, request, queryset):
        self.request = request
        self.queryset = queryset

    @staticmethod
    def _get_paginator_page(paginator, page_number=None):
        if page_number is not None:
            page_obj = paginator.get_page(page_number)
        else:
            page_obj = paginator.get_page(1)
        return page_obj

    def pagination(self, page_number, default_count_info=100):
        paginator = Paginator(self.queryset, default_count_info)
        return self._get_paginator_page(paginator, page_number)

    def pagination_with_filters(self, filtered_obj, page_number, default_count_info=100):
        paginator = Paginator(filtered_obj.qs, default_count_info)
        return self._get_paginator_page(paginator, page_number)
