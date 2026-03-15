import logging
from html import escape

from django.conf import settings
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.mail import EmailMultiAlternatives
from django.db.models import F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import DetailView, ListView, TemplateView

from .forms import ContactInquiryForm
from .models import (
    AboutPageContent,
    AboutProcessStep,
    AboutValue,
    BlogPageContent,
    BlogPost,
    BlogTag,
    CareerBenefit,
    CareerOpening,
    CareerPageContent,
    ContactPageContent,
    CoreFeature,
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
    Service,
    ServicePageContent,
    SiteSettings,
    SocialLink,
    Testimonial,
    WhyChooseUsItem,
)
from .seed_data import (
    ABOUT_PAGE_CONTENT,
    BLOG_PAGE_CONTENT,
    CAREER_PAGE_CONTENT,
    CONTACT_PAGE_CONTENT,
    HOME_PAGE_CONTENT,
    NAVIGATION_ITEMS,
    PROJECT_PAGE_CONTENT,
    SERVICE_PAGE_CONTENT,
    SITE_SETTINGS,
    SOCIAL_LINK_ROWS,
    WHY_CHOOSE_US_ITEMS,
)
from .seo import build_seo_context
from .templatetags.editorjs import editorjs_to_text, render_editorjs_html


logger = logging.getLogger(__name__)


cache_public_page = cache_page(getattr(settings, "PAGE_CACHE_SECONDS", 300))


def _send_contact_submission_emails(submission, site_settings):
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@jstechnova.local")
    internal_email = (
        getattr(settings, "CONTACT_NOTIFICATION_EMAIL", "").strip()
        or getattr(site_settings, "topbar_email", "").strip()
    )
    service_name = submission.service_interest.title if submission.service_interest else "General Inquiry"
    site_name = getattr(site_settings, "site_name", "JS Technova")
    custom_reply_html = render_editorjs_html(
        getattr(site_settings, "contact_auto_reply_message_json", None) or {"blocks": []}
    )
    custom_reply_text = editorjs_to_text(
        getattr(site_settings, "contact_auto_reply_message_json", None) or {"blocks": []}
    )

    customer_subject = f"Thanks for contacting {site_name}"
    customer_text = (
        f"Hi {submission.name},\n\n"
        f"Thank you for reaching out to {site_name}. We have received your inquiry about {service_name}.\n\n"
        f"{custom_reply_text}\n\n"
        f"Regards,\n{site_name}"
    )
    customer_html = (
        f"<p>Hi {escape(submission.name)},</p>"
        f"<p>Thank you for reaching out to <strong>{escape(site_name)}</strong>. "
        f"We have received your inquiry about <strong>{escape(service_name)}</strong>.</p>"
        f"{custom_reply_html}"
        f"<p>Regards,<br>{escape(site_name)}</p>"
    )

    customer_message = EmailMultiAlternatives(
        subject=customer_subject,
        body=customer_text,
        from_email=from_email,
        to=[submission.email],
    )
    customer_message.attach_alternative(customer_html, "text/html")
    customer_message.send(fail_silently=False)

    if internal_email:
        internal_subject = f"New contact inquiry from {submission.name}"
        internal_text = (
            "A new contact form submission has been received.\n\n"
            f"Name: {submission.name}\n"
            f"Email: {submission.email}\n"
            f"Phone: {submission.phone}\n"
            f"Service: {service_name}\n"
            f"Submitted at: {submission.created_at:%Y-%m-%d %H:%M:%S}\n\n"
            f"Project details:\n{submission.project_details or 'Not provided'}\n"
        )
        internal_html = (
            "<p>A new contact form submission has been received.</p>"
            "<ul>"
            f"<li><strong>Name:</strong> {escape(submission.name)}</li>"
            f"<li><strong>Email:</strong> {escape(submission.email)}</li>"
            f"<li><strong>Phone:</strong> {escape(submission.phone)}</li>"
            f"<li><strong>Service:</strong> {escape(service_name)}</li>"
            f"<li><strong>Submitted at:</strong> {submission.created_at:%Y-%m-%d %H:%M:%S}</li>"
            "</ul>"
            f"<p><strong>Project details</strong><br>{escape(submission.project_details or 'Not provided')}</p>"
        )
        internal_message = EmailMultiAlternatives(
            subject=internal_subject,
            body=internal_text,
            from_email=from_email,
            to=[internal_email],
            reply_to=[submission.email],
        )
        internal_message.attach_alternative(internal_html, "text/html")
        internal_message.send(fail_silently=False)


def _ensure_navigation_item(label, url, order):
    NavigationItem.objects.get_or_create(
        label=label,
        defaults={"url": url, "order": order},
    )


def _create_defaults(model, rows):
    if not model.objects.exists():
        model.objects.bulk_create([model(**row) for row in rows])


