/**
 * LiveKit Connection Test Utility
 * Use this to test your LiveKit configuration and troubleshoot connection issues
 */

export async function testLiveKitConnection() {
  const apiUrl = '/api/connection-details';
  
  console.log('🧪 Testing LiveKit Connection...');
  
  try {
    // Test 1: Check if the connection details endpoint is working
    console.log('📡 Testing connection details endpoint...');
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(`API Error: ${errorData.error || response.statusText}`);
    }

    const connectionDetails = await response.json();
    console.log('✅ Connection details retrieved successfully');
    console.log('🔗 Server URL:', connectionDetails.serverUrl);
    console.log('🏠 Room Name:', connectionDetails.roomName);
    console.log('👤 Participant Name:', connectionDetails.participantName);
    
    // Test 2: Validate token structure
    const tokenParts = connectionDetails.participantToken.split('.');
    if (tokenParts.length !== 3) {
      throw new Error('Invalid JWT token structure');
    }
    console.log('🎫 Token structure is valid');

    // Test 3: Check if LiveKit server is reachable
    console.log('🌐 Testing server reachability...');
    const serverUrl = connectionDetails.serverUrl;
    
    // Create a test WebSocket connection to check if server is reachable
    return new Promise((resolve, reject) => {
      const testSocket = new WebSocket(serverUrl);
      
      const timeout = setTimeout(() => {
        testSocket.close();
        reject(new Error('Connection timeout - LiveKit server may be unreachable'));
      }, 5000);
      
      testSocket.onopen = () => {
        console.log('✅ LiveKit server is reachable');
        clearTimeout(timeout);
        testSocket.close();
        resolve({
          status: 'success',
          message: 'All tests passed! LiveKit connection should work.',
          details: connectionDetails
        });
      };
      
      testSocket.onerror = (error) => {
        console.error('❌ Server connection failed:', error);
        clearTimeout(timeout);
        reject(new Error('Cannot connect to LiveKit server - check your LIVEKIT_URL configuration'));
      };
    });
    
  } catch (error) {
    console.error('❌ Connection test failed:', error);
    throw error;
  }
}

// Export a function to run the test from browser console
if (typeof window !== 'undefined') {
  (window as any).testLiveKitConnection = testLiveKitConnection;
  console.log('🔧 LiveKit connection test available. Run testLiveKitConnection() in console to test your setup.');
}