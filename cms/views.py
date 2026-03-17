import io
from pathlib import Path
from uuid import uuid4
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import user_passes_test
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from PIL import Image, ImageOps

from website.models import (
    AboutPageContent,
    AboutProcessStep,
    AboutValue,
    AuditLog,
    BlogPageContent,
    BlogPost,
    BlogTag,
    CareerBenefit,
    CareerOpening,
    CareerPageContent,
    ContactPageContent,
    ContactSubmission,
    CoreFeature,
    FeedbackPageContent,
    FooterLink,
    FaqItem,
    HeroSlide,
    HomeBlog,
    HomeFaq,
    HomePageContent,
    HomeProject,
    HomeService,
    HomeTestimonial,
    MediaAsset,
    NavigationItem,
    Project,
    ProjectPageContent,
    ProjectProcessStep,
    PrivacyPolicyPageContent,
    Service,
    ServicePageContent,
    SiteSettings,
    SocialLink,
    TermsAndConditionsPageContent,
    Testimonial,
    WhyChooseUsItem,
)

from .forms import (
    AboutPageContentForm,
    AboutProcessStepFormSet,
    AboutValueFormSet,
    BlogEditorForm,
    BlogPageContentForm,
    CareerBenefitFormSet,
    CmsUserCreateForm,
    CmsUserUpdateForm,
    CareerOpeningForm,
    CareerPageContentForm,
    ContactPageContentForm,
    CoreFeatureFormSet,
    BottomFooterLinkFormSet,
    FeedbackPageContentForm,
    FaqItemForm,
    FooterLinkSettingsForm,
    HeroSlideFormSet,
    HomeBlogFormSet,
    HomeFaqFormSet,
    HomePageContentForm,
    HomeProjectFormSet,
    HomeServiceFormSet,
    HomeTestimonialFormSet,
    NavigationItemFormSet,
    ProjectEditorForm,
    ProjectPageContentForm,
    ProjectProcessStepFormSet,
    PrivacyPolicyPageContentForm,
    QuickFooterLinkFormSet,
    ServiceEditorForm,
    ServicePageContentForm,
    SEO_FIELD_NAMES,
    SiteSettingsForm,
    SocialLinkFormSet,
    TestimonialForm,
    TermsAndConditionsPageContentForm,
    WhyChooseUsItemFormSet,
)

UserModel = get_user_model()


def _is_staff_user(user):
    return user.is_authenticated and user.is_staff


staff_required = user_passes_test(_is_staff_user, login_url="cms:login")


def cms_permission_required(*perms, any_perm=False):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not _is_staff_user(request.user):
                return redirect(f"{reverse('cms:login')}?next={request.get_full_path()}")
            if perms:
                has_access = any(request.user.has_perm(perm) for perm in perms) if any_perm else all(
                    request.user.has_perm(perm) for perm in perms
                )
                if not has_access:
                    raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def _require_perms(request, *perms, any_perm=False):
    has_access = any(request.user.has_perm(perm) for perm in perms) if any_perm else all(
        request.user.has_perm(perm) for perm in perms
    )
    if not has_access:
        raise PermissionDenied


def _disable_form_fields(form):
    for field in form.fields.values():
        field.disabled = True


def _disable_formset_fields(formset):
    for form in formset.forms:
        _disable_form_fields(form)


def _resolve_manage_panel(request, panels):
    visible_panels = [panel for panel in panels if panel.get("can_view")]
    default_panel = visible_panels[0]["slug"] if visible_panels else ""
    requested_panel = (request.POST.get("panel") or request.GET.get("panel") or default_panel).strip()
    allowed_slugs = {panel["slug"] for panel in visible_panels}
    if requested_panel in allowed_slugs:
        return requested_panel, visible_panels
    return default_panel, visible_panels


def _redirect_to_panel(route_name, panel):
    url = reverse(route_name)
    if panel:
        return redirect(f"{url}?panel={panel}")
    return redirect(route_name)

EDITOR_IMAGE_SIGNATURES = {
    ".jpg": lambda header: header.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda header: header.startswith(b"\xff\xd8\xff"),
    ".png": lambda header: header.startswith(b"\x89PNG\r\n\x1a\n"),
    ".gif": lambda header: header[:6] in (b"GIF87a", b"GIF89a"),
    ".webp": lambda header: header[:4] == b"RIFF" and header[8:12] == b"WEBP",
}
EDITOR_VIDEO_SIGNATURES = {
    ".mp4": lambda header: len(header) >= 12 and header[4:8] == b"ftyp",
    ".m4v": lambda header: len(header) >= 12 and header[4:8] == b"ftyp",
    ".mov": lambda header: len(header) >= 12 and header[4:8] == b"ftyp",
    ".webm": lambda header: header.startswith(b"\x1a\x45\xdf\xa3"),
}
EDITOR_FILE_SIGNATURES = {
    ".pdf": lambda header: header.startswith(b"%PDF"),
    ".docx": lambda header: header.startswith(b"PK\x03\x04"),
    ".xlsx": lambda header: header.startswith(b"PK\x03\x04"),
    ".pptx": lambda header: header.startswith(b"PK\x03\x04"),
}
MEDIA_TYPE_FILTERS = {
    MediaAsset.TYPE_IMAGE,
    MediaAsset.TYPE_VIDEO,
    MediaAsset.TYPE_FILE,
}


def _safe_next_url(request):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return next_url
    return reverse("cms:dashboard")


def _is_valid_editor_image(uploaded_file):
    extension = Path(uploaded_file.name or "").suffix.lower()
    validator = EDITOR_IMAGE_SIGNATURES.get(extension)
    if not validator:
        return None

    if uploaded_file.size > 5 * 1024 * 1024:
        return None

    header = uploaded_file.read(16)
    uploaded_file.seek(0)
    if not validator(header):
        return None
    return extension


def _is_valid_editor_video(uploaded_file):
    extension = Path(uploaded_file.name or "").suffix.lower()
    validator = EDITOR_VIDEO_SIGNATURES.get(extension)
    if not validator:
        return None
    if uploaded_file.size > 80 * 1024 * 1024:
        return None
    header = uploaded_file.read(16)
    uploaded_file.seek(0)
    if not validator(header):
        return None
    return extension


def _is_valid_media_file(uploaded_file):
    extension = Path(uploaded_file.name or "").suffix.lower()
    validator = EDITOR_FILE_SIGNATURES.get(extension)
    if not validator:
        return None
    if uploaded_file.size > 10 * 1024 * 1024:
        return None
    header = uploaded_file.read(16)
    uploaded_file.seek(0)
    if not validator(header):
        return None
    return extension


def _optimize_image(uploaded_file, *, extension, compress):
    if not compress or extension == ".gif":
        return uploaded_file, False, None, None

    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)
    max_dimension = 2400
    if max(image.size) > max_dimension:
        image.thumbnail((max_dimension, max_dimension))

    width, height = image.size
    buffer = io.BytesIO()

    save_kwargs = {"optimize": True}
    if extension in {".jpg", ".jpeg"}:
        if image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        save_kwargs["format"] = "JPEG"
        save_kwargs["quality"] = 82
        output_extension = ".jpg"
        content_type = "image/jpeg"
    elif extension == ".png":
        if image.mode not in {"RGB", "RGBA", "L"}:
            image = image.convert("RGBA")
        save_kwargs["format"] = "PNG"
        output_extension = ".png"
        content_type = "image/png"
    elif extension == ".webp":
        if image.mode not in {"RGB", "RGBA", "L"}:
            image = image.convert("RGBA")
        save_kwargs["format"] = "WEBP"
        save_kwargs["quality"] = 82
        output_extension = ".webp"
        content_type = "image/webp"
    else:
        return uploaded_file, False, None, None

    image.save(buffer, **save_kwargs)
    buffer.seek(0)
    optimized = ContentFile(buffer.getvalue(), name=f"{Path(uploaded_file.name or 'asset').stem}{output_extension}")
    optimized.content_type = content_type
    return optimized, True, width, height


