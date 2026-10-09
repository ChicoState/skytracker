from django.shortcuts import render

from implementation.sky_demo import DemoError, get_sky_report


# Show the search form and fetch a sky report when a location is submitted.
def home(request):
    city = request.GET.get("city", "").strip()
    context = {"city": city}
    if "city" in request.GET:
        if not city:
            context["error"] = "Enter a city or latitude,longitude coordinates."
        elif len(city) > 120:
            context["error"] = "Keep the location under 120 characters."
        else:
            try:
                report = get_sky_report(city)
                context["report"] = report
                # Keep this UI adapter separate from the data-collection layer,
                # which returns (name, altitude) tuples for the server-rendered list.
                context["filterable_constellations"] = [
                    {"id": name, "name": name, "altitude": altitude}
                    for name, altitude in report["visible"]
                ]
            except DemoError as exc:
                context["error"] = str(exc)
    return render(request, "sky.html", context)


def filters_preview(request):
    return render(request, "skytracker/filters_preview.html")