def _ensure_singleton(model, payload):
    instance, created = model.objects.get_or_create(pk=1, defaults=payload)
    if created:
        return instance

    changed = False
    for field_name, value in payload.items():
        current = getattr(instance, field_name)
        if current in ("", None):
            setattr(instance, field_name, value)
            changed = True
    if changed:
        instance.save()
    return instance


def bootstrap_homepage_defaults():
    _ensure_singleton(SiteSettings, SITE_SETTINGS)
    _ensure_singleton(HomePageContent, HOME_PAGE_CONTENT)
    _ensure_singleton(ServicePageContent, SERVICE_PAGE_CONTENT)
    _ensure_singleton(BlogPageContent, BLOG_PAGE_CONTENT)
    _ensure_singleton(AboutPageContent, ABOUT_PAGE_CONTENT)
    _ensure_singleton(ContactPageContent, CONTACT_PAGE_CONTENT)
    _ensure_singleton(ProjectPageContent, PROJECT_PAGE_CONTENT)
    _ensure_singleton(CareerPageContent, CAREER_PAGE_CONTENT)

    for item in NAVIGATION_ITEMS:
        _ensure_navigation_item(item["label"], item["url"], item["order"])

    if not SocialLink.objects.exists():
        for location in (SocialLink.LOCATION_TOPBAR, SocialLink.LOCATION_MOBILE, SocialLink.LOCATION_FOOTER):
            for index, row in enumerate(SOCIAL_LINK_ROWS, start=1):
                SocialLink.objects.create(
                    label=row[0],
                    icon_class=row[1],
                    url=row[2],
                    location=location,
                    order=index,
                )

    _create_defaults(
        HeroSlide,
        [
            {
                "order": 1,
                "image_url": "https://images.unsplash.com/photo-1521737604893-d14cc237f11d?q=80&w=1800&auto=format&fit=crop",
                "badge": "NUMBER #1 SOLVER AGENCY",
                "title": "Transform your business with expert consultation",
                "description": "Helping teams grow with strategy, design and development that converts.",
            },
            {
                "order": 2,
                "image_url": "https://images.unsplash.com/photo-1556761175-4b46a572b786?q=80&w=1800&auto=format&fit=crop",
                "badge": "STRATEGY | DESIGN | DEV",
                "title": "Build products users love and businesses trust",
                "description": "We deliver clean UI, scalable code and measurable results for your brand.",
            },
        ],
    )

    _create_defaults(
        CoreFeature,
        [
            {
                "order": 1,
                "icon_class": "fa-regular fa-lightbulb",
                "title": "Quick solutions",
                "description": "Fast business and product solutions tailored to your goals.",
            },
            {
                "order": 2,
                "icon_class": "fa-solid fa-user-tie",
                "title": "Expert advice",
                "description": "Top-tier guidance for strategy, design, and engineering delivery.",
            },
            {
                "order": 3,
                "icon_class": "fa-solid fa-gears",
                "title": "Efficient operations",
                "description": "Streamline workflows to improve output and lower delivery risk.",
            },
        ],
    )

    _create_defaults(
        WhyChooseUsItem,
        WHY_CHOOSE_US_ITEMS,
    )

    _create_defaults(
        AboutValue,
        [
            {
                "order": 1,
                "icon_class": "fa-solid fa-bolt",
                "title": "Speed with quality",
                "description": "We move quickly without compromising product quality.",
            },
            {
                "order": 2,
                "icon_class": "fa-solid fa-eye",
                "title": "Transparency",
                "description": "Clear milestones, direct updates, and practical delivery visibility.",
            },
            {
                "order": 3,
                "icon_class": "fa-solid fa-handshake",
                "title": "Partnership mindset",
                "description": "We work as an extension of your team, focused on outcomes.",
            },
        ],
    )

    _create_defaults(
        AboutProcessStep,
        [
            {"order": 1, "label": "Step 01", "title": "Discover and align", "description": "Clarify goals, users, and priorities before execution."},
            {"order": 2, "label": "Step 02", "title": "Design and build", "description": "Ship in focused cycles with demos and feedback loops."},
            {"order": 3, "label": "Step 03", "title": "Launch and optimize", "description": "Measure outcomes and improve where it matters."},
        ],
    )

    _create_defaults(
        Service,
        [
            {
                "title": "Business process optimization",
                "slug": "business-process-optimization",
                "icon_class": "fa-solid fa-chart-line",
                "summary": "Remove delivery bottlenecks and improve operational throughput.",
                "image_url": "https://images.unsplash.com/photo-1552664730-d307ca884978?q=80&w=1000&auto=format&fit=crop",
                "cta_text": "Learn more",
                "content_json": {
                    "blocks": [
                        {"type": "paragraph", "data": {"text": "We map workflows, identify friction, and implement practical improvements."}},
                        {"type": "list", "data": {"style": "unordered", "items": ["Process audit", "SOP design", "KPI optimization"]}},
                    ]
                },
            },
            {
                "title": "Strategic planning and execution",
                "slug": "strategic-planning-and-execution",
                "icon_class": "fa-solid fa-layer-group",
                "summary": "Translate business goals into focused, actionable delivery plans.",
                "image_url": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?q=80&w=1000&auto=format&fit=crop",
                "cta_text": "Learn more",
                "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "We align stakeholders around priorities and measurable outcomes."}}]},
            },
            {
                "title": "Leadership executive coaching",
                "slug": "leadership-executive-coaching",
                "icon_class": "fa-solid fa-user-tie",
                "summary": "Strengthen leadership communication and decision-making under growth pressure.",
                "image_url": "https://images.unsplash.com/photo-1573497620053-ea5300f94f21?q=80&w=1000&auto=format&fit=crop",
                "cta_text": "Learn more",
                "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "Coaching designed for founders, product heads, and engineering leaders."}}]},
            },
        ],
    )

    if not HomeService.objects.exists():
        for index, service in enumerate(Service.objects.filter(is_published=True)[:6], start=1):
            HomeService.objects.get_or_create(service=service, defaults={"display_order": index})

    _create_defaults(
        Testimonial,
        [
            {
                "order": 1,
                "name": "Esther Howard",
                "role": "Founder",
                "company": "SaaS Startup",
                "quote": "JS Technova delivered our web app faster than expected, with clean UX and strong backend architecture.",
                "image_url": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?q=80&w=200&auto=format&fit=crop",
                "rating": 5,
            },
            {
                "order": 2,
                "name": "Daniel Morgan",
                "role": "Product Manager",
                "company": "Enterprise Team",
                "quote": "They modernized our legacy platform into a scalable mobile-first solution.",
                "image_url": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?q=80&w=200&auto=format&fit=crop",
                "rating": 5,
            },
        ],
    )

    if not HomeTestimonial.objects.exists():
        for index, testimonial in enumerate(Testimonial.objects.filter(is_published=True)[:10], start=1):
            HomeTestimonial.objects.get_or_create(testimonial=testimonial, defaults={"display_order": index})

    _create_defaults(
        FaqItem,
        [
            {"order": 1, "question": "How do development agencies add value to a business?", "answer": "By combining strategy, design, engineering, and QA to improve delivery speed and outcomes."},
            {"order": 2, "question": "How are software projects priced?", "answer": "Usually fixed-scope milestones or sprint-based retainers depending on product maturity."},
            {"order": 3, "question": "How do we measure success after launch?", "answer": "We track conversion, adoption, uptime, bug rate, and release velocity."},
        ],
    )

    if not HomeFaq.objects.exists():
        for index, faq in enumerate(FaqItem.objects.filter(is_published=True)[:10], start=1):
            HomeFaq.objects.get_or_create(faq=faq, defaults={"display_order": index})

    _create_defaults(
        Project,
        [
            {
                "title": "Innovate consultancy business solutions",
                "slug": "innovate-consultancy-business-solutions",
                "category": "Consulting",
                "summary": "Modern consulting platform focused on strategy and growth.",
                "image_url": "https://images.unsplash.com/photo-1552581234-26160f608093?q=80&w=1400&auto=format&fit=crop",
                "vertical_label": "Consulting Hub",
                "tag_one": "Strategy",
                "tag_two": "Growth",
                "client_name": "Consulting Hub",
                "project_year": 2025,
                "status": "Live",
                "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "A full digital overhaul covering positioning, conversion-focused UI, and scalable CMS-driven content."}}]},
            },
            {
                "title": "Digital product transformation roadmap",
                "slug": "digital-product-transformation-roadmap",
                "category": "SaaS",
                "summary": "Delivery blueprint for digital transformation across product teams.",
                "image_url": "https://images.unsplash.com/photo-1526628953301-3e589a6a8b74?q=80&w=1400&auto=format&fit=crop",
                "vertical_label": "Product Lab",
                "tag_one": "SaaS",
                "tag_two": "UI/UX",
                "client_name": "Product Lab",
                "project_year": 2026,
                "status": "In Progress",
                "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "A transformation initiative combining design systems, product strategy, and delivery governance."}}]},
            },
            {
                "title": "Learning management app modernization",
                "slug": "learning-management-app-modernization",
                "category": "Education",
                "summary": "Education web app refresh for speed, retention, and analytics.",
                "image_url": "https://images.unsplash.com/photo-1488190211105-8b0e65b80b4e?q=80&w=1400&auto=format&fit=crop",
                "vertical_label": "Edu Core",
                "tag_one": "Web App",
                "tag_two": "Analytics",
                "client_name": "Edu Core",
                "project_year": 2025,
                "status": "Live",
                "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "We modernized learning workflows, content delivery, and reporting visibility."}}]},
            },
        ],
    )

    _create_defaults(
        ProjectProcessStep,
        [
            {"order": 1, "label": "01. Discovery", "title": "Align goals", "description": "Define scope, priorities, and success metrics before delivery starts."},
            {"order": 2, "label": "02. Build", "title": "Ship in sprints", "description": "Design and engineering run in tight cycles with demos and feedback."},
            {"order": 3, "label": "03. Optimize", "title": "Scale outcomes", "description": "Use performance signals to guide the next wave of improvements."},
        ],
    )

    if not HomeProject.objects.exists():
        for index, project in enumerate(Project.objects.filter(is_published=True)[:5], start=1):
            HomeProject.objects.get_or_create(project=project, defaults={"display_order": index})

    _create_defaults(
        BlogPost,
        [
            {
                "title": "How high-performing teams ship faster without sacrificing code quality",
                "slug": "how-high-performing-teams-ship-faster-without-sacrificing-code-quality",
                "category": "Product Strategy",
                "excerpt": "Frameworks and operating rituals that improve throughput without technical debt.",
                "image_url": "https://images.unsplash.com/photo-1552581234-26160f608093?q=80&w=1600&auto=format&fit=crop",
                "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "High-performing teams optimize clarity before speed and release in measurable increments."}}]},
            },
            {
                "title": "AI-ready architecture patterns for modern web platforms",
                "slug": "ai-ready-architecture-patterns-for-modern-web-platforms",
                "category": "Technology",
                "excerpt": "Practical architecture decisions to make web products AI-ready from day one.",
                "image_url": "https://images.unsplash.com/photo-1526628953301-3e589a6a8b74?q=80&w=1200&auto=format&fit=crop",
                "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "AI-ready architecture starts with clean data flows and modular service boundaries."}}]},
            },
            {
                "title": "Change management playbooks that keep delivery on track",
                "slug": "change-management-playbooks-that-keep-delivery-on-track",
                "category": "Leadership",
                "excerpt": "Leadership patterns that stabilize delivery during organizational change.",
                "image_url": "https://images.unsplash.com/photo-1573496130407-57329f01f769?q=80&w=1200&auto=format&fit=crop",
                "content_json": {"blocks": [{"type": "paragraph", "data": {"text": "Strong change management connects business outcomes to day-to-day execution."}}]},
            },
        ],
    )

    if not HomeBlog.objects.exists():
        for index, blog in enumerate(BlogPost.objects.filter(is_published=True)[:3], start=1):
            HomeBlog.objects.get_or_create(
                blog=blog,
                defaults={"display_order": index, "is_featured": index == 1},
            )

    _create_defaults(
        CareerBenefit,
        [
            {"order": 1, "title": "Remote-friendly", "description": "Flexible collaboration with an async-first workflow."},
            {"order": 2, "title": "Growth-focused", "description": "Own real features from idea to deployment."},
        ],
    )

    _create_defaults(
        CareerOpening,
        [
            {
                "order": 1,
                "title": "Frontend Developer (React)",
                "slug": "frontend-developer-react",
                "summary": "Build responsive interfaces for modern websites and web apps with React and Tailwind.",
                "department": "Engineering",
                "location": "Remote",
                "employment_type": "Full Time",
                "experience_level": "2+ years",
                "overview": "Build modern interfaces for websites and web apps in close collaboration with design and backend teams.",
                "responsibilities_text": "Build reusable UI components.\nImplement responsive layouts.\nIntegrate APIs cleanly.",
                "requirements_text": "2+ years of frontend development experience.\nStrong JavaScript and React skills.\nTailwind CSS experience.",
                "nice_to_have_text": "Next.js experience.\nBasic Node.js familiarity.",
                "apply_url": "mailto:hello@jstechnova.com?subject=Application%20for%20Frontend%20Developer",
            },
            {
                "order": 2,
                "title": "UI/UX Designer",
                "slug": "ui-ux-designer",
                "summary": "Design conversion-focused website and web app experiences from wireframe to prototype.",
                "department": "Design",
                "location": "Hybrid",
                "employment_type": "Full Time",
                "experience_level": "2+ years",
                "overview": "Own user flows, interface systems, and polished visual design across client delivery work.",
                "responsibilities_text": "Design wireframes and polished screens.\nCollaborate with product and frontend teams.",
                "requirements_text": "Strong Figma skills.\nPortfolio with responsive work samples.",
                "nice_to_have_text": "Motion design skills.",
                "apply_url": "mailto:hello@jstechnova.com?subject=Application%20for%20UI/UX%20Designer",
            },
        ],
    )