def _save_media_asset(uploaded_file, *, extension, asset_type, request, optimize=False):
    now = timezone.now()
    upload_dir = {
        MediaAsset.TYPE_IMAGE: "media-library/images",
        MediaAsset.TYPE_VIDEO: "media-library/videos",
        MediaAsset.TYPE_FILE: "media-library/files",
    }[asset_type]
    upload_dir = f"{upload_dir}/{now.year}/{now.month:02d}"
    image_width = None
    image_height = None
    is_optimized = False

    if asset_type == MediaAsset.TYPE_IMAGE:
        uploaded_file, is_optimized, image_width, image_height = _optimize_image(
            uploaded_file,
            extension=extension,
            compress=optimize,
        )
        if hasattr(uploaded_file, "size"):
            file_size = uploaded_file.size
        else:
            file_size = len(uploaded_file.read())
            uploaded_file.seek(0)
    else:
        file_size = uploaded_file.size

    upload_path = f"{upload_dir}/{uuid4().hex}{extension}"
    saved_path = default_storage.save(upload_path, uploaded_file)
    asset = MediaAsset.objects.create(
        title=Path(uploaded_file.name or "").stem[:160],
        original_name=uploaded_file.name or saved_path,
        file=saved_path,
        asset_type=asset_type,
        mime_type=getattr(uploaded_file, "content_type", "") or "",
        file_size=file_size,
        width=image_width,
        height=image_height,
        is_optimized=is_optimized,
        uploaded_by=request.user if request.user.is_authenticated else None,
    )
    file_url = asset.file_url
    if file_url.startswith("/"):
        file_url = request.build_absolute_uri(file_url)
    elif not file_url.startswith(("http://", "https://")):
        media_url = getattr(settings, "MEDIA_URL", "/media/").rstrip("/")
        file_url = request.build_absolute_uri(f"{media_url}/{saved_path}")
    return asset, file_url


def _serialize_media_asset(asset, request):
    file_url = asset.file_url
    absolute_url = request.build_absolute_uri(file_url) if file_url.startswith("/") else file_url
    return {
        "id": asset.pk,
        "title": asset.title,
        "caption": asset.caption,
        "original_name": asset.original_name,
        "asset_type": asset.asset_type,
        "mime_type": asset.mime_type,
        "file_size": asset.file_size,
        "width": asset.width,
        "height": asset.height,
        "is_optimized": asset.is_optimized,
        "url": absolute_url,
        "created_at": asset.created_at.isoformat(),
        "extension": asset.extension,
    }


def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("cms:dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        if not user.is_staff:
            form.add_error(None, "You do not have CMS access.")
        else:
            login(request, user)
            return redirect(_safe_next_url(request))

    return render(request, "cms/login.html", {"form": form})


@staff_required
def logout_view(request):
    logout(request)
    return redirect("cms:login")


@staff_required
def dashboard_view(request):
    context = {
        "cms_section": "dashboard",
        "projects_count": Project.objects.count(),
        "services_count": Service.objects.count(),
        "testimonials_count": Testimonial.objects.count(),
        "faqs_count": FaqItem.objects.count(),
        "blogs_count": BlogPost.objects.count(),
        "careers_count": CareerOpening.objects.count(),
        "home_projects_count": HomeProject.objects.filter(is_active=True).count(),
        "home_services_count": HomeService.objects.filter(is_active=True).count(),
        "home_testimonials_count": HomeTestimonial.objects.filter(is_active=True).count(),
        "home_faqs_count": HomeFaq.objects.filter(is_active=True).count(),
        "home_blogs_count": HomeBlog.objects.filter(is_active=True).count(),
        "slides_count": HeroSlide.objects.count(),
        "contact_submissions_count": ContactSubmission.objects.count(),
        "contact_unresolved_count": ContactSubmission.objects.filter(is_resolved=False).count(),
        "media_assets_count": MediaAsset.objects.count(),
        "users_count": UserModel.objects.count(),
        "audit_logs_count": AuditLog.objects.count(),
    }
    return render(request, "cms/dashboard.html", context)


@cms_permission_required("website.view_mediaasset")
def media_manage_view(request):
    queryset = MediaAsset.objects.order_by("-created_at", "-id")
    query = (request.GET.get("q") or "").strip()
    asset_type = (request.GET.get("type") or "").strip()

    if query:
        queryset = queryset.filter(Q(title__icontains=query) | Q(original_name__icontains=query))
    if asset_type in MEDIA_TYPE_FILTERS:
        queryset = queryset.filter(asset_type=asset_type)

    paginator = Paginator(queryset.order_by("-created_at", "-id"), 18)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "cms/media_manage.html",
        {
            "cms_section": "media_manage",
            "page_obj": page_obj,
            "paginator": paginator,
            "is_paginated": page_obj.has_other_pages(),
            "selected_type": asset_type,
            "search_query": query,
            "media_images_count": MediaAsset.objects.filter(asset_type=MediaAsset.TYPE_IMAGE).count(),
            "media_videos_count": MediaAsset.objects.filter(asset_type=MediaAsset.TYPE_VIDEO).count(),
            "media_files_count": MediaAsset.objects.filter(asset_type=MediaAsset.TYPE_FILE).count(),
        },
    )


@cms_permission_required("website.view_auditlog")
def audit_logs_view(request):
    query = (request.GET.get("q") or "").strip()
    action = (request.GET.get("action") or "").strip()
    queryset = AuditLog.objects.select_related("actor").order_by("-created_at", "-id")

    if query:
        queryset = queryset.filter(
            Q(model_label__icontains=query)
            | Q(object_repr__icontains=query)
            | Q(actor_username__icontains=query)
            | Q(object_pk__icontains=query)
        )
    if action in {AuditLog.ACTION_CREATE, AuditLog.ACTION_UPDATE, AuditLog.ACTION_DELETE}:
        queryset = queryset.filter(action=action)

    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "cms/audit_logs.html",
        {
            "cms_section": "audit_logs",
            "page_obj": page_obj,
            "paginator": paginator,
            "is_paginated": page_obj.has_other_pages(),
            "search_query": query,
            "selected_action": action,
            "create_count": AuditLog.objects.filter(action=AuditLog.ACTION_CREATE).count(),
            "update_count": AuditLog.objects.filter(action=AuditLog.ACTION_UPDATE).count(),
            "delete_count": AuditLog.objects.filter(action=AuditLog.ACTION_DELETE).count(),
        },
    )


@cms_permission_required("website.view_mediaasset")
def media_library_data_view(request):
    queryset = MediaAsset.objects.order_by("-created_at", "-id")
    query = (request.GET.get("q") or "").strip()
    asset_type = (request.GET.get("type") or "").strip()
    types = [item.strip() for item in (request.GET.get("types") or "").split(",") if item.strip()]

    if query:
        queryset = queryset.filter(Q(title__icontains=query) | Q(original_name__icontains=query))
    if asset_type in MEDIA_TYPE_FILTERS:
        queryset = queryset.filter(asset_type=asset_type)
    elif types:
        valid_types = [item for item in types if item in MEDIA_TYPE_FILTERS]
        if valid_types:
            queryset = queryset.filter(asset_type__in=valid_types)

    assets = [_serialize_media_asset(asset, request) for asset in queryset[:60]]
    return JsonResponse({"ok": True, "assets": assets})


