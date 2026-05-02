'use client';

import { useEffect, useRef, useState } from 'react';
import { useVoiceAssistant } from '@livekit/components-react';
import { cn } from '@/lib/utils';

interface AliceFaceProps {
  className?: string;
}

type Emotion = 'idle' | 'speaking' | 'listening' | 'thinking' | 'happy' | 'concerned';

export function AliceFace({ className }: AliceFaceProps) {
  const { state, audioTrack } = useVoiceAssistant();
  const [emotion, setEmotion] = useState<Emotion>('idle');
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();

  // Map agent state to emotions
  useEffect(() => {
    switch (state) {
      case 'listening':
        setEmotion('listening');
        break;
      case 'thinking':
        setEmotion('thinking');
        break;
      case 'speaking':
        setEmotion('speaking');
        break;
      default:
        setEmotion('idle');
    }
  }, [state]);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let blinkTimer = 0;
    let mouthOpen = 0;
    let eyeOffset = 0;

    const animate = () => {
      // Clear canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw face
      drawFace(ctx, emotion, blinkTimer, mouthOpen, eyeOffset);

      // Update animations
      blinkTimer = (blinkTimer + 0.1) % 100;
      if (emotion === 'speaking') {
        mouthOpen = Math.sin(Date.now() / 100) * 10 + 10;
      } else {
        mouthOpen = 0;
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [emotion]);

  return (
    <div className={cn('relative', className)}>
      {/* Placeholder for custom avatar */}
      <div className="relative aspect-square w-full max-w-md mx-auto">
        {/* You can replace this with actual avatar image/video */}
        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-purple-500/20 rounded-full" />
        
        {/* Canvas for facial animations */}
        <canvas
          ref={canvasRef}
          width={400}
          height={400}
          className="absolute inset-0 w-full h-full"
        />

        {/* Status indicator */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2">
          <div className={cn(
            'px-4 py-2 rounded-full backdrop-blur-sm text-sm font-medium',
            emotion === 'listening' && 'bg-cyan-500/20 text-cyan-300',
            emotion === 'thinking' && 'bg-purple-500/20 text-purple-300',
            emotion === 'speaking' && 'bg-green-500/20 text-green-300',
            emotion === 'idle' && 'bg-gray-500/20 text-gray-300'
          )}>
            {emotion === 'listening' && '👂 Listening...'}
            {emotion === 'thinking' && '🤔 Thinking...'}
            {emotion === 'speaking' && '💬 Speaking...'}
            {emotion === 'idle' && '😊 Ready'}
          </div>
        </div>
      </div>
    </div>
  );
}

// Simple face drawing function (placeholder)
function drawFace(
  ctx: CanvasRenderingContext2D,
  emotion: Emotion,
  blinkTimer: number,
  mouthOpen: number,
  eyeOffset: number
) {
  const centerX = ctx.canvas.width / 2;
  const centerY = ctx.canvas.height / 2;

  // Face outline
  ctx.strokeStyle = 'rgba(31, 213, 249, 0.5)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(centerX, centerY, 100, 0, Math.PI * 2);
  ctx.stroke();

  // Eyes
  const eyeY = centerY - 20;
  const eyeBlink = blinkTimer > 95 ? 5 : 0;
  
  // Left eye
  ctx.fillStyle = '#1fd5f9';
  ctx.beginPath();
  ctx.ellipse(centerX - 30, eyeY + eyeOffset, 8, 12 - eyeBlink, 0, 0, Math.PI * 2);
  ctx.fill();

  // Right eye
  ctx.beginPath();
  ctx.ellipse(centerX + 30, eyeY + eyeOffset, 8, 12 - eyeBlink, 0, 0, Math.PI * 2);
  ctx.fill();

  // Mouth
  ctx.strokeStyle = '#1fd5f9';
  ctx.lineWidth = 2;
  ctx.beginPath();
  
  if (emotion === 'speaking') {
    // Open mouth
    ctx.arc(centerX, centerY + 30, 15, 0, Math.PI);
  } else if (emotion === 'happy') {
    // Smile
    ctx.arc(centerX, centerY + 20, 30, 0.2, Math.PI - 0.2);
  } else {
    // Neutral
    ctx.moveTo(centerX - 20, centerY + 30);
    ctx.lineTo(centerX + 20, centerY + 30);
  }
  
  ctx.stroke();
}
