from django.shortcuts import render


def home_view(request):
    """Sirve la página principal del frontend (HTML + JS vainilla, sin build step)."""
    return render(request, "index.html")
