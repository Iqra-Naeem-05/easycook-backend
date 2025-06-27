from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from .models import ChefProfile, Dish, Booking, ChefRating
import re
from django.core.files.storage import default_storage
from django.core.exceptions import SuspiciousOperation
from datetime import date, timedelta
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from PIL import Image

User = get_user_model()  

class RegisterSerializer(serializers.ModelSerializer):

    confirm_password = serializers.CharField(write_only=True)  # used only for validation

    email = serializers.EmailField(
        required=True,  # Ensures email is required
        validators=[UniqueValidator(queryset=User.objects.all())]  # Enforces uniqueness
    )


    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 'role']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True}  # Ensuring email is required
        }

    def validate(self, data):
        pw = data.get('password')
        cpw = data.get('confirm_password')

        if pw != cpw:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        if len(pw) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters long."})

        if not re.search(r'\d', pw):
            raise serializers.ValidationError({"password": "Password must contain at least one number."})

        return data

    def create(self, validated_data):
        
        validated_data.pop('confirm_password')  # Remove confirm_password, it's not part of the model
        user = User.objects.create_user(**validated_data) 
        return user



class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        user = authenticate(username=username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials. Please try again.")

        data['user'] = user  # Store the user object in data
        return data
    

class ChefProfileSerializer(serializers.ModelSerializer):
    # profile_picture = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(required=False, use_url=True)  # Allow file upload

    
    class Meta:
        model = ChefProfile
        # fields = '__all__'
        fields = [
            'id', 'user', 'full_name', 'bio', 'profile_picture', 'experience',
            'specialties', 'location', 'created_at', 'gender', 'age', 'contact_number',
            'is_available', 'breakfast_available', 'lunch_available', 'dinner_available',
            'urgent_booking_available', 'pre_booking_available', 'average_rating', 'total_ratings'
        ]

    def validate_contact_number(self, value):
        if value:  # Only validate if a value is provided
            if not value.startswith("03") or len(value) != 11:
                raise serializers.ValidationError("Enter a valid Pakistani number (e.g., 03XXXXXXXXX)")
        return value


    def validate_age(self, value):
        if value:
            if value < 18 or value > 70:
                raise serializers.ValidationError("Age must be between 18 and 70")
        return value


    def validate_gender(self, value):
        if not value:  # allow blank
            return value
        if value not in ['male', 'female', 'other']:
            raise serializers.ValidationError("Please select a valid gender")
        return value

    def validate_experience(self, value):
        if value is None:
            return value
        if value < 0 or value > 50:
            raise serializers.ValidationError("Experience must be between 0 and 50 years")
        return value

    def validate_bio(self, value):
        if not value:  # allow empty
            return value
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Please provide more specific Bio or leave it blank.")
        return value

    
    def validate(self, data):
    # Determine final value of is_available
        is_available = data.get('is_available', self.instance.is_available if self.instance else True)

        if not is_available:
            # If is_available is False, prevent any individual field from being set to True
            restricted_fields = [
                'breakfast_available',
                'lunch_available',
                'dinner_available',
                'urgent_booking_available',
                'pre_booking_available'
            ]
            errors = {}
            for field in restricted_fields:
                if data.get(field) is True:
                    data[field] = False
                    field_name = field.replace('_available', '').replace('_', ' ').capitalize()
                    errors[field] = f"You cannot enable {field_name} while your availability is disabled. Please enable your availability first."
            if errors:
                raise serializers.ValidationError(errors)

        return data


    def update(self, instance, validated_data):
        
        new_picture = validated_data.get('profile_picture', None)
        if new_picture and instance.profile_picture and instance.profile_picture.name != "defaults/default_profile.png":
            print('new_picture', new_picture)
            try:
                default_storage.delete(instance.profile_picture.name)
            except SuspiciousOperation:
                pass
        instance = super().update(instance, validated_data)
        print('instance', instance)
        if 'is_available' in validated_data:
            instance = super().update(instance, validated_data)
            instance.update_availability()
            print('instance', instance)


        return instance
        
    
class UserSerializer(serializers.ModelSerializer):
    chefprofile = ChefProfileSerializer()
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'chefprofile']  

class DishSerializer(serializers.ModelSerializer):
    chef = UserSerializer(read_only=True) 
    picture = serializers.ImageField( use_url=True, error_messages={'required': 'Dish picture is required.'})

    class Meta:
        model = Dish
        fields = '__all__'
        read_only_fields = ['chef']
    
    def validate_picture(self, picture):
        try:
            img = Image.open(picture)
            img.verify()
        except Exception:
            raise serializers.ValidationError("Invalid image format.")
        return picture

    def validate_name(self, value):
        if not value:
            raise serializers.ValidationError("Dish name is required.")
        return value

    def validate_description(self, value):
        if not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be a positive number.")
        return value
    
    def validate_serving_number(self, value):
        if value <= 0:
            raise serializers.ValidationError("Serving number must be a positive number.")
        return value
    
    
    def update(self, instance, validated_data):
        new_picture = validated_data.get('picture', None)
        if new_picture and instance.picture and instance.picture.name != "defaults/default_dish.png":
            try:
                default_storage.delete(instance.picture.name)
            except SuspiciousOperation:
                pass
        return super().update(instance, validated_data)

class DishSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = ['id', 'name', 'price']