def get_site_context():
    return {
        "site_settings": SiteSettings.objects.first(),
        "header_nav_items": NavigationItem.objects.filter(is_active=True, show_in_header=True),
        "header_service_links": Service.objects.filter(is_published=True).order_by("title", "id"),
        "mobile_nav_items": NavigationItem.objects.filter(is_active=True, show_in_mobile=True),
        "topbar_social_links": SocialLink.objects.filter(is_active=True, location=SocialLink.LOCATION_TOPBAR),
        "mobile_social_links": SocialLink.objects.filter(is_active=True, location=SocialLink.LOCATION_MOBILE),
        "footer_social_links": SocialLink.objects.filter(is_active=True, location=SocialLink.LOCATION_FOOTER),
    }


class SiteContentMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_site_context())
        return context

    def add_seo(
        self,
        context,
        *,
        source,
        fallback_title,
        fallback_description="",
        fallback_keywords="",
        fallback_image_url="",
        og_type="website",
        schema=None,
    ):
        context["seo"] = build_seo_context(
            self.request,
            site_settings=context.get("site_settings"),
            source=source,
            fallback_title=fallback_title,
            fallback_description=fallback_description,
            fallback_keywords=fallback_keywords,
            fallback_image_url=fallback_image_url,
            og_type=og_type,
            schema=schema,
        )
        return context


