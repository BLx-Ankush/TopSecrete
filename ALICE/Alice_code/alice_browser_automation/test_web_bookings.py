"""
Integration tests for Web Bookings Action Suite (Task 14.3).

Tests travel booking, food ordering, and event booking flows with mock websites.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import date, datetime, timedelta

from alice_browser_automation.web_bookings import (
    WebBookingsActionSuite, TravelBookingDetails, EventTicketDetails,
    FoodOrderDetails, BookingType
)
from alice_browser_automation.types import TaskResult, TaskType
from alice_browser_automation.engine import BrowserAutomationEngine
from alice_browser_automation.config import Config


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return Config()


@pytest.fixture
def mock_engine(mock_config):
    """Create a mock browser automation engine."""
    engine = Mock(spec=BrowserAutomationEngine)
    engine.config = mock_config
    engine.execute_task = AsyncMock()
    return engine


@pytest.fixture
def web_bookings_suite(mock_engine):
    """Create Web Bookings Action Suite for testing."""
    return WebBookingsActionSuite(engine=mock_engine)


@pytest.fixture
def sample_travel_details():
    """Create sample travel booking details."""
    return TravelBookingDetails(
        booking_type=BookingType.FLIGHT,
        origin="New York",
        destination="Los Angeles",
        departure_date=date.today() + timedelta(days=30),
        return_date=date.today() + timedelta(days=37),
        passengers=2,
        class_preference="economy"
    )


@pytest.fixture
def sample_event_details():
    """Create sample event ticket details."""
    return EventTicketDetails(
        event_name="Concert in the Park",
        date=date.today() + timedelta(days=14),
        venue="Central Park",
        ticket_count=2,
        seat_preference="front"
    )


@pytest.fixture
def sample_food_order():
    """Create sample food order details."""
    return FoodOrderDetails(
        restaurant="Pizza Palace",
        items=["Large Pepperoni Pizza", "Caesar Salad", "Garlic Bread"],
        delivery_address="123 Main St, Apt 4B",
        platform="ubereats",
        special_instructions="Ring doorbell twice"
    )


# ============================================================================
# Test: Initialization
# ============================================================================

class TestWebBookingsInitialization:
    """Test Web Bookings Action Suite initialization."""
    
    def test_initialization_default_config(self, mock_engine):
        """Test initialization with default configuration."""
        suite = WebBookingsActionSuite(engine=mock_engine)
        
        assert suite.engine == mock_engine
        assert "flight" in suite.booking_websites
        assert "food" in suite.booking_websites
        assert "events" in suite.booking_websites
    
    def test_initialization_custom_config(self, mock_engine):
        """Test initialization with custom configuration."""
        custom_config = {
            "booking_websites": {
                "flight": "https://custom-flights.com",
                "food": "https://custom-food.com"
            }
        }
        
        suite = WebBookingsActionSuite(engine=mock_engine, config=custom_config)
        
        assert suite.booking_websites["flight"] == "https://custom-flights.com"
        assert suite.booking_websites["food"] == "https://custom-food.com"
    
    def test_get_supported_platforms(self, web_bookings_suite):
        """Test getting supported platforms."""
        platforms = web_bookings_suite.get_supported_platforms()
        
        assert "travel" in platforms
        assert "food" in platforms
        assert "events" in platforms
        assert isinstance(platforms["travel"], list)


# ============================================================================
# Test: Data Models
# ============================================================================

class TestDataModels:
    """Test data model conversions."""
    
    def test_travel_booking_details_to_dict(self, sample_travel_details):
        """Test TravelBookingDetails to_dict conversion."""
        data = sample_travel_details.to_dict()
        
        assert data["booking_type"] == "flight"
        assert data["origin"] == "New York"
        assert data["destination"] == "Los Angeles"
        assert data["passengers"] == 2
        assert "departure_date" in data
        assert "return_date" in data
    
    def test_event_ticket_details_to_dict(self, sample_event_details):
        """Test EventTicketDetails to_dict conversion."""
        data = sample_event_details.to_dict()
        
        assert data["event_name"] == "Concert in the Park"
        assert data["venue"] == "Central Park"
        assert data["ticket_count"] == 2
        assert "date" in data
    
    def test_food_order_details_to_dict(self, sample_food_order):
        """Test FoodOrderDetails to_dict conversion."""
        data = sample_food_order.to_dict()
        
        assert data["restaurant"] == "Pizza Palace"
        assert len(data["items"]) == 3
        assert data["delivery_address"] == "123 Main St, Apt 4B"
        assert data["platform"] == "ubereats"


# ============================================================================
# Test: Travel Bookings
# ============================================================================

class TestTravelBookings:
    """Test travel booking functionality."""
    
    @pytest.mark.asyncio
    async def test_book_travel_success(
        self, web_bookings_suite, sample_travel_details, mock_engine
    ):
        """Test successful travel booking."""
        # Mock successful result
        mock_result = TaskResult(
            task_id="travel_123",
            success=True,
            summary="Flight booked successfully",
            actions_taken=["navigate", "fill_form", "submit"],
            extracted_data={"confirmation": "ABC123"},
            error="",
            duration_seconds=45.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        # Execute booking
        result = await web_bookings_suite.book_travel(sample_travel_details)
        
        # Assertions
        assert result.success is True
        assert "confirmation" in result.extracted_data
        mock_engine.execute_task.assert_called_once()
        
        # Verify task parameters
        call_args = mock_engine.execute_task.call_args
        assert call_args.kwargs["task_type"] == TaskType.WEB_BOOKING
        assert "Los Angeles" in call_args.kwargs["task_description"]
    
    @pytest.mark.asyncio
    async def test_book_travel_with_progress_callback(
        self, web_bookings_suite, sample_travel_details, mock_engine
    ):
        """Test travel booking with progress callback."""
        mock_result = TaskResult(
            task_id="travel_123",
            success=True,
            summary="Booking completed",
            actions_taken=[],
            extracted_data={},
            error="",
            duration_seconds=30.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        progress_callback = Mock()
        
        result = await web_bookings_suite.book_travel(
            sample_travel_details,
            progress_callback=progress_callback
        )
        
        assert result.success is True
        # Progress callback should be passed to engine
        call_args = mock_engine.execute_task.call_args
        assert "progress_callback" in call_args.kwargs
    
    @pytest.mark.asyncio
    async def test_book_travel_failure(
        self, web_bookings_suite, sample_travel_details, mock_engine
    ):
        """Test travel booking failure handling."""
        # Mock engine to raise exception
        mock_engine.execute_task.side_effect = Exception("Booking failed")
        
        result = await web_bookings_suite.book_travel(sample_travel_details)
        
        assert result.success is False
        assert "failed" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_book_flight_convenience_method(
        self, web_bookings_suite, mock_engine
    ):
        """Test book_flight convenience method."""
        mock_result = TaskResult(
            task_id="flight_123",
            success=True,
            summary="Flight booked",
            actions_taken=[],
            extracted_data={},
            error="",
            duration_seconds=40.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        result = await web_bookings_suite.book_flight(
            origin="NYC",
            destination="LAX",
            departure_date=date.today() + timedelta(days=30),
            passengers=1
        )
        
        assert result.success is True
        mock_engine.execute_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_book_hotel_convenience_method(
        self, web_bookings_suite, mock_engine
    ):
        """Test book_hotel convenience method."""
        mock_result = TaskResult(
            task_id="hotel_123",
            success=True,
            summary="Hotel booked",
            actions_taken=[],
            extracted_data={},
            error="",
            duration_seconds=35.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        result = await web_bookings_suite.book_hotel(
            destination="Miami",
            check_in_date=date.today() + timedelta(days=20),
            check_out_date=date.today() + timedelta(days=25),
            guests=2
        )
        
        assert result.success is True
        mock_engine.execute_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_book_car_convenience_method(
        self, web_bookings_suite, mock_engine
    ):
        """Test book_car convenience method."""
        mock_result = TaskResult(
            task_id="car_123",
            success=True,
            summary="Car rental booked",
            actions_taken=[],
            extracted_data={},
            error="",
            duration_seconds=25.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        result = await web_bookings_suite.book_car(
            location="Airport",
            pickup_date=date.today() + timedelta(days=15),
            return_date=date.today() + timedelta(days=22)
        )
        
        assert result.success is True
        mock_engine.execute_task.assert_called_once()


# ============================================================================
# Test: Food Ordering
# ============================================================================

class TestFoodOrdering:
    """Test food ordering functionality."""
    
    @pytest.mark.asyncio
    async def test_order_food_success(
        self, web_bookings_suite, mock_engine
    ):
        """Test successful food order."""
        mock_result = TaskResult(
            task_id="food_123",
            success=True,
            summary="Order placed successfully",
            actions_taken=["search", "add_to_cart", "checkout"],
            extracted_data={"order_number": "ORD-456"},
            error="",
            duration_seconds=30.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        result = await web_bookings_suite.order_food(
            restaurant="Pizza Palace",
            items=["Large Pizza", "Salad"],
            delivery_address="123 Main St"
        )
        
        assert result.success is True
        assert "order_number" in result.extracted_data
        mock_engine.execute_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_order_food_with_platform(
        self, web_bookings_suite, mock_engine
    ):
        """Test food order with specific platform."""
        mock_result = TaskResult(
            task_id="food_123",
            success=True,
            summary="Order placed",
            actions_taken=[],
            extracted_data={},
            error="",
            duration_seconds=25.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        result = await web_bookings_suite.order_food(
            restaurant="Burger Joint",
            items=["Burger", "Fries"],
            delivery_address="456 Oak Ave",
            platform="doordash"
        )
        
        assert result.success is True
        
        # Verify correct platform URL was used
        call_args = mock_engine.execute_task.call_args
        assert "doordash" in call_args.kwargs["target_url"].lower()
    
    @pytest.mark.asyncio
    async def test_order_food_with_special_instructions(
        self, web_bookings_suite, mock_engine
    ):
        """Test food order with special instructions."""
        mock_result = TaskResult(
            task_id="food_123",
            success=True,
            summary="Order placed",
            actions_taken=[],
            extracted_data={},
            error="",
            duration_seconds=28.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        result = await web_bookings_suite.order_food(
            restaurant="Sushi Bar",
            items=["California Roll", "Miso Soup"],
            delivery_address="789 Pine St",
            special_instructions="No wasabi, extra ginger"
        )
        
        assert result.success is True
        
        # Verify special instructions in parameters
        call_args = mock_engine.execute_task.call_args
        params = call_args.kwargs["parameters"]
        assert params["special_instructions"] == "No wasabi, extra ginger"
    
    @pytest.mark.asyncio
    async def test_order_food_failure(
        self, web_bookings_suite, mock_engine
    ):
        """Test food order failure handling."""
        mock_engine.execute_task.side_effect = Exception("Restaurant closed")
        
        result = await web_bookings_suite.order_food(
            restaurant="Closed Restaurant",
            items=["Item"],
            delivery_address="Address"
        )
        
        assert result.success is False
        assert result.error  # Error message should be present


# ============================================================================
# Test: Event Bookings
# ============================================================================

class TestEventBookings:
    """Test event booking functionality."""
    
    @pytest.mark.asyncio
    async def test_book_event_success(
        self, web_bookings_suite, sample_event_details, mock_engine
    ):
        """Test successful event booking."""
        mock_result = TaskResult(
            task_id="event_123",
            success=True,
            summary="Tickets booked successfully",
            actions_taken=["search", "select_seats", "checkout"],
            extracted_data={"ticket_numbers": ["T001", "T002"]},
            error="",
            duration_seconds=40.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        result = await web_bookings_suite.book_event(
            event_name=sample_event_details.event_name,
            date=sample_event_details.date,
            venue=sample_event_details.venue,
            ticket_count=sample_event_details.ticket_count
        )
        
        assert result.success is True
        assert "ticket_numbers" in result.extracted_data
        mock_engine.execute_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_book_event_with_seat_preference(
        self, web_bookings_suite, mock_engine
    ):
        """Test event booking with seat preference."""
        mock_result = TaskResult(
            task_id="event_123",
            success=True,
            summary="Tickets booked",
            actions_taken=[],
            extracted_data={},
            error="",
            duration_seconds=35.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        result = await web_bookings_suite.book_event(
            event_name="Rock Concert",
            date=date.today() + timedelta(days=30),
            ticket_count=4,
            seat_preference="vip"
        )
        
        assert result.success is True
        
        # Verify seat preference in parameters
        call_args = mock_engine.execute_task.call_args
        params = call_args.kwargs["parameters"]
        assert params["seat_preference"] == "vip"
    
    @pytest.mark.asyncio
    async def test_book_event_with_ticket_type(
        self, web_bookings_suite, mock_engine
    ):
        """Test event booking with ticket type."""
        mock_result = TaskResult(
            task_id="event_123",
            success=True,
            summary="Tickets booked",
            actions_taken=[],
            extracted_data={},
            error="",
            duration_seconds=38.0
        )
        mock_engine.execute_task.return_value = mock_result
        
        result = await web_bookings_suite.book_event(
            event_name="Theater Show",
            date=date.today() + timedelta(days=45),
            ticket_count=2,
            ticket_type="premium"
        )
        
        assert result.success is True
        
        # Verify ticket type in parameters
        call_args = mock_engine.execute_task.call_args
        params = call_args.kwargs["parameters"]
        assert params["ticket_type"] == "premium"
    
    @pytest.mark.asyncio
    async def test_book_event_failure(
        self, web_bookings_suite, mock_engine
    ):
        """Test event booking failure handling."""
        mock_engine.execute_task.side_effect = Exception("Event sold out")
        
        result = await web_bookings_suite.book_event(
            event_name="Sold Out Event",
            date=date.today() + timedelta(days=10)
        )
        
        assert result.success is False
        assert result.error  # Error message should be present


# ============================================================================
# Test: Validation
# ============================================================================

class TestValidation:
    """Test booking details validation."""
    
    def test_validate_travel_booking_valid(self, web_bookings_suite):
        """Test validation of valid travel booking details."""
        details = {
            "destination": "Paris",
            "departure_date": "2026-06-01"
        }
        
        is_valid = web_bookings_suite.validate_booking_details("travel", details)
        assert is_valid is True
    
    def test_validate_travel_booking_invalid(self, web_bookings_suite):
        """Test validation of invalid travel booking details."""
        details = {
            "destination": "Paris"
            # Missing departure_date
        }
        
        is_valid = web_bookings_suite.validate_booking_details("travel", details)
        assert is_valid is False
    
    def test_validate_food_order_valid(self, web_bookings_suite):
        """Test validation of valid food order details."""
        details = {
            "restaurant": "Pizza Place",
            "items": ["Pizza"],
            "delivery_address": "123 Main St"
        }
        
        is_valid = web_bookings_suite.validate_booking_details("food", details)
        assert is_valid is True
    
    def test_validate_food_order_invalid(self, web_bookings_suite):
        """Test validation of invalid food order details."""
        details = {
            "restaurant": "Pizza Place",
            "items": ["Pizza"]
            # Missing delivery_address
        }
        
        is_valid = web_bookings_suite.validate_booking_details("food", details)
        assert is_valid is False
    
    def test_validate_event_booking_valid(self, web_bookings_suite):
        """Test validation of valid event booking details."""
        details = {
            "event_name": "Concert",
            "date": "2026-07-15"
        }
        
        is_valid = web_bookings_suite.validate_booking_details("event", details)
        assert is_valid is True
    
    def test_validate_event_booking_invalid(self, web_bookings_suite):
        """Test validation of invalid event booking details."""
        details = {
            "event_name": "Concert"
            # Missing date
        }
        
        is_valid = web_bookings_suite.validate_booking_details("event", details)
        assert is_valid is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
