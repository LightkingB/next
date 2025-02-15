from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.generic import UpdateView, DeleteView, CreateView


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


class AjaxContextData:
    def get_context_data(self, **kwargs):
        context = super(AjaxContextData, self).get_context_data(**kwargs)
        model_list = '%s_list' % self.model.__name__.lower()
        query = self.get_queryset().all()
        context[model_list] = query

        return context


class AjaxForm:
    def form_valid(self, form):
        data = dict()
        context = self.get_context_data()
        if form.is_valid():
            form.save()
            data['form_is_valid'] = True
            data['model_name'] = form.instance._meta.model_name.lower()
            data['html_list'] = render_to_string(
                self.ajax_list, context, request=self.request
            )
            data["message"] = "Успешно сохранена!"
        else:
            data['form_is_valid'] = False
            data['form_errors'] = form.errors.as_json()
            data["message"] = "Произошла ошибка при сохранении в БД!"
        data['html_form'] = render_to_string(self.ajax_modal, context, request=self.request)
        if is_ajax(request=self.request):
            return JsonResponse(data)
        else:
            return super().form_valid(form)

    def form_invalid(self, form):
        data = dict()
        context = self.get_context_data()
        response = super(AjaxForm, self).form_invalid(form)
        if is_ajax(request=self.request):
            data["message"] = "Произошла ошибка при сохранении в БД!"
            data['html_form'] = render_to_string(self.ajax_modal, context, request=self.request)
            return JsonResponse(data, status=400)
        else:
            return response


class AjaxCreateView(AjaxContextData, AjaxForm, CreateView):
    def get(self, request, *args, **kwargs):
        self.initial = self.kwargs
        self.object = None
        context = self.get_context_data()
        if is_ajax(request=request):
            html_form = render_to_string(self.ajax_modal, context, request)
            return JsonResponse({'html_form': html_form})
        else:
            return super().get(request, *args, **kwargs)


class AjaxUpdateView(AjaxContextData, AjaxForm, UpdateView):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        kwargs["faculty_id"] = self.kwargs.get("faculty_id")
        kwargs["transcript_id"] = self.kwargs.get("transcript_id")

        context = self.get_context_data()
        if is_ajax(request=request):
            html_form = render_to_string(self.ajax_modal, context, request)
            return JsonResponse({'html_form': html_form})
        else:
            return super().get(request, *args, **kwargs)


class AjaxDeleteView(AjaxContextData, DeleteView):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        if is_ajax(request=request):
            html_form = render_to_string(self.ajax_modal, context, request)
            return JsonResponse({'html_form': html_form})
        else:
            return super().get(request, *args, **kwargs)

    def post(self, *args, **kwargs):
        if is_ajax(request=self.request):
            self.object = self.get_object()
            data = dict()
            try:
                self.object.delete()
                data['form_is_valid'] = True
                data['message'] = 'Успешно удалена!'
            except Exception as _:
                data['form_is_valid'] = False
                data['message'] = 'Повторите попытку...'
            data['model_name'] = self.object._meta.model_name.lower()
            context = self.get_context_data()
            data['html_list'] = render_to_string(
                self.ajax_list, context, self.request)
            return JsonResponse(data)
        else:
            return self.delete(*args, **kwargs)


class AjaxCRUDGET:
    def get(self, request, *args, **kwargs):
        subject = self.get_object()
        if is_ajax(request=request):
            html_form = render_to_string(self.ajax_modal, {"object": subject}, request)
            return JsonResponse({'html_form': html_form})
        else:
            return super().get(request, *args, **kwargs)
