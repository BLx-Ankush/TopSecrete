"""
DOM Parser for Alice Browser Automation.

This module provides DOM parsing functionality to extract structured DOM data
and accessibility trees from web pages for LLM processing.

Validates Requirements: 2.1, 2.2, 12.2
"""

import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from .types import (
    StructuredDOM,
    InteractiveElement,
    ElementSelectors,
    AccessibilityTree,
    AccessibilityNode
)
from .exceptions import BrowserAutomationError


class DOMParser:
    """
    Parse DOM structure into LLM-friendly format.
    
    Extracts structured DOM data and accessibility tree from web pages,
    with caching to avoid re-parsing on rapid actions.
    
    Validates Requirements:
    - 2.1: Extract DOM structure from web pages into structured text format
    - 2.2: Parse the accessibility tree for accurate element identification
    - 12.2: Parse page structure within 2 seconds of page load
    """
    
    def __init__(self, cache_duration_seconds: float = 2.0):
        """
        Initialize DOM parser with caching configuration.
        
        Args:
            cache_duration_seconds: Duration to cache parsed DOM (default: 2 seconds)
        """
        self.cache_duration = timedelta(seconds=cache_duration_seconds)
        self._dom_cache: Dict[str, Tuple[StructuredDOM, datetime]] = {}
        self._accessibility_cache: Dict[str, Tuple[AccessibilityTree, datetime]] = {}
        
        # Performance monitoring
        self._parse_times: List[float] = []
        self._cache_hits = 0
        self._cache_misses = 0
    
    async def parse_page(self, page) -> StructuredDOM:
        """
        Extract DOM structure from current page.
        
        Uses JavaScript evaluation to extract DOM elements and their properties.
        Caches results for 2 seconds to avoid re-parsing on rapid actions.
        
        Validates Requirement 2.1: Extract DOM structure from web pages
        Validates Requirement 12.2: Parse page structure within 2 seconds
        
        Args:
            page: Playwright Page object
            
        Returns:
            StructuredDOM object containing parsed page structure
            
        Raises:
            BrowserAutomationError: If DOM parsing fails
        """
        url = page.url
        start_time = time.time()
        
        # Check cache first
        if url in self._dom_cache:
            cached_dom, cached_time = self._dom_cache[url]
            if datetime.now() - cached_time < self.cache_duration:
                self._cache_hits += 1
                return cached_dom
        
        self._cache_misses += 1
        
        try:
            # Get page title
            title = await page.title()
            
            # Extract interactive elements using JavaScript
            interactive_elements = await self._extract_interactive_elements(page)
            
            # Extract text content
            text_content = await self._extract_text_content(page)
            
            # Get page metadata
            metadata = await self._extract_metadata(page)
            
            # Create StructuredDOM object
            structured_dom = StructuredDOM(
                url=url,
                title=title,
                interactive_elements=interactive_elements,
                text_content=text_content,
                metadata=metadata,
                timestamp=datetime.now()
            )
            
            # Cache the result
            self._dom_cache[url] = (structured_dom, datetime.now())
            
            # Record parse time for performance monitoring
            parse_time = time.time() - start_time
            self._parse_times.append(parse_time)
            
            # Keep only last 100 parse times
            if len(self._parse_times) > 100:
                self._parse_times = self._parse_times[-100:]
            
            return structured_dom
            
        except Exception as e:
            raise BrowserAutomationError(
                f"Failed to parse DOM for {url}: {str(e)}"
            ) from e
    
    async def get_accessibility_tree(self, page) -> AccessibilityTree:
        """
        Extract accessibility tree for element identification.
        
        Uses Playwright's accessibility API to get semantic page structure.
        Caches results for 2 seconds to avoid re-parsing on rapid actions.
        
        Validates Requirement 2.2: Parse the accessibility tree for accurate element identification
        
        Args:
            page: Playwright Page object
            
        Returns:
            AccessibilityTree object containing accessibility structure
            
        Raises:
            BrowserAutomationError: If accessibility tree extraction fails
        """
        url = page.url
        
        # Check cache first
        if url in self._accessibility_cache:
            cached_tree, cached_time = self._accessibility_cache[url]
            if datetime.now() - cached_time < self.cache_duration:
                return cached_tree
        
        try:
            # Get accessibility snapshot from Playwright
            snapshot = await page.accessibility.snapshot()
            
            if not snapshot:
                # Return empty tree if no accessibility data
                root = AccessibilityNode(role="WebArea", name="")
                return AccessibilityTree(root=root, interactive_nodes=[])
            
            # Parse accessibility tree
            root = self._parse_accessibility_node(snapshot)
            
            # Extract interactive nodes
            interactive_nodes = self._extract_interactive_nodes(root)
            
            # Create AccessibilityTree object
            accessibility_tree = AccessibilityTree(
                root=root,
                interactive_nodes=interactive_nodes
            )
            
            # Cache the result
            self._accessibility_cache[url] = (accessibility_tree, datetime.now())
            
            return accessibility_tree
            
        except Exception as e:
            raise BrowserAutomationError(
                f"Failed to extract accessibility tree for {url}: {str(e)}"
            ) from e
    
    def filter_interactive_elements(
        self,
        dom: StructuredDOM
    ) -> List[InteractiveElement]:
        """
        Filter only interactive elements (buttons, inputs, links).
        
        Validates Requirement 2.6: Exclude non-interactive elements from structured output
        
        Args:
            dom: StructuredDOM object
            
        Returns:
            List of interactive elements
        """
        interactive_roles = {
            'button', 'link', 'textbox', 'searchbox', 'combobox',
            'listbox', 'menu', 'menuitem', 'tab', 'checkbox',
            'radio', 'switch', 'slider', 'spinbutton'
        }
        
        return [
            element for element in dom.interactive_elements
            if element.role.lower() in interactive_roles and element.is_visible
        ]
    
    def generate_selectors(
        self,
        element: InteractiveElement
    ) -> ElementSelectors:
        """
        Generate CSS and XPath selectors for element.
        
        Validates Requirement 2.3: Provide element selectors for interaction
        
        Args:
            element: InteractiveElement to generate selectors for
            
        Returns:
            ElementSelectors with multiple selector strategies
        """
        # Element already has selectors, return them
        return element.selectors
    
    async def _extract_interactive_elements(self, page, include_offscreen: bool = False) -> List[InteractiveElement]:
        """
        Extract interactive elements from page using JavaScript.
        
        **Validates: Requirement 12.2** - Lazy loading for off-screen elements
        
        Args:
            page: Playwright Page object
            include_offscreen: Whether to include off-screen elements (default: False for lazy loading)
            
        Returns:
            List of InteractiveElement objects
        """
        # JavaScript code to extract interactive elements
        js_code = f"""
        (includeOffscreen) => {{
            const elements = [];
            const interactiveTags = ['button', 'a', 'input', 'select', 'textarea'];
            const interactiveRoles = ['button', 'link', 'textbox', 'searchbox', 'combobox'];
            
            // Find all interactive elements
            const allElements = document.querySelectorAll('*');
            
            allElements.forEach((el, index) => {{
                const tagName = el.tagName.toLowerCase();
                const role = el.getAttribute('role') || el.getAttribute('aria-role') || '';
                const ariaLabel = el.getAttribute('aria-label') || '';
                const isInteractive = interactiveTags.includes(tagName) || 
                                     interactiveRoles.includes(role.toLowerCase()) ||
                                     el.onclick !== null;
                
                // Skip decorative elements
                if (tagName === 'img' && !el.alt) return;
                if (el.classList.contains('spacer')) return;
                if (tagName === 'div' && !isInteractive) return;
                
                if (isInteractive) {{
                    const rect = el.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0 && 
                                     window.getComputedStyle(el).visibility !== 'hidden' &&
                                     window.getComputedStyle(el).display !== 'none';
                    
                    // Lazy loading: skip off-screen elements unless explicitly requested
                    const isInViewport = rect.top >= 0 && rect.left >= 0 &&
                                        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                                        rect.right <= (window.innerWidth || document.documentElement.clientWidth);
                    
                    if (!includeOffscreen && !isInViewport && isVisible) {{
                        // Skip off-screen elements for performance
                        return;
                    }}
                    
                    // Generate CSS selector
                    let cssSelector = '';
                    if (el.id) {{
                        cssSelector = `#${{el.id}}`;
                    }} else if (el.className) {{
                        const classes = Array.from(el.classList).join('.');
                        cssSelector = `${{tagName}}.${{classes}}`;
                    }} else {{
                        cssSelector = tagName;
                    }}
                    
                    // Generate XPath
                    const getXPath = (element) => {{
                        if (element.id) {{
                            return `//*[@id="${{element.id}}"]`;
                        }}
                        if (element === document.body) {{
                            return '/html/body';
                        }}
                        let ix = 0;
                        const siblings = element.parentNode?.childNodes || [];
                        for (let i = 0; i < siblings.length; i++) {{
                            const sibling = siblings[i];
                            if (sibling === element) {{
                                const parentPath = element.parentNode ? getXPath(element.parentNode) : '';
                                return `${{parentPath}}/${{element.tagName.toLowerCase()}}[${{ix + 1}}]`;
                            }}
                            if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {{
                                ix++;
                            }}
                        }}
                        return '';
                    }};
                    
                    const xpath = getXPath(el);
                    
                    // Get text content
                    const textContent = el.textContent?.trim().substring(0, 100) || '';
                    
                    // Get label
                    const label = ariaLabel || el.getAttribute('placeholder') || 
                                 el.getAttribute('title') || textContent || el.value || '';
                    
                    // Determine role
                    let elementRole = role || tagName;
                    if (tagName === 'a') elementRole = 'link';
                    if (tagName === 'input') {{
                        const inputType = el.type || 'text';
                        elementRole = inputType === 'text' || inputType === 'email' ? 'textbox' : inputType;
                    }}
                    
                    elements.push({{
                        element_id: el.id || `element_${{index}}`,
                        tag_name: tagName,
                        role: elementRole,
                        label: label.substring(0, 100),
                        selectors: {{
                            css_selector: cssSelector,
                            xpath: xpath,
                            aria_label: ariaLabel || null,
                            test_id: el.getAttribute('data-testid') || null,
                            text_content: textContent || null
                        }},
                        attributes: {{
                            type: el.type || '',
                            name: el.name || '',
                            value: el.value || '',
                            href: el.href || '',
                            placeholder: el.placeholder || ''
                        }},
                        position: [Math.round(rect.left), Math.round(rect.top)],
                        is_visible: isVisible
                    }});
                }}
            }});
            
            return elements;
        }}
        """
        
        # Execute JavaScript and get results
        elements_data = await page.evaluate(js_code, include_offscreen)
        
        # Convert to InteractiveElement objects
        interactive_elements = []
        for elem_data in elements_data:
            selectors = ElementSelectors(
                css_selector=elem_data['selectors']['css_selector'],
                xpath=elem_data['selectors']['xpath'],
                aria_label=elem_data['selectors']['aria_label'],
                test_id=elem_data['selectors']['test_id'],
                text_content=elem_data['selectors']['text_content']
            )
            
            element = InteractiveElement(
                element_id=elem_data['element_id'],
                tag_name=elem_data['tag_name'],
                role=elem_data['role'],
                label=elem_data['label'],
                selectors=selectors,
                attributes=elem_data['attributes'],
                position=tuple(elem_data['position']),
                is_visible=elem_data['is_visible']
            )
            
            interactive_elements.append(element)
        
        return interactive_elements
    
    async def _extract_text_content(self, page) -> str:
        """
        Extract visible text content from page.
        
        Args:
            page: Playwright Page object
            
        Returns:
            Extracted text content
        """
        js_code = """
        () => {
            return document.body.innerText || '';
        }
        """
        
        text_content = await page.evaluate(js_code)
        return text_content.strip()
    
    async def _extract_metadata(self, page) -> Dict[str, Any]:
        """
        Extract page metadata.
        
        Args:
            page: Playwright Page object
            
        Returns:
            Dictionary of metadata
        """
        js_code = """
        () => {
            const metadata = {};
            
            // Get meta tags
            const metaTags = document.querySelectorAll('meta');
            metaTags.forEach(tag => {
                const name = tag.getAttribute('name') || tag.getAttribute('property');
                const content = tag.getAttribute('content');
                if (name && content) {
                    metadata[name] = content;
                }
            });
            
            // Get viewport size
            metadata.viewport_width = window.innerWidth;
            metadata.viewport_height = window.innerHeight;
            
            // Get document ready state
            metadata.ready_state = document.readyState;
            
            return metadata;
        }
        """
        
        metadata = await page.evaluate(js_code)
        return metadata
    
    def _parse_accessibility_node(self, node_data: Dict[str, Any]) -> AccessibilityNode:
        """
        Parse accessibility node from Playwright snapshot data.
        
        Args:
            node_data: Dictionary from Playwright accessibility snapshot
            
        Returns:
            AccessibilityNode object
        """
        role = node_data.get('role', '')
        name = node_data.get('name', '')
        description = node_data.get('description')
        
        # Parse children recursively
        children = []
        for child_data in node_data.get('children', []):
            child_node = self._parse_accessibility_node(child_data)
            children.append(child_node)
        
        return AccessibilityNode(
            role=role,
            name=name,
            description=description,
            children=children,
            selectors=None  # Selectors are generated separately
        )
    
    def _extract_interactive_nodes(
        self,
        root: AccessibilityNode
    ) -> List[AccessibilityNode]:
        """
        Extract interactive nodes from accessibility tree.
        
        Args:
            root: Root accessibility node
            
        Returns:
            List of interactive accessibility nodes
        """
        interactive_roles = {
            'button', 'link', 'textbox', 'searchbox', 'combobox',
            'listbox', 'menu', 'menuitem', 'tab', 'checkbox',
            'radio', 'switch', 'slider', 'spinbutton'
        }
        
        interactive_nodes = []
        
        def traverse(node: AccessibilityNode):
            if node.role.lower() in interactive_roles:
                interactive_nodes.append(node)
            
            for child in node.children:
                traverse(child)
        
        traverse(root)
        return interactive_nodes
    
    def clear_cache(self):
        """Clear DOM and accessibility tree caches."""
        self._dom_cache.clear()
        self._accessibility_cache.clear()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get performance statistics for DOM parsing.
        
        **Validates: Requirement 12.2** - Performance monitoring
        
        Returns:
            Dictionary with performance metrics
        """
        if not self._parse_times:
            return {
                "average_parse_time": 0.0,
                "min_parse_time": 0.0,
                "max_parse_time": 0.0,
                "total_parses": 0,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "cache_hit_rate": 0.0
            }
        
        total_requests = self._cache_hits + self._cache_misses
        cache_hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "average_parse_time": sum(self._parse_times) / len(self._parse_times),
            "min_parse_time": min(self._parse_times),
            "max_parse_time": max(self._parse_times),
            "total_parses": len(self._parse_times),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": cache_hit_rate
        }
    
    def reset_performance_stats(self):
        """Reset performance statistics."""
        self._parse_times.clear()
        self._cache_hits = 0
        self._cache_misses = 0
