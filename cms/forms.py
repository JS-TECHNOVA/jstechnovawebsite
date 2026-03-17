import json
from urllib.parse import urlparse

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.forms import BaseModelFormSet, modelformset_factory
from django.utils.html import strip_tags
from django.utils.text import slugify

from website.models import (
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
    FeedbackPageContent,
    FeedbackSubmission,
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
    PrivacyPolicyPageContent,
    Project,
    ProjectPageContent,
    ProjectProcessStep,
    Service,
    ServicePageContent,
    SiteSettings,
    SocialLink,
    Testimonial,
    TermsAndConditionsPageContent,
    WhyChooseUsItem,
)

UserModel = get_user_model()

INPUT_CLASS = (
    "min-w-0 max-w-full w-full rounded-[20px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 "
    "shadow-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
)
TEXTAREA_CLASS = (
    "min-w-0 max-w-full min-h-[120px] w-full rounded-[20px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 "
    "shadow-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
)
SELECT_CLASS = (
    "min-w-0 max-w-full w-full rounded-[20px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 "
    "shadow-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
)
CHECKBOX_CLASS = "h-5 w-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
SEO_FIELD_NAMES = [
    "seo_meta_title",
    "seo_meta_description",
    "seo_keywords",
    "seo_canonical_url",
    "seo_robots",
    "seo_og_title",
    "seo_og_description",
    "seo_og_image_url",
    "seo_twitter_card",
    "seo_twitter_title",
    "seo_twitter_description",
    "seo_schema_json_ld",
]
MEDIA_PICKER_FIELD_TYPES = {
    "logo_image_url": "image",
    "image_url": "image",
    "hero_image_url": "image",
    "featured_image_url": "image",
    "office_image_url": "image",
    "collage_primary_image_url": "image",
    "collage_secondary_image_url": "image",
    "faqs_side_image_url": "image",
    "seo_og_image_url": "image",
}


def _clean_editor_payload(raw):
    if isinstance(raw, dict):
        payload = raw
    else:
        raw = raw or "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationError("Invalid Editor.js JSON payload.") from exc
    if not isinstance(payload, dict):
        raise ValidationError("Content must be a JSON object.")
    payload.setdefault("blocks", [])
    return _sanitize_editor_payload(payload)


def _clean_plain_text(value, *, max_length=None):
    text = strip_tags(str(value or "")).replace("\x00", "").strip()
    if max_length is not None:
        text = text[:max_length]
    return text


def _clean_editor_url(value):
    url = str(value or "").strip()
    if not url:
        return ""
    if url.startswith("/"):
        return url
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return url
    return ""


def _sanitize_list_items(items):
    sanitized = []
    for item in items or []:
        if isinstance(item, dict):
            content = _clean_plain_text(item.get("content"), max_length=4000)
            if content:
                sanitized.append({"content": content})
        else:
            content = _clean_plain_text(item, max_length=4000)
            if content:
                sanitized.append(content)
    return sanitized


def _sanitize_checklist_items(items):
    sanitized = []
    for item in items or []:
        text = _clean_plain_text((item or {}).get("text"), max_length=4000)
        if text:
            sanitized.append(
                {
                    "text": text,
                    "checked": bool((item or {}).get("checked")),
                }
            )
    return sanitized


def _sanitize_table_rows(rows):
    sanitized_rows = []
    for row in rows or []:
        cleaned_row = []
        for cell in row or []:
            cleaned_cell = _clean_plain_text(cell, max_length=4000)
            if cleaned_cell:
                cleaned_row.append(cleaned_cell)
        if cleaned_row:
            sanitized_rows.append(cleaned_row)
    return sanitized_rows