@cms_permission_required(
    "website.view_sitesettings",
    "website.view_homepagecontent",
    "website.view_heroslide",
    "website.view_corefeature",
    "website.view_whychooseusitem",
    "website.view_navigationitem",
    "website.view_sociallink",
    "website.view_footerlink",
    any_perm=True,
)
def homepage_manage_view(request):
    site_settings = SiteSettings.objects.first()
    homepage_content = HomePageContent.objects.first()
    can_change_site = request.user.has_perm("website.change_sitesettings")
    can_change_homepage = request.user.has_perm("website.change_homepagecontent")
    can_change_hero = request.user.has_perm("website.change_heroslide")
    can_change_core = request.user.has_perm("website.change_corefeature")
    can_change_why_choose = request.user.has_perm("website.change_whychooseusitem")
    can_change_nav = request.user.has_perm("website.change_navigationitem")
    can_change_social = request.user.has_perm("website.change_sociallink")
    can_change_footer_links = request.user.has_perm("website.change_footerlink")
    can_change_footer_link_settings = request.user.has_perm("website.change_sitesettings")
    homepage_panel_aliases = {
        "hero-copy": "hero",
        "hero-slides": "hero",
        "why-choose-copy": "why-choose",
        "why-choose-items": "why-choose",
    }
    requested_homepage_panel = (request.POST.get("panel") or request.GET.get("panel") or "").strip()
    normalized_homepage_panel = homepage_panel_aliases.get(requested_homepage_panel)
    if normalized_homepage_panel:
        if request.method == "POST":
            request.POST = request.POST.copy()
            request.POST["panel"] = normalized_homepage_panel
        else:
            request.GET = request.GET.copy()
            request.GET["panel"] = normalized_homepage_panel
    homepage_panels = [
        {"slug": "site", "label": "Site Settings", "can_view": request.user.has_perm("website.view_sitesettings")},
        {
            "slug": "hero",
            "label": "Hero",
            "can_view": request.user.has_perm("website.view_homepagecontent") or request.user.has_perm("website.view_heroslide"),
        },
        {
            "slug": "core-features",
            "label": "Core Features",
            "can_view": request.user.has_perm("website.view_homepagecontent") or request.user.has_perm("website.view_corefeature"),
        },
        {
            "slug": "why-choose",
            "label": "Why Choose Us",
            "can_view": request.user.has_perm("website.view_homepagecontent") or request.user.has_perm("website.view_whychooseusitem"),
        },
        {"slug": "featured", "label": "Featured Sections", "can_view": request.user.has_perm("website.view_homepagecontent")},
        {"slug": "final-cta", "label": "Final CTA", "can_view": request.user.has_perm("website.view_homepagecontent")},
        {"slug": "seo", "label": "Homepage SEO", "can_view": request.user.has_perm("website.view_homepagecontent")},
        {"slug": "navigation", "label": "Navigation", "can_view": request.user.has_perm("website.view_navigationitem")},
        {"slug": "social-links", "label": "Social Links", "can_view": request.user.has_perm("website.view_sociallink")},
        {
            "slug": "footer-links",
            "label": "Footer Links",
            "can_view": request.user.has_perm("website.view_footerlink") or request.user.has_perm("website.view_sitesettings"),
        },
    ]
    active_panel, visible_homepage_panels = _resolve_manage_panel(request, homepage_panels)
    active_homepage_panel_label = next(
        (panel["label"] for panel in visible_homepage_panels if panel["slug"] == active_panel),
        active_panel.replace("-", " ").title(),
    )

    site_form = SiteSettingsForm(instance=site_settings, prefix="site")
    homepage_form = HomePageContentForm(instance=homepage_content, prefix="home")
    hero_formset = HeroSlideFormSet(queryset=HeroSlide.objects.order_by("order", "id"), prefix="hero")
    core_formset = CoreFeatureFormSet(queryset=CoreFeature.objects.order_by("order", "id"), prefix="core")
    why_choose_formset = WhyChooseUsItemFormSet(
        queryset=WhyChooseUsItem.objects.order_by("order", "id"),
        prefix="why_choose",
    )
    nav_formset = NavigationItemFormSet(queryset=NavigationItem.objects.order_by("order", "id"), prefix="nav")
    social_formset = SocialLinkFormSet(
        queryset=SocialLink.objects.order_by("location", "order", "id"),
        prefix="social",
    )
    footer_link_settings_form = FooterLinkSettingsForm(instance=site_settings, prefix="footer_settings")
    footer_quick_formset = QuickFooterLinkFormSet(
        queryset=FooterLink.objects.filter(section=FooterLink.SECTION_QUICK).order_by("order", "id"),
        prefix="footer_quick",
    )
    footer_bottom_formset = BottomFooterLinkFormSet(
        queryset=FooterLink.objects.filter(section=FooterLink.SECTION_BOTTOM).order_by("order", "id"),
        prefix="footer_bottom",
    )

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "site":
            _require_perms(request, "website.change_sitesettings")
            site_form = SiteSettingsForm(request.POST, instance=site_settings, prefix="site")
            if site_form.is_valid():
                site_form.save()
                messages.success(request, "Site settings updated.")
                return _redirect_to_panel("cms:homepage_manage", active_panel)
        elif form_type == "home":
            _require_perms(request, "website.change_homepagecontent")
            homepage_form = HomePageContentForm(request.POST, instance=homepage_content, prefix="home")
            if homepage_form.is_valid():
                homepage_form.save()
                messages.success(request, "Homepage section settings updated.")
                return _redirect_to_panel("cms:homepage_manage", active_panel)
        elif form_type == "hero":
            _require_perms(request, "website.change_heroslide")
            hero_formset = HeroSlideFormSet(request.POST, queryset=HeroSlide.objects.order_by("order", "id"), prefix="hero")
            if hero_formset.is_valid():
                hero_formset.save()
                messages.success(request, "Hero slides updated.")
                return _redirect_to_panel("cms:homepage_manage", active_panel)
        elif form_type == "core":
            _require_perms(request, "website.change_corefeature")
            core_formset = CoreFeatureFormSet(request.POST, queryset=CoreFeature.objects.order_by("order", "id"), prefix="core")
            if core_formset.is_valid():
                core_formset.save()
                messages.success(request, "Core features updated.")
                return _redirect_to_panel("cms:homepage_manage", active_panel)
        elif form_type == "why_choose":
            _require_perms(request, "website.change_whychooseusitem")
            why_choose_formset = WhyChooseUsItemFormSet(
                request.POST,
                queryset=WhyChooseUsItem.objects.order_by("order", "id"),
                prefix="why_choose",
            )
            if why_choose_formset.is_valid():
                why_choose_formset.save()
                messages.success(request, "Why choose us items updated.")
                return _redirect_to_panel("cms:homepage_manage", active_panel)
        elif form_type == "nav":
            _require_perms(request, "website.change_navigationitem")
            nav_formset = NavigationItemFormSet(request.POST, queryset=NavigationItem.objects.order_by("order", "id"), prefix="nav")
            if nav_formset.is_valid():
                nav_formset.save()
                messages.success(request, "Navigation menu updated.")
                return _redirect_to_panel("cms:homepage_manage", active_panel)
        elif form_type == "social":
            _require_perms(request, "website.change_sociallink")
            social_formset = SocialLinkFormSet(
                request.POST,
                queryset=SocialLink.objects.order_by("location", "order", "id"),
                prefix="social",
            )
            if social_formset.is_valid():
                social_formset.save()
                messages.success(request, "Social links updated.")
                return _redirect_to_panel("cms:homepage_manage", active_panel)
        elif form_type == "footer_link_settings":
            _require_perms(request, "website.change_sitesettings")
            footer_link_settings_form = FooterLinkSettingsForm(request.POST, instance=site_settings, prefix="footer_settings")
            if footer_link_settings_form.is_valid():
                footer_link_settings_form.save()
                messages.success(request, "Footer quick-link title updated.")
                return _redirect_to_panel("cms:homepage_manage", active_panel)
        elif form_type == "footer_links":
            _require_perms(request, "website.change_footerlink")
            footer_quick_formset = QuickFooterLinkFormSet(
                request.POST,
                queryset=FooterLink.objects.filter(section=FooterLink.SECTION_QUICK).order_by("order", "id"),
                prefix="footer_quick",
            )
            footer_bottom_formset = BottomFooterLinkFormSet(
                request.POST,
                queryset=FooterLink.objects.filter(section=FooterLink.SECTION_BOTTOM).order_by("order", "id"),
                prefix="footer_bottom",
            )
            if footer_quick_formset.is_valid() and footer_bottom_formset.is_valid():
                footer_quick_formset.save()
                footer_bottom_formset.save()
                messages.success(request, "Footer links updated.")
                return _redirect_to_panel("cms:homepage_manage", active_panel)

    if not can_change_site:
        _disable_form_fields(site_form)
    if not can_change_homepage:
        _disable_form_fields(homepage_form)
    if not can_change_hero:
        _disable_formset_fields(hero_formset)
    if not can_change_core:
        _disable_formset_fields(core_formset)
    if not can_change_why_choose:
        _disable_formset_fields(why_choose_formset)
    if not can_change_nav:
        _disable_formset_fields(nav_formset)
    if not can_change_social:
        _disable_formset_fields(social_formset)
    if not can_change_footer_link_settings:
        _disable_form_fields(footer_link_settings_form)
    if not can_change_footer_links:
        _disable_formset_fields(footer_quick_formset)
        _disable_formset_fields(footer_bottom_formset)

    return render(
        request,
        "cms/homepage_manage.html",
        {
            "cms_section": "homepage_manage",
            "cms_subsection": active_panel,
            "active_panel_label": active_homepage_panel_label,
            "homepage_panels": visible_homepage_panels,
            "site_form": site_form,
            "homepage_form": homepage_form,
            "hero_formset": hero_formset,
            "core_formset": core_formset,
            "why_choose_formset": why_choose_formset,
            "nav_formset": nav_formset,
            "social_formset": social_formset,
            "footer_link_settings_form": footer_link_settings_form,
            "footer_quick_formset": footer_quick_formset,
            "footer_bottom_formset": footer_bottom_formset,
            "seo_field_names": SEO_FIELD_NAMES,
            "can_change_site": can_change_site,
            "can_change_homepage": can_change_homepage,
            "can_change_hero": can_change_hero,
            "can_change_core": can_change_core,
            "can_change_why_choose": can_change_why_choose,
            "can_change_nav": can_change_nav,
            "can_change_social": can_change_social,
            "can_change_footer_link_settings": can_change_footer_link_settings,
            "can_change_footer_links": can_change_footer_links,
            "home_hero_fields": [
                "hero_cta_text",
                "hero_cta_url",
                "hero_right_title",
                "hero_right_subtitle",
                "hero_right_description",
            ],
            "home_core_fields": [
                "core_badge",
                "core_title",
                "core_description",
                "core_cta_text",
                "core_cta_url",
            ],
            "home_why_choose_copy_fields": [
                "why_choose_badge",
                "why_choose_title",
                "why_choose_description",
                "why_choose_image_url",
                "why_choose_highlight_title",
                "why_choose_highlight_text",
            ],
            "home_featured_fields": [
                "projects_badge",
                "projects_title",
                "projects_button_text",
                "projects_button_url",
                "blogs_badge",
                "blogs_title",
                "blogs_button_text",
                "blogs_button_url",
                "testimonials_title",
                "faqs_side_title",
                "faqs_side_image_url",
            ],
            "home_final_cta_fields": [
                "final_cta_badge",
                "final_cta_title",
                "final_cta_description",
                "final_cta_button_text",
                "final_cta_button_url",
            ],
        },
    )


