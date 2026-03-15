from django.contrib import admin

from .models import (
    AboutPageContent,
    AboutProcessStep,
    AboutValue,
    AuditLog,
    BlogPageContent,
    BlogPost,
    CareerBenefit,
    CareerOpening,
    CareerPageContent,
    ContactPageContent,
    ContactSubmission,
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


class SingletonAdmin(admin.ModelAdmin):
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")

    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonAdmin):
    pass


@admin.register(HomePageContent)
class HomePageContentAdmin(SingletonAdmin):
    pass


@admin.register(ServicePageContent)
class ServicePageContentAdmin(SingletonAdmin):
    pass


@admin.register(BlogPageContent)
class BlogPageContentAdmin(SingletonAdmin):
    pass


@admin.register(AboutPageContent)
class AboutPageContentAdmin(SingletonAdmin):
    pass


@admin.register(ContactPageContent)
class ContactPageContentAdmin(SingletonAdmin):
    pass


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "service_interest", "is_resolved", "created_at", "updated_at")
    list_filter = ("is_resolved", "service_interest")
    search_fields = ("name", "email", "phone", "project_details")
    autocomplete_fields = ("service_interest",)
    ordering = ("is_resolved", "-created_at", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(ProjectPageContent)
class ProjectPageContentAdmin(SingletonAdmin):
    pass


@admin.register(CareerPageContent)
class CareerPageContentAdmin(SingletonAdmin):
    pass


@admin.register(NavigationItem)
class NavigationItemAdmin(admin.ModelAdmin):
    list_display = ("label", "url", "order", "is_active", "show_in_header", "show_in_mobile", "updated_at")
    list_filter = ("is_active", "show_in_header", "show_in_mobile")
    search_fields = ("label", "url")
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(SocialLink)
class SocialLinkAdmin(admin.ModelAdmin):
    list_display = ("label", "location", "order", "is_active", "updated_at")
    list_filter = ("location", "is_active")
    search_fields = ("label", "url", "icon_class")
    ordering = ("location", "order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(HeroSlide)
class HeroSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "updated_at")
    search_fields = ("title", "badge")
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(CoreFeature)
class CoreFeatureAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "updated_at")
    search_fields = ("title",)
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(WhyChooseUsItem)
class WhyChooseUsItemAdmin(admin.ModelAdmin):
    list_display = ("title", "metric", "order", "updated_at")
    search_fields = ("title", "description", "metric")
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(AboutValue)
class AboutValueAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "updated_at")
    search_fields = ("title",)
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(AboutProcessStep)
class AboutProcessStepAdmin(admin.ModelAdmin):
    list_display = ("label", "title", "order", "updated_at")
    search_fields = ("label", "title")
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "updated_at", "updated_by")
    list_filter = ("is_published",)
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(HomeService)
class HomeServiceAdmin(admin.ModelAdmin):
    list_display = ("service", "display_order", "is_active", "updated_at")
    list_filter = ("is_active",)
    autocomplete_fields = ("service",)
    ordering = ("display_order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "company", "rating", "is_published", "order", "updated_at")
    list_filter = ("is_published", "rating")
    search_fields = ("name", "role", "company", "quote")
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(HomeTestimonial)
class HomeTestimonialAdmin(admin.ModelAdmin):
    list_display = ("testimonial", "display_order", "is_active", "updated_at")
    list_filter = ("is_active",)
    autocomplete_fields = ("testimonial",)
    ordering = ("display_order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(FaqItem)
class FaqItemAdmin(admin.ModelAdmin):
    list_display = ("question", "is_published", "order", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("question", "answer")
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(HomeFaq)
class HomeFaqAdmin(admin.ModelAdmin):
    list_display = ("faq", "display_order", "is_active", "updated_at")
    list_filter = ("is_active",)
    autocomplete_fields = ("faq",)
    ordering = ("display_order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "project_year", "is_published", "updated_at", "updated_by")
    list_filter = ("category", "status", "is_published")
    search_fields = ("title", "summary", "tag_one", "tag_two", "client_name")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(HomeProject)
class HomeProjectAdmin(admin.ModelAdmin):
    list_display = ("project", "display_order", "is_active", "updated_at")
    list_filter = ("is_active",)
    autocomplete_fields = ("project",)
    ordering = ("display_order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(ProjectProcessStep)
class ProjectProcessStepAdmin(admin.ModelAdmin):
    list_display = ("label", "title", "order", "updated_at")
    search_fields = ("label", "title")
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "published_on", "is_published", "updated_at", "updated_by")
    list_filter = ("category", "is_published")
    search_fields = ("title", "excerpt", "category")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-published_on", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("title", "caption", "original_name", "asset_type", "file_size", "is_optimized", "uploaded_by", "created_at")
    list_filter = ("asset_type", "is_optimized", "created_at")
    search_fields = ("title", "caption", "original_name", "mime_type")
    readonly_fields = ("file_size", "mime_type", "width", "height", "created_at", "updated_at", "created_by", "updated_by")
    ordering = ("-created_at", "-id")


@admin.register(HomeBlog)
class HomeBlogAdmin(admin.ModelAdmin):
    list_display = ("blog", "display_order", "is_featured", "is_active", "updated_at")
    list_filter = ("is_featured", "is_active")
    autocomplete_fields = ("blog",)
    ordering = ("display_order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(CareerBenefit)
class CareerBenefitAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "updated_at")
    search_fields = ("title",)
    ordering = ("order", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(CareerOpening)
class CareerOpeningAdmin(admin.ModelAdmin):
    list_display = ("title", "department", "location", "employment_type", "is_published", "updated_at", "updated_by")
    list_filter = ("department", "location", "employment_type", "is_published")
    search_fields = ("title", "summary", "department", "location")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("order", "title", "id")
    readonly_fields = ("created_at", "updated_at", "created_by", "updated_by")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "model_label", "object_repr", "actor_username")
    list_filter = ("action", "model_label", "created_at")
    search_fields = ("model_label", "object_repr", "actor_username", "object_pk")
    readonly_fields = ("created_at", "action", "model_label", "object_pk", "object_repr", "actor", "actor_username", "details")
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