def _sanitize_editor_payload(payload):
    sanitized_blocks = []
    for block in payload.get("blocks", []):
        block_type = str((block or {}).get("type") or "").strip()
        data = (block or {}).get("data", {}) or {}
        clean_data = None

        if block_type == "header":
            text = _clean_plain_text(data.get("text"), max_length=4000)
            level = data.get("level", 2)
            if text:
                if not isinstance(level, int) or level < 1 or level > 6:
                    level = 2
                clean_data = {"text": text, "level": level}
        elif block_type == "paragraph":
            text = _clean_plain_text(data.get("text"), max_length=10000)
            if text:
                clean_data = {"text": text}
        elif block_type == "list":
            items = _sanitize_list_items(data.get("items", []))
            if items:
                style = "ordered" if data.get("style") == "ordered" else "unordered"
                clean_data = {"style": style, "items": items}
        elif block_type == "quote":
            text = _clean_plain_text(data.get("text"), max_length=6000)
            caption = _clean_plain_text(data.get("caption"), max_length=255)
            if text:
                clean_data = {"text": text, "caption": caption}
        elif block_type == "delimiter":
            clean_data = {}
        elif block_type == "code":
            code = str(data.get("code", "")).replace("\x00", "").strip()
            if code:
                clean_data = {"code": code[:20000]}
        elif block_type == "checklist":
            items = _sanitize_checklist_items(data.get("items", []))
            if items:
                clean_data = {"items": items}
        elif block_type == "table":
            rows = _sanitize_table_rows(data.get("content", []))
            if rows:
                clean_data = {"content": rows}
        elif block_type == "image":
            url = _clean_editor_url((data.get("file") or {}).get("url") or data.get("url"))
            caption = _clean_plain_text(data.get("caption"), max_length=255)
            if url:
                clean_data = {
                    "file": {"url": url},
                    "caption": caption,
                }
        elif block_type == "embed":
            source = _clean_editor_url(data.get("source"))
            embed = _clean_editor_url(data.get("embed"))
            service = _clean_plain_text(data.get("service"), max_length=60)
            caption = _clean_plain_text(data.get("caption"), max_length=255)
            if source or embed:
                clean_data = {
                    "source": source,
                    "embed": embed,
                    "service": service,
                    "caption": caption,
                }

        if clean_data is not None:
            sanitized_blocks.append({"type": block_type, "data": clean_data})

    return {"blocks": sanitized_blocks}


def _editorjs_to_text(payload):
    if not isinstance(payload, dict):
        return ""

    lines = []
    for block in payload.get("blocks", []):
        block_type = (block or {}).get("type")
        data = (block or {}).get("data", {}) or {}
        if block_type in {"paragraph", "header", "quote"}:
            text = strip_tags(str(data.get("text", "")).strip())
            if text:
                lines.append(text)
        elif block_type == "list":
            for item in data.get("items", []):
                if isinstance(item, dict):
                    text = strip_tags(str(item.get("content", "")).strip())
                else:
                    text = strip_tags(str(item).strip())
                if text:
                    lines.append(text)
        elif block_type == "checklist":
            for item in data.get("items", []):
                text = strip_tags(str((item or {}).get("text", "")).strip())
                if text:
                    lines.append(text)
        elif block_type == "table":
            for row in data.get("content", []):
                if row:
                    lines.append(" | ".join(strip_tags(str(cell).strip()) for cell in row if strip_tags(str(cell).strip())))
        elif block_type == "code":
            text = str(data.get("code", "")).strip()
            if text:
                lines.append(text)
    return "\n".join(lines)


class StyledModelForm(forms.ModelForm):
    media_picker_fields = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        picker_fields = {**MEDIA_PICKER_FIELD_TYPES, **getattr(self, "media_picker_fields", {})}
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = CHECKBOX_CLASS
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = TEXTAREA_CLASS
                widget.attrs.setdefault("rows", 3)
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = SELECT_CLASS
            elif isinstance(widget, forms.DateInput):
                widget.attrs["class"] = INPUT_CLASS
                widget.attrs["type"] = "date"
            else:
                widget.attrs["class"] = INPUT_CLASS

            picker_types = picker_fields.get(field_name)
            if picker_types and isinstance(widget, (forms.URLInput, forms.TextInput)):
                widget.attrs["data-media-picker"] = "true"
                widget.attrs["data-media-types"] = picker_types
                widget.attrs["data-media-picker-label"] = field.label