@cms_permission_required(
    "website.view_aboutpagecontent",
    "website.view_contactpagecontent",
    "website.view_aboutvalue",
    "website.view_aboutprocessstep",
    "website.view_feedbackpagecontent",
    "website.view_privacypolicypagecontent",
    "website.view_termsandconditionspagecontent",
    any_perm=True,
)
def pages_manage_view(request):
    about_page = AboutPageContent.objects.first()
    contact_page = ContactPageContent.objects.first()
    feedback_page = FeedbackPageContent.objects.first()
    privacy_page = PrivacyPolicyPageContent.objects.first()
    terms_page = TermsAndConditionsPageContent.objects.first()
    can_change_about = request.user.has_perm("website.change_aboutpagecontent")
    can_change_contact = request.user.has_perm("website.change_contactpagecontent")
    can_change_values = request.user.has_perm("website.change_aboutvalue")
    can_change_steps = request.user.has_perm("website.change_aboutprocessstep")
    can_change_feedback = request.user.has_perm("website.change_feedbackpagecontent")
    can_change_privacy = request.user.has_perm("website.change_privacypolicypagecontent")
    can_change_terms = request.user.has_perm("website.change_termsandconditionspagecontent")
    pages_panel_aliases = {
        "about-hero": "about-overview",
        "about-story": "about-overview",
        "about-company": "about-overview",
        "about-mission": "about-overview",
        "about-headings": "about-values-process",
        "about-values": "about-values-process",
        "about-steps": "about-values-process",
        "contact-hero": "contact-page",
        "contact-form": "contact-page",
        "contact-office": "contact-page",
        "privacy-policy": "legal-pages",
        "terms-and-conditions": "legal-pages",
    }
    requested_pages_panel = (request.POST.get("panel") or request.GET.get("panel") or "").strip()
    normalized_pages_panel = pages_panel_aliases.get(requested_pages_panel)
    if normalized_pages_panel:
        if request.method == "POST":
            request.POST = request.POST.copy()
            request.POST["panel"] = normalized_pages_panel
        else:
            request.GET = request.GET.copy()
            request.GET["panel"] = normalized_pages_panel
    pages_panels = [
        {"slug": "about-overview", "label": "About Overview", "can_view": request.user.has_perm("website.view_aboutpagecontent")},
        {
            "slug": "about-values-process",
            "label": "About Values & Process",
            "can_view": request.user.has_perm("website.view_aboutpagecontent")
            or request.user.has_perm("website.view_aboutvalue")
            or request.user.has_perm("website.view_aboutprocessstep"),
        },
        {"slug": "about-seo", "label": "About SEO", "can_view": request.user.has_perm("website.view_aboutpagecontent")},
        {"slug": "contact-page", "label": "Contact Page", "can_view": request.user.has_perm("website.view_contactpagecontent")},
        {"slug": "contact-seo", "label": "Contact SEO", "can_view": request.user.has_perm("website.view_contactpagecontent")},
        {"slug": "feedback-page", "label": "Feedback Page", "can_view": request.user.has_perm("website.view_feedbackpagecontent")},
        {
            "slug": "legal-pages",
            "label": "Legal Pages",
            "can_view": request.user.has_perm("website.view_privacypolicypagecontent")
            or request.user.has_perm("website.view_termsandconditionspagecontent"),
        },
    ]
    active_panel, visible_pages_panels = _resolve_manage_panel(request, pages_panels)
    active_pages_panel_label = next(
        (panel["label"] for panel in visible_pages_panels if panel["slug"] == active_panel),
        active_panel.replace("-", " ").title(),
    )

    about_form = AboutPageContentForm(instance=about_page, prefix="about")
    contact_form = ContactPageContentForm(instance=contact_page, prefix="contact")
    feedback_page_form = FeedbackPageContentForm(instance=feedback_page, prefix="feedback_page")
    privacy_page_form = PrivacyPolicyPageContentForm(instance=privacy_page, prefix="privacy_page")
    terms_page_form = TermsAndConditionsPageContentForm(instance=terms_page, prefix="terms_page")
    about_values_formset = AboutValueFormSet(queryset=AboutValue.objects.order_by("order", "id"), prefix="values")
    about_steps_formset = AboutProcessStepFormSet(
        queryset=AboutProcessStep.objects.order_by("order", "id"),
        prefix="steps",
    )

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "about":
            _require_perms(request, "website.change_aboutpagecontent")
            about_form = AboutPageContentForm(request.POST, instance=about_page, prefix="about")
            if about_form.is_valid():
                about_form.save()
                messages.success(request, "About page updated.")
                return _redirect_to_panel("cms:pages_manage", active_panel)
        elif form_type == "contact":
            _require_perms(request, "website.change_contactpagecontent")
            contact_form = ContactPageContentForm(request.POST, instance=contact_page, prefix="contact")
            if contact_form.is_valid():
                contact_form.save()
                messages.success(request, "Contact page updated.")
                return _redirect_to_panel("cms:pages_manage", active_panel)
        elif form_type == "feedback_page":
            _require_perms(request, "website.change_feedbackpagecontent")
            feedback_page_form = FeedbackPageContentForm(request.POST, instance=feedback_page, prefix="feedback_page")
            if feedback_page_form.is_valid():
                feedback_page_form.save()
                messages.success(request, "Feedback page updated.")
                return _redirect_to_panel("cms:pages_manage", active_panel)
        elif form_type == "privacy_page":
            _require_perms(request, "website.change_privacypolicypagecontent")
            privacy_page_form = PrivacyPolicyPageContentForm(request.POST, instance=privacy_page, prefix="privacy_page")
            if privacy_page_form.is_valid():
                privacy_page_form.save()
                messages.success(request, "Privacy policy page updated.")
                return _redirect_to_panel("cms:pages_manage", active_panel)
        elif form_type == "terms_page":
            _require_perms(request, "website.change_termsandconditionspagecontent")
            terms_page_form = TermsAndConditionsPageContentForm(request.POST, instance=terms_page, prefix="terms_page")
            if terms_page_form.is_valid():
                terms_page_form.save()
                messages.success(request, "Terms and conditions page updated.")
                return _redirect_to_panel("cms:pages_manage", active_panel)
        elif form_type == "values":
            _require_perms(request, "website.change_aboutvalue")
            about_values_formset = AboutValueFormSet(
                request.POST,
                queryset=AboutValue.objects.order_by("order", "id"),
                prefix="values",
            )
            if about_values_formset.is_valid():
                about_values_formset.save()
                messages.success(request, "About values updated.")
                return _redirect_to_panel("cms:pages_manage", active_panel)
        elif form_type == "steps":
            _require_perms(request, "website.change_aboutprocessstep")
            about_steps_formset = AboutProcessStepFormSet(
                request.POST,
                queryset=AboutProcessStep.objects.order_by("order", "id"),
                prefix="steps",
            )
            if about_steps_formset.is_valid():
                about_steps_formset.save()
                messages.success(request, "About process steps updated.")
                return _redirect_to_panel("cms:pages_manage", active_panel)

    if not can_change_about:
        _disable_form_fields(about_form)
    if not can_change_contact:
        _disable_form_fields(contact_form)
    if not can_change_feedback:
        _disable_form_fields(feedback_page_form)
    if not can_change_privacy:
        _disable_form_fields(privacy_page_form)
    if not can_change_terms:
        _disable_form_fields(terms_page_form)
    if not can_change_values:
        _disable_formset_fields(about_values_formset)
    if not can_change_steps:
        _disable_formset_fields(about_steps_formset)

    return render(
        request,
        "cms/pages_manage.html",
        {
            "cms_section": "pages_manage",
            "cms_subsection": active_panel,
            "active_panel_label": active_pages_panel_label,
            "pages_panels": visible_pages_panels,
            "about_form": about_form,
            "contact_form": contact_form,
            "feedback_page_form": feedback_page_form,
            "privacy_page_form": privacy_page_form,
            "terms_page_form": terms_page_form,
            "about_values_formset": about_values_formset,
            "about_steps_formset": about_steps_formset,
            "seo_field_names": SEO_FIELD_NAMES,
            "can_change_about": can_change_about,
            "can_change_contact": can_change_contact,
            "can_change_feedback": can_change_feedback,
            "can_change_privacy": can_change_privacy,
            "can_change_terms": can_change_terms,
            "can_change_values": can_change_values,
            "can_change_steps": can_change_steps,
            "about_hero_fields": ["hero_title", "hero_image_url"],
            "about_story_fields": [
                "intro_badge",
                "intro_title",
                "intro_description_primary",
                "intro_description_secondary",
                "intro_cta_text",
                "intro_cta_url",
                "collage_primary_image_url",
                "collage_secondary_image_url",
            ],
            "about_company_fields": ["company_badge", "company_title", "company_description"],
            "about_mission_fields": [
                "mission_vision_badge",
                "mission_vision_title",
                "mission_vision_description",
                "mission_card_title",
                "vision_card_title",
                "mission_card_text",
                "vision_card_text",
            ],
            "about_heading_fields": [
                "values_badge",
                "values_title",
                "process_badge",
                "process_title",
                "process_description",
            ],
            "contact_hero_fields": [
                "hero_title",
                "hero_image_url",
                "intro_badge",
                "intro_title",
                "intro_description",
                "reply_badge_text",
                "privacy_badge_text",
            ],
            "contact_form_fields": [
                "form_title",
                "form_description",
                "contact_info_email_label",
                "contact_info_phone_label",
                "contact_info_location_label",
                "form_submit_text",
                "form_name_label",
                "form_name_placeholder",
                "form_email_label",
                "form_email_placeholder",
                "form_phone_label",
                "form_phone_placeholder",
                "form_service_label",
                "form_service_placeholder",
                "form_details_label",
                "form_details_placeholder",
            ],
            "contact_office_fields": [
                "office_heading",
                "office_country",
                "office_phone",
                "office_hours_title",
                "office_address",
                "office_hours_days",
                "office_hours_time",
                "office_hours_note",
                "office_image_url",
                "office_image_badge",
                "office_image_title",
                "office_image_description",
            ],
            "feedback_intro_fields": ["hero_badge", "hero_title", "hero_description", "success_message", "privacy_note"],
            "feedback_interaction_fields": ["mood_question", "rating_prompt", "image_prompt", "image_help_text"],
            "feedback_form_fields": [
                "name_label",
                "name_placeholder",
                "email_label",
                "email_placeholder",
                "message_label",
                "message_placeholder",
                "submit_text",
            ],
            "legal_copy_fields": ["hero_badge", "hero_title", "intro_text", "content_json"],
        },
    )


