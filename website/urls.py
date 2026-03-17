from django.urls import path

from . import views

urlpatterns = [
    path("", views.HomePageView.as_view(), name="home"),
    path("about/", views.AboutPageView.as_view(), name="about"),
    path("contact/", views.ContactPageView.as_view(), name="contact"),
    path("feedback/", views.FeedbackPageView.as_view(), name="feedback"),
    path("privacy-policy/", views.PrivacyPolicyPageView.as_view(), name="privacy_policy"),
    path("terms-and-conditions/", views.TermsAndConditionsPageView.as_view(), name="terms_and_conditions"),
    path("services/", views.ServiceListView.as_view(), name="services"),
    path("services/<slug:slug>/", views.ServiceDetailView.as_view(), name="service_detail"),
    path("projects/", views.ProjectListView.as_view(), name="projects"),
    path("projects/<slug:slug>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("blogs/", views.BlogListView.as_view(), name="blogs"),
    path("blogs/<slug:slug>/", views.BlogDetailView.as_view(), name="blog_detail"),
    path("blogs/<slug:slug>/like/", views.blog_like_view, name="blog_like"),
    path("blogs/<slug:slug>/share/", views.blog_share_view, name="blog_share"),
    path("blogs/<slug:slug>/read-time/", views.blog_read_time_view, name="blog_read_time"),
    path("careers/", views.CareerListView.as_view(), name="careers"),
    path("careers/<slug:slug>/", views.CareerDetailView.as_view(), name="career_detail"),
]
