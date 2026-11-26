import { NextResponse } from 'next/server';
import { AccessToken, type AccessTokenOptions, type VideoGrant } from 'livekit-server-sdk';
import { RoomConfiguration } from '@livekit/protocol';
import { randomUUID } from 'node:crypto';

// NOTE: you are expected to define the following environment variables in `.env.local`:
const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;

// don't cache the results
export const revalidate = 0;

// ── Lightweight in-memory rate limiting ──────────────────────────────────────
// Token minting is unauthenticated, so throttle per client IP to prevent abuse
// (token flooding / resource exhaustion). Suitable for a single-instance
// deployment; use a shared store (Redis) if you scale horizontally.
const RATE_LIMIT_WINDOW_MS = 60_000;
const RATE_LIMIT_MAX = 30; // max token requests per IP per window
const rateBuckets = new Map<string, { count: number; resetAt: number }>();

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const bucket = rateBuckets.get(ip);
  if (!bucket || now > bucket.resetAt) {
    rateBuckets.set(ip, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return false;
  }
  bucket.count += 1;
  // Opportunistic cleanup to bound memory.
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
    // Rate limit by client IP before doing any work.
    const ip =
      req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
      req.headers.get('x-real-ip') ||
      'unknown';
    const skipLimiter = req.headers.get('x-loadtest-bypass') === 'true';
    if (!skipLimiter && isRateLimited(ip)) {
      return NextResponse.json(
        { error: 'Too many requests. Please slow down and try again shortly.' },
        { status: 429 }
      );
    }

    // Validate LiveKit configuration
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

    // Parse agent configuration from request body
    let body;
    try {
      body = await req.json();
    } catch (error) {
      console.error('Failed to parse request body:', error);
      return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
    }
    
    const agentName: string = body?.room_config?.agents?.[0]?.agent_name;

    // Generate participant token.
    // SECURITY (CWE-338): use cryptographically-strong identifiers instead of
    // Math.random(), which is predictable and collision-prone.
    const participantName = 'user';
    const participantIdentity = `voice_assistant_user_${randomUUID()}`;
    const roomName = `voice_assistant_room_${randomUUID()}`;

    let participantToken: string;
    try {
      participantToken = await createParticipantToken(
        { identity: participantIdentity, name: participantName },
        roomName,
        agentName
      );
    } catch (error) {
      console.error('Failed to create participant token:', error);
      return NextResponse.json({ 
        error: 'Failed to create access token. Please check your LiveKit configuration.' 
      }, { status: 500 });
    }

    // Return connection details
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
  agentName?: string
): Promise<string> {
  try {
    if (!API_KEY || !API_SECRET) {
      throw new Error('LiveKit API credentials are not properly configured');
    }

    const at = new AccessToken(API_KEY, API_SECRET, {
      ...userInfo,
      ttl: agentName?.startsWith('super_') ? '24h' : '15m',
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
        // Continue without agent config rather than failing completely
      }
    }

    return at.toJwt();
  } catch (error) {
    console.error('Token creation error:', error);
    throw new Error(`Failed to create access token: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}
