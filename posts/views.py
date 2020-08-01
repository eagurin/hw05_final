from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import reverse, render, redirect, get_object_or_404

from .forms import PostForm, CommentForm
from .models import *


def index(request):
    latest = Post.objects.order_by('-pub_date').all()
    paginator = Paginator(latest, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'index.html',
        {'page': page, 'paginator': paginator}
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = Post.objects.filter(group=group).order_by('-pub_date').all()
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'group.html',
        {'group': group, 'page': page, 'paginator': paginator}
    )


@login_required
def new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST or None, files=request.FILES or None)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('index')
        return render(request, 'new.html', {'form': form})
    form = PostForm()
    return render(request, 'new.html', {'form': form})


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=author).order_by('-pub_date').all()

    followers = Follow.objects.filter(author=author).count
    following_authors = Follow.objects.filter(user=author).count

    paginator = Paginator(posts, 10)
    page_num = request.GET.get('page')
    page = paginator.get_page(page_num)
    return render(
        request,
        'profile.html',
        {'author': author, 'page': page, 'paginator': paginator,
            'followers': followers, 'following_authors': following_authors}
    )


def post_view(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, author=author.pk, id=post_id)

    followers = Follow.objects.filter(author=author).count
    following_authors = Follow.objects.filter(user=author).count

    count = Post.objects.filter(author=author).count()
    form = CommentForm()
    comments = Comment.objects.filter(post=post_id)
    return render(request, 'post.html', {'post': post,
                                         'author': author,
                                         'count': count,
                                         'form': form,
                                         'comments': comments,
                                         'followers': followers,
                                         'following_authors': following_authors
                                         }
                  )


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)
    if request.user != post.author:
        return redirect('post', username=username, post_id=post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('post', username=username, post_id=post_id)
    return render(request, 'new.html', {'form': form, 'post': post})


def page_not_found(request, exception):
    # Переменная exception содержит отладочную информацию,
    # выводить её в шаблон пользователской страницы 404 мы не станем
    return render(
        request,
        'misc/404.html',
        {'path': request.path},
        status=404
    )


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    form = CommentForm(request.POST)
    comments = Comment.objects.filter(post=post_id)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        return redirect('post', username=username, post_id=post_id)
    else:
        comment_form = CommentForm()
        return redirect('post', username=username, post_id=post_id)
    return render(request, 'post.html',
                  {'form': form,
                   'post': post,
                   'comments': comments}
                  )


@login_required
def follow_index(request):
    posts = Post.objects.filter(
        author__following__user=request.user).select_related(
        'author', 'group').order_by('-pub_date')
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    count = Post.objects.all().count()
    return render(
        request, 'follow.html', {'page': page, 'paginator': paginator}
    )


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author == request.user or Follow.objects.filter(
        user=request.user, author=author).exists():
        return redirect(reverse("profile", kwargs={'username': username}))
    follow = Follow.objects.create(user=request.user, author=author)
    follow.save()
    return redirect(reverse("profile", kwargs={'username': username}))


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    follow = Follow.objects.filter(user=request.user, author=author)
    if Follow.objects.filter(user=request.user, author=author).exists():
        follow.delete()
    return redirect(reverse("profile", kwargs={'username': username}))


def page_not_found(request, exception):
    '''Display error 404 page.'''
    return render(
        request, 'misc/404.html', {'path': request.path}, status=404)


def server_error(request):
    '''Display error 500 page.'''
    return render(request, 'misc/500.html', status=500)
