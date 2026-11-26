import flagsmith from 'flagsmith';
import { NextResponse } from 'next/server';
import { AccessToken, type AccessTokenOptions, type VideoGrant } from 'livekit-server-sdk';
import { RoomConfiguration } from '@livekit/protocol';
import { randomUUID } from 'node:crypto';

const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;

export const revalidate = 0;

const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX = 30;
const rateBuckets = new Map<string, { count: number; resetAt: number }>();

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const bucket = rateBuckets.get(ip);
  if (!bucket || now > bucket.resetAt) {
    rateBuckets.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return false;
  }
  bucket.count += 1;
  if (rateBuckets.size > 10_000) {
    Array.from(rateBuckets.entries()).forEach(([k, v]) => {
      if (now > v.resetAt) rateBuckets.delete(k);
    });
  }
  return bucket.count > RATE_LIMIT_MAX;
}

export type ConnectionDetails = {
  serverUrl: string;
  roomName: string;
  participantName: string;
  participantToken: string;
};

export async function POST(req: Request) {
  try {
    const ip =
      req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
      req.headers.get('x-real-ip') ||
      'unknown';
    const allowBypass = flagsmith.hasFeature('enable_super_agent_ttl_override');
    const skipLimiter = allowBypass && req.headers.get('x-loadtest-bypass') === 'true';
    if (!skipLimiter && isRateLimited(ip)) {
      return NextResponse.json(
        { error: 'Too many requests. Please slow down and try again shortly.' },
        { status: 429 }
      );
    }

    if (!LIVEKIT_URL || LIVEKIT_URL === 'wss://your-project.livekit.cloud') {
      console.error('LiveKit URL not configured');
      return NextResponse.json({ 
        error: 'LiveKit server URL not configured. Please check your .env.local file and set LIVEKIT_URL.' 
      }, { status: 500 });
    }
    if (!API_KEY || API_KEY === 'your_livekit_api_key') {
      console.error('LiveKit API key not configured');
      return NextResponse.json({ 
        error: 'LiveKit API key not configured. Please check your .env.local file and set LIVEKIT_API_KEY.' 
      }, { status: 500 });
    }
    if (!API_SECRET || API_SECRET === 'your_livekit_api_secret') {
      console.error('LiveKit API secret not configured');
      return NextResponse.json({ 
        error: 'LiveKit API secret not configured. Please check your .env.local file and set LIVEKIT_API_SECRET.' 
      }, { status: 500 });
    }

    let body;
    try {
      body = await req.json();
    } catch (error) {
      console.error('Failed to parse request body:', error);
      return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
    }
    
    const agentName: string = body?.room_config?.agents?.[0]?.agent_name;

    const participantName = 'user';
    const participantIdentity = `voice_assistant_user_${randomUUID()}`;
    const roomName = `voice_assistant_room_${randomUUID()}`;

    let participantToken: string;
    try {
      participantToken = await createParticipantToken(
        { identity: participantIdentity, name: participantName },
        roomName,
        agentName,
        allowBypass
      );
    } catch (error) {
      console.error('Failed to create participant token:', error);
      return NextResponse.json({ 
        error: 'Failed to create access token. Please check your LiveKit configuration.' 
      }, { status: 500 });
    }

    const data: ConnectionDetails = {
      serverUrl: LIVEKIT_URL,
      roomName,
      participantToken: participantToken,
      participantName,
    };
    const headers = new Headers({
      'Cache-Control': 'no-store',
    });
    return NextResponse.json(data, { headers });
  } catch (error) {
    console.error('Connection details API error:', error);
    if (error instanceof Error) {
      return NextResponse.json({ 
        error: `Failed to generate connection details: ${error.message}` 
      }, { status: 500 });
    }
    return NextResponse.json({ 
      error: 'An unexpected error occurred while generating connection details' 
    }, { status: 500 });
  }
}

function createParticipantToken(
  userInfo: AccessTokenOptions,
  roomName: string,
  agentName?: string,
  allowOverride: boolean = false
): Promise<string> {
  try {
    if (!API_KEY || !API_SECRET) {
      throw new Error('LiveKit API credentials are not properly configured');
    }

    const useExtendedTtl = allowOverride && agentName?.startsWith('super_');
    const at = new AccessToken(API_KEY, API_SECRET, {
      ...userInfo,
      ttl: useExtendedTtl ? '24h' : '15m',
    });
    
    const grant: VideoGrant = {
      room: roomName,
      roomJoin: true,
      canPublish: true,
      canPublishData: true,
      canSubscribe: true,
    };
    at.addGrant(grant);

    if (agentName) {
      try {
        at.roomConfig = new RoomConfiguration({
          agents: [{ agentName }],
        });
      } catch (error) {
        console.warn('Failed to set agent configuration:', error);
      }
    }

    return at.toJwt();
  } catch (error) {
    console.error('Token creation error:', error);
    throw new Error(`Failed to create access token: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}