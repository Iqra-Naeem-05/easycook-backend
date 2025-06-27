from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, LoginSerializer, ChefProfileSerializer, UserSerializer, DishSerializer, BookingSerializer, ChefRatingSerializer
from django.contrib.auth import login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from .models import ChefProfile, Dish, Booking, ChefRating
# from .models import *
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from datetime import timedelta
from django.utils import timezone
from datetime import datetime
from django.db.models import Case, When, Value, IntegerField
from django.core.exceptions import ObjectDoesNotExist
from .pagination import StandardResultsSetPagination


User = get_user_model()

@api_view(["POST"])
@ensure_csrf_cookie
def register_user(request):
    serializer = RegisterSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()  
        login(request, user)

        response = Response({"message": "User registered and logged in successfully!"}, status=status.HTTP_201_CREATED)

        request.session.create()
        response.set_cookie("sessionid", request.session.session_key, httponly=True)   
        return response 

    return Response( serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@ensure_csrf_cookie
def login_user(request):
    serializer = LoginSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.validated_data['user']
        login(request, user) 

        user_data = {
            "username": user.username,
            "role": user.role,  
        }

        response = Response({"message": "Login successful", "user": user_data}, status=status.HTTP_200_OK)
        
        request.session.create()
        response.set_cookie("sessionid", request.session.session_key, httponly=True)
        return response
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    user = request.user
    print("user pasword", user)
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')

    if not old_password or not new_password:
        return Response({"detail": "Both old and new passwords are required."}, status=status.HTTP_400_BAD_REQUEST)

    if old_password == new_password:
        return Response({"detail": "New password cannot be the same as the old password."}, status=status.HTTP_400_BAD_REQUEST)
    
    if not user.check_password(old_password):
        return Response({"detail": "Incorrect current password."}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save()

    return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)



@api_view(["GET"])
def user_info(request):
    if request.user.is_authenticated:
        return Response({
            "isAuthenticated": True,
            "id": request.user.id,
            "username": request.user.username,
            "role": request.user.role, 
        })
    return Response({"isAuthenticated": False}, status=200)

# @login_required
@api_view(["POST"])
def logout_user(request):
    if request.user.is_authenticated:
        logout(request)
        response = Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        return response
    return Response({"detail": "User is not logged in"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def chef_profile_view(request):
    """Retrieve and update the chef's profile."""
    print('request', request.data)
    try:
        profile = ChefProfile.objects.get(user=request.user)
    except ChefProfile.DoesNotExist:
        return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':  # Fetch profile
        # serializer = ChefProfileSerializer(profile)
        serializer = ChefProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ChefProfileSerializer(profile, data=request.data,  partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_profile_picture(request):
    try:
        profile = ChefProfile.objects.get(user=request.user)
        if profile.profile_picture and profile.profile_picture.name != 'defaults/default_profile.png':
            profile.profile_picture.delete(save=False)
            profile.profile_picture = 'defaults/default_profile.png'
            profile.save()
            return Response({'detail': 'Profile picture removed successfully.'})
        return Response({'detail': 'No custom profile picture to delete.'}, status=400)
    except ChefProfile.DoesNotExist:
        return Response({'detail': 'Profile not found.'}, status=404)

    
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def chef_availability(request):
    try:
        availability = ChefProfile.objects.get(user=request.user)
    except ChefProfile.DoesNotExist:
        return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = ChefProfileSerializer(availability)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    if request.method == 'PATCH':
        serializer = ChefProfileSerializer(availability, data=request.data, partial=True)
        if serializer.is_valid():
            updated_availability  = serializer.save()
            return Response({
                'message': 'Availability updated successfully',
                'pre_booking_available': updated_availability.pre_booking_available,
                'urgent_booking_available': updated_availability.urgent_booking_available,
                'dinner_available': updated_availability.dinner_available,
                'lunch_available': updated_availability.lunch_available,
                'breakfast_available': updated_availability.breakfast_available,
                'is_available': updated_availability.is_available,
            }, status=status.HTTP_200_OK)   
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def chefs_list(request):
    chefs = User.objects.filter(role="chef").select_related('chefprofile')

    if request.user.is_authenticated and request.user.role == "chef":
        chefs = chefs.exclude(id=request.user.id)

    chefs = chefs.order_by('-chefprofile__average_rating')

    paginator = StandardResultsSetPagination()
    paginated_chefs = paginator.paginate_queryset(chefs, request)
    serializer = UserSerializer(paginated_chefs, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
def featured_chefs(request):
    chefs = User.objects.filter(role="chef").select_related('chefprofile')

    if request.user.is_authenticated and request.user.role == "chef":
        chefs = chefs.exclude(id=request.user.id)

    chefs = chefs.order_by('-chefprofile__average_rating')[:4]  # Apply ordering and slicing after filtering

    serializer = UserSerializer(chefs, many=True, context={'request': request})
    return Response(serializer.data)


@api_view(['GET'])
def chef_dishes(request, chef_id, meal_type=None):
    """Fetch all dishes of a specific chef filtered by meal type."""
    chef = get_object_or_404(User.objects.select_related('chefprofile'), id=chef_id, role="chef")
    chef_data = UserSerializer(chef, context={'request': request})  # Fetch chef & profile data

    # Check if a meal_type is provided, and filter dishes accordingly
    if meal_type:
        dishes = Dish.objects.filter(chef=chef, available_time=meal_type)
    else:
        dishes = Dish.objects.filter(chef=chef)

    # Paginate the dishes based on the meal type (breakfast, lunch, or dinner)
    paginator = StandardResultsSetPagination()
    paginated_dishes = paginator.paginate_queryset(dishes, request)

    return Response({
        "chef": chef_data.data,
        "dishes": DishSerializer(paginated_dishes, many=True, context={'request': request}).data,
        "pagination": {
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link()
        }
    })



@api_view(['GET'])
def get_dish(request, dish_id):
    """Retrieve details of a single dish."""
    dish = get_object_or_404(Dish.objects.select_related('chef'), id=dish_id)
    serializer = DishSerializer(dish, context={'request': request})
    return Response(serializer.data)


@api_view(['POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated]) 
@parser_classes([MultiPartParser, FormParser]) 
def manage_dish(request, dish_id=None, chef_id=None):

    dish = None
    if dish_id:
        try:
            dish = Dish.objects.get(id=dish_id, chef=request.user)
        except Dish.DoesNotExist:
            return Response({"error": "Dish not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':  # Create new dish
        serializer = DishSerializer(data=request.data, context={'request': request})

    elif request.method == 'PUT':  # Update existing dish
        serializer = DishSerializer(dish, data=request.data, partial=True, context={'request': request})

    elif request.method == 'DELETE':
        # Delete a dish
        dish.delete()
        return Response({"message": "Dish deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    if serializer.is_valid():
        serializer.save(chef=request.user)  # Ensure the dish belongs to the logged-in chef
        return Response(serializer.data, status=status.HTTP_201_CREATED if request.method == 'POST' else status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Booking
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_booking(request):
    serializer = BookingSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        saved_booking = serializer.save()
        # If multiple bookings were created
        if isinstance(saved_booking, list):
            serialized_data = BookingSerializer(saved_booking, many=True).data
        else:
            serialized_data = BookingSerializer(saved_booking).data

        return Response(serialized_data, status=status.HTTP_201_CREATED)
    else:
        print("Serializer Errors:", serializer.errors)  # Add this line to print errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_bookings(request):
    bookings = Booking.objects.filter(customer=request.user).annotate(
        custom_priority=Case(
            When(status='pending', booking_type='urgent', then=Value(1)),
            When(status='pending', booking_type='prebooking', then=Value(2)),
            When(status='confirmed', booking_type='urgent', then=Value(3)),
            When(status='confirmed', booking_type='prebooking', then=Value(4)),
            When(status='completed', booking_type='urgent', then=Value(5)),
            When(status='completed', booking_type='prebooking', then=Value(6)),
            When(status='cancelled', booking_type='urgent', then=Value(7)),
            When(status='cancelled', booking_type='prebooking', then=Value(8)),
            When(status='rejected', booking_type='urgent', then=Value(9)),
            When(status='rejected', booking_type='prebooking', then=Value(10)),
            When(status='expired', booking_type='urgent', then=Value(11)),
            When(status='expired', booking_type='prebooking', then=Value(12)),
            default=Value(13),
            output_field=IntegerField()
        ),
    ).order_by('custom_priority')

    # Apply pagination
    paginator = StandardResultsSetPagination()
    paginated_bookings = paginator.paginate_queryset(bookings, request)

    # Run status checks only on paginated items
    for booking in paginated_bookings:
        check_and_expire_booking(booking)
        check_and_complete_booking(booking)

    serializer = BookingSerializer(paginated_bookings, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chef_upcoming_bookings(request):
    bookings = Booking.objects.filter(chef=request.user).annotate(
        custom_priority=Case(
            When(status='pending', booking_type='urgent', then=Value(1)),
            When(status='pending', booking_type='prebooking', then=Value(2)),
            When(status='confirmed', booking_type='urgent', then=Value(3)),
            When(status='confirmed', booking_type='prebooking', then=Value(4)),
            When(status='completed', booking_type='urgent', then=Value(5)),
            When(status='completed', booking_type='prebooking', then=Value(6)),
            When(status='cancelled', booking_type='urgent', then=Value(7)),
            When(status='cancelled', booking_type='prebooking', then=Value(8)),
            When(status='rejected', booking_type='urgent', then=Value(9)),
            When(status='rejected', booking_type='prebooking', then=Value(10)),
            When(status='expired', booking_type='urgent', then=Value(11)),
            When(status='expired', booking_type='prebooking', then=Value(12)),
            default=Value(13),
            output_field=IntegerField()
        )
    ).order_by('custom_priority')
    for booking in bookings:
        check_and_expire_booking(booking)
        check_and_complete_booking(booking)

    paginator = StandardResultsSetPagination()
    paginated_bookings = paginator.paginate_queryset(bookings, request)

    serializer = BookingSerializer(paginated_bookings, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_booking_status(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)

        new_status = request.data.get('status')
        if new_status not in ['pending', 'confirmed', 'rejected', 'cancelled', 'completed']:
            return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        
        if new_status == 'confirmed':
            # Prevent confirming if another booking is already confirmed
            exists = Booking.objects.filter(
                chef=booking.chef,
                date=booking.date,
                slot=booking.slot,
                booking_type=booking.booking_type,
                status='confirmed'
            ).exclude(id=booking.id).exists()

            if exists:
                return Response(
                    {'error': f"You have already confirmed a booking for {booking.slot} ({booking.booking_type}) on {booking.date}."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        booking.status = new_status
        booking.status_updated_at = timezone.now()
        booking.save()
        return Response({'message': 'Booking status updated successfully'})

    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)


def check_and_expire_booking(booking):
    now = timezone.now()

    if booking.status != 'pending':
        return  # No need to check if already confirmed/rejected

    if booking.booking_type == 'urgent':
        expiry_time = booking.created_at + timedelta(minutes=15)
    elif booking.booking_type == 'prebooking':
        expiry_time = booking.created_at + timedelta(hours=1)
    else:
        return 

    if now > expiry_time:
        booking.status = 'expired'
        booking.save()


def check_and_complete_booking(booking):
    if booking.status != 'confirmed':
        return  # Only confirmed bookings are eligible

    now = timezone.now()

    # Get the time range for the booking slot
    time_range = Dish.AVAILABLE_TIME_RANGES.get(booking.slot)
    if not time_range:
        return  

    slot_end_str = time_range[1] 
    
    # Combine the booking date and slot end time
    slot_end_time = datetime.combine(booking.date, datetime.strptime(slot_end_str, "%H:%M").time())
    slot_end_time = timezone.make_aware(slot_end_time, timezone.get_current_timezone())

    # If current time is past slot end, mark as completed
    if now > slot_end_time:
        booking.status = 'completed'
        booking.save()

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_booking_paid(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id, chef=request.user)
        booking.is_paid = True
        booking.save()
        return Response({'message': 'Marked as paid'}, status=status.HTTP_200_OK)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rate_chef(request, chef_id):
    try:
        chef = ChefProfile.objects.get(user__id=chef_id)
    except ObjectDoesNotExist:
        return Response({"error": "Chef not found"}, status=404)

    # Extract rating from the request
    rating_value = request.data.get('rating')
    # Validate the rating value (1-5)
    if not rating_value or int(rating_value) not in range(1, 6):
        return Response({"error": "Invalid rating"}, status=400)

    # Check if the user has already rated this chef
    existing_rating = ChefRating.objects.filter(user=request.user, chef=chef.user).first()

    if existing_rating:
        existing_rating.rating = rating_value
        existing_rating.save()
    else:
        ChefRating.objects.create(user=request.user, chef=chef.user, rating=rating_value)
    
    # After rating, update the chef's average rating and total ratings
    chef.update_rating()
    
    return Response({"success": "Rating submitted successfully"}, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chef_rating(request, chef_id):
    try:
        chef = get_object_or_404(ChefProfile, user__id=chef_id)
        existing_rating = ChefRating.objects.filter(user=request.user, chef=chef.user).first()

        rating_value = getattr(existing_rating, 'rating', 0) if existing_rating else 0
        return Response({'rating': rating_value})

    except Exception as e:
        return Response({'error': 'An internal error occurred.'}, status=500)