'use client';

import { useEffect, useMemo, useState } from 'react';
import { Room, RoomEvent } from 'livekit-client';
import { motion } from 'motion/react';
import { RoomAudioRenderer, RoomContext, StartAudio } from '@livekit/components-react';
import { toastAlert } from '@/components/alert-toast';
import { SessionView } from '@/components/session-view';
import { Toaster } from '@/components/ui/sonner';
import { Welcome } from '@/components/welcome';
import useConnectionDetails from '@/hooks/useConnectionDetails';
import type { AppConfig } from '@/lib/types';

// Import the test utility for debugging
if (process.env.NODE_ENV === 'development') {
  import('@/lib/livekit-test');
}

const MotionWelcome = motion.create(Welcome);
const MotionSessionView = motion.create(SessionView);

interface AppProps {
  appConfig: AppConfig;
}

export function App({ appConfig }: AppProps) {
  const room = useMemo(() => new Room(), []);
  const [sessionStarted, setSessionStarted] = useState(false);
  const { refreshConnectionDetails, existingOrRefreshConnectionDetails } =
    useConnectionDetails(appConfig);

  useEffect(() => {
    const onDisconnected = (reason?: import('livekit-client').DisconnectReason) => {
      console.log('Room disconnected. Reason:', reason);
      setSessionStarted(false);
      
      // Only attempt to reconnect if it wasn't a manual disconnect
      if (reason !== 'manual') {
        console.log('Attempting to refresh connection details...');
        setTimeout(() => {
          refreshConnectionDetails().catch(error => {
            console.error('Failed to refresh connection details:', error);
            toastAlert({
              title: 'Connection Error',
              description: 'Failed to refresh connection details. Please try again.',
            });
          });
        }, 3000);
      }
    };
    const onMediaDevicesError = (error: Error) => {
      console.error('Media devices error:', error);
      toastAlert({
        title: 'Encountered an error with your media devices',
        description: `${error.name}: ${error.message}`,
      });
    };
    const onConnected = () => {
      console.log('Room connected successfully');
    };
    const onConnecting = () => {
      console.log('Room connecting...');
    };
    const onConnectionError = (error: Error) => {
      console.error('Room connection error:', error);
      setSessionStarted(false);
      toastAlert({
        title: 'Connection Error',
        description: `Failed to connect to the room: ${error.message}`,
      });
    };
    
    room.on(RoomEvent.Connected, onConnected);
    room.on(RoomEvent.SignalConnected, onConnecting);
    room.on(RoomEvent.MediaDevicesError, onMediaDevicesError);
    room.on(RoomEvent.Disconnected, onDisconnected);
    room.on(RoomEvent.ConnectionError, onConnectionError);
    
    return () => {
      room.off(RoomEvent.Connected, onConnected);
      room.off(RoomEvent.SignalConnected, onConnecting);
      room.off(RoomEvent.Disconnected, onDisconnected);
      room.off(RoomEvent.MediaDevicesError, onMediaDevicesError);
      room.off(RoomEvent.ConnectionError, onConnectionError);
    };
  }, [room, refreshConnectionDetails]);

  useEffect(() => {
    let aborted = false;
    let connectionTimeout: NodeJS.Timeout;
    
    if (sessionStarted && room.state === 'disconnected') {
      // Set connection timeout
      connectionTimeout = setTimeout(() => {
        if (!aborted && room.state !== 'connected') {
          console.warn('Connection timeout reached');
          room.disconnect();
          setSessionStarted(false);
          toastAlert({
            title: 'Connection Timeout',
            description: 'Failed to connect to the room within the expected time. Please try again.',
          });
        }
      }, 10000); // 10 second timeout
      
      Promise.all([
        room.localParticipant.setMicrophoneEnabled(true, undefined, {
          preConnectBuffer: appConfig.isPreConnectBufferEnabled,
        }),
        existingOrRefreshConnectionDetails().then((connectionDetails) => {
          if (aborted) throw new Error('Connection aborted');
          console.log('Connecting to room with details:', connectionDetails);
          return room.connect(connectionDetails.serverUrl, connectionDetails.participantToken, {
            autoSubscribe: true,
            maxRetries: 3,
            retryDelayMs: 1000,
          });
        }),
      ])
        .then(() => {
          if (!aborted) {
            console.log('Successfully connected to room');
            clearTimeout(connectionTimeout);
          }
        })
        .catch((error) => {
          clearTimeout(connectionTimeout);
          if (aborted) {
            // Once the effect has cleaned up after itself, drop any errors
            //
            // These errors are likely caused by this effect rerunning rapidly,
            // resulting in a previous run `disconnect` running in parallel with
            // a current run `connect`
            return;
          }

          console.error('Room connection error:', error);
          const errorMessage = error?.message || 'Unknown connection error';
          
          toastAlert({
            title: 'Connection Failed',
            description: `Unable to connect to the voice agent: ${errorMessage}`,
          });

          // Reset session on connection failure
          setSessionStarted(false);
        });
    }
    
    return () => {
      aborted = true;
      clearTimeout(connectionTimeout);
      if (room.state !== 'disconnected') {
        room.disconnect();
      }
    };
  }, [room, sessionStarted, appConfig.isPreConnectBufferEnabled, existingOrRefreshConnectionDetails]);

  const { startButtonText } = appConfig;

  return (
    <main>
      <MotionWelcome
        key="welcome"
        startButtonText={startButtonText}
        onStartCall={() => setSessionStarted(true)}
        disabled={sessionStarted}
        initial={{ opacity: 1 }}
        animate={{ opacity: sessionStarted ? 0 : 1 }}
        transition={{ duration: 0.5, ease: 'linear', delay: sessionStarted ? 0 : 0.5 }}
      />

      <RoomContext.Provider value={room}>
        <RoomAudioRenderer />
        <StartAudio label="Start Audio" />
        {/* --- */}
        <MotionSessionView
          key="session-view"
          appConfig={appConfig}
          disabled={!sessionStarted}
          sessionStarted={sessionStarted}
          initial={{ opacity: 0 }}
          animate={{ opacity: sessionStarted ? 1 : 0 }}
          transition={{
            duration: 0.5,
            ease: 'linear',
            delay: sessionStarted ? 0.5 : 0,
          }}
        />
      </RoomContext.Provider>

      <Toaster />
    </main>
  );
}
