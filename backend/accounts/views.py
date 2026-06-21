from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import School, User
from .forms import SchoolForm, UserForm


def admin_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_superuser or u.role == "admin"))(view_func)


@login_required
def post_login_redirect(request):
    """Route users to the portal that matches their role."""
    u = request.user
    if u.is_authenticated and not u.is_superuser:
        if u.role == "parent":
            return redirect("/api/parent/")
        if u.role == "student":
            return redirect("/api/student/")
        if u.role == "teacher":
            return redirect("/api/teacher/")
    return redirect("/api/dashboard/")


@login_required
def school_profile(request):
    school = School.get_active()
    if request.method == "POST":
        form = SchoolForm(request.POST, request.FILES, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, "School profile updated.")
            return redirect("school_profile")
    else:
        form = SchoolForm(instance=school)
    return render(request, "accounts/school_profile.html", {"form": form, "school_obj": school})


@login_required
@admin_required
def user_list(request):
    users = User.objects.all().order_by("-id")
    return render(request, "accounts/user_list.html", {"users": users})


@login_required
@admin_required
def user_create(request):
    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            if not form.cleaned_data.get("password"):
                messages.error(request, "Password is required for new users.")
            else:
                form.save()
                messages.success(request, "User created.")
                return redirect("user_list")
    else:
        form = UserForm()
    return render(request, "accounts/user_form.html", {"form": form, "title": "Add User"})


@login_required
@admin_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "User updated.")
            return redirect("user_list")
    else:
        form = UserForm(instance=user)
    return render(request, "accounts/user_form.html", {"form": form, "title": "Edit User"})


@login_required
@admin_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        if user == request.user:
            messages.error(request, "You cannot delete yourself.")
        else:
            user.delete()
            messages.success(request, "User deleted.")
        return redirect("user_list")
    return render(request, "accounts/confirm_delete.html", {"object": user, "type": "user"})



@login_required
@admin_required
def parent_links(request):
    """Admin screen to link parent users to students (many-to-many)."""
    from erp.models import Student
    parents = User.objects.filter(role="parent").order_by("username")

    if request.method == "POST":
        parent_id = request.POST.get("parent_id")
        student_id = request.POST.get("student_id")
        action = request.POST.get("action")
        parent = get_object_or_404(User, pk=parent_id, role="parent")
        student = get_object_or_404(Student, pk=student_id)
        if action == "link":
            student.parent_users.add(parent)
            messages.success(request, f"{parent.username} linked to {student.full_name}.")
        elif action == "unlink":
            student.parent_users.remove(parent)
            messages.success(request, f"{parent.username} unlinked from {student.full_name}.")
        return redirect("parent_links")

    parent_rows = []
    all_students = list(Student.objects.select_related("school_class").order_by("first_name", "last_name"))
    for p in parents:
        linked_ids = set(p.children.values_list("id", flat=True))
        parent_rows.append({
            "parent": p,
            "linked": [s for s in all_students if s.id in linked_ids],
            "candidates": [s for s in all_students if s.id not in linked_ids],
        })
    return render(request, "accounts/parent_links.html", {"parent_rows": parent_rows})