# Booking
class BookingSerializer(serializers.ModelSerializer):
    dishes_details = DishSimpleSerializer(source='dishes', many=True, read_only=True)
    dishes = serializers.PrimaryKeyRelatedField(queryset=Dish.objects.all(), many=True)  # Handle multiple dishes
    slot = serializers.ListField(child=serializers.CharField(), write_only=True)
    slot_display = serializers.CharField(source='slot', read_only=True)

    chef_name = serializers.CharField(source='chef.username', read_only=True)
    customer_name = serializers.CharField(source='customer.username', read_only=True)


    class Meta:
        model = Booking
        fields = [
            'id', 'customer','customer_name', 'chef', 'chef_name', 'dishes', 'dishes_details',  'slot', 'slot_display', 'booking_type', 'date',
            'address', 'contact_number', 'special_instructions', 'status', 'is_paid', 'created_at', 'status_updated_at'
        ]

    def validate_address(self, value):
        cleaned_value = value.strip()

        if not cleaned_value or len(cleaned_value) < 10:
            raise serializers.ValidationError("Please provide a complete address.")

        if cleaned_value.isdigit():
            raise serializers.ValidationError("Address cannot consist of only numbers.")

        if not re.match(r'^[a-zA-Z0-9\s,.-]+$', cleaned_value):
            raise serializers.ValidationError("Address contains invalid characters.")

        if re.fullmatch(r'(.)\1{4,}', cleaned_value):  # e.g., 'aaaaa', '11111'
            raise serializers.ValidationError("Please provide a real address.")

        if re.search(r'(.)\1{4,}', cleaned_value):
            raise serializers.ValidationError("Address seems invalid due to excessive repetition.")

        return cleaned_value

    def validate_contact_number(self, value):
        phone_regex = r'^03\d{9}$' 
        if not re.match(phone_regex, value):
            raise serializers.ValidationError("Enter a valid Pakistani number (e.g. 03XXXXXXXXX)")
        return value


    def validate_special_instructions(self, value):
        if value and len(value.strip()) < 5:
            raise serializers.ValidationError("Please provide more specific instructions or leave it blank.")
        return value
    
    def validate(self, data):
        chef = data['chef']
        booking_type = data['booking_type']
        date_ = data['date']
        slot = data['slot']  

        # Prebooking-specific date validation
        if booking_type == 'prebooking':
            tomorrow = date.today() + timedelta(days=1) 
            seven_days_later = tomorrow + timedelta(days=7)
            if date_ < tomorrow or date_ > seven_days_later:
                raise serializers.ValidationError(
                    f"Date must be between {tomorrow} and {seven_days_later} for pre-booking."
                )

        if isinstance(slot, list):
            slot = slot[0]
            slot = slot.strip().lower()
        profile = chef.chefprofile

        # Global availability check
        if not profile.is_available:
            raise serializers.ValidationError("Chef is currently not available for bookings.")

        # Slot-level check for each meal type (breakfast, lunch, dinner)
        if slot == 'breakfast':
            if not profile.breakfast_available:
                raise serializers.ValidationError("Chef is not available for breakfast slot.")
            if booking_type == 'urgent' and not profile.urgent_booking_available:
                raise serializers.ValidationError("Urgent booking is currently disabled by the chef for breakfast.")
            if booking_type == 'prebooking' and not profile.pre_booking_available:
                raise serializers.ValidationError("Pre-booking is currently disabled by the chef for breakfast.")
            
        elif slot == 'lunch':
            if not profile.lunch_available:
                raise serializers.ValidationError("Chef is not available for lunch slot.")
            if booking_type == 'urgent' and not profile.urgent_booking_available:
                raise serializers.ValidationError("Urgent booking is currently disabled by the chef for lunch.")
            if booking_type == 'prebooking' and not profile.pre_booking_available:
                raise serializers.ValidationError("Pre-booking is currently disabled by the chef for lunch.")
            
        elif slot == 'dinner':
            if not profile.dinner_available:
                raise serializers.ValidationError("Chef is not available for dinner slot.")
            if booking_type == 'urgent' and not profile.urgent_booking_available:
                raise serializers.ValidationError("Urgent booking is currently disabled by the chef for dinner.")
            if booking_type == 'prebooking' and not profile.pre_booking_available:
                raise serializers.ValidationError("Pre-booking is currently disabled by the chef for dinner.")

        # Booking type check for unavailable global or slot-level availability
        if booking_type == 'prebooking' and not profile.pre_booking_available:
            raise serializers.ValidationError("Pre-booking is currently disabled by the chef.")
        
        if booking_type == 'urgent' and not profile.urgent_booking_available:
            raise serializers.ValidationError("Urgent booking is currently disabled by the chef.")
        
         # ✅ Check for existing confirmed booking with same date, slot, and booking type
        existing_booking = Booking.objects.filter(
            chef=chef,
            date=date_,
            slot=slot,
            booking_type=booking_type,
            status='confirmed'
        )
        if self.instance:
            existing_booking = existing_booking.exclude(id=self.instance.id)

        if existing_booking.exists():
            raise serializers.ValidationError(
                f"{slot.capitalize()} slot is already booked for {booking_type} on {date_}."
            )
        return data



    def create(self, validated_data):
        request = self.context['request']
        user = request.user

        dishes = validated_data.pop('dishes')  # take out dishes separately
        slots = validated_data.pop('slot')
        
        bookings = []  # to store created bookings
       
        for dish, slot in zip(dishes, slots):  # Pair dishes with slots
            booking_data = validated_data.copy()
            booking_data['customer'] = user  # Set the logged-in user as the customer
            booking_data['chef'] = dish.chef  # Set the chef based on the dish
            booking_data['slot'] = slot  # Set the slot

            booking = Booking.objects.create(**booking_data)
            booking.dishes.set([dish])  # Set the dish (many-to-many relation)
            bookings.append(booking)

        if len(bookings) == 1:
            return bookings[0]
        return bookings


class ChefRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChefRating
        fields = ['id', 'chef', 'user', 'rating', 'created_at']
        read_only_fields = ['user', 'created_at']