@cms_permission_required("website.view_contactsubmission")
def contact_submissions_manage_view(request):
    paginator = Paginator(ContactSubmission.objects.select_related("service_interest"), 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "cms/contact_submissions_manage.html",
        {
            "cms_section": "contact_submissions_manage",
            "page_obj": page_obj,
            "paginator": paginator,
            "unresolved_count": ContactSubmission.objects.filter(is_resolved=False).count(),
            "resolved_count": ContactSubmission.objects.filter(is_resolved=True).count(),
        },
    )


@cms_permission_required("website.change_contactsubmission")
def contact_submission_toggle_view(request, pk):
    submission = get_object_or_404(ContactSubmission, pk=pk)
    if request.method == "POST":
        submission.is_resolved = not submission.is_resolved
        submission.save(update_fields=["is_resolved"])
        messages.success(
            request,
            f"Inquiry marked as {'resolved' if submission.is_resolved else 'open'}.",
        )
    return redirect("cms:contact_submissions_manage")


@cms_permission_required("website.add_mediaasset")
def editorjs_image_upload_view(request):
    if request.method != "POST":
        return JsonResponse({"success": 0, "message": "POST required."}, status=405)

    uploaded_file = request.FILES.get("image")
    if not uploaded_file:
        return JsonResponse({"success": 0, "message": "No image uploaded."}, status=400)

    extension = _is_valid_editor_image(uploaded_file)
    if not extension:
        return JsonResponse(
            {
                "success": 0,
                "message": "Only JPG, PNG, GIF, and WEBP images up to 5MB are allowed.",
            },
            status=400,
        )

    _, file_url = _save_media_asset(
        uploaded_file,
        extension=extension,
        asset_type=MediaAsset.TYPE_IMAGE,
        request=request,
    )
    return JsonResponse({"success": 1, "file": {"url": file_url}})


@cms_permission_required("website.add_mediaasset")
def media_asset_upload_view(request):
    if request.method != "POST":
        return JsonResponse({"success": 0, "message": "POST required."}, status=405)

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"success": 0, "message": "No file uploaded."}, status=400)

    optimize = str(request.POST.get("optimize", "")).lower() in {"1", "true", "yes", "on"}
    image_extension = _is_valid_editor_image(uploaded_file)
    video_extension = None if image_extension else _is_valid_editor_video(uploaded_file)
    file_extension = None if image_extension or video_extension else _is_valid_media_file(uploaded_file)

    if image_extension:
        asset_type = MediaAsset.TYPE_IMAGE
        extension = image_extension
    elif video_extension:
        asset_type = MediaAsset.TYPE_VIDEO
        extension = video_extension
    elif file_extension:
        asset_type = MediaAsset.TYPE_FILE
        extension = file_extension
    else:
        return JsonResponse(
            {
                "success": 0,
                "message": "Allowed uploads: JPG, PNG, GIF, WEBP, MP4, MOV, M4V, WEBM, PDF, DOCX, XLSX, PPTX.",
            },
            status=400,
        )

    asset, file_url = _save_media_asset(
        uploaded_file,
        extension=extension,
        asset_type=asset_type,
        request=request,
        optimize=optimize,
    )
    return JsonResponse(
        {
            "success": 1,
            "file": {"url": file_url},
            "asset": _serialize_media_asset(asset, request),
        }
    )


