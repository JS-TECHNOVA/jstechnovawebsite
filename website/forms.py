from django import forms
from django.core.exceptions import ValidationError

from .models import ContactSubmission, FeedbackSubmission, Service


class ContactInquiryForm(forms.ModelForm):
    class Meta:
        model = ContactSubmission
        fields = ["name", "email", "phone", "service_interest", "project_details"]

    def __init__(self, *args, page_content=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service_interest"].queryset = Service.objects.filter(is_published=True).order_by("title", "id")
        self.fields["service_interest"].required = False

        input_class = (
            "mt-2 w-full border-b border-white/25 bg-transparent pb-2 text-sm text-white "
            "outline-none placeholder:text-slate-400 focus:border-accent"
        )
        textarea_class = (
            "mt-2 w-full border-b border-white/25 bg-transparent pb-2 text-sm text-white "
            "outline-none placeholder:text-slate-400 focus:border-accent"
        )
        select_class = (
            "contact-service-select mt-2 w-full border-b border-white/25 bg-transparent pb-2 text-sm text-white "
            "outline-none focus:border-accent"
        )

        self.fields["name"].widget.attrs.update({"class": input_class})
        self.fields["email"].widget.attrs.update({"class": input_class})
        self.fields["phone"].widget.attrs.update({"class": input_class})
        self.fields["service_interest"].widget.attrs.update({"class": select_class})
        self.fields["project_details"].widget.attrs.update({"class": textarea_class, "rows": 4})

        if page_content:
            self.fields["name"].widget.attrs["placeholder"] = page_content.form_name_placeholder
            self.fields["email"].widget.attrs["placeholder"] = page_content.form_email_placeholder
            self.fields["phone"].widget.attrs["placeholder"] = page_content.form_phone_placeholder
            self.fields["project_details"].widget.attrs["placeholder"] = page_content.form_details_placeholder
            self.fields["service_interest"].empty_label = page_content.form_service_placeholder


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = FeedbackSubmission
        fields = ["name", "email", "feeling", "rating", "message", "profile_image"]

    def __init__(self, *args, page_content=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["feeling"].widget = forms.HiddenInput()
        self.fields["rating"].widget = forms.HiddenInput()

        input_class = (
            "w-full rounded-[20px] border border-slate-200 bg-white px-5 py-4 text-base text-slate-900 "
            "shadow-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
        )
        textarea_class = (
            "w-full rounded-[24px] border border-slate-200 bg-white px-5 py-4 text-base text-slate-900 "
            "shadow-sm outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
        )

        self.fields["name"].widget.attrs.update({"class": input_class, "placeholder": "Enter your full name"})
        self.fields["email"].widget.attrs.update({"class": input_class, "placeholder": "you@example.com"})
        self.fields["message"].widget.attrs.update(
            {"class": textarea_class, "rows": 5, "placeholder": "Share your thoughts, suggestions, or what stood out most."}
        )
        self.fields["profile_image"].required = False
        self.fields["profile_image"].widget.attrs.update(
            {
                "class": "hidden",
                "accept": "image/png,image/jpeg,image/webp,image/gif",
            }
        )

        if page_content:
            self.fields["name"].widget.attrs["placeholder"] = page_content.name_placeholder
            self.fields["email"].widget.attrs["placeholder"] = page_content.email_placeholder
            self.fields["message"].widget.attrs["placeholder"] = page_content.message_placeholder

    def clean_profile_image(self):
        image = self.cleaned_data.get("profile_image")
        if not image:
            return image
        content_type = getattr(image, "content_type", "") or ""
        if content_type not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
            raise ValidationError("Upload a PNG, JPG, WEBP, or GIF image.")
        if image.size > 5 * 1024 * 1024:
            raise ValidationError("Profile image must be 5MB or smaller.")
        return image