class JsonEditorFormMixin:
    json_field_name = "content_json"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["details_url"].required = False
        json_field = self.fields[self.json_field_name]
        json_field.widget = forms.HiddenInput()
        if self.instance and self.instance.pk:
            json_field.initial = json.dumps(getattr(self.instance, self.json_field_name) or {"blocks": []})

    def clean_content_json(self):
        return _clean_editor_payload(self.cleaned_data.get("content_json"))

    def clean_details_url(self):
        return self.cleaned_data.get("details_url") or "#"


class SiteSettingsForm(StyledModelForm):
    editor_json_fields = ["contact_auto_reply_message_json"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.editor_json_fields:
            self.fields[field_name].widget = forms.HiddenInput()
            initial_value = {"blocks": []}
            if self.instance and self.instance.pk:
                initial_value = getattr(self.instance, field_name) or {"blocks": []}
            self.fields[field_name].initial = json.dumps(initial_value)

    def clean_contact_auto_reply_message_json(self):
        return _clean_editor_payload(self.cleaned_data.get("contact_auto_reply_message_json"))

    class Meta:
        model = SiteSettings
        fields = [
            "site_name",
            "logo_text",
            "logo_image_url",
            "topbar_email",
            "topbar_phone",
            "topbar_location",
            "quote_button_text",
            "quote_button_url",
            "footer_newsletter_text",
            "footer_cta_title",
            "footer_address_label",
            "footer_address",
            "footer_phone",
            "footer_quick_links_title",
            "footer_trust_text",
            "footer_copyright_text",
            "quick_action_email_url",
            "quick_action_whatsapp_url",
            "quick_action_contact_url",
            "contact_auto_reply_message_json",
        ]


class SingletonEditorContentForm(StyledModelForm):
    editor_json_fields = ["content_json"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.editor_json_fields:
            self.fields[field_name].widget = forms.HiddenInput()
            initial_value = {"blocks": []}
            if self.instance and self.instance.pk:
                initial_value = getattr(self.instance, field_name) or {"blocks": []}
            self.fields[field_name].initial = json.dumps(initial_value)

    def clean_content_json(self):
        return _clean_editor_payload(self.cleaned_data.get("content_json"))


class FooterLinkSettingsForm(StyledModelForm):
    class Meta:
        model = SiteSettings
        fields = ["footer_quick_links_title"]


class HomePageContentForm(StyledModelForm):
    class Meta:
        model = HomePageContent
        fields = [
            "hero_cta_text",
            "hero_cta_url",
            "hero_right_title",
            "hero_right_subtitle",
            "hero_right_description",
            "core_badge",
            "core_title",
            "core_description",
            "core_cta_text",
            "core_cta_url",
            "why_choose_badge",
            "why_choose_title",
            "why_choose_description",
            "why_choose_image_url",
            "why_choose_highlight_title",
            "why_choose_highlight_text",
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
            "final_cta_badge",
            "final_cta_title",
            "final_cta_description",
            "final_cta_button_text",
            "final_cta_button_url",
        ] + SEO_FIELD_NAMES


class ServicePageContentForm(StyledModelForm):
    class Meta:
        model = ServicePageContent
        fields = [
            "home_badge",
            "home_title",
            "home_benefit_badge",
            "home_benefit_text",
            "page_hero_title",
            "page_hero_subtitle",
            "page_intro_text",
            "detail_sidebar_title",
        ] + SEO_FIELD_NAMES


class BlogPageContentForm(StyledModelForm):
    class Meta:
        model = BlogPageContent
        fields = [
            "page_hero_title",
            "page_hero_subtitle",
            "page_intro_text",
            "detail_sidebar_title",
        ] + SEO_FIELD_NAMES


class AboutPageContentForm(StyledModelForm):
    class Meta:
        model = AboutPageContent
        fields = [
            "hero_title",
            "hero_image_url",
            "intro_badge",
            "intro_title",
            "intro_description_primary",
            "intro_description_secondary",
            "intro_cta_text",
            "intro_cta_url",
            "collage_primary_image_url",
            "collage_secondary_image_url",
            "company_badge",
            "company_title",
            "company_description",
            "mission_vision_badge",
            "mission_vision_title",
            "mission_vision_description",
            "mission_card_title",
            "mission_card_text",
            "vision_card_title",
            "vision_card_text",
            "values_badge",
            "values_title",
            "process_badge",
            "process_title",
            "process_description",
        ] + SEO_FIELD_NAMES


class ContactPageContentForm(StyledModelForm):
    class Meta:
        model = ContactPageContent
        fields = [
            "hero_title",
            "hero_image_url",
            "intro_badge",
            "intro_title",
            "intro_description",
            "reply_badge_text",
            "privacy_badge_text",
            "form_title",
            "form_description",
            "contact_info_email_label",
            "contact_info_phone_label",
            "contact_info_location_label",
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
            "form_submit_text",
            "office_heading",
            "office_country",
            "office_address",
            "office_phone",
            "office_hours_title",
            "office_hours_days",
            "office_hours_time",
            "office_hours_note",
            "office_image_url",
            "office_image_title",
            "office_image_description",
            "office_image_badge",
        ] + SEO_FIELD_NAMES


class FeedbackPageContentForm(StyledModelForm):
    class Meta:
        model = FeedbackPageContent
        fields = [
            "hero_badge",
            "hero_title",
            "hero_description",
            "mood_question",
            "rating_prompt",
            "image_prompt",
            "image_help_text",
            "name_label",
            "name_placeholder",
            "email_label",
            "email_placeholder",
            "message_label",
            "message_placeholder",
            "submit_text",
            "success_message",
            "privacy_note",
        ] + SEO_FIELD_NAMES


class PrivacyPolicyPageContentForm(SingletonEditorContentForm):
    class Meta:
        model = PrivacyPolicyPageContent
        fields = [
            "hero_badge",
            "hero_title",
            "intro_text",
            "content_json",
        ] + SEO_FIELD_NAMES


class TermsAndConditionsPageContentForm(SingletonEditorContentForm):
    class Meta:
        model = TermsAndConditionsPageContent
        fields = [
            "hero_badge",
            "hero_title",
            "intro_text",
            "content_json",
        ] + SEO_FIELD_NAMES


class ProjectPageContentForm(StyledModelForm):
    class Meta:
        model = ProjectPageContent
        fields = [
            "hero_title",
            "hero_image_url",
            "intro_badge",
            "intro_title",
            "intro_description",
            "featured_badge",
            "featured_title",
            "featured_description",
            "featured_image_url",
            "featured_stat_one_value",
            "featured_stat_one_label",
            "featured_stat_two_value",
            "featured_stat_two_label",
            "featured_stat_three_value",
            "featured_stat_three_label",
            "process_badge",
            "process_title",
            "filter_all_label",
            "card_cta_text",
            "empty_state_text",
            "detail_back_text",
            "detail_meta_title",
            "detail_recent_title",
            "detail_client_label",
            "detail_category_label",
            "detail_status_label",
            "detail_tags_label",
            "detail_default_client_name",
            "detail_empty_recent_text",
        ] + SEO_FIELD_NAMES


class CareerPageContentForm(StyledModelForm):
    class Meta:
        model = CareerPageContent
        fields = [
            "hero_title",
            "hero_image_url",
            "intro_badge",
            "intro_title",
            "intro_description",
            "openings_badge",
            "openings_title",
            "cta_badge",
            "cta_title",
            "cta_description",
            "cta_button_text",
            "cta_button_url",
            "filter_all_label",
            "listing_cta_text",
            "empty_state_text",
            "detail_badge",
        ] + SEO_FIELD_NAMES


class HeroSlideForm(StyledModelForm):
    class Meta:
        model = HeroSlide
        fields = ["order", "image_url", "badge", "title", "description"]


class CoreFeatureForm(StyledModelForm):
    class Meta:
        model = CoreFeature
        fields = ["order", "icon_class", "title", "description", "cta_text", "cta_url"]


class WhyChooseUsItemForm(StyledModelForm):
    class Meta:
        model = WhyChooseUsItem
        fields = ["order", "icon_class", "title", "description", "metric"]


class NavigationItemForm(StyledModelForm):
    class Meta:
        model = NavigationItem
        fields = ["label", "url", "order", "is_active", "show_in_header", "show_in_mobile"]


class SocialLinkForm(StyledModelForm):
    class Meta:
        model = SocialLink
        fields = ["label", "icon_class", "url", "location", "order", "is_active"]


class BaseFooterLinkForm(StyledModelForm):
    fixed_section = ""

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.section = self.fixed_section
        if commit:
            instance.save()
        return instance


class QuickFooterLinkForm(BaseFooterLinkForm):
    fixed_section = FooterLink.SECTION_QUICK

    class Meta:
        model = FooterLink
        fields = ["label", "url", "order", "is_active"]


class BottomFooterLinkForm(BaseFooterLinkForm):
    fixed_section = FooterLink.SECTION_BOTTOM

    class Meta:
        model = FooterLink
        fields = ["label", "url", "order", "is_active"]


class AboutValueForm(StyledModelForm):
    class Meta:
        model = AboutValue
        fields = ["order", "icon_class", "title", "description"]


class AboutProcessStepForm(StyledModelForm):
    class Meta:
        model = AboutProcessStep
        fields = ["order", "label", "title", "description"]


class ProjectProcessStepForm(StyledModelForm):
    class Meta:
        model = ProjectProcessStep
        fields = ["order", "label", "title", "description"]


class CareerBenefitForm(StyledModelForm):
    class Meta:
        model = CareerBenefit
        fields = ["order", "title", "description"]


class ProjectEditorForm(JsonEditorFormMixin, StyledModelForm):
    class Meta:
        model = Project
        fields = [
            "title",
            "slug",
            "category",
            "summary",
            "image_url",
            "vertical_label",
            "tag_one",
            "tag_two",
            "client_name",
            "project_year",
            "status",
            "details_url",
            "content_json",
            "is_published",
        ] + SEO_FIELD_NAMES


class ServiceEditorForm(JsonEditorFormMixin, StyledModelForm):
    class Meta:
        model = Service
        fields = [
            "title",
            "slug",
            "icon_class",
            "summary",
            "image_url",
            "cta_text",
            "details_url",
            "content_json",
            "is_published",
        ] + SEO_FIELD_NAMES


class BlogEditorForm(JsonEditorFormMixin, StyledModelForm):
    tag_names = forms.CharField(required=False, help_text="Comma-separated tags such as AI, Product, Growth.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["tag_names"].initial = ", ".join(self.instance.tags.values_list("name", flat=True))
            self.fields["related_posts"].queryset = BlogPost.objects.exclude(pk=self.instance.pk).order_by("-published_on", "title")
        else:
            self.fields["related_posts"].queryset = BlogPost.objects.order_by("-published_on", "title")
        self.fields["attachment_assets"].queryset = MediaAsset.objects.order_by("-created_at")
        self.fields["attachment_assets"].required = False
        self.fields["related_posts"].required = False
        self.fields["status"].required = False
        self.fields["status"].initial = self.instance.status if self.instance and self.instance.pk else BlogPost.STATUS_PUBLISHED
        self.fields["scheduled_for"].required = False
        self.fields["published_on"].required = False
        self.fields["comment_count"].required = False
        self.fields["comment_count"].initial = self.instance.comment_count if self.instance and self.instance.pk else 0
        self.fields["scheduled_for"].input_formats = ["%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]
        self.fields["scheduled_for"].widget = forms.DateTimeInput(
            attrs={"type": "datetime-local", "class": INPUT_CLASS},
            format="%Y-%m-%dT%H:%M",
        )
        if self.instance and self.instance.pk and self.instance.scheduled_for:
            self.initial["scheduled_for"] = self.instance.scheduled_for.strftime("%Y-%m-%dT%H:%M")

    def clean_tag_names(self):
        raw = self.cleaned_data.get("tag_names", "")
        names = []
        for part in raw.split(","):
            name = part.strip()
            if name and name.lower() not in {item.lower() for item in names}:
                names.append(name)
        return names

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("status"):
            cleaned_data["status"] = (
                BlogPost.STATUS_PUBLISHED if cleaned_data.get("is_published") else BlogPost.STATUS_DRAFT
            )
        if cleaned_data.get("comment_count") in (None, ""):
            cleaned_data["comment_count"] = 0
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)
        tags = [BlogTag.objects.get_or_create(name=name, defaults={"slug": slugify(name)})[0] for name in self.cleaned_data.get("tag_names", [])]
        if commit:
            instance.tags.set(tags)
            self.save_m2m()
        else:
            self._pending_tags = tags
        return instance

    def save_m2m(self):
        self._save_m2m()
        pending_tags = getattr(self, "_pending_tags", None)
        if pending_tags is not None:
            self.instance.tags.set(pending_tags)
            del self._pending_tags

    class Meta:
        model = BlogPost
        fields = [
            "title",
            "slug",
            "category",
            "tag_names",
            "related_posts",
            "attachment_assets",
            "excerpt",
            "image_url",
            "status",
            "scheduled_for",
            "published_on",
            "comment_count",
            "details_url",
            "content_json",
            "is_published",
        ] + SEO_FIELD_NAMES


class CareerOpeningForm(StyledModelForm):
    editor_json_fields = [
        "overview_json",
        "responsibilities_json",
        "requirements_json",
        "nice_to_have_json",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ["overview", "responsibilities_text", "requirements_text", "nice_to_have_text"]:
            self.fields[field_name].widget = forms.HiddenInput()
            self.fields[field_name].required = False
        for field_name in self.editor_json_fields:
            self.fields[field_name].widget = forms.HiddenInput()
            if self.instance and self.instance.pk:
                self.fields[field_name].initial = json.dumps(getattr(self.instance, field_name) or {"blocks": []})

    def clean_overview_json(self):
        return _clean_editor_payload(self.cleaned_data.get("overview_json"))

    def clean_responsibilities_json(self):
        return _clean_editor_payload(self.cleaned_data.get("responsibilities_json"))

    def clean_requirements_json(self):
        return _clean_editor_payload(self.cleaned_data.get("requirements_json"))

    def clean_nice_to_have_json(self):
        return _clean_editor_payload(self.cleaned_data.get("nice_to_have_json"))

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["overview"] = _editorjs_to_text(cleaned_data.get("overview_json"))
        cleaned_data["responsibilities_text"] = _editorjs_to_text(cleaned_data.get("responsibilities_json"))
        cleaned_data["requirements_text"] = _editorjs_to_text(cleaned_data.get("requirements_json"))
        cleaned_data["nice_to_have_text"] = _editorjs_to_text(cleaned_data.get("nice_to_have_json"))
        return cleaned_data

    class Meta:
        model = CareerOpening
        fields = [
            "title",
            "slug",
            "order",
            "summary",
            "department",
            "location",
            "employment_type",
            "experience_level",
            "hero_image_url",
            "overview",
            "overview_json",
            "responsibilities_text",
            "responsibilities_json",
            "requirements_text",
            "requirements_json",
            "nice_to_have_text",
            "nice_to_have_json",
            "apply_url",
            "is_published",
        ] + SEO_FIELD_NAMES


class HomeProjectForm(StyledModelForm):
    class Meta:
        model = HomeProject
        fields = ["project", "display_order", "is_active"]


class HomeServiceForm(StyledModelForm):
    class Meta:
        model = HomeService
        fields = ["service", "display_order", "is_active"]


class HomeBlogForm(StyledModelForm):
    class Meta:
        model = HomeBlog
        fields = ["blog", "display_order", "is_featured", "is_active"]


class HomeBlogBaseFormSet(BaseModelFormSet):
    def clean(self):
        super().clean()
        featured_count = 0
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data:
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            if form.cleaned_data.get("is_active") and form.cleaned_data.get("is_featured"):
                featured_count += 1
        if featured_count > 1:
            raise ValidationError("Only one active featured blog can be selected for the homepage.")


class TestimonialForm(StyledModelForm):
    class Meta:
        model = Testimonial
        fields = ["order", "name", "role", "company", "quote", "image_url", "rating", "is_published"]


class HomeTestimonialForm(StyledModelForm):
    class Meta:
        model = HomeTestimonial
        fields = ["testimonial", "display_order", "is_active"]


class FaqItemForm(StyledModelForm):
    class Meta:
        model = FaqItem
        fields = ["order", "question", "answer", "is_published"]


class HomeFaqForm(StyledModelForm):
    class Meta:
        model = HomeFaq
        fields = ["faq", "display_order", "is_active"]


class CmsUserCreateForm(StyledModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput())
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = Group.objects.order_by("name")
        self.fields["user_permissions"].queryset = Permission.objects.filter(
            content_type__app_label__in=["website", "auth"]
        ).select_related("content_type").order_by("content_type__app_label", "content_type__model", "codename")
        self.fields["groups"].widget.attrs["size"] = 8
        self.fields["user_permissions"].widget.attrs["size"] = 14

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.set_password(self.cleaned_data["password1"])
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    class Meta:
        model = UserModel
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "groups",
            "user_permissions",
        ]


class CmsUserUpdateForm(StyledModelForm):
    new_password1 = forms.CharField(label="New password", widget=forms.PasswordInput(), required=False)
    new_password2 = forms.CharField(label="Confirm new password", widget=forms.PasswordInput(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["groups"].queryset = Group.objects.order_by("name")
        self.fields["user_permissions"].queryset = Permission.objects.filter(
            content_type__app_label__in=["website", "auth"]
        ).select_related("content_type").order_by("content_type__app_label", "content_type__model", "codename")
        self.fields["groups"].widget.attrs["size"] = 8
        self.fields["user_permissions"].widget.attrs["size"] = 14

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")
        if password1 or password2:
            if password1 != password2:
                self.add_error("new_password2", "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password1")
        if new_password:
            instance.set_password(new_password)
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    class Meta:
        model = UserModel
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_active",
            "groups",
            "user_permissions",
        ]


HeroSlideFormSet = modelformset_factory(HeroSlide, form=HeroSlideForm, extra=1, can_delete=True)
CoreFeatureFormSet = modelformset_factory(CoreFeature, form=CoreFeatureForm, extra=1, can_delete=True)
WhyChooseUsItemFormSet = modelformset_factory(WhyChooseUsItem, form=WhyChooseUsItemForm, extra=1, can_delete=True)
NavigationItemFormSet = modelformset_factory(NavigationItem, form=NavigationItemForm, extra=1, can_delete=True)
SocialLinkFormSet = modelformset_factory(SocialLink, form=SocialLinkForm, extra=1, can_delete=True)
QuickFooterLinkFormSet = modelformset_factory(FooterLink, form=QuickFooterLinkForm, extra=1, can_delete=True)
BottomFooterLinkFormSet = modelformset_factory(FooterLink, form=BottomFooterLinkForm, extra=1, can_delete=True)
AboutValueFormSet = modelformset_factory(AboutValue, form=AboutValueForm, extra=1, can_delete=True)
AboutProcessStepFormSet = modelformset_factory(AboutProcessStep, form=AboutProcessStepForm, extra=1, can_delete=True)
ProjectProcessStepFormSet = modelformset_factory(ProjectProcessStep, form=ProjectProcessStepForm, extra=1, can_delete=True)
CareerBenefitFormSet = modelformset_factory(CareerBenefit, form=CareerBenefitForm, extra=1, can_delete=True)
HomeProjectFormSet = modelformset_factory(HomeProject, form=HomeProjectForm, extra=1, can_delete=True)
HomeServiceFormSet = modelformset_factory(HomeService, form=HomeServiceForm, extra=1, can_delete=True)
HomeTestimonialFormSet = modelformset_factory(HomeTestimonial, form=HomeTestimonialForm, extra=1, can_delete=True)
HomeFaqFormSet = modelformset_factory(HomeFaq, form=HomeFaqForm, extra=1, can_delete=True)
HomeBlogFormSet = modelformset_factory(
    HomeBlog,
    form=HomeBlogForm,
    extra=1,
    can_delete=True,
    formset=HomeBlogBaseFormSet,
)
