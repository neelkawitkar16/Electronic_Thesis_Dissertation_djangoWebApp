from django.views.generic import TemplateView


class HomePageView(TemplateView):
    template_name = 'home.html'

    print("entered hompage in pages app")
