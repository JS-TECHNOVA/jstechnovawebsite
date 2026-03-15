from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import (
    AboutPageContent,
    BlogPageContent,
    BlogPost,
    CareerOpening,
    CareerPageContent,
    ContactPageContent,
    HomePageContent,
    Project,
    ProjectPageContent,
    Service,
    ServicePageContent,
)


STATIC_VIEW_MODELS = {
    "home": HomePageContent,
    "about": AboutPageContent,
    "services": ServicePageContent,
    "projects": ProjectPageContent,
    "blogs": BlogPageContent,
    "contact": ContactPageContent,
    "careers": CareerPageContent,
}


class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ["home", "about", "services", "projects", "blogs", "contact", "careers"]

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        model = STATIC_VIEW_MODELS.get(item)
        instance = model.objects.first() if model else None
        return instance.updated_at if instance else None


class ServiceSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Service.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


class ProjectSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Project.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


class BlogSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return BlogPost.objects.live()

    def lastmod(self, obj):
        return obj.updated_at


class CareerSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return CareerOpening.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at