@method_decorator(cache_public_page, name="dispatch")
class HomePageView(SiteContentMixin, TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        homepage_content = HomePageContent.objects.first()
        service_page_content = ServicePageContent.objects.first()
        hero_slides = list(HeroSlide.objects.all())
        core_features = list(CoreFeature.objects.all())
        why_choose_items = list(WhyChooseUsItem.objects.all())
        home_services = list(
            HomeService.objects.filter(
                is_active=True,
                service__is_published=True,
            ).select_related("service")
        )
        home_testimonials = list(
            HomeTestimonial.objects.filter(
                is_active=True,
                testimonial__is_published=True,
            ).select_related("testimonial")
        )
        home_faqs = list(
            HomeFaq.objects.filter(
                is_active=True,
                faq__is_published=True,
            ).select_related("faq")
        )
        home_projects = list(
            HomeProject.objects.filter(
                is_active=True,
                project__is_published=True,
            ).select_related("project")
        )
        home_blog_entries = list(
            HomeBlog.objects.filter(is_active=True, blog__is_published=True).select_related("blog")
        )
        featured_blog_entry = next((item for item in home_blog_entries if item.is_featured), None)
        if featured_blog_entry is None and home_blog_entries:
            featured_blog_entry = home_blog_entries[0]

        context.update(
            {
                "homepage_content": homepage_content,
                "service_page_content": service_page_content,
                "hero_slides": hero_slides,
                "hero_first_slide": hero_slides[0] if hero_slides else None,
                "core_features": core_features,
                "why_choose_items": why_choose_items,
                "home_services": home_services,
                "home_testimonials": home_testimonials,
                "home_faqs": home_faqs,
                "home_projects": home_projects,
                "home_featured_blog": featured_blog_entry.blog if featured_blog_entry else None,
                "home_secondary_blogs": [item.blog for item in home_blog_entries if item != featured_blog_entry][:2],
            }
        )
        site_name = getattr(context.get("site_settings"), "site_name", "JS Technova")
        return self.add_seo(
            context,
            source=homepage_content,
            fallback_title=site_name,
            fallback_description=homepage_content.hero_right_description if homepage_content else "",
            fallback_keywords="web development, mobile apps, product design, software agency",
            fallback_image_url=(
                hero_slides[0].image_url if hero_slides else getattr(context.get("site_settings"), "logo_image_url", "")
            ),
            schema={
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": site_name,
                "url": self.request.build_absolute_uri(reverse("home")),
            },
        )


@method_decorator(cache_public_page, name="dispatch")
class AboutPageView(SiteContentMixin, TemplateView):
    template_name = "about.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        about_page = AboutPageContent.objects.first()
        about_values = list(AboutValue.objects.all())
        about_steps = list(AboutProcessStep.objects.all())
        context.update(
            {
                "about_page": about_page,
                "about_values": about_values,
                "about_steps": about_steps,
            }
        )
        return self.add_seo(
            context,
            source=about_page,
            fallback_title=about_page.hero_title if about_page else "About",
            fallback_description=about_page.intro_description_primary if about_page else "",
            fallback_keywords="about us, product agency, web development company",
            fallback_image_url=about_page.hero_image_url if about_page else "",
            schema={
                "@context": "https://schema.org",
                "@type": "AboutPage",
                "name": about_page.hero_title if about_page else "About",
                "description": about_page.intro_description_primary if about_page else "",
                "url": self.request.build_absolute_uri(reverse("about")),
            },
        )


class ContactPageView(SiteContentMixin, TemplateView):
    template_name = "contact.html"

    def get_contact_page(self):
        return ContactPageContent.objects.first()

    def get_form(self, page_content, data=None):
        return ContactInquiryForm(data=data, page_content=page_content)

    def post(self, request, *args, **kwargs):
        page_content = self.get_contact_page()
        form = self.get_form(page_content, data=request.POST)
        if form.is_valid():
            submission = form.save()
            try:
                _send_contact_submission_emails(submission, SiteSettings.objects.first())
            except Exception:
                logger.exception("Failed to send contact submission emails for submission %s", submission.pk)
            messages.success(request, "Your inquiry has been received. Our team will get back to you shortly.")
            return redirect("contact")
        context = self.get_context_data(contact_form=form, contact_page=page_content)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact_page = kwargs.get("contact_page") or self.get_contact_page()
        context.update(
            {
                "contact_page": contact_page,
                "contact_form": kwargs.get("contact_form") or self.get_form(contact_page),
            }
        )
        return self.add_seo(
            context,
            source=contact_page,
            fallback_title=contact_page.hero_title if contact_page else "Contact",
            fallback_description=contact_page.intro_description if contact_page else "",
            fallback_keywords="contact, project inquiry, software consultation",
            fallback_image_url=contact_page.hero_image_url if contact_page else "",
            schema={
                "@context": "https://schema.org",
                "@type": "ContactPage",
                "name": contact_page.hero_title if contact_page else "Contact",
                "description": contact_page.intro_description if contact_page else "",
                "url": self.request.build_absolute_uri(reverse("contact")),
            },
        )


@method_decorator(cache_public_page, name="dispatch")
class BlogListView(SiteContentMixin, ListView):
    model = BlogPost
    template_name = "blogs.html"
    context_object_name = "blogs"
    paginate_by = 6

    def get_queryset(self):
        queryset = BlogPost.objects.live().prefetch_related("tags")
        query = (self.request.GET.get("q") or "").strip()
        category = (self.request.GET.get("category") or "").strip()
        tag = (self.request.GET.get("tag") or "").strip()
        sort = (self.request.GET.get("sort") or "latest").strip()

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(excerpt__icontains=query)
                | Q(category__icontains=query)
                | Q(tags__name__icontains=query)
            )
        if category:
            queryset = queryset.filter(category=category)
        if tag:
            queryset = queryset.filter(tags__slug=tag)

        if sort == "popular":
            queryset = queryset.order_by("-view_count", "-share_count", "-like_count", "-published_on", "-id")
        elif sort == "comments":
            queryset = queryset.order_by("-comment_count", "-published_on", "-id")
        elif sort == "oldest":
            queryset = queryset.order_by("published_on", "id")
        else:
            queryset = queryset.order_by("-published_on", "-id")
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blog_page_content = BlogPageContent.objects.first()
        live_blogs = BlogPost.objects.live()
        context.update(
            {
                "blog_page_content": blog_page_content,
                "recent_blogs": live_blogs.order_by("-published_on", "-id")[:5],
                "blog_categories": live_blogs.order_by("category").values_list("category", flat=True).distinct(),
                "blog_tags": BlogTag.objects.filter(posts__in=live_blogs).distinct().order_by("name"),
                "selected_category": self.request.GET.get("category", ""),
                "selected_tag": self.request.GET.get("tag", ""),
                "search_query": self.request.GET.get("q", ""),
                "sort_value": self.request.GET.get("sort", "latest"),
                "top_blogs": live_blogs.order_by("-view_count", "-share_count", "-like_count", "-comment_count")[:5],
            }
        )
        return self.add_seo(
            context,
            source=blog_page_content,
            fallback_title=blog_page_content.page_hero_title if blog_page_content else "Blogs",
            fallback_description=blog_page_content.page_intro_text if blog_page_content else "",
            fallback_keywords="blog, insights, product strategy, engineering",
            schema={
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": blog_page_content.page_hero_title if blog_page_content else "Blogs",
                "description": blog_page_content.page_intro_text if blog_page_content else "",
                "url": self.request.build_absolute_uri(),
            },
        )


