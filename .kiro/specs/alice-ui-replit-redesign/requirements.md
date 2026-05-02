# Requirements Document

## Introduction

This document specifies the requirements for redesigning the Alice voice assistant UI to be deployable on Replit. The current implementation uses Next.js 15, React 19, LiveKit for real-time communication, Three.js for 3D graphics, and various modern web technologies. The redesign must maintain core functionality while optimizing for Replit's environment, which includes considerations for resource constraints, deployment simplicity, and potential limitations in WebGL/3D rendering capabilities.

The redesigned system will preserve the two-phase user experience: a visually engaging welcome screen with 3D animation, and an active session interface with real-time voice/video communication, chat, and media controls.

## Glossary

- **Alice_UI**: The complete user interface system for the Alice voice assistant
- **Welcome_Screen**: The initial landing page featuring 3D ghost animation and start button
- **Session_View**: The active communication interface displayed after connection
- **Control_Bar**: The bottom toolbar containing microphone, camera, screen share, chat, and disconnect controls
- **LiveKit_Client**: The real-time communication library managing WebRTC connections
- **Media_Tiles**: Video/screen share display components in the session view
- **Chat_System**: Text-based messaging interface integrated with voice transcription
- **Settings_Panel**: Customizable color configuration interface
- **Audio_Visualizer**: Real-time visual representation of audio input levels
- **Connection_Manager**: System handling LiveKit room connection and token management
- **Replit_Environment**: The cloud-based development and hosting platform with specific resource constraints
- **WebGL_Scene**: Three.js-based 3D rendering context for the ghost animation
- **Agent_State**: The current status of the voice assistant (connecting, listening, thinking, speaking)
- **Device_Manager**: System handling audio/video device selection and permissions
- **Preloader**: Loading screen displayed during initial asset and scene initialization

## Requirements

### Requirement 1: Welcome Screen Architecture

**User Story:** As a user, I want to see an engaging welcome screen when I first access Alice, so that I have a visually appealing introduction to the voice assistant.

#### Acceptance Criteria

1. THE Welcome_Screen SHALL display a 3D ghost animation using Three.js and WebGL
2. WHEN the WebGL_Scene is initializing, THE Preloader SHALL display loading progress with visual feedback
3. WHEN WebGL initialization fails, THE Welcome_Screen SHALL gracefully degrade to show the start button without 3D effects
4. THE Welcome_Screen SHALL include a "START UI" button that becomes visible after scene initialization
5. WHEN the user clicks the start button, THE Alice_UI SHALL play a button click sound and transition to Session_View
6. THE WebGL_Scene SHALL respond to mouse movement with ghost position tracking and eye glow effects
7. THE Welcome_Screen SHALL display the Alice branding text and contact information in the footer
8. WHILE the Preloader is active, THE Welcome_Screen SHALL show a ghost SVG loader with floating animation

### Requirement 2: Replit Environment Optimization

**User Story:** As a developer, I want the Alice UI to run efficiently on Replit, so that users experience smooth performance despite platform constraints.

#### Acceptance Criteria

1. THE Alice_UI SHALL minimize bundle size by using dynamic imports for Three.js and postprocessing libraries
2. THE Alice_UI SHALL implement lazy loading for the WebGL_Scene to reduce initial page load time
3. WHEN running on Replit, THE Alice_UI SHALL detect available GPU resources and adjust rendering quality accordingly
4. THE Alice_UI SHALL provide a fallback rendering mode for environments with limited WebGL support
5. THE Alice_UI SHALL use environment variables for configuration without requiring build-time compilation
6. THE Alice_UI SHALL support hot module replacement for rapid development iteration on Replit
7. THE Alice_UI SHALL implement proper cleanup of Three.js resources to prevent memory leaks
8. WHEN the viewport is resized, THE WebGL_Scene SHALL update camera and renderer dimensions efficiently

### Requirement 3: LiveKit Integration and Connection Management

**User Story:** As a user, I want to connect to the Alice voice assistant reliably, so that I can have uninterrupted voice conversations.

#### Acceptance Criteria

