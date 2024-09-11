# forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import HookContent

class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email address', max_length=254)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)


class HookContentForm(forms.ModelForm):
    class Meta:
        model = HookContent
        fields = ['hooks_content', 'google_sheets_link', 'eleven_labs_api_key', 'voice_id', 'main_box_color', 'font_color',
            'task_id', 'parallel_processing']
        widgets = {
            'main_box_color': forms.TextInput(attrs={'type': 'color'}),
            'font_color': forms.TextInput(attrs={'type': 'color'}),
        }