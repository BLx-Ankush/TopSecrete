"""
Unit tests for DOM Parser.

Tests DOM parsing functionality including element extraction,
accessibility tree parsing, and caching mechanisms.

Validates Requirements: 2.1, 2.2, 12.2
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from alice_browser_automation.dom_parser import DOMParser
from alice_browser_automation.types import (
    StructuredDOM,
    InteractiveElement,
    ElementSelectors,
    AccessibilityTree,
    AccessibilityNode
)
from alice_browser_automation.exceptions import BrowserAutomationError


class TestDOMParser:
    """Test suite for DOMParser class."""
    
    @pytest.fixture
    def dom_parser(self):
        """Create DOMParser instance for testing."""
        return DOMParser(cache_duration_seconds=2.0)
    
    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        page = MagicMock()
        page.url = "https://example.com/test"
        page.title = AsyncMock(return_value="Test Page")
        page.evaluate = AsyncMock()
        page.accessibility = MagicMock()
        page.accessibility.snapshot = AsyncMock()
        return page
    
    @pytest.mark.asyncio
    async def test_parse_page_basic(self, dom_parser, mock_page):
        """
        Test basic page parsing functionality.
        
        Validates Requirement 2.1: Extract DOM structure from web pages
        """
        # Setup mock responses
        mock_page.evaluate.side_effect = [
            # Interactive elements
            [
                {
                    'element_id': 'login-btn',
                    'tag_name': 'button',
                    'role': 'button',
                    'label': 'Login',
                    'selectors': {
                        'css_selector': '#login-btn',
                        'xpath': '//*[@id="login-btn"]',
                        'aria_label': 'Login',
                        'test_id': None,
                        'text_content': 'Login'
                    },
                    'attributes': {'type': 'submit', 'name': '', 'value': '', 'href': '', 'placeholder': ''},
                    'position': [100, 200],
                    'is_visible': True
                }
            ],
            # Text content
            "Welcome to Test Page\nLogin",
            # Metadata
            {'viewport_width': 1920, 'viewport_height': 1080, 'ready_state': 'complete'}
        ]
        
        # Parse page
        result = await dom_parser.parse_page(mock_page)
        
        # Verify result
        assert isinstance(result, StructuredDOM)
        assert result.url == "https://example.com/test"
        assert result.title == "Test Page"
        assert len(result.interactive_elements) == 1
        assert result.interactive_elements[0].element_id == 'login-btn'
        assert result.text_content == "Welcome to Test Page\nLogin"
        assert result.metadata['viewport_width'] == 1920
    
    @pytest.mark.asyncio
    async def test_parse_page_caching(self, dom_parser, mock_page):
        """
        Test DOM caching mechanism.
        
        Validates Requirement 12.2: Cache parsed DOM for 2 seconds
        """
        # Setup mock responses
        mock_page.evaluate.side_effect = [
            [],  # Interactive elements
            "Test content",  # Text content
            {'ready_state': 'complete'}  # Metadata
        ]
        
        # First parse
        result1 = await dom_parser.parse_page(mock_page)
        
        # Second parse (should use cache)
        result2 = await dom_parser.parse_page(mock_page)
        
        # Verify same object returned from cache
        assert result1 is result2
        
        # Verify evaluate was only called once (3 times for first parse)
        assert mock_page.evaluate.call_count == 3
    
    @pytest.mark.asyncio
    async def test_parse_page_cache_expiration(self, dom_parser, mock_page):
        """Test that cache expires after duration."""
        # Setup mock responses for two parses
        mock_page.evaluate.side_effect = [
            [],  # First parse - interactive elements
            "Test content 1",  # First parse - text content
            {'ready_state': 'complete'},  # First parse - metadata
            [],  # Second parse - interactive elements
            "Test content 2",  # Second parse - text content
            {'ready_state': 'complete'}  # Second parse - metadata
        ]
        
        # First parse
        result1 = await dom_parser.parse_page(mock_page)
        
        # Manually expire cache
        url = mock_page.url
        cached_dom, cached_time = dom_parser._dom_cache[url]
        dom_parser._dom_cache[url] = (cached_dom, datetime.now() - timedelta(seconds=3))
        
        # Second parse (cache expired)
        result2 = await dom_parser.parse_page(mock_page)
        
        # Verify different objects
        assert result1 is not result2
        
        # Verify evaluate was called twice (3 times each)
        assert mock_page.evaluate.call_count == 6
    
    @pytest.mark.asyncio
    async def test_parse_page_error_handling(self, dom_parser, mock_page):
        """
        Test error handling during page parsing.
        
        Validates proper exception raising on parse failure.
        """
        # Setup mock to raise exception
        mock_page.title.side_effect = Exception("Page load failed")
        
        # Verify exception is raised
        with pytest.raises(BrowserAutomationError) as exc_info:
            await dom_parser.parse_page(mock_page)
        
        assert "Failed to parse DOM" in str(exc_info.value)
        assert "https://example.com/test" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_accessibility_tree_basic(self, dom_parser, mock_page):
        """
        Test basic accessibility tree extraction.
        
        Validates Requirement 2.2: Parse the accessibility tree
        """
        # Setup mock accessibility snapshot
        mock_page.accessibility.snapshot.return_value = {
            'role': 'WebArea',
            'name': 'Test Page',
            'children': [
                {
                    'role': 'button',
                    'name': 'Login',
                    'children': []
                },
                {
                    'role': 'link',
                    'name': 'Dashboard',
                    'children': []
                }
            ]
        }
        
        # Get accessibility tree
        result = await dom_parser.get_accessibility_tree(mock_page)
        
        # Verify result
        assert isinstance(result, AccessibilityTree)
        assert result.root.role == 'WebArea'
        assert result.root.name == 'Test Page'
        assert len(result.root.children) == 2
        assert len(result.interactive_nodes) == 2
        assert result.interactive_nodes[0].role == 'button'
        assert result.interactive_nodes[1].role == 'link'
    
    @pytest.mark.asyncio
    async def test_get_accessibility_tree_empty(self, dom_parser, mock_page):
        """Test accessibility tree extraction with no data."""
        # Setup mock to return None
        mock_page.accessibility.snapshot.return_value = None
        
        # Get accessibility tree
        result = await dom_parser.get_accessibility_tree(mock_page)
        
        # Verify empty tree
        assert isinstance(result, AccessibilityTree)
        assert result.root.role == 'WebArea'
        assert result.root.name == ''
        assert len(result.interactive_nodes) == 0
    
    @pytest.mark.asyncio
    async def test_get_accessibility_tree_caching(self, dom_parser, mock_page):
        """Test accessibility tree caching mechanism."""
        # Setup mock snapshot
        mock_page.accessibility.snapshot.return_value = {
            'role': 'WebArea',
            'name': 'Test',
            'children': []
        }
        
        # First call
        result1 = await dom_parser.get_accessibility_tree(mock_page)
        
        # Second call (should use cache)
        result2 = await dom_parser.get_accessibility_tree(mock_page)
        
        # Verify same object returned
        assert result1 is result2
        
        # Verify snapshot was only called once
        assert mock_page.accessibility.snapshot.call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_accessibility_tree_error_handling(self, dom_parser, mock_page):
        """Test error handling during accessibility tree extraction."""
        # Setup mock to raise exception
        mock_page.accessibility.snapshot.side_effect = Exception("Accessibility API failed")
        
        # Verify exception is raised
        with pytest.raises(BrowserAutomationError) as exc_info:
            await dom_parser.get_accessibility_tree(mock_page)
        
        assert "Failed to extract accessibility tree" in str(exc_info.value)
    
    def test_filter_interactive_elements(self, dom_parser):
        """
        Test filtering of interactive elements.
        
        Validates Requirement 2.6: Exclude non-interactive elements
        """
        # Create test DOM with mixed elements
        selectors = ElementSelectors(
            css_selector='#test',
            xpath='//*[@id="test"]'
        )
        
        elements = [
            InteractiveElement(
                element_id='btn1',
                tag_name='button',
                role='button',
                label='Click me',
                selectors=selectors,
                attributes={},
                position=(0, 0),
                is_visible=True
            ),
            InteractiveElement(
                element_id='div1',
                tag_name='div',
                role='generic',
                label='Container',
                selectors=selectors,
                attributes={},
                position=(0, 0),
                is_visible=True
            ),
            InteractiveElement(
                element_id='link1',
                tag_name='a',
                role='link',
                label='Go to page',
                selectors=selectors,
                attributes={},
                position=(0, 0),
                is_visible=True
            ),
            InteractiveElement(
                element_id='btn2',
                tag_name='button',
                role='button',
                label='Hidden',
                selectors=selectors,
                attributes={},
                position=(0, 0),
                is_visible=False
            )
        ]
        
        dom = StructuredDOM(
            url='https://example.com',
            title='Test',
            interactive_elements=elements,
            text_content='',
            metadata={}
        )
        
        # Filter interactive elements
        result = dom_parser.filter_interactive_elements(dom)
        
        # Verify only visible interactive elements returned
        assert len(result) == 2
        assert result[0].element_id == 'btn1'
        assert result[1].element_id == 'link1'
    
    def test_generate_selectors(self, dom_parser):
        """
        Test selector generation for elements.
        
        Validates Requirement 2.3: Provide element selectors
        """
        # Create test element
        selectors = ElementSelectors(
            css_selector='#login-btn',
            xpath='//*[@id="login-btn"]',
            aria_label='Login',
            test_id='login-button',
            text_content='Login'
        )
        
        element = InteractiveElement(
            element_id='login-btn',
            tag_name='button',
            role='button',
            label='Login',
            selectors=selectors,
            attributes={},
            position=(0, 0),
            is_visible=True
        )
        
        # Generate selectors
        result = dom_parser.generate_selectors(element)
        
        # Verify selectors
        assert isinstance(result, ElementSelectors)
        assert result.css_selector == '#login-btn'
        assert result.xpath == '//*[@id="login-btn"]'
        assert result.aria_label == 'Login'
        assert result.test_id == 'login-button'
    
    @pytest.mark.asyncio
    async def test_extract_interactive_elements_filters_decorative(self, dom_parser, mock_page):
        """Test that decorative elements are filtered out."""
        # Setup mock to return elements including decorative ones
        mock_page.evaluate.return_value = [
            {
                'element_id': 'btn1',
                'tag_name': 'button',
                'role': 'button',
                'label': 'Click',
                'selectors': {
                    'css_selector': '#btn1',
                    'xpath': '//*[@id="btn1"]',
                    'aria_label': None,
                    'test_id': None,
                    'text_content': 'Click'
                },
                'attributes': {},
                'position': [0, 0],
                'is_visible': True
            }
        ]
        
        # Extract elements
        result = await dom_parser._extract_interactive_elements(mock_page)
        
        # Verify only interactive elements returned
        assert len(result) == 1
        assert result[0].element_id == 'btn1'
    
    def test_parse_accessibility_node_recursive(self, dom_parser):
        """Test recursive parsing of accessibility nodes."""
        # Create nested node data
        node_data = {
            'role': 'form',
            'name': 'Login Form',
            'description': 'User login',
            'children': [
                {
                    'role': 'textbox',
                    'name': 'Email',
                    'children': []
                },
                {
                    'role': 'button',
                    'name': 'Submit',
                    'children': []
                }
            ]
        }
        
        # Parse node
        result = dom_parser._parse_accessibility_node(node_data)
        
        # Verify structure
        assert result.role == 'form'
        assert result.name == 'Login Form'
        assert result.description == 'User login'
        assert len(result.children) == 2
        assert result.children[0].role == 'textbox'
        assert result.children[1].role == 'button'
    
    def test_extract_interactive_nodes(self, dom_parser):
        """Test extraction of interactive nodes from tree."""
        # Create accessibility tree
        root = AccessibilityNode(
            role='WebArea',
            name='Page',
            children=[
                AccessibilityNode(role='button', name='Click'),
                AccessibilityNode(
                    role='form',
                    name='Login',
                    children=[
                        AccessibilityNode(role='textbox', name='Email'),
                        AccessibilityNode(role='button', name='Submit')
                    ]
                ),
                AccessibilityNode(role='generic', name='Container')
            ]
        )
        
        # Extract interactive nodes
        result = dom_parser._extract_interactive_nodes(root)
        
        # Verify only interactive nodes extracted
        assert len(result) == 3
        assert result[0].role == 'button'
        assert result[1].role == 'textbox'
        assert result[2].role == 'button'
    
    def test_clear_cache(self, dom_parser):
        """Test cache clearing functionality."""
        # Add items to cache
        dom_parser._dom_cache['url1'] = (MagicMock(), datetime.now())
        dom_parser._accessibility_cache['url1'] = (MagicMock(), datetime.now())
        
        # Clear cache
        dom_parser.clear_cache()
        
        # Verify caches are empty
        assert len(dom_parser._dom_cache) == 0
        assert len(dom_parser._accessibility_cache) == 0
    
    @pytest.mark.asyncio
    async def test_parse_page_performance(self, dom_parser, mock_page):
        """
        Test that page parsing completes within 2 seconds.
        
        Validates Requirement 12.2: Parse page structure within 2 seconds
        """
        import time
        
        # Setup mock responses
        mock_page.evaluate.side_effect = [
            [],  # Interactive elements
            "Test content",  # Text content
            {'ready_state': 'complete'}  # Metadata
        ]
        
        # Measure parse time
        start_time = time.time()
        await dom_parser.parse_page(mock_page)
        elapsed_time = time.time() - start_time
        
        # Verify performance requirement
        assert elapsed_time < 2.0, f"Parse took {elapsed_time}s, should be < 2s"
