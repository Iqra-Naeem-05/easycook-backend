from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ChefProfile, Dish, Booking, ChefRating

admin.site.site_header = "EasyCook Admin"
admin.site.site_title = "EasyCook Dashboard"
admin.site.index_title = "Welcome to EasyCook"


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ("id", "username", "email", "role", "is_staff", "is_active")  

    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "role")
    ordering = ("id",)


    fieldsets = UserAdmin.fieldsets + (
        ("Custom Fields", {"fields": ("role", )}),  
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Custom Fields", {"fields": ("role",)}),
    )

class ChefProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'gender', 'location', 'is_available', 'breakfast_available', 'lunch_available', 'dinner_available', 'urgent_booking_available', 'pre_booking_available', 'average_rating')
    list_filter = ('gender', 'location', 'is_available')
    search_fields = ('user__username', 'full_name')

class DishAdmin(admin.ModelAdmin):
    list_display = ('id', 'chef', 'name', 'available_time', 'serving_number', 'price')
    list_filter = ('available_time',)
    search_fields = ('name', 'chef__username')

class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'chef', 'slot', 'booking_type', 'date', 'status', 'is_paid', 'status_updated_at')
    list_filter = ('status', 'booking_type', 'slot', 'is_paid')
    search_fields = ('customer__username', 'chef__user__username', 'address')
    date_hierarchy = 'date'
    ordering = ('-date',)

class ChefRatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'chef', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ( 'user__username', 'chef__user__username')

admin.site.register(User, CustomUserAdmin)
admin.site.register(ChefProfile, ChefProfileAdmin)
admin.site.register(Dish, DishAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(ChefRating, ChefRatingAdmin)