class BlogDetailView(SiteContentMixin, DetailView):
    model = BlogPost
    template_name = "blog_detail.html"
    context_object_name = "blog"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return BlogPost.objects.live().prefetch_related("tags", "attachment_assets", "related_posts")

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        session_key = f"blog_viewed_{obj.pk}"
        if not self.request.session.get(session_key):
            BlogPost.objects.filter(pk=obj.pk).update(view_count=F("view_count") + 1)
            obj.view_count += 1
            self.request.session[session_key] = True
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        blog_page_content = BlogPageContent.objects.first()
        related_posts = self.object.related_posts.live().exclude(pk=self.object.pk)[:4]
        if not related_posts:
            related_posts = BlogPost.objects.live().filter(category=self.object.category).exclude(pk=self.object.pk)[:4]
        context.update(
            {
                "blog_page_content": blog_page_content,
                "recent_blogs": BlogPost.objects.live()
                .exclude(pk=self.object.pk)
                .order_by("-published_on", "-id")[:5],
                "related_blogs": related_posts,
            }
        )
        return self.add_seo(
            context,
            source=self.object,
            fallback_title=self.object.title,
            fallback_description=self.object.excerpt,
            fallback_keywords=self.object.category,
            fallback_image_url=self.object.image_url,
            og_type="article",
            schema={
                "@context": "https://schema.org",
                "@type": "BlogPosting",
                "headline": self.object.title,
                "description": self.object.excerpt,
                "image": [self.object.image_url],
                "datePublished": self.object.published_on.isoformat(),
                "mainEntityOfPage": self.request.build_absolute_uri(self.object.get_absolute_url()),
            },
        )


