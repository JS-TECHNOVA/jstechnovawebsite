from django import forms

from .models import ContactSubmission, Service


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
