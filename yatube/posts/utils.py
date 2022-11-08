from django.core.paginator import Paginator, Page
from django.db.models.query import QuerySet


def create_page_obj(post_list: QuerySet, posts_per_page: int,
                    request) -> Page:
    """Creates paginator and returns page objects"""
    paginator = Paginator(post_list, posts_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