1. THE Connection_Manager SHALL fetch connection details from the backend API endpoint
2. WHEN connection details are requested, THE Connection_Manager SHALL include the sandbox ID in request headers
3. THE Connection_Manager SHALL validate JWT token expiration and refresh tokens within one minute of expiry
4. WHEN the session starts, THE LiveKit_Client SHALL enable the microphone with optional pre-connect buffering
5. THE LiveKit_Client SHALL implement automatic reconnection with exponential backoff (max 3 retries, 1000ms delay)
6. WHEN connection fails, THE Alice_UI SHALL display a descriptive error message via toast notification
7. THE LiveKit_Client SHALL implement a 10-second connection timeout with user notification on failure
8. WHEN the room disconnects for non-manual reasons, THE Connection_Manager SHALL attempt to refresh connection details after 3 seconds
9. THE LiveKit_Client SHALL subscribe to all remote participant tracks automatically
10. WHEN the Agent_State remains in "connecting" for more than 20 seconds, THE Alice_UI SHALL notify the user and disconnect

### Requirement 4: Session View and Media Management

**User Story:** As a user, I want to see and control my audio/video during a session, so that I can manage my communication preferences.

#### Acceptance Criteria

1. THE Session_View SHALL display Media_Tiles for remote participant video and screen shares
2. THE Session_View SHALL show a scrollable chat message view with transcriptions and text messages merged chronologically
3. WHEN new messages arrive, THE Session_View SHALL animate message entry with fade-in and height expansion
4. THE Session_View SHALL display an Audio_Visualizer with 3 bars showing real-time microphone input levels
5. THE Control_Bar SHALL provide toggle buttons for microphone, camera, screen share, and chat
6. THE Device_Manager SHALL allow users to select audio input and video input devices via dropdown menus
7. WHEN a device selection error occurs, THE Alice_UI SHALL notify the user with the specific error details
8. THE Control_Bar SHALL disable controls appropriately when operations are pending
9. THE Session_View SHALL display "Alice is now listening..." text when pre-connect buffer is enabled and no messages exist
10. WHEN the Agent_State changes, THE Session_View SHALL update control availability accordingly

### Requirement 5: Chat System and Transcription Integration

**User Story:** As a user, I want to send text messages and see voice transcriptions, so that I have multiple ways to communicate with Alice.

#### Acceptance Criteria

1. THE Chat_System SHALL merge voice transcriptions and text messages into a unified chronological view
2. WHEN the chat toggle is pressed, THE Chat_System SHALL expand the chat input field with smooth animation
3. THE Chat_System SHALL disable message sending when the agent is unavailable or a message is in flight
4. WHEN a user sends a message, THE Chat_System SHALL transmit it via LiveKit data channel
5. THE Chat_System SHALL display participant names for each message unless hideName is specified
6. THE Chat_System SHALL format transcription data into chat message format with proper timestamps
7. THE Chat_System SHALL support custom input border colors via CSS variables
8. WHEN chat is closed, THE Session_View SHALL hide overflow to prevent scrollbar appearance

### Requirement 6: Device Control and Audio/Video Management

**User Story:** As a user, I want to control my microphone, camera, and screen sharing, so that I can manage my privacy and presentation.

#### Acceptance Criteria

1. THE Device_Manager SHALL enumerate available audio input and video input devices
2. THE Device_Manager SHALL persist user device choices to localStorage when saveUserChoices is enabled
3. WHEN a user toggles the microphone, THE Control_Bar SHALL update the Audio_Visualizer display state
4. WHEN a user toggles the camera, THE LiveKit_Client SHALL enable or disable the camera track
5. WHEN a user toggles screen share, THE LiveKit_Client SHALL start or stop screen capture
6. THE Control_Bar SHALL display device selection dropdowns adjacent to their respective toggle buttons
7. THE Device_Manager SHALL request media permissions only when explicitly needed (not on page load)
8. WHEN a media device error occurs, THE Device_Manager SHALL invoke the error callback with source and error details
9. THE Control_Bar SHALL show visual feedback for pending operations (disabled state during toggle)
10. THE Audio_Visualizer SHALL display 3 vertical bars that animate based on microphone input amplitude

### Requirement 7: Settings Panel and Customization

**User Story:** As a user, I want to customize the UI colors, so that I can personalize my Alice experience.

#### Acceptance Criteria

1. THE Settings_Panel SHALL provide color pickers for visualizer, microphone, camera, screen share, chat, disconnect button, input border, and text colors
2. THE Settings_Panel SHALL persist color settings to localStorage
3. WHEN a color is changed, THE Settings_Panel SHALL immediately apply the color via CSS custom properties
4. THE Settings_Panel SHALL provide 8 preset colors (cyan, orange, purple, green, pink, blue, white, red) for quick selection
5. THE Settings_Panel SHALL include a reset button that restores default color values
6. THE Settings_Panel SHALL display a gear icon button in the bottom-right corner
7. WHEN the settings button is clicked, THE Settings_Panel SHALL expand with smooth animation
8. THE Settings_Panel SHALL support both color picker input and hex code text input for each setting
9. THE Settings_Panel SHALL highlight the currently selected preset color with a border and scale effect
10. THE Settings_Panel SHALL load saved colors from localStorage on initial page load

