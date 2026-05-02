"""
Web Bookings Action Suite for Alice Browser Automation.

This module implements the Web Bookings Action Suite that handles:
- Travel bookings (flights, hotels, car rentals)
- Food delivery orders
- Event ticket bookings

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from alice_browser_automation.types import (
    BrowserTask, TaskResult, BrowserSession, TaskType,
    BrowserAction, ActionType, ElementSelectors
)
from alice_browser_automation.exceptions import BrowserAutomationError


logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class BookingType(Enum):
    """Types of travel bookings."""
    FLIGHT = "flight"
    HOTEL = "hotel"
    CAR = "car"


@dataclass
class TravelBookingDetails:
    """Travel booking parameters."""
    booking_type: BookingType
    destination: str
    departure_date: date
    origin: Optional[str] = None
    return_date: Optional[date] = None
    passengers: int = 1
    class_preference: Optional[str] = None  # economy, business, first
    preferences: Optional[Dict[str, Any]] = None  # flexible_dates, direct_flights, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for task parameters."""
        return {
            "booking_type": self.booking_type.value,
            "destination": self.destination,
            "departure_date": self.departure_date.isoformat(),
            "origin": self.origin,
            "return_date": self.return_date.isoformat() if self.return_date else None,
            "passengers": self.passengers,
            "class_preference": self.class_preference,
            "preferences": self.preferences or {}
        }


@dataclass
class EventTicketDetails:
    """Event ticket booking parameters."""
    event_name: str
    date: date
    venue: Optional[str] = None
    time: Optional[str] = None
    ticket_count: int = 1
    seat_preference: Optional[str] = None  # front, middle, back, vip
    ticket_type: Optional[str] = None  # general, vip, premium
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for task parameters."""
        return {
            "event_name": self.event_name,
            "date": self.date.isoformat(),
            "venue": self.venue,
            "time": self.time,
            "ticket_count": self.ticket_count,
            "seat_preference": self.seat_preference,
            "ticket_type": self.ticket_type
        }


@dataclass
class FoodOrderDetails:
    """Food order parameters."""
    restaurant: str
    items: List[str]
    delivery_address: str
    platform: Optional[str] = None  # ubereats, doordash, grubhub
    special_instructions: Optional[str] = None
    delivery_time: Optional[str] = None  # asap, scheduled
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for task parameters."""
        return {
            "restaurant": self.restaurant,
            "items": self.items,
            "delivery_address": self.delivery_address,
            "platform": self.platform,
            "special_instructions": self.special_instructions,
            "delivery_time": self.delivery_time
        }


# ============================================================================
# Web Bookings Action Suite
# ============================================================================

