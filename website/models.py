from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from pathlib import Path
from uuid import uuid4


class SeoFieldsMixin(models.Model):
    seo_meta_title = models.CharField(max_length=160, blank=True)
    seo_meta_description = models.CharField(max_length=320, blank=True)
    seo_keywords = models.CharField(max_length=255, blank=True)
    seo_canonical_url = models.URLField(blank=True)
    seo_robots = models.CharField(max_length=80, default="index,follow", blank=True)
    seo_og_title = models.CharField(max_length=160, blank=True)
    seo_og_description = models.CharField(max_length=320, blank=True)
    seo_og_image_url = models.URLField(blank=True)
    seo_twitter_card = models.CharField(max_length=40, default="summary_large_image", blank=True)
    seo_twitter_title = models.CharField(max_length=160, blank=True)
    seo_twitter_description = models.CharField(max_length=320, blank=True)
    seo_schema_json_ld = models.TextField(blank=True)

    class Meta:
        abstract = True


class AuditFieldsMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
    )

    class Meta:
        abstract = True


class SingletonModel(AuditFieldsMixin, models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class OrderedModel(AuditFieldsMixin, models.Model):
    order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True


class SiteSettings(SingletonModel):
    site_name = models.CharField(max_length=120)
    logo_text = models.CharField(max_length=120)
    logo_image_url = models.URLField(blank=True)

    topbar_email = models.EmailField()
    topbar_phone = models.CharField(max_length=40)
    topbar_location = models.CharField(max_length=180)

    quote_button_text = models.CharField(max_length=60)
    quote_button_url = models.CharField(max_length=255)

    footer_newsletter_text = models.CharField(max_length=255)
    footer_cta_title = models.CharField(max_length=120)
    footer_address_label = models.CharField(max_length=80)
    footer_address = models.CharField(max_length=255)
    footer_phone = models.CharField(max_length=40)
    footer_trust_text = models.CharField(max_length=120)
    footer_copyright_text = models.CharField(max_length=120)
    footer_policy_text = models.CharField(max_length=50)
    footer_policy_url = models.CharField(max_length=255)
    footer_terms_text = models.CharField(max_length=50)
    footer_terms_url = models.CharField(max_length=255)

    quick_action_email_url = models.CharField(max_length=255)
    quick_action_whatsapp_url = models.CharField(max_length=255)
    quick_action_contact_url = models.CharField(max_length=255)
    contact_auto_reply_message_json = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return "Site Settings"


class HomePageContent(SeoFieldsMixin, SingletonModel):
    hero_cta_text = models.CharField(max_length=60)
    hero_cta_url = models.CharField(max_length=255)
    hero_right_title = models.CharField(max_length=80)
    hero_right_subtitle = models.CharField(max_length=100)
    hero_right_description = models.TextField()

    core_badge = models.CharField(max_length=120)
    core_title = models.CharField(max_length=120)
    core_description = models.CharField(max_length=255)
    core_cta_text = models.CharField(max_length=60)
    core_cta_url = models.CharField(max_length=255)
    why_choose_badge = models.CharField(max_length=120)
    why_choose_title = models.CharField(max_length=180)
    why_choose_description = models.CharField(max_length=255)
    why_choose_image_url = models.URLField()
    why_choose_highlight_title = models.CharField(max_length=120)
    why_choose_highlight_text = models.CharField(max_length=160)

    projects_badge = models.CharField(max_length=120)
    projects_title = models.CharField(max_length=160)
    projects_button_text = models.CharField(max_length=60)
    projects_button_url = models.CharField(max_length=255)

    blogs_badge = models.CharField(max_length=120)
    blogs_title = models.CharField(max_length=180)
    blogs_button_text = models.CharField(max_length=60)
    blogs_button_url = models.CharField(max_length=255)
    testimonials_title = models.CharField(max_length=180)
    faqs_side_title = models.CharField(max_length=120)
    faqs_side_image_url = models.URLField()

    final_cta_badge = models.CharField(max_length=120)
    final_cta_title = models.CharField(max_length=180)
    final_cta_description = models.CharField(max_length=255)
    final_cta_button_text = models.CharField(max_length=60)
    final_cta_button_url = models.CharField(max_length=255)

    def __str__(self):
        return "Homepage Content"


class ServicePageContent(SeoFieldsMixin, SingletonModel):
    home_badge = models.CharField(max_length=120)
    home_title = models.CharField(max_length=180)
    home_benefit_badge = models.CharField(max_length=120)
    home_benefit_text = models.CharField(max_length=255)

    page_hero_title = models.CharField(max_length=120)
    page_hero_subtitle = models.CharField(max_length=120)
    page_intro_text = models.CharField(max_length=255)
    detail_sidebar_title = models.CharField(max_length=120)

    def __str__(self):
        return "Service Page Content"


class BlogPageContent(SeoFieldsMixin, SingletonModel):
    page_hero_title = models.CharField(max_length=120)
    page_hero_subtitle = models.CharField(max_length=120)
    page_intro_text = models.CharField(max_length=255)
    detail_sidebar_title = models.CharField(max_length=120)

    def __str__(self):
        return "Blog Page Content"


class AboutPageContent(SeoFieldsMixin, SingletonModel):
    hero_title = models.CharField(max_length=120)
    hero_image_url = models.URLField()
    intro_badge = models.CharField(max_length=120)
    intro_title = models.CharField(max_length=180)
    intro_description_primary = models.TextField()
    intro_description_secondary = models.TextField()
    intro_cta_text = models.CharField(max_length=60)
    intro_cta_url = models.CharField(max_length=255)
    collage_primary_image_url = models.URLField()
    collage_secondary_image_url = models.URLField()
    company_badge = models.CharField(max_length=120)
    company_title = models.CharField(max_length=180)
    company_description = models.TextField()
    mission_vision_badge = models.CharField(max_length=120)
    mission_vision_title = models.CharField(max_length=180)
    mission_vision_description = models.CharField(max_length=255)
    mission_card_title = models.CharField(max_length=120)
    mission_card_text = models.TextField()
    vision_card_title = models.CharField(max_length=120)
    vision_card_text = models.TextField()
    values_badge = models.CharField(max_length=120)
    values_title = models.CharField(max_length=180)
    process_badge = models.CharField(max_length=120)
    process_title = models.CharField(max_length=180)
    process_description = models.CharField(max_length=255)

    def __str__(self):
        return "About Page Content"


class ContactPageContent(SeoFieldsMixin, SingletonModel):
    hero_title = models.CharField(max_length=120)
    hero_image_url = models.URLField()
    intro_badge = models.CharField(max_length=120)
    intro_title = models.CharField(max_length=180)
    intro_description = models.TextField()
    reply_badge_text = models.CharField(max_length=120)
    privacy_badge_text = models.CharField(max_length=120)
    form_title = models.CharField(max_length=120)
    form_description = models.CharField(max_length=255)
    contact_info_email_label = models.CharField(max_length=60)
    contact_info_phone_label = models.CharField(max_length=60)
    contact_info_location_label = models.CharField(max_length=60)
    form_name_label = models.CharField(max_length=120)
    form_name_placeholder = models.CharField(max_length=255)
    form_email_label = models.CharField(max_length=120)
    form_email_placeholder = models.CharField(max_length=255)
    form_phone_label = models.CharField(max_length=120)
    form_phone_placeholder = models.CharField(max_length=255)
    form_service_label = models.CharField(max_length=120)
    form_service_placeholder = models.CharField(max_length=120)
    form_details_label = models.CharField(max_length=120)
    form_details_placeholder = models.CharField(max_length=255)
    form_submit_text = models.CharField(max_length=60)
    office_heading = models.CharField(max_length=120)
    office_country = models.CharField(max_length=120)
    office_address = models.CharField(max_length=255)
    office_phone = models.CharField(max_length=40)
    office_hours_title = models.CharField(max_length=120)
    office_hours_days = models.CharField(max_length=120)
    office_hours_time = models.CharField(max_length=120)
    office_hours_note = models.CharField(max_length=255)
    office_image_url = models.URLField()
    office_image_title = models.CharField(max_length=120)
    office_image_description = models.CharField(max_length=255)
    office_image_badge = models.CharField(max_length=60)

    def __str__(self):
        return "Contact Page Content"


class ProjectPageContent(SeoFieldsMixin, SingletonModel):
    hero_title = models.CharField(max_length=120)
    hero_image_url = models.URLField()
    intro_badge = models.CharField(max_length=120)
    intro_title = models.CharField(max_length=180)
    intro_description = models.CharField(max_length=255)
    featured_badge = models.CharField(max_length=120)
    featured_title = models.CharField(max_length=180)
    featured_description = models.TextField()
    featured_image_url = models.URLField()
    featured_stat_one_value = models.CharField(max_length=80)
    featured_stat_one_label = models.CharField(max_length=80)
    featured_stat_two_value = models.CharField(max_length=80)
    featured_stat_two_label = models.CharField(max_length=80)
    featured_stat_three_value = models.CharField(max_length=80)
    featured_stat_three_label = models.CharField(max_length=80)
    process_badge = models.CharField(max_length=120)
    process_title = models.CharField(max_length=180)
    filter_all_label = models.CharField(max_length=40)
    card_cta_text = models.CharField(max_length=60)
    empty_state_text = models.CharField(max_length=255)
    detail_back_text = models.CharField(max_length=80)
    detail_meta_title = models.CharField(max_length=120)
    detail_recent_title = models.CharField(max_length=120)
    detail_client_label = models.CharField(max_length=80)
    detail_category_label = models.CharField(max_length=80)
    detail_status_label = models.CharField(max_length=80)
    detail_tags_label = models.CharField(max_length=80)
    detail_default_client_name = models.CharField(max_length=120)
    detail_empty_recent_text = models.CharField(max_length=255)

    def __str__(self):
        return "Project Page Content"


class CareerPageContent(SeoFieldsMixin, SingletonModel):
    hero_title = models.CharField(max_length=120)
    hero_image_url = models.URLField()
    intro_badge = models.CharField(max_length=120)
    intro_title = models.CharField(max_length=180)
    intro_description = models.TextField()
    openings_badge = models.CharField(max_length=120)
    openings_title = models.CharField(max_length=180)
    cta_badge = models.CharField(max_length=120)
    cta_title = models.CharField(max_length=180)
    cta_description = models.TextField()
    cta_button_text = models.CharField(max_length=60)
    cta_button_url = models.CharField(max_length=255)
    filter_all_label = models.CharField(max_length=40)
    listing_cta_text = models.CharField(max_length=60)
    empty_state_text = models.CharField(max_length=255)
    detail_badge = models.CharField(max_length=120)
    detail_overview_title = models.CharField(max_length=120)
    detail_responsibilities_title = models.CharField(max_length=120)
    detail_responsibilities_empty_text = models.CharField(max_length=255)
    detail_requirements_title = models.CharField(max_length=120)
    detail_requirements_empty_text = models.CharField(max_length=255)
    detail_nice_to_have_title = models.CharField(max_length=120)
    detail_nice_to_have_empty_text = models.CharField(max_length=255)
    detail_sidebar_title = models.CharField(max_length=120)
    detail_department_label = models.CharField(max_length=80)
    detail_employment_label = models.CharField(max_length=80)
    detail_location_label = models.CharField(max_length=80)
    detail_experience_label = models.CharField(max_length=80)
    detail_apply_title = models.CharField(max_length=120)
    detail_apply_description = models.CharField(max_length=255)
    detail_apply_button_text = models.CharField(max_length=60)
    detail_more_openings_badge = models.CharField(max_length=120)
    detail_more_openings_title = models.CharField(max_length=180)
    detail_back_text = models.CharField(max_length=120)
    detail_other_cta_text = models.CharField(max_length=60)
    detail_other_empty_text = models.CharField(max_length=255)

    def __str__(self):
        return "Career Page Content"


class NavigationItem(AuditFieldsMixin, models.Model):
    label = models.CharField(max_length=80)
    url = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    show_in_header = models.BooleanField(default=True)
    show_in_mobile = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.label


class SocialLink(AuditFieldsMixin, models.Model):
    LOCATION_TOPBAR = "topbar"
    LOCATION_MOBILE = "mobile"
    LOCATION_FOOTER = "footer"
    LOCATION_CHOICES = [
        (LOCATION_TOPBAR, "Topbar"),
        (LOCATION_MOBILE, "Mobile menu"),
        (LOCATION_FOOTER, "Footer"),
    ]

    label = models.CharField(max_length=60)
    icon_class = models.CharField(max_length=80, help_text="Example: fa-brands fa-linkedin-in")
    url = models.CharField(max_length=255)
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["location", "order", "id"]

    def __str__(self):
        return f"{self.label} ({self.location})"


class HeroSlide(OrderedModel):
    image_url = models.URLField()
    badge = models.CharField(max_length=120)
    title = models.CharField(max_length=200)
    description = models.TextField()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.order:02d} - {self.title}"


