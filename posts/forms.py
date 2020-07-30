from django.forms import ModelForm
from django import forms

from .models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ('group', 'text', 'image')
        widgets = {
            'text': forms.Textarea(),
            'image': forms.FileInput()
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text', )
        widgets = {
            'text': forms.Textarea(),
        }