class WebBookingsActionSuite:
    """
    Web Bookings Action Suite for browser automation.
    
    Handles travel bookings, food delivery orders, and event ticket bookings
    through voice-controlled browser automation.
    
    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8
    """
    
    def __init__(
        self,
        engine: Any,  # BrowserAutomationEngine (avoid circular import)
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Web Bookings Action Suite.
        
        Args:
            engine: BrowserAutomationEngine instance
            config: Optional configuration dictionary
        """
        self.engine = engine
        self.config = config or {}
        
        # Default booking websites (can be overridden in config)
        self.booking_websites = self.config.get("booking_websites", {
            "flight": "https://www.google.com/travel/flights",
            "hotel": "https://www.google.com/travel/hotels",
            "car": "https://www.google.com/travel/cars",
            "food": "https://www.ubereats.com",
            "events": "https://www.ticketmaster.com"
        })
        
        logger.info("Web Bookings Action Suite initialized")
    
    # ========================================================================
    # Travel Bookings
    # ========================================================================
    
    async def book_travel(
        self,
        details: TravelBookingDetails,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> TaskResult:
        """
        Automate travel booking process.
        
        Steps:
        1. Navigate to booking website
        2. Fill search form (dates, destinations, preferences)
        3. Browse results and select option
        4. Fill passenger/guest details
        5. Handle payment (with user confirmation)
        6. Handle OTP if required
        7. Extract confirmation details
        
        Args:
            details: Travel booking details
            progress_callback: Optional callback for progress updates
        
        Returns:
            TaskResult with booking confirmation
        
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
        """
        logger.info(f"Starting travel booking: {details.booking_type.value}")
        
        try:
            # Create browser task
            task = BrowserTask(
                task_id=f"travel_booking_{datetime.now().timestamp()}",
                description=f"Book {details.booking_type.value} from {details.origin} to {details.destination}",
                task_type=TaskType.WEB_BOOKING,
                parameters=details.to_dict(),
                target_url=self.booking_websites.get(details.booking_type.value),
                expected_outcome="Booking confirmed with confirmation number"
            )
            
            # Execute task through engine
            result = await self.engine.execute_task(
                task_description=task.description,
                task_type=task.task_type,
                parameters=task.parameters,
                target_url=task.target_url,
                progress_callback=progress_callback
            )
            
            logger.info(f"Travel booking completed: {result.success}")
            return result
            
        except Exception as e:
            logger.error(f"Travel booking failed: {e}")
            return TaskResult(
                task_id=f"travel_booking_{datetime.now().timestamp()}",
                success=False,
                summary=f"Travel booking failed: {str(e)}",
                actions_taken=[],
                extracted_data={},
                error=str(e),
                duration_seconds=0.0
            )
    
    async def book_flight(
        self,
        origin: str,
        destination: str,
        departure_date: date,
        return_date: Optional[date] = None,
        passengers: int = 1,
        class_preference: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> TaskResult:
        """
        Book a flight.
        
        Convenience method for flight bookings.
        
        Args:
            origin: Departure airport/city
            destination: Arrival airport/city
            departure_date: Departure date
            return_date: Optional return date (for round trip)
            passengers: Number of passengers
            class_preference: economy, business, or first
            progress_callback: Optional callback for progress updates
        
        Returns:
            TaskResult with booking confirmation
        """
        details = TravelBookingDetails(
            booking_type=BookingType.FLIGHT,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            passengers=passengers,
            class_preference=class_preference
        )
        return await self.book_travel(details, progress_callback)
    
    async def book_hotel(
        self,
        destination: str,
        check_in_date: date,
        check_out_date: date,
        guests: int = 1,
        preferences: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> TaskResult:
        """
        Book a hotel.
        
        Convenience method for hotel bookings.
        
        Args:
            destination: Hotel location/city
            check_in_date: Check-in date
            check_out_date: Check-out date
            guests: Number of guests
            preferences: Optional preferences (pool, wifi, etc.)
            progress_callback: Optional callback for progress updates
        
        Returns:
            TaskResult with booking confirmation
        """
        details = TravelBookingDetails(
            booking_type=BookingType.HOTEL,
            destination=destination,
            departure_date=check_in_date,
            return_date=check_out_date,
            passengers=guests,
            preferences=preferences
        )
        return await self.book_travel(details, progress_callback)
    
    async def book_car(
        self,
        location: str,
        pickup_date: date,
        return_date: date,
        preferences: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> TaskResult:
        """
        Book a rental car.
        
        Convenience method for car rental bookings.
        
        Args:
            location: Pickup location
            pickup_date: Pickup date
            return_date: Return date
            preferences: Optional preferences (car type, transmission, etc.)
            progress_callback: Optional callback for progress updates
        
        Returns:
            TaskResult with booking confirmation
        """
        details = TravelBookingDetails(
            booking_type=BookingType.CAR,
            destination=location,
            departure_date=pickup_date,
            return_date=return_date,
            preferences=preferences
        )
        return await self.book_travel(details, progress_callback)
    
    # ========================================================================
    # Food Delivery
    # ========================================================================
    
    async def order_food(
        self,
        restaurant: str,
        items: List[str],
        delivery_address: str,
        platform: Optional[str] = None,
        special_instructions: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> TaskResult:
        """
        Automate food delivery order.
        
        Steps:
        1. Navigate to food delivery platform
        2. Search for restaurant
        3. Browse menu and add items to cart
        4. Proceed to checkout
        5. Confirm delivery address
        6. Handle payment (with user confirmation)
        7. Extract order confirmation
        
        Args:
            restaurant: Restaurant name
            items: List of menu items to order
            delivery_address: Delivery address
            platform: Optional platform (ubereats, doordash, grubhub)
            special_instructions: Optional delivery instructions
            progress_callback: Optional callback for progress updates
        
        Returns:
            TaskResult with order confirmation
        
        Requirements: 5.6
        """
        logger.info(f"Starting food order from {restaurant}")
        
        try:
            # Create food order details
            order_details = FoodOrderDetails(
                restaurant=restaurant,
                items=items,
                delivery_address=delivery_address,
                platform=platform,
                special_instructions=special_instructions
            )
            
            # Determine platform URL
            platform_url = self.booking_websites.get("food")
            if platform:
                platform_urls = {
                    "ubereats": "https://www.ubereats.com",
                    "doordash": "https://www.doordash.com",
                    "grubhub": "https://www.grubhub.com"
                }
                platform_url = platform_urls.get(platform.lower(), platform_url)
            
            # Create browser task
            task = BrowserTask(
                task_id=f"food_order_{datetime.now().timestamp()}",
                description=f"Order food from {restaurant}: {', '.join(items)}",
                task_type=TaskType.WEB_BOOKING,
                parameters=order_details.to_dict(),
                target_url=platform_url,
                expected_outcome="Order placed with confirmation number"
            )
            
            # Execute task through engine
            result = await self.engine.execute_task(
                task_description=task.description,
                task_type=task.task_type,
                parameters=task.parameters,
                target_url=task.target_url,
                progress_callback=progress_callback
            )
            
            logger.info(f"Food order completed: {result.success}")
            return result
            
        except Exception as e:
            logger.error(f"Food order failed: {e}")
            return TaskResult(
                task_id=f"food_order_{datetime.now().timestamp()}",
                success=False,
                summary=f"Food order failed: {str(e)}",
                actions_taken=[],
                extracted_data={},
                error=str(e),
                duration_seconds=0.0
            )
    
    # ========================================================================
    # Event Bookings
    # ========================================================================
    
    async def book_event(
        self,
        event_name: str,
        date: date,
        venue: Optional[str] = None,
        ticket_count: int = 1,
        seat_preference: Optional[str] = None,
        ticket_type: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> TaskResult:
        """
        Automate event ticket booking.
        
        Steps:
        1. Navigate to ticketing platform
        2. Search for event
        3. Select date and time
        4. Choose seats/tickets
        5. Fill attendee details
        6. Handle payment (with user confirmation)
        7. Extract booking confirmation
        
        Args:
            event_name: Name of the event
            date: Event date
            venue: Optional venue name
            ticket_count: Number of tickets
            seat_preference: Optional seat preference (front, middle, back, vip)
            ticket_type: Optional ticket type (general, vip, premium)
            progress_callback: Optional callback for progress updates
        
        Returns:
            TaskResult with booking confirmation
        
        Requirements: 5.7
        """
        logger.info(f"Starting event booking for {event_name}")
        
        try:
            # Create event ticket details
            ticket_details = EventTicketDetails(
                event_name=event_name,
                date=date,
                venue=venue,
                ticket_count=ticket_count,
                seat_preference=seat_preference,
                ticket_type=ticket_type
            )
            
            # Create browser task
            task = BrowserTask(
                task_id=f"event_booking_{datetime.now().timestamp()}",
                description=f"Book tickets for {event_name} on {date}",
                task_type=TaskType.WEB_BOOKING,
                parameters=ticket_details.to_dict(),
                target_url=self.booking_websites.get("events"),
                expected_outcome="Tickets booked with confirmation number"
            )
            
            # Execute task through engine
            result = await self.engine.execute_task(
                task_description=task.description,
                task_type=task.task_type,
                parameters=task.parameters,
                target_url=task.target_url,
                progress_callback=progress_callback
            )
            
            logger.info(f"Event booking completed: {result.success}")
            return result
            
        except Exception as e:
            logger.error(f"Event booking failed: {e}")
            return TaskResult(
                task_id=f"event_booking_{datetime.now().timestamp()}",
                success=False,
                summary=f"Event booking failed: {str(e)}",
                actions_taken=[],
                extracted_data={},
                error=str(e),
                duration_seconds=0.0
            )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def get_supported_platforms(self) -> Dict[str, List[str]]:
        """
        Get list of supported booking platforms.
        
        Returns:
            Dictionary of booking types and their supported platforms
        """
        return {
            "travel": ["google_flights", "google_hotels", "google_cars"],
            "food": ["ubereats", "doordash", "grubhub"],
            "events": ["ticketmaster", "eventbrite", "stubhub"]
        }
    
    def validate_booking_details(
        self,
        booking_type: str,
        details: Dict[str, Any]
    ) -> bool:
        """
        Validate booking details before processing.
        
        Args:
            booking_type: Type of booking (travel, food, event)
            details: Booking details dictionary
        
        Returns:
            True if valid, False otherwise
        """
        try:
            if booking_type == "travel":
                required_fields = ["destination", "departure_date"]
                return all(field in details for field in required_fields)
            
            elif booking_type == "food":
                required_fields = ["restaurant", "items", "delivery_address"]
                return all(field in details for field in required_fields)
            
            elif booking_type == "event":
                required_fields = ["event_name", "date"]
                return all(field in details for field in required_fields)
            
            return False
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
