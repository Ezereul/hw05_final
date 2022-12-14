from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_page

from posts.models import Post, Group, Follow
from .forms import PostForm, CommentForm
from .utils import create_page_obj


POSTS_PER_PAGE = 10

User = get_user_model()


@cache_page(20)
def index(request):
    post_list = Post.objects.all()
    page_obj = create_page_obj(post_list, POSTS_PER_PAGE, request)
    context = {
        'page_obj': page_obj
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    page_obj = create_page_obj(post_list, POSTS_PER_PAGE, request)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    count_posts = post_list.count()
    page_obj = create_page_obj(post_list, POSTS_PER_PAGE, request)
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user=request.user,
            author=author).exists()
    else:
        following = False
    context = {
        'author': author,
        'page_obj': page_obj,
        'count_posts': count_posts,
        'following': following
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    author = post.author
    comments = post.comments.all()
    count_posts = author.posts.all().count()
    context = {
        'post': post,
        'count_posts': count_posts,
        'form': CommentForm(),
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES or None)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', username=post.author.username)
        return render(request, 'posts/post_create.html', {'form': form})
    form = PostForm()
    return render(request, 'posts/post_create.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    current_user = request.user
    if current_user != post.author:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('posts:post_detail', post_id=post_id)
    context = {
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/post_create.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required()
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    page_obj = create_page_obj(post_list, POSTS_PER_PAGE, request)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required()
def profile_follow(request, username):
    get_author = get_object_or_404(User, username=username)
    if request.user != get_author:
        Follow.objects.get_or_create(
            user=request.user,
            author=get_author
        )
    return redirect('posts:profile', username=username)


@login_required()
def profile_unfollow(request, username):
    get_author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=get_author).delete()

    return redirect('posts:profile', username=username)
