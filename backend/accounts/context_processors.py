from .models import School


def school_context(request):
    return {"school": School.get_active()}