def blog_like_view(request, slug):
    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "POST required."}, status=405)
    blog = BlogPost.objects.live().filter(slug=slug).first()
    if not blog:
        return JsonResponse({"ok": False, "message": "Blog not found."}, status=404)
    session_key = f"blog_liked_{blog.pk}"
    if not request.session.get(session_key):
        BlogPost.objects.filter(pk=blog.pk).update(like_count=F("like_count") + 1)
        request.session[session_key] = True
        blog.refresh_from_db(fields=["like_count"])
    else:
        blog.refresh_from_db(fields=["like_count"])
    return JsonResponse({"ok": True, "like_count": blog.like_count})


def blog_share_view(request, slug):
    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "POST required."}, status=405)
    blog = BlogPost.objects.live().filter(slug=slug).first()
    if not blog:
        return JsonResponse({"ok": False, "message": "Blog not found."}, status=404)
    session_key = f"blog_shared_{blog.pk}"
    if not request.session.get(session_key):
        BlogPost.objects.filter(pk=blog.pk).update(share_count=F("share_count") + 1)
        request.session[session_key] = True
        blog.refresh_from_db(fields=["share_count"])
    else:
        blog.refresh_from_db(fields=["share_count"])
    return JsonResponse({"ok": True, "share_count": blog.share_count})