### Requirement 8: Responsive Design and Accessibility

**User Story:** As a user on various devices, I want the Alice UI to work well on different screen sizes, so that I can use it on desktop, tablet, or mobile.

#### Acceptance Criteria

1. THE Alice_UI SHALL use responsive Tailwind CSS classes for layout adaptation
2. THE Control_Bar SHALL hide device selection dropdowns on mobile screens (below md breakpoint)
3. THE Control_Bar SHALL display abbreviated button text on mobile ("END" instead of "Say Bye")
4. THE Session_View SHALL adjust padding and spacing for mobile viewports
5. THE Welcome_Screen SHALL scale the quote text using viewport-relative units (6vw)
6. THE WebGL_Scene SHALL update renderer and camera aspect ratio on window resize
7. THE Settings_Panel SHALL limit maximum height to 80vh with scrollable overflow
8. THE Alice_UI SHALL use the inert attribute to disable interaction with hidden views
9. THE Control_Bar SHALL provide proper ARIA labels for all interactive controls
10. THE Alice_UI SHALL support keyboard navigation for all primary controls

### Requirement 9: Error Handling and User Feedback

**User Story:** As a user, I want clear feedback when errors occur, so that I understand what went wrong and how to proceed.

#### Acceptance Criteria

1. WHEN a connection error occurs, THE Alice_UI SHALL display a toast notification with the error title and description
2. WHEN media device errors occur, THE Alice_UI SHALL show specific error messages including error name and message
3. WHEN the agent fails to join within 20 seconds, THE Alice_UI SHALL notify the user and provide a link to documentation
4. WHEN WebGL initialization fails, THE Alice_UI SHALL log the error to console and show the welcome content without 3D effects
5. THE Alice_UI SHALL implement proper error boundaries to prevent complete application crashes
6. WHEN connection details fetch fails, THE Connection_Manager SHALL throw an error with the server response message
7. THE Alice_UI SHALL display loading states during connection establishment
8. WHEN the connection times out, THE Alice_UI SHALL reset the session state and allow retry
9. THE Alice_UI SHALL provide visual feedback for all asynchronous operations (pending states)
10. WHEN the room disconnects, THE Alice_UI SHALL log the disconnect reason to console for debugging

### Requirement 10: State Management and Data Flow

**User Story:** As a developer, I want clear state management patterns, so that the application behavior is predictable and maintainable.

#### Acceptance Criteria

1. THE Alice_UI SHALL use React hooks (useState, useEffect, useCallback, useMemo) for local state management
2. THE Alice_UI SHALL use LiveKit's context providers (RoomContext) for shared room state
3. THE Connection_Manager SHALL maintain connection details state and provide refresh functions
4. THE Chat_System SHALL merge transcription and chat message arrays using useMemo with proper dependencies
5. THE Alice_UI SHALL use the sessionStarted boolean to control view transitions and component rendering
6. THE Control_Bar SHALL track pending states for each toggle operation independently
7. THE Settings_Panel SHALL synchronize color state between localStorage, React state, and CSS variables
8. THE Alice_UI SHALL use motion/framer-motion for declarative animation state management
9. THE Device_Manager SHALL track selected devices and persist choices to localStorage
10. THE Alice_UI SHALL implement proper cleanup in useEffect return functions to prevent memory leaks

### Requirement 11: Build and Deployment Configuration

**User Story:** As a developer, I want to deploy Alice UI on Replit easily, so that I can share it with users quickly.

#### Acceptance Criteria

1. THE Alice_UI SHALL use Next.js with Turbopack for fast development builds
2. THE Alice_UI SHALL support environment variables for API endpoints and configuration
3. THE Alice_UI SHALL provide a production build command that optimizes bundle size
4. THE Alice_UI SHALL configure proper CORS headers for API routes
5. THE Alice_UI SHALL use concurrent script execution for frontend and backend development
6. THE Alice_UI SHALL support HTTPS in development for WebRTC functionality
7. THE Alice_UI SHALL implement proper TypeScript configuration for type safety
8. THE Alice_UI SHALL use ESLint and Prettier for code quality and formatting
9. THE Alice_UI SHALL configure Tailwind CSS v4 with PostCSS for styling
10. THE Alice_UI SHALL provide clear documentation for Replit deployment steps

