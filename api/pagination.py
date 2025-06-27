from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 8  # Default page size
    max_page_size = 8 # Maximum page size