def blog_read_time_view(request, slug):
    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "POST required."}, status=405)
    blog = BlogPost.objects.live().filter(slug=slug).first()
    if not blog:
        return JsonResponse({"ok": False, "message": "Blog not found."}, status=404)
    try:
        seconds = int(request.POST.get("seconds", 0))
    except (TypeError, ValueError):
        seconds = 0
    seconds = max(0, min(seconds, 900))
    if seconds:
        BlogPost.objects.filter(pk=blog.pk).update(
            read_time_total_seconds=F("read_time_total_seconds") + seconds,
            read_sessions_count=F("read_sessions_count") + 1,
        )
    return JsonResponse({"ok": True})


@method_decorator(cache_public_page, name="dispatch")
class ServiceListView(SiteContentMixin, ListView):
    model = Service
    template_name = "services.html"
    context_object_name = "services"
    paginate_by = 6

    def get_queryset(self):
        return Service.objects.filter(is_published=True).order_by("title", "id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service_page_content = ServicePageContent.objects.first()
        context.update(
            {
                "service_page_content": service_page_content,
                "recent_services": Service.objects.filter(is_published=True).order_by("title", "id")[:5],
            }
        )
        return self.add_seo(
            context,
            source=service_page_content,
            fallback_title=service_page_content.page_hero_title if service_page_content else "Services",
            fallback_description=service_page_content.page_intro_text if service_page_content else "",
            fallback_keywords="services, web development, ui ux, consulting",
            schema={
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": service_page_content.page_hero_title if service_page_content else "Services",
                "description": service_page_content.page_intro_text if service_page_content else "",
                "url": self.request.build_absolute_uri(),
            },
        )


@method_decorator(cache_public_page, name="dispatch")
class ServiceDetailView(SiteContentMixin, DetailView):
    model = Service
    template_name = "service_detail.html"
    context_object_name = "service"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Service.objects.filter(is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service_page_content = ServicePageContent.objects.first()
        context.update(
            {
                "service_page_content": service_page_content,
                "recent_services": Service.objects.filter(is_published=True)
                .exclude(pk=self.object.pk)
                .order_by("title", "id")[:5],
            }
        )
        site_name = getattr(context.get("site_settings"), "site_name", "JS Technova")
        return self.add_seo(
            context,
            source=self.object,
            fallback_title=self.object.title,
            fallback_description=self.object.summary,
            fallback_keywords="service, consulting",
            fallback_image_url=self.object.image_url,
            schema={
                "@context": "https://schema.org",
                "@type": "Service",
                "name": self.object.title,
                "description": self.object.summary,
                "provider": {"@type": "Organization", "name": site_name},
                "url": self.request.build_absolute_uri(self.object.get_absolute_url()),
            },
        )


@method_decorator(cache_public_page, name="dispatch")
class ProjectListView(SiteContentMixin, ListView):
    model = Project
    template_name = "projects.html"
    context_object_name = "projects"
    paginate_by = 6

    def get_queryset(self):
        queryset = Project.objects.filter(is_published=True).order_by("title", "id")
        category = self.request.GET.get("category")
        project_page_content = ProjectPageContent.objects.first()
        all_label = project_page_content.filter_all_label if project_page_content else "All"
        if category and category.lower() != "all" and category != all_label:
            queryset = queryset.filter(category=category)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_projects = Project.objects.filter(is_published=True).order_by("title", "id")
        project_page_content = ProjectPageContent.objects.first()
        context.update(
            {
                "project_page_content": project_page_content,
                "project_process_steps": ProjectProcessStep.objects.all(),
                "project_categories": list(all_projects.values_list("category", flat=True).distinct()),
                "selected_category": self.request.GET.get(
                    "category",
                    project_page_content.filter_all_label if project_page_content else "All",
                ),
                "featured_project": all_projects.first(),
            }
        )
        return self.add_seo(
            context,
            source=project_page_content,
            fallback_title=project_page_content.hero_title if project_page_content else "Projects",
            fallback_description=project_page_content.intro_description if project_page_content else "",
            fallback_keywords="projects, case studies, portfolio",
            fallback_image_url=project_page_content.hero_image_url if project_page_content else "",
            schema={
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": project_page_content.hero_title if project_page_content else "Projects",
                "description": project_page_content.intro_description if project_page_content else "",
                "url": self.request.build_absolute_uri(),
            },
        )


@method_decorator(cache_public_page, name="dispatch")
class ProjectDetailView(SiteContentMixin, DetailView):
    model = Project
    template_name = "project_detail.html"
    context_object_name = "project"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Project.objects.filter(is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_page_content = ProjectPageContent.objects.first()
        context["project_page_content"] = project_page_content
        context.update(
            {
                "recent_projects": Project.objects.filter(is_published=True)
                .exclude(pk=self.object.pk)
                .order_by("title", "id")[:4],
            }
        )
        return self.add_seo(
            context,
            source=self.object,
            fallback_title=self.object.title,
            fallback_description=self.object.summary,
            fallback_keywords=", ".join(filter(None, [self.object.category, self.object.tag_one, self.object.tag_two])),
            fallback_image_url=self.object.image_url,
            schema={
                "@context": "https://schema.org",
                "@type": "CreativeWork",
                "name": self.object.title,
                "description": self.object.summary,
                "image": self.object.image_url,
                "url": self.request.build_absolute_uri(self.object.get_absolute_url()),
            },
        )


@method_decorator(cache_public_page, name="dispatch")
class CareerListView(SiteContentMixin, ListView):
    model = CareerOpening
    template_name = "careers.html"
    context_object_name = "careers"
    paginate_by = 6

    def get_queryset(self):
        queryset = CareerOpening.objects.filter(is_published=True).order_by("order", "title", "id")
        department = self.request.GET.get("department")
        career_page_content = CareerPageContent.objects.first()
        all_label = career_page_content.filter_all_label if career_page_content else "All"
        if department and department.lower() != "all" and department != all_label:
            queryset = queryset.filter(department=department)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        career_page_content = CareerPageContent.objects.first()
        career_benefits = list(CareerBenefit.objects.all())
        context.update(
            {
                "career_page_content": career_page_content,
                "career_benefits": career_benefits,
                "career_departments": list(
                    CareerOpening.objects.filter(is_published=True)
                    .order_by("department")
                    .values_list("department", flat=True)
                    .distinct()
                ),
                "selected_department": self.request.GET.get(
                    "department",
                    career_page_content.filter_all_label if career_page_content else "All",
                ),
            }
        )
        return self.add_seo(
            context,
            source=career_page_content,
            fallback_title=career_page_content.hero_title if career_page_content else "Careers",
            fallback_description=career_page_content.intro_description if career_page_content else "",
            fallback_keywords="careers, jobs, frontend, design, remote",
            fallback_image_url=career_page_content.hero_image_url if career_page_content else "",
            schema={
                "@context": "https://schema.org",
                "@type": "CollectionPage",
                "name": career_page_content.hero_title if career_page_content else "Careers",
                "description": career_page_content.intro_description if career_page_content else "",
                "url": self.request.build_absolute_uri(),
            },
        )


@method_decorator(cache_public_page, name="dispatch")
class CareerDetailView(SiteContentMixin, DetailView):
    model = CareerOpening
    template_name = "career.html"
    context_object_name = "career"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return CareerOpening.objects.filter(is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        career_page_content = CareerPageContent.objects.first()
        context["career_page_content"] = career_page_content
        context.update(
            {
                "other_careers": CareerOpening.objects.filter(is_published=True)
                .exclude(pk=self.object.pk)
                .order_by("order", "title", "id")[:3],
            }
        )
        return self.add_seo(
            context,
            source=self.object,
            fallback_title=self.object.title,
            fallback_description=self.object.summary,
            fallback_keywords=", ".join(filter(None, [self.object.department, self.object.location, self.object.employment_type])),
            fallback_image_url=self.object.hero_image_url,
            schema={
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": self.object.title,
                "description": self.object.overview,
                "employmentType": self.object.employment_type,
                "industry": self.object.department,
                "experienceRequirements": self.object.experience_level,
                "jobLocationType": "TELECOMMUTE" if self.object.location.lower() == "remote" else None,
                "url": self.request.build_absolute_uri(self.object.get_absolute_url()),
            },
        )


def robots_txt_view(request):
    sitemap_url = request.build_absolute_uri(reverse("sitemap"))
    return HttpResponse(
        f"User-agent: *\nAllow: /\n\nSitemap: {sitemap_url}\n",
        content_type="text/plain",
    )
