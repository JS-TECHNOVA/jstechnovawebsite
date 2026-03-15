from datetime import date, timedelta

from django.conf import settings
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    AboutPageContent,
    BlogPost,
    BlogTag,
    CareerOpening,
    ContactSubmission,
    FaqItem,
    HomeBlog,
    HomeFaq,
    HomePageContent,
    HomeProject,
    HomeService,
    HomeTestimonial,
    Project,
    Service,
    SiteSettings,
    Testimonial,
    WhyChooseUsItem,
)
from .views import bootstrap_homepage_defaults


class HomePageViewTests(TestCase):
    def test_homepage_does_not_auto_seed_backend_records(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SiteSettings.objects.count(), 0)
        self.assertIn("hero_slides", response.context)
        self.assertEqual(len(response.context["hero_slides"]), 0)

    def test_homepage_featured_blog_comes_from_home_blog_mapping(self):
        bootstrap_homepage_defaults()

        HomeBlog.objects.all().delete()
        BlogPost.objects.all().delete()

        primary = BlogPost.objects.create(
            title="Primary Blog",
            category="Strategy",
            excerpt="Primary excerpt",
            image_url="https://example.com/primary.jpg",
            details_url="/blogs/primary/",
            published_on=date(2026, 1, 5),
        )
        secondary = BlogPost.objects.create(
            title="Secondary Blog",
            category="Tech",
            excerpt="Secondary excerpt",
            image_url="https://example.com/secondary.jpg",
            details_url="/blogs/secondary/",
            published_on=date(2026, 1, 6),
        )

        HomeBlog.objects.create(blog=secondary, display_order=1, is_featured=False, is_active=True)
        HomeBlog.objects.create(blog=primary, display_order=2, is_featured=True, is_active=True)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.context["home_featured_blog"], primary)
        self.assertEqual(len(response.context["home_secondary_blogs"]), 1)

    def test_homepage_projects_respect_publish_and_home_mapping(self):
        bootstrap_homepage_defaults()

        HomeProject.objects.all().delete()
        Project.objects.all().delete()

        visible = Project.objects.create(
            title="Visible Project",
            summary="Visible summary",
            image_url="https://example.com/visible.jpg",
            vertical_label="Visible",
            is_published=True,
        )
        hidden = Project.objects.create(
            title="Hidden Project",
            summary="Hidden summary",
            image_url="https://example.com/hidden.jpg",
            vertical_label="Hidden",
            is_published=False,
        )

        HomeProject.objects.create(project=visible, display_order=1, is_active=True)
        HomeProject.objects.create(project=hidden, display_order=2, is_active=True)

        response = self.client.get(reverse("home"))
        home_projects = [entry.project for entry in response.context["home_projects"]]

        self.assertEqual(home_projects, [visible])

    def test_homepage_testimonials_respect_publish_and_home_mapping(self):
        bootstrap_homepage_defaults()

        HomeTestimonial.objects.all().delete()
        Testimonial.objects.all().delete()

        visible = Testimonial.objects.create(
            name="Visible Testimonial",
            quote="Visible quote",
            image_url="https://example.com/visible-testimonial.jpg",
            is_published=True,
        )
        hidden = Testimonial.objects.create(
            name="Hidden Testimonial",
            quote="Hidden quote",
            image_url="https://example.com/hidden-testimonial.jpg",
            is_published=False,
        )

        HomeTestimonial.objects.create(testimonial=visible, display_order=1, is_active=True)
        HomeTestimonial.objects.create(testimonial=hidden, display_order=2, is_active=True)

        response = self.client.get(reverse("home"))
        home_testimonials = [entry.testimonial for entry in response.context["home_testimonials"]]

        self.assertEqual(home_testimonials, [visible])

    def test_homepage_faqs_respect_publish_and_home_mapping(self):
        bootstrap_homepage_defaults()

        HomeFaq.objects.all().delete()
        FaqItem.objects.all().delete()

        visible = FaqItem.objects.create(
            question="Visible question?",
            answer="Visible answer.",
            is_published=True,
        )
        hidden = FaqItem.objects.create(
            question="Hidden question?",
            answer="Hidden answer.",
            is_published=False,
        )

        HomeFaq.objects.create(faq=visible, display_order=1, is_active=True)
        HomeFaq.objects.create(faq=hidden, display_order=2, is_active=True)

        response = self.client.get(reverse("home"))
        home_faqs = [entry.faq for entry in response.context["home_faqs"]]

        self.assertEqual(home_faqs, [visible])

    def test_homepage_renders_seo_meta_tags(self):
        bootstrap_homepage_defaults()
        homepage_content = HomePageContent.objects.get(pk=1)
        homepage_content.seo_meta_title = "Custom Home"
        homepage_content.seo_meta_description = "Home meta description"
        homepage_content.seo_keywords = "agency, product, development"
        homepage_content.seo_schema_json_ld = '{"@context":"https://schema.org","@type":"WebSite"}'
        homepage_content.save()

        response = self.client.get(reverse("home"))

        self.assertContains(response, "<title>Custom Home | JS Technova</title>", html=True)
        self.assertContains(response, 'meta name="description" content="Home meta description"', html=False)
        self.assertContains(response, 'meta name="keywords" content="agency, product, development"', html=False)
        self.assertContains(response, '"@type":"WebSite"', html=False)

    def test_homepage_renders_why_choose_us_section(self):
        bootstrap_homepage_defaults()

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("why_choose_items", response.context)
        self.assertTrue(response.context["why_choose_items"])
        self.assertContains(response, HomePageContent.objects.get(pk=1).why_choose_title)
        self.assertContains(response, WhyChooseUsItem.objects.order_by("order", "id").first().title)

    def test_homepage_response_is_page_cached(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(f"max-age={settings.PAGE_CACHE_SECONDS}", response.headers.get("Cache-Control", ""))


class BlogPageTests(TestCase):
    def test_blogs_page_is_paginated(self):
        bootstrap_homepage_defaults()
        BlogPost.objects.all().delete()

        for index in range(1, 9):
            BlogPost.objects.create(
                title=f"Blog {index}",
                slug=f"blog-{index}",
                category="General",
                excerpt="Sample excerpt",
                image_url="https://example.com/blog.jpg",
                published_on=date(2026, 1, index),
                is_published=True,
            )

        response = self.client.get(reverse("blogs"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["blogs"]), 6)

    def test_blog_detail_renders_editorjs_content(self):
        bootstrap_homepage_defaults()
        blog = BlogPost.objects.create(
            title="Editor Blog",
            slug="editor-blog",
            category="General",
            excerpt="Editor excerpt",
            image_url="https://example.com/editor.jpg",
            content_json={
                "blocks": [
                    {"type": "header", "data": {"text": "Hello", "level": 2}},
                    {"type": "paragraph", "data": {"text": "Editor.js body"}},
                ]
            },
            is_published=True,
        )

        response = self.client.get(reverse("blog_detail", kwargs={"slug": blog.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello")
        self.assertContains(response, "Editor.js body")

    def test_blogs_page_supports_search_tag_and_popularity_filters(self):
        bootstrap_homepage_defaults()
        BlogPost.objects.all().delete()
        ai_tag = BlogTag.objects.create(name="AI", slug="ai")
        growth_tag = BlogTag.objects.create(name="Growth", slug="growth")

        first = BlogPost.objects.create(
            title="AI Architecture",
            slug="ai-architecture",
            category="Technology",
            excerpt="AI systems",
            image_url="https://example.com/ai.jpg",
            view_count=10,
            is_published=True,
        )
        first.tags.add(ai_tag)
        second = BlogPost.objects.create(
            title="Growth Playbook",
            slug="growth-playbook",
            category="Leadership",
            excerpt="Growth systems",
            image_url="https://example.com/growth.jpg",
            view_count=50,
            is_published=True,
        )
        second.tags.add(growth_tag)

        response = self.client.get(reverse("blogs"), {"q": "AI", "tag": "ai", "sort": "popular"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, first.title)
        self.assertEqual(list(response.context["blogs"]), [first])

    def test_blogs_page_response_is_page_cached(self):
        bootstrap_homepage_defaults()
        response = self.client.get(reverse("blogs"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(f"max-age={settings.PAGE_CACHE_SECONDS}", response.headers.get("Cache-Control", ""))

    def test_blog_engagement_endpoints_update_metrics(self):
        bootstrap_homepage_defaults()
        blog = BlogPost.objects.create(
            title="Tracked Blog",
            slug="tracked-blog",
            category="General",
            excerpt="Tracked excerpt",
            image_url="https://example.com/tracked.jpg",
            is_published=True,
        )

        like_response = self.client.post(reverse("blog_like", kwargs={"slug": blog.slug}))
        share_response = self.client.post(reverse("blog_share", kwargs={"slug": blog.slug}))
        read_response = self.client.post(reverse("blog_read_time", kwargs={"slug": blog.slug}), {"seconds": "30"})

        blog.refresh_from_db()
        self.assertEqual(like_response.status_code, 200)
        self.assertEqual(share_response.status_code, 200)
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(blog.like_count, 1)
        self.assertEqual(blog.share_count, 1)
        self.assertEqual(blog.read_time_total_seconds, 30)
        self.assertEqual(blog.read_sessions_count, 1)


class ServicePageTests(TestCase):
    def test_homepage_services_respect_publish_and_home_mapping(self):
        bootstrap_homepage_defaults()
        HomeService.objects.all().delete()
        Service.objects.all().delete()

        visible = Service.objects.create(
            title="Visible Service",
            summary="Visible service summary",
            image_url="https://example.com/visible-service.jpg",
            is_published=True,
        )
        hidden = Service.objects.create(
            title="Hidden Service",
            summary="Hidden service summary",
            image_url="https://example.com/hidden-service.jpg",
            is_published=False,
        )

        HomeService.objects.create(service=visible, display_order=1, is_active=True)
        HomeService.objects.create(service=hidden, display_order=2, is_active=True)

        response = self.client.get(reverse("home"))
        home_services = [entry.service for entry in response.context["home_services"]]

        self.assertEqual(home_services, [visible])

    def test_services_page_is_paginated(self):
        bootstrap_homepage_defaults()
        HomeService.objects.all().delete()
        Service.objects.all().delete()

        for index in range(1, 9):
            Service.objects.create(
                title=f"Service {index}",
                slug=f"service-{index}",
                summary="Sample service summary",
                image_url="https://example.com/service.jpg",
                is_published=True,
            )

        response = self.client.get(reverse("services"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["services"]), 6)

    def test_service_detail_renders_editorjs_content(self):
        bootstrap_homepage_defaults()
        service = Service.objects.create(
            title="Editor Service",
            slug="editor-service",
            summary="Editor summary",
            image_url="https://example.com/editor-service.jpg",
            content_json={
                "blocks": [
                    {"type": "header", "data": {"text": "Service Header", "level": 2}},
                    {"type": "paragraph", "data": {"text": "Service body text"}},
                ]
            },
            is_published=True,
        )

        response = self.client.get(reverse("service_detail", kwargs={"slug": service.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Service Header")
        self.assertContains(response, "Service body text")


class AdditionalPageTests(TestCase):
    def test_about_and_contact_pages_render(self):
        bootstrap_homepage_defaults()
        about_page = AboutPageContent.objects.get(pk=1)
        about_page.seo_meta_title = "About JS Technova"
        about_page.seo_meta_description = "About page SEO copy"
        about_page.save()

        about_response = self.client.get(reverse("about"))
        contact_response = self.client.get(reverse("contact"))

        self.assertEqual(about_response.status_code, 200)
        self.assertEqual(contact_response.status_code, 200)
        self.assertContains(about_response, "About")
        self.assertContains(contact_response, "Contact")
        self.assertContains(about_response, "<title>About JS Technova | JS Technova</title>", html=True)
        self.assertContains(about_response, 'meta name="description" content="About page SEO copy"', html=False)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="hello@test.com",
        CONTACT_NOTIFICATION_EMAIL="team@test.com",
    )
    def test_contact_form_submission_creates_contact_submission_and_sends_emails(self):
        bootstrap_homepage_defaults()
        site_settings = SiteSettings.objects.get(pk=1)
        site_settings.contact_auto_reply_message_json = {
            "blocks": [
                {
                    "type": "paragraph",
                    "data": {"text": "We will review your request and reply with the next steps shortly."},
                },
                {
                    "type": "paragraph",
                    "data": {"text": "If you have more details to share, reply directly to this email."},
                },
            ]
        }
        site_settings.save()
        service = Service.objects.filter(is_published=True).first()

        response = self.client.post(
            reverse("contact"),
            {
                "name": "Alex Founder",
                "email": "alex@example.com",
                "phone": "+1 555 0100",
                "service_interest": service.pk if service else "",
                "project_details": "Need a marketing site and admin dashboard.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactSubmission.objects.count(), 1)
        self.assertContains(response, "Your inquiry has been received.")
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("Thanks for contacting", mail.outbox[0].subject)
        self.assertIn("Alex Founder", mail.outbox[0].body)
        self.assertIn("We will review your request and reply with the next steps shortly.", mail.outbox[0].body)
        self.assertIn("If you have more details to share, reply directly to this email.", mail.outbox[0].alternatives[0][0])
        self.assertIn("New contact inquiry from Alex Founder", mail.outbox[1].subject)
        self.assertIn("Need a marketing site and admin dashboard.", mail.outbox[1].body)

    def test_projects_page_is_paginated_and_detail_renders(self):
        bootstrap_homepage_defaults()
        HomeProject.objects.all().delete()
        Project.objects.all().delete()

        created = []
        for index in range(1, 9):
            created.append(
                Project.objects.create(
                    title=f"Project {index}",
                    slug=f"project-{index}",
                    category="Web App",
                    summary="Sample project summary",
                    image_url="https://example.com/project.jpg",
                    vertical_label="Project",
                    is_published=True,
                )
            )

        response = self.client.get(reverse("projects"))
        detail_response = self.client.get(reverse("project_detail", kwargs={"slug": created[0].slug}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["projects"]), 6)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, created[0].title)

    def test_careers_page_is_paginated_and_detail_renders(self):
        bootstrap_homepage_defaults()
        CareerOpening.objects.all().delete()

        created = []
        for index in range(1, 9):
            created.append(
                CareerOpening.objects.create(
                    title=f"Role {index}",
                    slug=f"role-{index}",
                    summary="Sample role summary",
                    department="Engineering",
                    location="Remote",
                    employment_type="Full Time",
                    experience_level="2+ years",
                    overview="Role overview",
                    responsibilities_text="Do work",
                    requirements_text="Know things",
                    nice_to_have_text="Bonus",
                    is_published=True,
                )
            )

        response = self.client.get(reverse("careers"))
        detail_response = self.client.get(reverse("career_detail", kwargs={"slug": created[0].slug}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["careers"]), 6)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, created[0].title)

    def test_career_detail_renders_editorjs_sections(self):
        bootstrap_homepage_defaults()
        career = CareerOpening.objects.create(
            title="Editor Career",
            slug="editor-career",
            summary="Editor career summary",
            department="Engineering",
            location="Remote",
            employment_type="Full Time",
            experience_level="3+ years",
            overview="Fallback overview",
            overview_json={
                "blocks": [
                    {"type": "header", "data": {"text": "Career Overview", "level": 2}},
                    {"type": "paragraph", "data": {"text": "Editor.js overview body"}},
                ]
            },
            responsibilities_json={
                "blocks": [
                    {"type": "list", "data": {"style": "unordered", "items": ["Lead delivery", "Own quality"]}}
                ]
            },
            requirements_json={
                "blocks": [
                    {"type": "checklist", "data": {"items": [{"text": "Strong React", "checked": True}]}}
                ]
            },
            nice_to_have_json={
                "blocks": [
                    {"type": "paragraph", "data": {"text": "Startup experience is a plus"}}
                ]
            },
            is_published=True,
        )

        response = self.client.get(reverse("career_detail", kwargs={"slug": career.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Career Overview")
        self.assertContains(response, "Editor.js overview body")
        self.assertContains(response, "Lead delivery")
        self.assertContains(response, "Strong React")
        self.assertContains(response, "Startup experience is a plus")

    def test_robots_and_sitemap_routes_render(self):
        bootstrap_homepage_defaults()

        robots_response = self.client.get(reverse("robots_txt"))
        sitemap_response = self.client.get(reverse("sitemap"))

        self.assertEqual(robots_response.status_code, 200)
        self.assertEqual(sitemap_response.status_code, 200)
        self.assertContains(robots_response, "Sitemap:")
        self.assertContains(sitemap_response, "<urlset", html=False)

    def test_sitemap_only_contains_live_blog_posts(self):
        bootstrap_homepage_defaults()
        BlogPost.objects.all().delete()
        live_blog = BlogPost.objects.create(
            title="Live Sitemap Blog",
            slug="live-sitemap-blog",
            category="General",
            excerpt="Visible in sitemap",
            image_url="https://example.com/live.jpg",
            status=BlogPost.STATUS_PUBLISHED,
            is_published=True,
        )
        BlogPost.objects.create(
            title="Scheduled Sitemap Blog",
            slug="scheduled-sitemap-blog",
            category="General",
            excerpt="Should not be visible yet",
            image_url="https://example.com/scheduled.jpg",
            status=BlogPost.STATUS_PUBLISHED,
            scheduled_for=timezone.now() + timedelta(days=2),
            is_published=True,
        )

        sitemap_response = self.client.get(reverse("sitemap"))

        self.assertEqual(sitemap_response.status_code, 200)
        self.assertContains(sitemap_response, live_blog.get_absolute_url(), html=False)
        self.assertNotContains(sitemap_response, "/blogs/scheduled-sitemap-blog/", html=False)