class CoreFeature(OrderedModel):
    icon_class = models.CharField(max_length=80, default="fa-solid fa-star")
    title = models.CharField(max_length=120)
    description = models.TextField()
    cta_text = models.CharField(max_length=50, default="Read More")
    cta_url = models.CharField(max_length=255, default="#")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class WhyChooseUsItem(OrderedModel):
    icon_class = models.CharField(max_length=80, default="fa-solid fa-star")
    title = models.CharField(max_length=120)
    description = models.TextField()
    metric = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class AboutValue(OrderedModel):
    icon_class = models.CharField(max_length=80, default="fa-solid fa-star")
    title = models.CharField(max_length=120)
    description = models.TextField()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class AboutProcessStep(OrderedModel):
    label = models.CharField(max_length=60, default="Step 01")
    title = models.CharField(max_length=120)
    description = models.TextField()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Service(SeoFieldsMixin, AuditFieldsMixin, models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    icon_class = models.CharField(max_length=80, default="fa-solid fa-briefcase")
    summary = models.CharField(max_length=255)
    image_url = models.URLField()
    cta_text = models.CharField(max_length=60, default="Learn more")
    details_url = models.CharField(max_length=255, default="#")
    content_json = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["title", "id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.details_url and self.details_url != "#":
            return self.details_url
        return reverse("service_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title


class HomeService(AuditFieldsMixin, models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="home_entries")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["service"], name="unique_home_service"),
        ]

    def __str__(self):
        return f"Home Service: {self.service.title}"


class ContactSubmission(AuditFieldsMixin, models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40)
    service_interest = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_submissions",
    )
    project_details = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["is_resolved", "-created_at", "id"]

    def __str__(self):
        return f"{self.name} ({self.email})"