@cms_permission_required("website.delete_mediaasset")
def media_delete_view(request, pk):
    asset = get_object_or_404(MediaAsset, pk=pk)
    if request.method == "POST":
        if asset.file:
            default_storage.delete(asset.file.name)
        asset.delete()
        messages.success(request, "Media asset deleted.")
    next_url = request.POST.get("next") or reverse("cms:media_manage")
    return redirect(next_url)


@cms_permission_required("website.change_mediaasset")
def media_update_view(request, pk):
    asset = get_object_or_404(MediaAsset, pk=pk)
    if request.method == "POST":
        asset.title = (request.POST.get("title") or "").strip()[:160]
        asset.caption = (request.POST.get("caption") or "").strip()[:255]
        asset.save(update_fields=["title", "caption"])
        messages.success(request, "Media details updated.")
    next_url = request.POST.get("next") or reverse("cms:media_manage")
    return redirect(next_url)


@cms_permission_required(
    "website.view_blogpost",
    "website.view_blogpagecontent",
    "website.view_homeblog",
    any_perm=True,
)
def blogs_manage_view(request):
    blog_page_content = BlogPageContent.objects.first()
    blog_page_form = BlogPageContentForm(instance=blog_page_content, prefix="blog_page")
    home_blogs_formset = HomeBlogFormSet(
        queryset=HomeBlog.objects.select_related("blog").order_by("display_order", "id"),
        prefix="home_blogs",
    )
    blog_queryset = BlogPost.objects.prefetch_related("tags").all()
    query = (request.GET.get("q") or "").strip()
    category = (request.GET.get("category") or "").strip()
    tag = (request.GET.get("tag") or "").strip()
    status = (request.GET.get("status") or "").strip()
    sort = (request.GET.get("sort") or "latest").strip()
    can_change_blog_page = request.user.has_perm("website.change_blogpagecontent")
    can_change_home_blogs = request.user.has_perm("website.change_homeblog")
    can_add_blog = request.user.has_perm("website.add_blogpost")
    can_change_blog = request.user.has_perm("website.change_blogpost")
    can_delete_blog = request.user.has_perm("website.delete_blogpost")

    if query:
        blog_queryset = blog_queryset.filter(
            Q(title__icontains=query)
            | Q(excerpt__icontains=query)
            | Q(category__icontains=query)
            | Q(tags__name__icontains=query)
        )
    if category:
        blog_queryset = blog_queryset.filter(category=category)
    if tag:
        blog_queryset = blog_queryset.filter(tags__slug=tag)
    if status:
        blog_queryset = blog_queryset.filter(status=status)

    if sort == "popular":
        blog_queryset = blog_queryset.order_by("-view_count", "-share_count", "-like_count", "-published_on", "-id")
    elif sort == "comments":
        blog_queryset = blog_queryset.order_by("-comment_count", "-published_on", "-id")
    elif sort == "oldest":
        blog_queryset = blog_queryset.order_by("published_on", "id")
    else:
        blog_queryset = blog_queryset.order_by("-published_on", "-id")

    paginator = Paginator(blog_queryset.distinct(), 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "blog_page":
            _require_perms(request, "website.change_blogpagecontent")
            blog_page_form = BlogPageContentForm(request.POST, instance=blog_page_content, prefix="blog_page")
            if blog_page_form.is_valid():
                blog_page_form.save()
                messages.success(request, "Blog page content updated.")
                return redirect("cms:blogs_manage")
        elif form_type == "home_blogs":
            _require_perms(request, "website.change_homeblog")
            home_blogs_formset = HomeBlogFormSet(
                request.POST,
                queryset=HomeBlog.objects.select_related("blog").order_by("display_order", "id"),
                prefix="home_blogs",
            )
            if home_blogs_formset.is_valid():
                home_blogs_formset.save()
                messages.success(request, "Homepage blog mapping updated.")
                return redirect("cms:blogs_manage")

    if not can_change_blog_page:
        _disable_form_fields(blog_page_form)
    if not can_change_home_blogs:
        _disable_formset_fields(home_blogs_formset)

    return render(
        request,
        "cms/blogs_manage.html",
        {
            "cms_section": "blogs_manage",
            "blog_page_form": blog_page_form,
            "page_obj": page_obj,
            "paginator": paginator,
            "home_blogs_formset": home_blogs_formset,
            "blog_categories": BlogPost.objects.order_by("category").values_list("category", flat=True).distinct(),
            "blog_tags": BlogTag.objects.order_by("name"),
            "selected_category": category,
            "selected_tag": tag,
            "selected_status": status,
            "sort_value": sort,
            "search_query": query,
            "media_assets": MediaAsset.objects.order_by("-created_at")[:12],
            "blogs_total": BlogPost.objects.count(),
            "blogs_live_total": BlogPost.objects.live().count(),
            "blogs_draft_total": BlogPost.objects.filter(status=BlogPost.STATUS_DRAFT).count(),
            "blogs_pending_total": BlogPost.objects.filter(status=BlogPost.STATUS_PENDING).count(),
            "top_posts": BlogPost.objects.order_by("-view_count", "-share_count", "-like_count", "-comment_count")[:5],
            "can_add_blog": can_add_blog,
            "can_change_blog": can_change_blog,
            "can_delete_blog": can_delete_blog,
            "can_change_blog_page": can_change_blog_page,
            "can_change_home_blogs": can_change_home_blogs,
        },
    )


@cms_permission_required("website.add_blogpost")
def blog_create_view(request):
    form = BlogEditorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Blog created.")
        return redirect("cms:blogs_manage")
    return render(
        request,
        "cms/blog_form.html",
        {"cms_section": "blogs_manage", "form": form, "mode": "create", "seo_field_names": SEO_FIELD_NAMES},
    )


@cms_permission_required("website.change_blogpost")
def blog_edit_view(request, pk):
    blog = get_object_or_404(BlogPost, pk=pk)
    form = BlogEditorForm(request.POST or None, instance=blog)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Blog updated.")
        return redirect("cms:blogs_manage")
    return render(
        request,
        "cms/blog_form.html",
        {
            "cms_section": "blogs_manage",
            "form": form,
            "blog": blog,
            "mode": "edit",
            "seo_field_names": SEO_FIELD_NAMES,
        },
    )


@cms_permission_required("website.delete_blogpost")
def blog_delete_view(request, pk):
    blog = get_object_or_404(BlogPost, pk=pk)
    if request.method == "POST":
        blog.delete()
        messages.success(request, "Blog deleted.")
    return redirect("cms:blogs_manage")


@cms_permission_required(
    "website.view_service",
    "website.view_servicepagecontent",
    "website.view_homeservice",
    any_perm=True,
)
def services_manage_view(request):
    service_page_content = ServicePageContent.objects.first()
    service_page_form = ServicePageContentForm(instance=service_page_content, prefix="service_page")
    home_services_formset = HomeServiceFormSet(
        queryset=HomeService.objects.select_related("service").order_by("display_order", "id"),
        prefix="home_services",
    )
    paginator = Paginator(Service.objects.order_by("title", "id"), 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    can_change_service_page = request.user.has_perm("website.change_servicepagecontent")
    can_change_home_services = request.user.has_perm("website.change_homeservice")
    can_add_service = request.user.has_perm("website.add_service")
    can_change_service = request.user.has_perm("website.change_service")
    can_delete_service = request.user.has_perm("website.delete_service")

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "service_page":
            _require_perms(request, "website.change_servicepagecontent")
            service_page_form = ServicePageContentForm(
                request.POST,
                instance=service_page_content,
                prefix="service_page",
            )
            if service_page_form.is_valid():
                service_page_form.save()
                messages.success(request, "Service page content updated.")
                return redirect("cms:services_manage")
        elif form_type == "home_services":
            _require_perms(request, "website.change_homeservice")
            home_services_formset = HomeServiceFormSet(
                request.POST,
                queryset=HomeService.objects.select_related("service").order_by("display_order", "id"),
                prefix="home_services",
            )
            if home_services_formset.is_valid():
                home_services_formset.save()
                messages.success(request, "Homepage service mapping updated.")
                return redirect("cms:services_manage")

    if not can_change_service_page:
        _disable_form_fields(service_page_form)
    if not can_change_home_services:
        _disable_formset_fields(home_services_formset)

    return render(
        request,
        "cms/services_manage.html",
        {
            "cms_section": "services_manage",
            "service_page_form": service_page_form,
            "page_obj": page_obj,
            "paginator": paginator,
            "home_services_formset": home_services_formset,
            "seo_field_names": SEO_FIELD_NAMES,
            "can_add_service": can_add_service,
            "can_change_service": can_change_service,
            "can_delete_service": can_delete_service,
            "can_change_service_page": can_change_service_page,
            "can_change_home_services": can_change_home_services,
        },
    )


@cms_permission_required("website.add_service")
def service_create_view(request):
    form = ServiceEditorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Service created.")
        return redirect("cms:services_manage")
    return render(
        request,
        "cms/service_form.html",
        {"cms_section": "services_manage", "form": form, "mode": "create", "seo_field_names": SEO_FIELD_NAMES},
    )


@cms_permission_required("website.change_service")
def service_edit_view(request, pk):
    service = get_object_or_404(Service, pk=pk)
    form = ServiceEditorForm(request.POST or None, instance=service)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Service updated.")
        return redirect("cms:services_manage")
    return render(
        request,
        "cms/service_form.html",
        {
            "cms_section": "services_manage",
            "form": form,
            "service": service,
            "mode": "edit",
            "seo_field_names": SEO_FIELD_NAMES,
        },
    )


@cms_permission_required("website.delete_service")
def service_delete_view(request, pk):
    service = get_object_or_404(Service, pk=pk)
    if request.method == "POST":
        service.delete()
        messages.success(request, "Service deleted.")
    return redirect("cms:services_manage")


@cms_permission_required(
    "website.view_project",
    "website.view_projectpagecontent",
    "website.view_projectprocessstep",
    "website.view_homeproject",
    any_perm=True,
)
def projects_manage_view(request):
    project_page_content = ProjectPageContent.objects.first()
    project_page_form = ProjectPageContentForm(instance=project_page_content, prefix="project_page")
    process_steps_formset = ProjectProcessStepFormSet(
        queryset=ProjectProcessStep.objects.order_by("order", "id"),
        prefix="process",
    )
    home_projects_formset = HomeProjectFormSet(
        queryset=HomeProject.objects.select_related("project").order_by("display_order", "id"),
        prefix="home_projects",
    )
    paginator = Paginator(Project.objects.order_by("title", "id"), 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    can_change_project_page = request.user.has_perm("website.change_projectpagecontent")
    can_change_process = request.user.has_perm("website.change_projectprocessstep")
    can_change_home_projects = request.user.has_perm("website.change_homeproject")
    can_add_project = request.user.has_perm("website.add_project")
    can_change_project = request.user.has_perm("website.change_project")
    can_delete_project = request.user.has_perm("website.delete_project")

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "project_page":
            _require_perms(request, "website.change_projectpagecontent")
            project_page_form = ProjectPageContentForm(
                request.POST,
                instance=project_page_content,
                prefix="project_page",
            )
            if project_page_form.is_valid():
                project_page_form.save()
                messages.success(request, "Project page content updated.")
                return redirect("cms:projects_manage")
        elif form_type == "process":
            _require_perms(request, "website.change_projectprocessstep")
            process_steps_formset = ProjectProcessStepFormSet(
                request.POST,
                queryset=ProjectProcessStep.objects.order_by("order", "id"),
                prefix="process",
            )
            if process_steps_formset.is_valid():
                process_steps_formset.save()
                messages.success(request, "Project process steps updated.")
                return redirect("cms:projects_manage")
        elif form_type == "home_projects":
            _require_perms(request, "website.change_homeproject")
            home_projects_formset = HomeProjectFormSet(
                request.POST,
                queryset=HomeProject.objects.select_related("project").order_by("display_order", "id"),
                prefix="home_projects",
            )
            if home_projects_formset.is_valid():
                home_projects_formset.save()
                messages.success(request, "Homepage project mapping updated.")
                return redirect("cms:projects_manage")

    if not can_change_project_page:
        _disable_form_fields(project_page_form)
    if not can_change_process:
        _disable_formset_fields(process_steps_formset)
    if not can_change_home_projects:
        _disable_formset_fields(home_projects_formset)

    return render(
        request,
        "cms/projects_manage.html",
        {
            "cms_section": "projects_manage",
            "project_page_form": project_page_form,
            "process_steps_formset": process_steps_formset,
            "page_obj": page_obj,
            "paginator": paginator,
            "home_projects_formset": home_projects_formset,
            "seo_field_names": SEO_FIELD_NAMES,
            "can_add_project": can_add_project,
            "can_change_project": can_change_project,
            "can_delete_project": can_delete_project,
            "can_change_project_page": can_change_project_page,
            "can_change_process": can_change_process,
            "can_change_home_projects": can_change_home_projects,
        },
    )


@cms_permission_required("website.add_project")
def project_create_view(request):
    form = ProjectEditorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Project created.")
        return redirect("cms:projects_manage")
    return render(
        request,
        "cms/project_form.html",
        {"cms_section": "projects_manage", "form": form, "mode": "create", "seo_field_names": SEO_FIELD_NAMES},
    )


@cms_permission_required("website.change_project")
def project_edit_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    form = ProjectEditorForm(request.POST or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Project updated.")
        return redirect("cms:projects_manage")
    return render(
        request,
        "cms/project_form.html",
        {
            "cms_section": "projects_manage",
            "form": form,
            "project": project,
            "mode": "edit",
            "seo_field_names": SEO_FIELD_NAMES,
        },
    )


@cms_permission_required("website.delete_project")
def project_delete_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted.")
    return redirect("cms:projects_manage")


@cms_permission_required(
    "website.view_careeropening",
    "website.view_careerpagecontent",
    "website.view_careerbenefit",
    any_perm=True,
)
def careers_manage_view(request):
    career_page_content = CareerPageContent.objects.first()
    career_page_form = CareerPageContentForm(instance=career_page_content, prefix="career_page")
    career_benefits_formset = CareerBenefitFormSet(
        queryset=CareerBenefit.objects.order_by("order", "id"),
        prefix="benefits",
    )
    paginator = Paginator(CareerOpening.objects.order_by("order", "title", "id"), 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    can_change_career_page = request.user.has_perm("website.change_careerpagecontent")
    can_change_benefits = request.user.has_perm("website.change_careerbenefit")
    can_add_career = request.user.has_perm("website.add_careeropening")
    can_change_career = request.user.has_perm("website.change_careeropening")
    can_delete_career = request.user.has_perm("website.delete_careeropening")

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "career_page":
            _require_perms(request, "website.change_careerpagecontent")
            career_page_form = CareerPageContentForm(
                request.POST,
                instance=career_page_content,
                prefix="career_page",
            )
            if career_page_form.is_valid():
                career_page_form.save()
                messages.success(request, "Careers page content updated.")
                return redirect("cms:careers_manage")
        elif form_type == "benefits":
            _require_perms(request, "website.change_careerbenefit")
            career_benefits_formset = CareerBenefitFormSet(
                request.POST,
                queryset=CareerBenefit.objects.order_by("order", "id"),
                prefix="benefits",
            )
            if career_benefits_formset.is_valid():
                career_benefits_formset.save()
                messages.success(request, "Career benefits updated.")
                return redirect("cms:careers_manage")

    if not can_change_career_page:
        _disable_form_fields(career_page_form)
    if not can_change_benefits:
        _disable_formset_fields(career_benefits_formset)

    return render(
        request,
        "cms/careers_manage.html",
        {
            "cms_section": "careers_manage",
            "career_page_form": career_page_form,
            "career_benefits_formset": career_benefits_formset,
            "page_obj": page_obj,
            "paginator": paginator,
            "seo_field_names": SEO_FIELD_NAMES,
            "can_add_career": can_add_career,
            "can_change_career": can_change_career,
            "can_delete_career": can_delete_career,
            "can_change_career_page": can_change_career_page,
            "can_change_benefits": can_change_benefits,
        },
    )


@cms_permission_required("website.add_careeropening")
def career_create_view(request):
    form = CareerOpeningForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Career opening created.")
        return redirect("cms:careers_manage")
    return render(
        request,
        "cms/career_form.html",
        {"cms_section": "careers_manage", "form": form, "mode": "create", "seo_field_names": SEO_FIELD_NAMES},
    )


@cms_permission_required("website.change_careeropening")
def career_edit_view(request, pk):
    career = get_object_or_404(CareerOpening, pk=pk)
    form = CareerOpeningForm(request.POST or None, instance=career)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Career opening updated.")
        return redirect("cms:careers_manage")
    return render(
        request,
        "cms/career_form.html",
        {
            "cms_section": "careers_manage",
            "form": form,
            "career": career,
            "mode": "edit",
            "seo_field_names": SEO_FIELD_NAMES,
        },
    )


@cms_permission_required("website.delete_careeropening")
def career_delete_view(request, pk):
    career = get_object_or_404(CareerOpening, pk=pk)
    if request.method == "POST":
        career.delete()
        messages.success(request, "Career opening deleted.")
    return redirect("cms:careers_manage")


@cms_permission_required(
    "website.view_testimonial",
    "website.view_hometestimonial",
    any_perm=True,
)
def testimonials_manage_view(request):
    home_testimonials_formset = HomeTestimonialFormSet(
        queryset=HomeTestimonial.objects.select_related("testimonial").order_by("display_order", "id"),
        prefix="home_testimonials",
    )
    paginator = Paginator(Testimonial.objects.order_by("order", "id"), 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    can_change_home_testimonials = request.user.has_perm("website.change_hometestimonial")
    can_add_testimonial = request.user.has_perm("website.add_testimonial")
    can_change_testimonial = request.user.has_perm("website.change_testimonial")
    can_delete_testimonial = request.user.has_perm("website.delete_testimonial")

    if request.method == "POST" and request.POST.get("form_type") == "home_testimonials":
        _require_perms(request, "website.change_hometestimonial")
        home_testimonials_formset = HomeTestimonialFormSet(
            request.POST,
            queryset=HomeTestimonial.objects.select_related("testimonial").order_by("display_order", "id"),
            prefix="home_testimonials",
        )
        if home_testimonials_formset.is_valid():
            home_testimonials_formset.save()
            messages.success(request, "Homepage testimonial mapping updated.")
            return redirect("cms:testimonials_manage")

    if not can_change_home_testimonials:
        _disable_formset_fields(home_testimonials_formset)

    return render(
        request,
        "cms/testimonials_manage.html",
        {
            "cms_section": "testimonials_manage",
            "page_obj": page_obj,
            "paginator": paginator,
            "home_testimonials_formset": home_testimonials_formset,
            "can_add_testimonial": can_add_testimonial,
            "can_change_testimonial": can_change_testimonial,
            "can_delete_testimonial": can_delete_testimonial,
            "can_change_home_testimonials": can_change_home_testimonials,
        },
    )


@cms_permission_required("website.add_testimonial")
def testimonial_create_view(request):
    form = TestimonialForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Testimonial created.")
        return redirect("cms:testimonials_manage")
    return render(request, "cms/testimonial_form.html", {"cms_section": "testimonials_manage", "form": form, "mode": "create"})


@cms_permission_required("website.change_testimonial")
def testimonial_edit_view(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk)
    form = TestimonialForm(request.POST or None, instance=testimonial)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Testimonial updated.")
        return redirect("cms:testimonials_manage")
    return render(
        request,
        "cms/testimonial_form.html",
        {"cms_section": "testimonials_manage", "form": form, "testimonial": testimonial, "mode": "edit"},
    )


@cms_permission_required("website.delete_testimonial")
def testimonial_delete_view(request, pk):
    testimonial = get_object_or_404(Testimonial, pk=pk)
    if request.method == "POST":
        testimonial.delete()
        messages.success(request, "Testimonial deleted.")
    return redirect("cms:testimonials_manage")


@cms_permission_required(
    "website.view_faqitem",
    "website.view_homefaq",
    any_perm=True,
)
def faqs_manage_view(request):
    home_faqs_formset = HomeFaqFormSet(
        queryset=HomeFaq.objects.select_related("faq").order_by("display_order", "id"),
        prefix="home_faqs",
    )
    paginator = Paginator(FaqItem.objects.order_by("order", "id"), 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    can_change_home_faqs = request.user.has_perm("website.change_homefaq")
    can_add_faq = request.user.has_perm("website.add_faqitem")
    can_change_faq = request.user.has_perm("website.change_faqitem")
    can_delete_faq = request.user.has_perm("website.delete_faqitem")

    if request.method == "POST" and request.POST.get("form_type") == "home_faqs":
        _require_perms(request, "website.change_homefaq")
        home_faqs_formset = HomeFaqFormSet(
            request.POST,
            queryset=HomeFaq.objects.select_related("faq").order_by("display_order", "id"),
            prefix="home_faqs",
        )
        if home_faqs_formset.is_valid():
            home_faqs_formset.save()
            messages.success(request, "Homepage FAQ mapping updated.")
            return redirect("cms:faqs_manage")

    if not can_change_home_faqs:
        _disable_formset_fields(home_faqs_formset)

    return render(
        request,
        "cms/faqs_manage.html",
        {
            "cms_section": "faqs_manage",
            "page_obj": page_obj,
            "paginator": paginator,
            "home_faqs_formset": home_faqs_formset,
            "can_add_faq": can_add_faq,
            "can_change_faq": can_change_faq,
            "can_delete_faq": can_delete_faq,
            "can_change_home_faqs": can_change_home_faqs,
        },
    )


@cms_permission_required("website.add_faqitem")
def faq_create_view(request):
    form = FaqItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "FAQ created.")
        return redirect("cms:faqs_manage")
    return render(request, "cms/faq_form.html", {"cms_section": "faqs_manage", "form": form, "mode": "create"})


@cms_permission_required("website.change_faqitem")
def faq_edit_view(request, pk):
    faq = get_object_or_404(FaqItem, pk=pk)
    form = FaqItemForm(request.POST or None, instance=faq)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "FAQ updated.")
        return redirect("cms:faqs_manage")
    return render(request, "cms/faq_form.html", {"cms_section": "faqs_manage", "form": form, "faq": faq, "mode": "edit"})


@cms_permission_required("website.delete_faqitem")
def faq_delete_view(request, pk):
    faq = get_object_or_404(FaqItem, pk=pk)
    if request.method == "POST":
        faq.delete()
        messages.success(request, "FAQ deleted.")
    return redirect("cms:faqs_manage")


@cms_permission_required("auth.view_user")
def users_manage_view(request):
    paginator = Paginator(UserModel.objects.order_by("username", "id"), 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "cms/users_manage.html",
        {
            "cms_section": "users_manage",
            "page_obj": page_obj,
            "paginator": paginator,
            "can_add_user": request.user.has_perm("auth.add_user"),
            "can_change_user": request.user.has_perm("auth.change_user"),
            "can_delete_user": request.user.has_perm("auth.delete_user"),
        },
    )


@cms_permission_required("auth.add_user")
def user_create_view(request):
    form = CmsUserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "User created.")
        return redirect("cms:users_manage")
    return render(request, "cms/user_form.html", {"cms_section": "users_manage", "form": form, "mode": "create"})


@cms_permission_required("auth.change_user")
def user_edit_view(request, pk):
    user_obj = get_object_or_404(UserModel, pk=pk)
    form = CmsUserUpdateForm(request.POST or None, instance=user_obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "User updated.")
        return redirect("cms:users_manage")
    return render(
        request,
        "cms/user_form.html",
        {"cms_section": "users_manage", "form": form, "mode": "edit", "managed_user": user_obj},
    )


@cms_permission_required("auth.delete_user")
def user_delete_view(request, pk):
    user_obj = get_object_or_404(UserModel, pk=pk)
    if request.user.pk == user_obj.pk:
        messages.error(request, "You cannot delete your own account from the CMS.")
        return redirect("cms:users_manage")
    if request.method == "POST":
        user_obj.delete()
        messages.success(request, "User deleted.")
    return redirect("cms:users_manage")
