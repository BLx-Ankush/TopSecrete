# Alice Avatar Implementation Guide

## Overview
This guide explains how to create an interactive, human-like face for Alice that responds to conversations.

## Quick Start Options

### Option 1: Simple Canvas Animation (Current Implementation)
**Status:** ✅ Ready to use
**File:** `components/alice-face/AliceFace.tsx`

**Usage:**
```tsx
import { AliceFace } from '@/components/alice-face/AliceFace';

<AliceFace className="w-64 h-64" />
```

**Features:**
- Basic facial animations
- State-responsive (listening, speaking, thinking)
- No external dependencies
- Lightweight

### Option 2: Live2D Anime Avatar
**Best for:** Anime-style characters like your reference image

**Steps:**
1. **Create Character:**
   - Use VRoid Studio (Free): https://vroid.com/studio
   - Or commission artist on Fiverr

2. **Export to Live2D:**
   - Export as .vrm file
   - Convert to Live2D Cubism format

3. **Install Dependencies:**
```bash
npm install pixi.js pixi-live2d-display
```

4. **Implementation:**
```typescript
// components/alice-face/Live2DAlice.tsx
import * as PIXI from 'pixi.js';
import { Live2DModel } from 'pixi-live2d-display';

export function Live2DAlice() {
  useEffect(() => {
    const app = new PIXI.Application({
      view: canvasRef.current,
      transparent: true,
      width: 400,
      height: 600
    });

    (async function() {
      const model = await Live2DModel.from('/models/alice.model3.json');
      
      app.stage.addChild(model);
      
      // Lip sync
      model.internalModel.coreModel.setParameterValueById(
        'ParamMouthOpenY', 
        mouthValue
      );
      
      // Eye blink
      model.internalModel.motionManager.startRandomMotion('Idle');
    })();
  }, []);
  
  return <canvas ref={canvasRef} />;
}
```

### Option 3: D-ID Realistic Avatar
**Best for:** Photorealistic human face

**Steps:**
1. **Sign up:** https://www.d-id.com/
2. **Get API Key**
3. **Create talking avatar:**

```typescript
// components/alice-face/RealisticAlice.tsx
const createAvatar = async (text: string) => {
  const response = await fetch('https://api.d-id.com/talks', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.NEXT_PUBLIC_DID_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      script: {
        type: 'text',
        input: text,
      },
      source_url: 'https://your-site.com/alice-portrait.jpg',
      config: { fluent: true, pad_audio: 0 }
    })
  });
  
  return response.json();
};
```

### Option 4: Ready Player Me 3D Avatar
**Best for:** Quick 3D implementation

**Steps:**
1. **Create Avatar:** https://readyplayer.me/
2. **Get Avatar URL**
3. **Install Three.js:**
```bash
npm install three @react-three/fiber @react-three/drei
```

4. **Implementation:**
```typescript
import { Canvas } from '@react-three/fiber';
import { useGLTF } from '@react-three/drei';

function AliceModel() {
  const { scene } = useGLTF('https://models.readyplayer.me/YOUR_ID.glb');
  return <primitive object={scene} />;
}

export function Alice3D() {
  return (
    <Canvas>
      <ambientLight intensity={0.5} />
      <AliceModel />
    </Canvas>
  );
}
```

## Integration with Session View

Update `session-view.tsx` to include the avatar:

```typescript
import { AliceFace } from '@/components/alice-face/AliceFace';

export const SessionView = ({ ... }) => {
  return (
    <section>
      {/* Add avatar at top center */}
      <div className="fixed top-20 left-1/2 -translate-x-1/2 z-40">
        <AliceFace className="w-48 h-48" />
      </div>
      
      {/* Existing chat and controls */}
      <ChatMessageView>...</ChatMessageView>
      <MediaTiles />
      <AgentControlBar />
    </section>
  );
};
```

## Advanced Features

### Real-time Lip Sync
```typescript
import { useEffect } from 'react';

function useLipSync(audioTrack) {
  const [mouthValue, setMouthValue] = useState(0);
  
  useEffect(() => {
    if (!audioTrack) return;
    
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(audioTrack);
    source.connect(analyser);
    
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    
    function updateMouth() {
      analyser.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      setMouthValue(average / 255);
      requestAnimationFrame(updateMouth);
    }
    
    updateMouth();
  }, [audioTrack]);
  
  return mouthValue;
}
```

### Emotion Detection
```typescript
function detectEmotion(text: string): Emotion {
  const emotions = {
    happy: /happy|joy|great|awesome|love/i,
    sad: /sad|sorry|unfortunate/i,
    excited: /excited|amazing|wonderful/i,
    thinking: /hmm|let me think|consider/i,
  };
  
  for (const [emotion, pattern] of Object.entries(emotions)) {
    if (pattern.test(text)) return emotion as Emotion;
  }
  
  return 'neutral';
}
```

## Recommended Workflow

1. **Start Simple:** Use the built-in canvas animation
2. **Get Character Art:** Commission or create your Alice design
3. **Choose Technology:** Live2D for anime, D-ID for realistic
4. **Integrate:** Replace canvas with chosen solution
5. **Add Features:** Lip sync, emotions, eye tracking

## Resources

- **Character Design:** Fiverr, ArtStation, VRoid Studio
- **Live2D:** https://www.live2d.com/
- **D-ID:** https://www.d-id.com/
- **Ready Player Me:** https://readyplayer.me/
- **Animation Tools:** Adobe Character Animator, Blender

## Cost Estimates

- **Simple Canvas:** Free
- **VRoid Studio:** Free
- **Live2D Cubism:** $49-$269 (one-time)
- **D-ID:** $0.12/minute of video
- **Character Commission:** $50-$500
- **Ready Player Me:** Free

## Next Steps

1. Try the current simple implementation
2. Decide on visual style (anime vs realistic)
3. Get character artwork
4. Implement chosen technology
5. Add lip sync and expressions

Want me to implement any specific avatar solution for you?
