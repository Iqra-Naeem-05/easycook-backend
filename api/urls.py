
from django.urls import path
from . import views

urlpatterns = [
    # Authorization
    path("register/", views.register_user, name="register"), 
    path("login/", views.login_user, name="login"),
    path('change-password/', views.change_password, name='change-password'),
    path("user-info/", views.user_info, name="user_info"),
    path("logout/", views.logout_user, name="logout"),

    # chef
    path('chef-profile/', views.chef_profile_view, name='chef-profile'),
    path('delete-profile-picture/', views.delete_profile_picture, name='delete-profile-picture'),
    path('chefs-list/', views.chefs_list, name='chefs_list'),
    path('featured-Chef/', views.featured_chefs, name='featured-Chef'),
    path('chef-dishes/<int:chef_id>/<str:meal_type>/', views.chef_dishes, name='chef_dishes'),
    path('chef-availability/', views.chef_availability, name='chef-availability'),

    # dishes
    path('get-dish/<int:dish_id>/', views.get_dish, name='get_dish'),
    path('add-dishes/', views.manage_dish, name='add_dishes'),
    path('edit-dish/<int:dish_id>/', views.manage_dish, name='edit_dishes'),
    path('delete-dish/<int:dish_id>/', views.manage_dish, name='delete-dish'),

    # Booking
    path('book-chef/', views.create_booking, name='create-booking'),
    path('my-bookings/', views.customer_bookings, name='customer-bookings'),
    path('chef-upcoming-bookings/', views.chef_upcoming_bookings, name='chef-upcoming-bookings'),
    path('update-booking-status/<int:booking_id>/', views.update_booking_status, name='update-booking-status'),
    path('mark-booking-paid/<int:booking_id>/', views.mark_booking_paid, name='mark-booking-paid'),


    # Rating
    path('rate-chef/<int:chef_id>/', views.rate_chef, name='rate-chef'),
    path('get-chef-rating/<int:chef_id>/', views.get_chef_rating, name='get-chef-rating'),

    

]