class Testimonial(OrderedModel):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True)
    company = models.CharField(max_length=120, blank=True)
    quote = models.TextField()
    image_url = models.URLField()
    rating = models.PositiveSmallIntegerField(default=5, validators=[MinValueValidator(1), MaxValueValidator(5)])
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class HomeTestimonial(AuditFieldsMixin, models.Model):
    testimonial = models.ForeignKey(Testimonial, on_delete=models.CASCADE, related_name="home_entries")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["testimonial"], name="unique_home_testimonial"),
        ]

    def __str__(self):
        return f"Home Testimonial: {self.testimonial.name}"


class FaqItem(OrderedModel):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.question


class HomeFaq(AuditFieldsMixin, models.Model):
    faq = models.ForeignKey(FaqItem, on_delete=models.CASCADE, related_name="home_entries")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["faq"], name="unique_home_faq"),
        ]

    def __str__(self):
        return f"Home FAQ: {self.faq.question}"


class Project(SeoFieldsMixin, AuditFieldsMixin, models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.CharField(max_length=80, default="Web App")
    summary = models.CharField(max_length=255)
    image_url = models.URLField()
    vertical_label = models.CharField(max_length=80, help_text="Vertical text shown on project card")
    tag_one = models.CharField(max_length=40, blank=True)
    tag_two = models.CharField(max_length=40, blank=True)
    client_name = models.CharField(max_length=120, blank=True)
    project_year = models.PositiveIntegerField(blank=True, null=True)
    status = models.CharField(max_length=80, default="Live")
    details_url = models.CharField(max_length=255, default="#")
    content_json = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["title", "id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.details_url and self.details_url != "#":
            return self.details_url
        return reverse("project_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title


class ProjectProcessStep(OrderedModel):
    label = models.CharField(max_length=60, default="01. Discovery")
    title = models.CharField(max_length=120)
    description = models.TextField()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class HomeProject(AuditFieldsMixin, models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="home_entries")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["project"], name="unique_home_project"),
        ]

    def __str__(self):
        return f"Home Project: {self.project.title}"


class BlogTag(AuditFieldsMixin, models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


def media_asset_upload_to(instance, filename):
    extension = Path(filename or "").suffix.lower()
    asset_folder = {
        "image": "images",
        "video": "videos",
        "file": "files",
    }.get(getattr(instance, "asset_type", "file"), "files")
    today = timezone.now()
    return f"media-library/{asset_folder}/{today.year}/{today.month:02d}/{uuid4().hex}{extension}"


class MediaAsset(AuditFieldsMixin, models.Model):
    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPE_FILE = "file"
    TYPE_CHOICES = [
        (TYPE_IMAGE, "Image"),
        (TYPE_VIDEO, "Video"),
        (TYPE_FILE, "File"),
    ]

    title = models.CharField(max_length=160, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    original_name = models.CharField(max_length=255)
    file = models.FileField(upload_to=media_asset_upload_to)
    asset_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_FILE)
    mime_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    is_optimized = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="media_assets",
    )

    class Meta:
        ordering = ["-created_at", "-id"]

    @property
    def file_url(self):
        return self.file.url if self.file else ""

    @property
    def extension(self):
        return Path(self.original_name or self.file.name or "").suffix.lower()

    def __str__(self):
        return self.title or self.original_name


class BlogPostQuerySet(models.QuerySet):
    def live(self):
        now = timezone.now()
        return self.filter(
            status=BlogPost.STATUS_PUBLISHED,
        ).filter(
            models.Q(scheduled_for__isnull=True) | models.Q(scheduled_for__lte=now)
        )


class BlogPost(SeoFieldsMixin, AuditFieldsMixin, models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending_review"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending Review"),
        (STATUS_PUBLISHED, "Published"),
    ]

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.CharField(max_length=80, default="General")
    tags = models.ManyToManyField(BlogTag, blank=True, related_name="posts")
    related_posts = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="related_to_posts",
    )
    attachment_assets = models.ManyToManyField(MediaAsset, blank=True, related_name="blog_posts")
    excerpt = models.CharField(max_length=255)
    image_url = models.URLField()
    content_json = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PUBLISHED)
    scheduled_for = models.DateTimeField(blank=True, null=True)
    published_on = models.DateField(default=timezone.now)
    comment_count = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    view_count = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    like_count = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    share_count = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    read_time_total_seconds = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    read_sessions_count = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    details_url = models.CharField(max_length=255, default="#")
    is_published = models.BooleanField(default=True)

    objects = BlogPostQuerySet.as_manager()

    class Meta:
        ordering = ["-published_on", "id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        self.is_published = self.status == self.STATUS_PUBLISHED
        if self.status == self.STATUS_PUBLISHED and not self.scheduled_for:
            self.published_on = timezone.localdate()
        elif self.scheduled_for:
            self.published_on = timezone.localtime(self.scheduled_for).date()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.details_url and self.details_url != "#":
            return self.details_url
        return reverse("blog_detail", kwargs={"slug": self.slug})

    @property
    def is_live(self):
        if self.status != self.STATUS_PUBLISHED:
            return False
        if not self.scheduled_for:
            return True
        return self.scheduled_for <= timezone.now()

    @property
    def average_read_time_seconds(self):
        if not self.read_sessions_count:
            return 0
        return round(self.read_time_total_seconds / self.read_sessions_count)

    @property
    def popularity_score(self):
        return self.view_count + (self.like_count * 3) + (self.share_count * 4) + (self.comment_count * 2)

    def __str__(self):
        return self.title


class HomeBlog(AuditFieldsMixin, models.Model):
    blog = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="home_entries")
    display_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["blog"], name="unique_home_blog"),
        ]

    def __str__(self):
        return f"Home Blog: {self.blog.title}"


