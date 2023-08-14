import subprocess
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from cd_manager.models import GpgKey


# If GpgKeySubmitForm gets updated, adjust GpgKeyAdmin.add_fieldsets accordingly!!
class GpgKeySubmitForm(forms.ModelForm):

    class Meta:
        model = GpgKey
        fields = ('owner', 'label', 'allow_sign_by_other_users',)

    gpg_key = forms.CharField(widget=forms.Textarea, required=True)

    def clean_gpg_key(self):
        key = self.cleaned_data['gpg_key']
        passwd_protected = subprocess.run(['/usr/bin/gpg', '--list-packets'],
                                          input=key.encode('ascii'), capture_output=True)
        if passwd_protected.returncode == 0:
            if b"protected" in passwd_protected.stdout:
                raise ValidationError(_("PGP mustn\'t be password protected."), code='passwd_protected')
            else:
                return key
        else:
            raise ValidationError(_("Gpg can\'t parse key input:\n %(stderr)s"),
                                  params={'stderr': passwd_protected.stderr.decode('utf-8')},
                                  code='gpg_parse_fail')

    def save(self, commit=True):
        super().save(commit=False)
        self.instance.key = self.cleaned_data['gpg_key']
        return super().save(commit=commit)