### Requirement 12: Performance Optimization

**User Story:** As a user, I want the Alice UI to load and run smoothly, so that I have a responsive experience.

#### Acceptance Criteria

1. THE Alice_UI SHALL use dynamic imports for Three.js libraries to reduce initial bundle size
2. THE WebGL_Scene SHALL use requestAnimationFrame for efficient animation loops
3. THE Alice_UI SHALL implement proper disposal of Three.js geometries, materials, and textures
4. THE Audio_Visualizer SHALL use efficient bar count (3 bars) to minimize rendering overhead
5. THE Alice_UI SHALL debounce window resize handlers to prevent excessive recalculations
6. THE Chat_System SHALL use AnimatePresence for efficient list animations
7. THE Alice_UI SHALL minimize re-renders by using proper React.memo and useMemo optimizations
8. THE WebGL_Scene SHALL use GPU acceleration hints (transform: translateZ(0), backfaceVisibility: hidden)
9. THE Alice_UI SHALL implement lazy loading for the Settings_Panel to reduce initial render cost
10. THE Alice_UI SHALL use efficient CSS transitions instead of JavaScript animations where possible

### Requirement 13: Component Architecture and Modularity

**User Story:** As a developer, I want a well-organized component structure, so that the codebase is maintainable and extensible.

#### Acceptance Criteria

1. THE Alice_UI SHALL separate concerns into distinct components (App, Welcome, SessionView, ControlBar, SettingsPanel)
2. THE Alice_UI SHALL extract reusable hooks (useConnectionDetails, useChatAndTranscription, useAgentControlBar)
3. THE Alice_UI SHALL define clear prop interfaces using TypeScript for all components
4. THE Alice_UI SHALL use composition patterns for complex components (ControlBar contains TrackToggle and DeviceSelect)
5. THE Alice_UI SHALL separate UI components from business logic (hooks handle state, components handle rendering)
6. THE Alice_UI SHALL use a centralized configuration file (app-config.ts) for application settings
7. THE Alice_UI SHALL implement utility functions in a shared lib directory (utils.ts, types.ts)
8. THE Alice_UI SHALL use Radix UI primitives for accessible base components (Toggle, Button, Select)
9. THE Alice_UI SHALL organize styles using Tailwind utility classes with CSS variables for theming
10. THE Alice_UI SHALL implement proper TypeScript types for all props, state, and function signatures

### Requirement 14: Real-time Communication Features

**User Story:** As a user, I want reliable real-time voice and video communication, so that I can interact naturally with Alice.

#### Acceptance Criteria

1. THE LiveKit_Client SHALL establish WebRTC connections for audio and video tracks
2. THE LiveKit_Client SHALL support automatic track subscription for remote participants
3. THE Audio_Visualizer SHALL display real-time audio levels using LiveKit's BarVisualizer component
4. THE LiveKit_Client SHALL handle track muting and unmuting without disconnection
5. THE LiveKit_Client SHALL support screen sharing with proper track management
6. THE Chat_System SHALL use LiveKit's data channel for text message transmission
7. THE LiveKit_Client SHALL handle participant join and leave events
8. THE LiveKit_Client SHALL support agent-specific participant detection (isAgent property)
9. THE LiveKit_Client SHALL render remote audio using RoomAudioRenderer component
10. THE LiveKit_Client SHALL implement StartAudio component for browser autoplay policy compliance

### Requirement 15: Theme and Visual Design

**User Story:** As a user, I want a visually cohesive dark-themed interface, so that the UI is comfortable to use and aesthetically pleasing.

#### Acceptance Criteria

1. THE Alice_UI SHALL implement a dark color scheme with black background and cyan/orange accents
2. THE Alice_UI SHALL use CSS custom properties for all theme colors to enable runtime customization
3. THE Welcome_Screen SHALL display a gradient background (linear-gradient from #0a0a0a to #1a1a1a)
4. THE Control_Bar SHALL use rounded corners (31px border-radius) and subtle drop shadows
5. THE Alice_UI SHALL use the "PPSupplyMono" font for monospace text and "Boldonse" for display text
6. THE Settings_Panel SHALL use semi-transparent backgrounds (bg-black/95) with backdrop blur
7. THE Alice_UI SHALL implement smooth transitions for all interactive elements (300ms duration)
8. THE Control_Bar buttons SHALL use color-coded states (white for active, red for destructive)
9. THE Chat_System SHALL use subtle separators and proper text hierarchy
10. THE Alice_UI SHALL implement hover and focus states for all interactive elements with appropriate visual feedback
