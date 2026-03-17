import json
from datetime import date

from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from website.models import (
    AuditLog,
    BlogPost,
    FeedbackPageContent,
    FooterLink,
    FaqItem,
    HomeBlog,
    MediaAsset,
    PrivacyPolicyPageContent,
    Service,
    SiteSettings,
    TermsAndConditionsPageContent,
    Testimonial,
)
from website.views import bootstrap_homepage_defaults


User = get_user_model()


class CmsAccessTests(TestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="pass12345",
            is_staff=True,
        )
        self.staff_user.user_permissions.set(
            Permission.objects.filter(content_type__app_label__in=["website", "auth"])
        )
        self.normal_user = User.objects.create_user(
            username="normal",
            email="normal@example.com",
            password="pass12345",
            is_staff=False,
        )
        self.limited_staff_user = User.objects.create_user(
            username="limited",
            email="limited@example.com",
            password="pass12345",
            is_staff=True,
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("cms:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("cms:login"), response.url)

    def test_non_staff_user_cannot_access_dashboard(self):
        self.client.login(username="normal", password="pass12345")
        response = self.client.get(reverse("cms:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("cms:login"), response.url)

    def test_staff_user_can_access_dashboard(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.get(reverse("cms:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_staff_user_can_access_services_manager(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.get(reverse("cms:services_manage"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("service_page_form", response.context)
        self.assertIn("home_services_formset", response.context)

    def test_staff_user_can_access_media_library_manager(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.get(reverse("cms:media_manage"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("page_obj", response.context)

    def test_staff_user_can_access_audit_logs(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.get(reverse("cms:audit_logs"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("page_obj", response.context)

    def test_homepage_manager_supports_panel_navigation(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.get(reverse("cms:homepage_manage"), {"panel": "hero"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["cms_subsection"], "hero")

    def test_homepage_manager_supports_footer_links_panel(self):
        bootstrap_homepage_defaults()
        self.client.login(username="staff", password="pass12345")

        response = self.client.get(reverse("cms:homepage_manage"), {"panel": "footer-links"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["cms_subsection"], "footer-links")
        self.assertIn("footer_quick_formset", response.context)
        self.assertIn("footer_bottom_formset", response.context)

    def test_staff_can_update_footer_link_title(self):
        bootstrap_homepage_defaults()
        self.client.login(username="staff", password="pass12345")

        response = self.client.post(
            reverse("cms:homepage_manage"),
            {
                "form_type": "footer_link_settings",
                "panel": "footer-links",
                "footer_settings-footer_quick_links_title": "Useful Links",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SiteSettings.objects.get(pk=1).footer_quick_links_title, "Useful Links")

    def test_staff_can_update_footer_links(self):
        bootstrap_homepage_defaults()
        self.client.login(username="staff", password="pass12345")
        quick_link = FooterLink.objects.filter(section=FooterLink.SECTION_QUICK).order_by("order", "id").first()
        bottom_link = FooterLink.objects.filter(section=FooterLink.SECTION_BOTTOM).order_by("order", "id").first()
        FooterLink.objects.filter(section=FooterLink.SECTION_QUICK).exclude(pk=quick_link.pk).delete()
        FooterLink.objects.filter(section=FooterLink.SECTION_BOTTOM).exclude(pk=bottom_link.pk).delete()

        response = self.client.post(
            reverse("cms:homepage_manage"),
            {
                "form_type": "footer_links",
                "panel": "footer-links",
                "footer_quick-TOTAL_FORMS": "1",
                "footer_quick-INITIAL_FORMS": "1",
                "footer_quick-MIN_NUM_FORMS": "0",
                "footer_quick-MAX_NUM_FORMS": "1000",
                "footer_quick-0-id": str(quick_link.id),
                "footer_quick-0-label": "Company",
                "footer_quick-0-url": "/company/",
                "footer_quick-0-order": "1",
                "footer_quick-0-is_active": "on",
                "footer_bottom-TOTAL_FORMS": "1",
                "footer_bottom-INITIAL_FORMS": "1",
                "footer_bottom-MIN_NUM_FORMS": "0",
                "footer_bottom-MAX_NUM_FORMS": "1000",
                "footer_bottom-0-id": str(bottom_link.id),
                "footer_bottom-0-label": "Legal",
                "footer_bottom-0-url": "/legal/",
                "footer_bottom-0-order": "1",
                "footer_bottom-0-is_active": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        quick_link.refresh_from_db()
        bottom_link.refresh_from_db()
        self.assertEqual(quick_link.label, "Company")
        self.assertEqual(quick_link.url, "/company/")
        self.assertEqual(bottom_link.label, "Legal")
        self.assertEqual(bottom_link.url, "/legal/")

    def test_pages_manager_supports_panel_navigation(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.get(reverse("cms:pages_manage"), {"panel": "contact-page"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["cms_subsection"], "contact-page")

    def test_pages_manager_supports_feedback_and_legal_panels(self):
        bootstrap_homepage_defaults()
        self.client.login(username="staff", password="pass12345")

        feedback_response = self.client.get(reverse("cms:pages_manage"), {"panel": "feedback-page"})
        legal_response = self.client.get(reverse("cms:pages_manage"), {"panel": "legal-pages"})

        self.assertEqual(feedback_response.status_code, 200)
        self.assertEqual(feedback_response.context["cms_subsection"], "feedback-page")
        self.assertIn("feedback_page_form", feedback_response.context)
        self.assertEqual(legal_response.status_code, 200)
        self.assertEqual(legal_response.context["cms_subsection"], "legal-pages")
        self.assertIn("privacy_page_form", legal_response.context)
        self.assertIn("terms_page_form", legal_response.context)

    def test_legacy_grouped_panel_aliases_resolve_to_new_sections(self):
        self.client.login(username="staff", password="pass12345")

        homepage_response = self.client.get(reverse("cms:homepage_manage"), {"panel": "why-choose-items"})
        pages_response = self.client.get(reverse("cms:pages_manage"), {"panel": "about-steps"})
        legal_response = self.client.get(reverse("cms:pages_manage"), {"panel": "privacy-policy"})

        self.assertEqual(homepage_response.status_code, 200)
        self.assertEqual(homepage_response.context["cms_subsection"], "why-choose")
        self.assertEqual(pages_response.status_code, 200)
        self.assertEqual(pages_response.context["cms_subsection"], "about-values-process")
        self.assertEqual(legal_response.status_code, 200)
        self.assertEqual(legal_response.context["cms_subsection"], "legal-pages")

    def test_staff_can_update_feedback_page_copy(self):
        bootstrap_homepage_defaults()
        self.client.login(username="staff", password="pass12345")

        response = self.client.post(
            reverse("cms:pages_manage"),
            {
                "form_type": "feedback_page",
                "panel": "feedback-page",
                "feedback_page-hero_badge": "Client Voice",
                "feedback_page-hero_title": "Tell us what the experience felt like",
                "feedback_page-hero_description": "Feedback page intro",
                "feedback_page-mood_question": "How are you feeling today?",
                "feedback_page-rating_prompt": "Rate the journey",
                "feedback_page-image_prompt": "Add your photo",
                "feedback_page-image_help_text": "Upload an image to personalize your response.",
                "feedback_page-name_label": "Your name",
                "feedback_page-name_placeholder": "Enter your name",
                "feedback_page-email_label": "Your email",
                "feedback_page-email_placeholder": "Enter your email",
                "feedback_page-message_label": "What is on your mind?",
                "feedback_page-message_placeholder": "Share your feedback",
                "feedback_page-submit_text": "Send feedback",
                "feedback_page-success_message": "Thank you for sharing your feedback.",
                "feedback_page-privacy_note": "We only use this to improve our service.",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FeedbackPageContent.objects.get(pk=1).hero_badge, "Client Voice")

    def test_staff_can_update_legal_pages_from_grouped_panel(self):
        bootstrap_homepage_defaults()
        self.client.login(username="staff", password="pass12345")

        privacy_response = self.client.post(
            reverse("cms:pages_manage"),
            {
                "form_type": "privacy_page",
                "panel": "legal-pages",
                "privacy_page-hero_badge": "Privacy",
                "privacy_page-hero_title": "Privacy Center",
                "privacy_page-intro_text": "How we handle information.",
                "privacy_page-content_json": json.dumps(
                    {"blocks": [{"type": "paragraph", "data": {"text": "Privacy body"}}]}
                ),
            },
            follow=True,
        )
        terms_response = self.client.post(
            reverse("cms:pages_manage"),
            {
                "form_type": "terms_page",
                "panel": "legal-pages",
                "terms_page-hero_badge": "Terms",
                "terms_page-hero_title": "Terms Center",
                "terms_page-intro_text": "Rules for using the site.",
                "terms_page-content_json": json.dumps(
                    {"blocks": [{"type": "paragraph", "data": {"text": "Terms body"}}]}
                ),
            },
            follow=True,
        )

        self.assertEqual(privacy_response.status_code, 200)
        self.assertEqual(terms_response.status_code, 200)
        self.assertEqual(PrivacyPolicyPageContent.objects.get(pk=1).hero_title, "Privacy Center")
        self.assertEqual(TermsAndConditionsPageContent.objects.get(pk=1).hero_title, "Terms Center")

    def test_staff_without_permission_cannot_access_services_manager(self):
        self.client.login(username="limited", password="pass12345")
        response = self.client.get(reverse("cms:services_manage"))
        self.assertEqual(response.status_code, 403)

    def test_staff_user_can_access_testimonials_and_faq_managers(self):
        self.client.login(username="staff", password="pass12345")
        testimonials_response = self.client.get(reverse("cms:testimonials_manage"))
        faqs_response = self.client.get(reverse("cms:faqs_manage"))
        self.assertEqual(testimonials_response.status_code, 200)
        self.assertEqual(faqs_response.status_code, 200)
        self.assertIn("home_testimonials_formset", testimonials_response.context)
        self.assertIn("home_faqs_formset", faqs_response.context)

    def test_staff_can_create_service_with_editor_payload(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.post(
            reverse("cms:service_create"),
            {
                "title": "Service via CMS",
                "slug": "",
                "icon_class": "fa-solid fa-briefcase",
                "summary": "Service summary",
                "image_url": "https://example.com/service.jpg",
                "cta_text": "Learn more",
                "details_url": "#",
                "content_json": '{"blocks":[{"type":"paragraph","data":{"text":"Service body"}}]}',
                "is_published": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Service.objects.filter(title="Service via CMS").exists())
        service = Service.objects.get(title="Service via CMS")
        self.assertEqual(service.content_json.get("blocks", [])[0]["type"], "paragraph")
        self.assertEqual(service.created_by, self.staff_user)
        self.assertEqual(service.updated_by, self.staff_user)
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ACTION_CREATE,
                model_label="website.Service",
                object_pk=str(service.pk),
                actor=self.staff_user,
            ).exists()
        )

    def test_service_update_and_delete_create_audit_logs(self):
        service = Service.objects.create(
            title="Audited Service",
            slug="audited-service",
            summary="Initial summary",
            image_url="https://example.com/service.jpg",
            created_by=self.staff_user,
            updated_by=self.staff_user,
        )
        AuditLog.objects.all().delete()

        self.client.login(username="staff", password="pass12345")
        edit_response = self.client.post(
            reverse("cms:service_edit", args=[service.pk]),
            {
                "title": "Audited Service",
                "slug": "audited-service",
                "icon_class": "fa-solid fa-briefcase",
                "summary": "Updated summary",
                "image_url": "https://example.com/service.jpg",
                "cta_text": "Learn more",
                "details_url": "#",
                "content_json": '{"blocks":[{"type":"paragraph","data":{"text":"Updated body"}}]}',
                "is_published": "on",
            },
            follow=True,
        )

        self.assertEqual(edit_response.status_code, 200)
        service.refresh_from_db()
        self.assertEqual(service.updated_by, self.staff_user)
        update_log = AuditLog.objects.get(action=AuditLog.ACTION_UPDATE, model_label="website.Service", object_pk=str(service.pk))
        self.assertEqual(update_log.actor, self.staff_user)
        self.assertIn("summary", update_log.details.get("changed_fields", []))

        delete_response = self.client.post(reverse("cms:service_delete", args=[service.pk]), follow=True)

        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(Service.objects.filter(pk=service.pk).exists())
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.ACTION_DELETE,
                model_label="website.Service",
                object_pk=str(service.pk),
                actor=self.staff_user,
            ).exists()
        )

    def test_editor_payload_is_sanitized_before_save(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.post(
            reverse("cms:service_create"),
            {
                "title": "Sanitized Service",
                "slug": "",
                "icon_class": "fa-solid fa-briefcase",
                "summary": "Service summary",
                "image_url": "https://example.com/service.jpg",
                "cta_text": "Learn more",
                "details_url": "#",
                "content_json": json.dumps(
                    {
                        "blocks": [
                            {"type": "paragraph", "data": {"text": "<script>alert(1)</script><b>Clean body</b>"}},
                            {
                                "type": "image",
                                "data": {
                                    "file": {"url": "javascript:alert(1)"},
                                    "caption": "<img src=x onerror=alert(1)>Unsafe",
                                },
                            },
                        ]
                    }
                ),
                "is_published": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        service = Service.objects.get(title="Sanitized Service")
        self.assertEqual(service.content_json["blocks"][0]["data"]["text"], "alert(1)Clean body")
        self.assertEqual(len(service.content_json["blocks"]), 1)

    def test_staff_can_create_blog_with_editor_payload(self):
        self.client.login(username="staff", password="pass12345")
        response = self.client.post(
            reverse("cms:blog_create"),
            {
                "title": "Blog via CMS",
                "slug": "",
                "category": "General",
                "excerpt": "Blog summary",
                "image_url": "https://example.com/blog.jpg",
                "status": BlogPost.STATUS_PUBLISHED,
                "published_on": "",
                "comment_count": "",
                "details_url": "#",
                "content_json": json.dumps(
                    {"blocks": [{"type": "paragraph", "data": {"text": "Saved blog body"}}]}
                ),
                "is_published": "on",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        blog = BlogPost.objects.get(title="Blog via CMS")
        self.assertEqual(blog.content_json["blocks"][0]["data"]["text"], "Saved blog body")

    def test_staff_can_create_testimonial_and_faq(self):
        self.client.login(username="staff", password="pass12345")

        testimonial_response = self.client.post(
            reverse("cms:testimonial_create"),
            {
                "order": "1",
                "name": "Client A",
                "role": "Founder",
                "company": "Startup",
                "quote": "Great delivery and communication.",
                "image_url": "https://example.com/client-a.jpg",
                "rating": "5",
                "is_published": "on",
            },
            follow=True,
        )
        faq_response = self.client.post(
            reverse("cms:faq_create"),
            {
                "order": "1",
                "question": "Do you support post-launch maintenance?",
                "answer": "Yes, we provide support and iterative improvements.",
                "is_published": "on",
            },
            follow=True,
        )

        self.assertEqual(testimonial_response.status_code, 200)
        self.assertEqual(faq_response.status_code, 200)
        self.assertTrue(Testimonial.objects.filter(name="Client A").exists())
        self.assertTrue(FaqItem.objects.filter(question="Do you support post-launch maintenance?").exists())

    def test_home_blog_mapping_allows_only_one_active_featured(self):
        bootstrap_homepage_defaults()
        HomeBlog.objects.all().delete()
        BlogPost.objects.all().delete()

        blog_one = BlogPost.objects.create(
            title="Blog One",
            slug="blog-one",
            category="General",
            excerpt="First blog",
            image_url="https://example.com/1.jpg",
            published_on=date(2026, 1, 10),
        )
        blog_two = BlogPost.objects.create(
            title="Blog Two",
            slug="blog-two",
            category="General",
            excerpt="Second blog",
            image_url="https://example.com/2.jpg",
            published_on=date(2026, 1, 11),
        )

        entry_one = HomeBlog.objects.create(blog=blog_one, display_order=1, is_featured=False, is_active=True)
        entry_two = HomeBlog.objects.create(blog=blog_two, display_order=2, is_featured=False, is_active=True)

        self.client.login(username="staff", password="pass12345")
        response = self.client.post(
            reverse("cms:blogs_manage"),
            {
                "form_type": "home_blogs",
                "home_blogs-TOTAL_FORMS": "2",
                "home_blogs-INITIAL_FORMS": "2",
                "home_blogs-MIN_NUM_FORMS": "0",
                "home_blogs-MAX_NUM_FORMS": "1000",
                "home_blogs-0-id": str(entry_one.id),
                "home_blogs-0-blog": str(blog_one.id),
                "home_blogs-0-display_order": "1",
                "home_blogs-0-is_featured": "on",
                "home_blogs-0-is_active": "on",
                "home_blogs-1-id": str(entry_two.id),
                "home_blogs-1-blog": str(blog_two.id),
                "home_blogs-1-display_order": "2",
                "home_blogs-1-is_featured": "on",
                "home_blogs-1-is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["home_blogs_formset"].non_form_errors())

    def test_staff_can_upload_editorjs_image(self):
        self.client.login(username="staff", password="pass12345")
        image_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDAT\x08\x99c``\x00\x00\x00\x04\x00\x01"
            b"\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        upload = SimpleUploadedFile("tiny.png", image_bytes, content_type="image/png")

        response = self.client.post(reverse("cms:editorjs_image_upload"), {"image": upload})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["success"], 1)
        self.assertRegex(payload["file"]["url"], r"/media/media-library/images/\d{4}/\d{2}/")

    def test_staff_can_upload_media_file(self):
        self.client.login(username="staff", password="pass12345")
        file_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        upload = SimpleUploadedFile("brief.pdf", file_bytes, content_type="application/pdf")

        response = self.client.post(reverse("cms:media_asset_upload"), {"file": upload})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["success"], 1)
        self.assertRegex(payload["file"]["url"], r"/media/media-library/files/\d{4}/\d{2}/")
        self.assertEqual(payload["asset"]["asset_type"], MediaAsset.TYPE_FILE)

    def test_staff_can_upload_media_video(self):
        self.client.login(username="staff", password="pass12345")
        video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
        upload = SimpleUploadedFile("demo.mp4", video_bytes, content_type="video/mp4")

        response = self.client.post(reverse("cms:media_asset_upload"), {"file": upload})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["success"], 1)
        self.assertEqual(payload["asset"]["asset_type"], MediaAsset.TYPE_VIDEO)
        self.assertRegex(payload["file"]["url"], r"/media/media-library/videos/\d{4}/\d{2}/")

    def test_media_library_data_endpoint_filters_assets(self):
        self.client.login(username="staff", password="pass12345")
        MediaAsset.objects.create(
            title="Quarterly Brief",
            caption="Document asset",
            original_name="brief.pdf",
            file="media-library/files/brief.pdf",
            asset_type=MediaAsset.TYPE_FILE,
        )
        MediaAsset.objects.create(
            title="Homepage Hero",
            original_name="hero.jpg",
            file="media-library/images/hero.jpg",
            asset_type=MediaAsset.TYPE_IMAGE,
        )

        response = self.client.get(reverse("cms:media_library_data"), {"type": MediaAsset.TYPE_IMAGE})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(len(payload["assets"]), 1)
        self.assertEqual(payload["assets"][0]["asset_type"], MediaAsset.TYPE_IMAGE)

    def test_staff_can_update_media_title_and_caption(self):
        self.client.login(username="staff", password="pass12345")
        asset = MediaAsset.objects.create(
            title="Old title",
            original_name="hero.jpg",
            file="media-library/images/hero.jpg",
            asset_type=MediaAsset.TYPE_IMAGE,
        )

        response = self.client.post(
            reverse("cms:media_update", args=[asset.pk]),
            {
                "title": "Homepage hero",
                "caption": "Primary banner image for the homepage.",
                "next": reverse("cms:media_manage"),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        asset.refresh_from_db()
        self.assertEqual(asset.title, "Homepage hero")
        self.assertEqual(asset.caption, "Primary banner image for the homepage.")
