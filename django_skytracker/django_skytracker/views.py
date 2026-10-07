from django.shortcuts import render


def filters_preview(request):
    return render(request, "skytracker/filters_preview.html")