class CareerBenefit(OrderedModel):
    title = models.CharField(max_length=120)
    description = models.CharField(max_length=255)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class CareerOpening(SeoFieldsMixin, AuditFieldsMixin, models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    summary = models.CharField(max_length=255)
    department = models.CharField(max_length=120, default="Engineering")
    location = models.CharField(max_length=120, default="Remote")
    employment_type = models.CharField(max_length=80, default="Full Time")
    experience_level = models.CharField(max_length=80, default="2+ years")
    hero_image_url = models.URLField(
        default="https://images.unsplash.com/photo-1517048676732-d65bc937f952?q=80&w=2200&auto=format&fit=crop"
    )
    overview = models.TextField()
    overview_json = models.JSONField(default=dict, blank=True)
    responsibilities_text = models.TextField(blank=True)
    responsibilities_json = models.JSONField(default=dict, blank=True)
    requirements_text = models.TextField(blank=True)
    requirements_json = models.JSONField(default=dict, blank=True)
    nice_to_have_text = models.TextField(blank=True)
    nice_to_have_json = models.JSONField(default=dict, blank=True)
    apply_url = models.CharField(max_length=255, default="mailto:hello@jstechnova.com")
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "title", "id"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("career_detail", kwargs={"slug": self.slug})

    @staticmethod
    def _split_lines(value):
        return [line.strip() for line in (value or "").splitlines() if line.strip()]

    @property
    def responsibilities(self):
        return self._split_lines(self.responsibilities_text)

    @property
    def requirements(self):
        return self._split_lines(self.requirements_text)

    @property
    def nice_to_have(self):
        return self._split_lines(self.nice_to_have_text)

    @staticmethod
    def _paragraph_content(value):
        if not value:
            return {"blocks": []}
        return {"blocks": [{"type": "paragraph", "data": {"text": value}}]}

    @staticmethod
    def _list_content(values):
        items = [item for item in values if item]
        if not items:
            return {"blocks": []}
        return {"blocks": [{"type": "list", "data": {"style": "unordered", "items": items}}]}

    @property
    def overview_content(self):
        payload = self.overview_json or {}
        if payload.get("blocks"):
            return payload
        return self._paragraph_content(self.overview)

    @property
    def responsibilities_content(self):
        payload = self.responsibilities_json or {}
        if payload.get("blocks"):
            return payload
        return self._list_content(self.responsibilities)

    @property
    def requirements_content(self):
        payload = self.requirements_json or {}
        if payload.get("blocks"):
            return payload
        return self._list_content(self.requirements)

    @property
    def nice_to_have_content(self):
        payload = self.nice_to_have_json or {}
        if payload.get("blocks"):
            return payload
        return self._list_content(self.nice_to_have)

    def __str__(self):
        return self.title


class AuditLog(models.Model):
    ACTION_CREATE = "create"
    ACTION_UPDATE = "update"
    ACTION_DELETE = "delete"
    ACTION_CHOICES = [
        (ACTION_CREATE, "Create"),
        (ACTION_UPDATE, "Update"),
        (ACTION_DELETE, "Delete"),
    ]

    action = models.CharField(max_length=12, choices=ACTION_CHOICES)
    model_label = models.CharField(max_length=120)
    object_pk = models.CharField(max_length=64)
    object_repr = models.CharField(max_length=255)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="website_audit_logs",
    )
    actor_username = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_action_display()} {self.model_label} #{self.object_pk}"
