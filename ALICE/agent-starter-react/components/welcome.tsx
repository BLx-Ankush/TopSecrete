'use client';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useEffect, useRef, useState } from 'react';

interface WelcomeProps {
  disabled: boolean;
  startButtonText: string;
  onStartCall: () => void;
}

export const Welcome = ({
  disabled,
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeProps) => {
  const canvasContainerRef = useRef<HTMLDivElement>(null);
  const preloaderRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    let cleanup: (() => void) | undefined = undefined;

    const initSpectralGhost = async () => {
      if (!canvasContainerRef.current) return;

      try {
        // Import required libraries
        const THREE = await import('three');
        const { EffectComposer, RenderPass, BloomEffect, EffectPass, ShaderPass } = await import('postprocessing');

        // Preloader management
        class PreloaderManager {
          steps: number;
          currentStep: number;
          progressBar: HTMLElement | null;

          constructor() {
            this.steps = 5;
            this.currentStep = 0;
            this.progressBar = preloaderRef.current?.querySelector('.progress-bar') as HTMLElement;
          }

          updateProgress(step: number) {
            this.currentStep = step;
            const progress = (step / this.steps) * 100;
            if (this.progressBar) {
              this.progressBar.style.width = `${progress}%`;
              this.progressBar.style.opacity = '1';
            }
          }

          complete(canvas: HTMLCanvasElement) {
            setTimeout(() => {
              if (preloaderRef.current) {
                preloaderRef.current.classList.add('fade-out');
              }
              if (contentRef.current) {
                contentRef.current.classList.add('fade-in');
              }
              if (canvas) {
                canvas.classList.add('fade-in');
              }
              
              setTimeout(() => {
                setIsLoaded(true);
              }, 1000);
            }, 500);
          }
        }

        const preloader = new PreloaderManager();

        // Force browser to use GPU acceleration
        if (canvasContainerRef.current) {
          canvasContainerRef.current.style.transform = "translateZ(0)";
          canvasContainerRef.current.style.backfaceVisibility = "hidden";
          canvasContainerRef.current.style.perspective = "1000px";
        }

        preloader.updateProgress(1);

        // Create scene
        const scene = new THREE.Scene();
        scene.background = null;

        const camera = new THREE.PerspectiveCamera(
          75,
          window.innerWidth / window.innerHeight,
          0.1,
          1000
        );
        camera.position.z = 20;

        preloader.updateProgress(2);

        // Enhanced renderer with transparency
        const renderer = new THREE.WebGLRenderer({
          antialias: true,
          powerPreference: "high-performance",
          alpha: true,
          premultipliedAlpha: false,
          stencil: false,
          depth: true,
          preserveDrawingBuffer: false
        });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 0.9;
        renderer.setClearColor(0x000000, 0);
        
        // Append canvas to our container
        canvasContainerRef.current.appendChild(renderer.domElement);

        // Canvas styling - initially hidden
        renderer.domElement.style.position = "absolute";
        renderer.domElement.style.top = "0";
        renderer.domElement.style.left = "0";
        renderer.domElement.style.zIndex = "2";
        renderer.domElement.style.pointerEvents = "auto";
        renderer.domElement.style.background = "transparent";
        renderer.domElement.style.opacity = "0";
        renderer.domElement.style.transition = "opacity 2s ease-in";

        // Store original bloom values
        const originalBloomSettings = {
          strength: 0.3,
          radius: 1.25,
          threshold: 0.0
        };

        // Setup post-processing for bloom effects
        const composer = new EffectComposer(renderer);
        const renderPass = new RenderPass(scene, camera);
        composer.addPass(renderPass);

        // Fixed bloom settings to avoid transparency issues
        const bloomEffect = new BloomEffect({
          luminanceThreshold: originalBloomSettings.threshold,
          luminanceSmoothing: 0.9,
          intensity: originalBloomSettings.strength,
          radius: originalBloomSettings.radius
        });
        const bloomPass = new EffectPass(camera, bloomEffect);
        composer.addPass(bloomPass);

        preloader.updateProgress(3);

        // Production parameters
        const params = {
          bodyColor: 0x0f2027,
          glowColor: "orange",
          eyeGlowColor: "green",
          ghostOpacity: 0.88,
          emissiveIntensity: 5.8,
          pulseSpeed: 1.6,
          pulseIntensity: 0.6,
          eyeGlowIntensity: 4.5,
          eyeGlowDecay: 0.95,
          eyeGlowResponse: 0.31,
          rimLightIntensity: 1.8,
          followSpeed: 0.075,
          wobbleAmount: 0.35,
          floatSpeed: 1.6,
          movementThreshold: 0.07,
          revealRadius: 43,
          fadeStrength: 2.2,
          baseOpacity: 0.35,
          revealOpacity: 0.0,
          analogIntensity: 0.6
        };

        // Fluorescent color palette
        const fluorescentColors: Record<string, number> = {
          cyan: 0x00ffff,
          lime: 0x00ff00,
          magenta: 0xff00ff,
          yellow: 0xffff00,
          orange: 0xff4500,
          pink: 0xff1493,
          purple: 0x9400d3,
          blue: 0x0080ff,
          green: 0x00ff80,
          red: 0xff0040,
          teal: 0x00ffaa,
          violet: 0x8a2be2
        };

        // Create atmosphere
        const atmosphereGeometry = new THREE.PlaneGeometry(300, 300);
        const atmosphereMaterial = new THREE.ShaderMaterial({
          uniforms: {
            ghostPosition: { value: new THREE.Vector3(0, 0, 0) },
            revealRadius: { value: params.revealRadius },
            fadeStrength: { value: params.fadeStrength },
            baseOpacity: { value: params.baseOpacity },
            revealOpacity: { value: params.revealOpacity },
            time: { value: 0 }
          },
          vertexShader: `
            varying vec2 vUv;
            varying vec3 vWorldPosition;
            void main() {
              vUv = uv;
              vec4 worldPos = modelMatrix * vec4(position, 1.0);
              vWorldPosition = worldPos.xyz;
              gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
          `,
          fragmentShader: `
            uniform vec3 ghostPosition;
            uniform float revealRadius;
            uniform float fadeStrength;
            uniform float baseOpacity;
            uniform float revealOpacity;
            uniform float time;
            varying vec2 vUv;
            varying vec3 vWorldPosition;
            
            void main() {
              float dist = distance(vWorldPosition.xy, ghostPosition.xy);
              
              float dynamicRadius = revealRadius + sin(time * 2.0) * 5.0;
              
              float reveal = smoothstep(dynamicRadius * 0.2, dynamicRadius, dist);
              reveal = pow(reveal, fadeStrength);
              
              float opacity = mix(revealOpacity, baseOpacity, reveal);
              
              gl_FragColor = vec4(0.001, 0.001, 0.002, opacity);
            }
          `,
          transparent: true,
          depthWrite: false
        });

        const atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial);
        atmosphere.position.z = -50;
        atmosphere.renderOrder = -100;
        scene.add(atmosphere);

        // Minimal ambient light
        const ambientLight = new THREE.AmbientLight(0x0a0a2e, 0.08);
        scene.add(ambientLight);

        // Create ghost
        const ghostGroup = new THREE.Group();
        scene.add(ghostGroup);

        const ghostGeometry = new THREE.SphereGeometry(2, 40, 40);
        const positionAttribute = ghostGeometry.getAttribute("position");
        const positions = positionAttribute.array;
        for (let i = 0; i < positions.length; i += 3) {
          if (positions[i + 1] < -0.2) {
            const wobbleX = Math.sin(positions[i] * 3) * 0.3;
            const wobbleY = Math.cos(positions[i + 2] * 2) * 0.2;
            positions[i] += wobbleX;
            positions[i + 1] += wobbleY;
          }
        }
        ghostGeometry.computeVertexNormals();

        const ghostMaterial = new THREE.MeshStandardMaterial({
          color: params.bodyColor,
          transparent: true,
          opacity: params.ghostOpacity,
          emissive: fluorescentColors[params.glowColor],
          emissiveIntensity: params.emissiveIntensity,
          roughness: 0.02,
          metalness: 0.0,
          side: THREE.DoubleSide,
          alphaTest: 0.1
        });

        const ghostBody = new THREE.Mesh(ghostGeometry, ghostMaterial);
        ghostGroup.add(ghostBody);

        // Rim lights
        const rimLight1 = new THREE.DirectionalLight(0x4a90e2, params.rimLightIntensity);
        rimLight1.position.set(-8, 6, -4);
        scene.add(rimLight1);

        const rimLight2 = new THREE.DirectionalLight(0x50e3c2, params.rimLightIntensity * 0.7);
        rimLight2.position.set(8, -4, -6);
        scene.add(rimLight2);

        preloader.updateProgress(4);

        // Create eyes
        const eyeGroup = new THREE.Group();
        ghostGroup.add(eyeGroup);

        const socketGeometry = new THREE.SphereGeometry(0.45, 16, 16);
        const socketMaterial = new THREE.MeshBasicMaterial({ color: 0x000000 });

        const leftSocket = new THREE.Mesh(socketGeometry, socketMaterial);
        leftSocket.position.set(-0.7, 0.6, 1.9);
        leftSocket.scale.set(1.1, 1.0, 0.6);
        eyeGroup.add(leftSocket);

        const rightSocket = new THREE.Mesh(socketGeometry, socketMaterial);
        rightSocket.position.set(0.7, 0.6, 1.9);
        rightSocket.scale.set(1.1, 1.0, 0.6);
        eyeGroup.add(rightSocket);

        const eyeGeometry = new THREE.SphereGeometry(0.3, 12, 12);
        const leftEyeMaterial = new THREE.MeshBasicMaterial({
          color: fluorescentColors[params.eyeGlowColor],
          transparent: true,
          opacity: 0
        });
        const leftEye = new THREE.Mesh(eyeGeometry, leftEyeMaterial);
        leftEye.position.set(-0.7, 0.6, 2.0);
        eyeGroup.add(leftEye);

        const rightEyeMaterial = new THREE.MeshBasicMaterial({
          color: fluorescentColors[params.eyeGlowColor],
          transparent: true,
          opacity: 0
        });
        const rightEye = new THREE.Mesh(eyeGeometry, rightEyeMaterial);
        rightEye.position.set(0.7, 0.6, 2.0);
        eyeGroup.add(rightEye);

        // Create glitch overlay
        const glitchGeometry = new THREE.PlaneGeometry(2, 2);
        const glitchMaterial = new THREE.ShaderMaterial({
          uniforms: {
            time: { value: 0.0 },
            resolution: { value: new THREE.Vector2(window.innerWidth, window.innerHeight) },
            glitchIntensity: { value: 0.3 }
          },
          vertexShader: `
            varying vec2 vUv;
            void main() {
              vUv = uv;
              gl_Position = vec4(position, 1.0);
            }
          `,
          fragmentShader: `
            uniform float time;
            uniform vec2 resolution;
            uniform float glitchIntensity;
            varying vec2 vUv;
            
            float random(vec2 st) {
              return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
            }
            
            void main() {
              vec2 uv = vUv;
              float glitchTime = floor(time * 4.0);
              
              // Horizontal glitch lines
              float glitch = step(0.98, random(vec2(floor(uv.y * 100.0), glitchTime)));
              
              // RGB shift
              vec2 shift = vec2(
                sin(time * 10.0 + uv.y * 50.0) * 0.01,
                cos(time * 8.0 + uv.x * 30.0) * 0.005
              ) * glitchIntensity;
              
              vec3 color = vec3(0.0);
              
              // Digital noise overlay
              float noise = random(uv + time) * 0.1;
              
              // Scanlines
              float scanline = sin(uv.y * 800.0) * 0.1;
              
              color += vec3(noise + scanline) * glitchIntensity;
              color.r += glitch * 0.5;
              color.g += glitch * 0.3;
              
              gl_FragColor = vec4(color, glitchIntensity * 0.3);
            }
          `,
          transparent: true,
          blending: THREE.AdditiveBlending
        });

        const glitchCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
        const glitchScene = new THREE.Scene();
        const glitchMesh = new THREE.Mesh(glitchGeometry, glitchMaterial);
        glitchScene.add(glitchMesh);

        // Mouse tracking
        const mouse = new THREE.Vector2();
        let isMouseMoving = false;

        const handleMouseMove = (e: MouseEvent) => {
          mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
          mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
          isMouseMoving = true;
        };

        window.addEventListener('mousemove', handleMouseMove);

        // Animation variables
        let time = 0;
        let currentEyeGlow = 0;

        // Animation loop
        const animate = (timestamp: number) => {
          requestAnimationFrame(animate);

          time = timestamp * 0.001;

          // Update shader uniforms - removed problematic analog decay
          atmosphereMaterial.uniforms.time.value = time;

          // Ghost movement
          const targetX = mouse.x * 3;
          const targetY = mouse.y * 3;

          ghostGroup.position.x += (targetX - ghostGroup.position.x) * params.followSpeed;
          ghostGroup.position.y += (targetY - ghostGroup.position.y) * params.followSpeed;

          // Ghost floating
          const floatOffset = Math.sin(time * params.floatSpeed) * params.wobbleAmount;
          ghostGroup.position.y += floatOffset * 0.1;

          // Eye glow based on movement
          if (isMouseMoving) {
            currentEyeGlow = Math.min(currentEyeGlow + params.eyeGlowResponse, params.eyeGlowIntensity);
            isMouseMoving = false;
          } else {
            currentEyeGlow *= params.eyeGlowDecay;
          }

          leftEyeMaterial.opacity = Math.min(currentEyeGlow / params.eyeGlowIntensity, 1);
          rightEyeMaterial.opacity = Math.min(currentEyeGlow / params.eyeGlowIntensity, 1);

          // Update atmosphere
          atmosphereMaterial.uniforms.ghostPosition.value.copy(ghostGroup.position);

          // Animate glitch overlay
          glitchMaterial.uniforms.time.value = time;
          
          // Make glitch more intense when mouse moves
          const targetGlitchIntensity = isMouseMoving ? 0.6 : 0.1;
          const currentIntensity = glitchMaterial.uniforms.glitchIntensity.value;
          glitchMaterial.uniforms.glitchIntensity.value = THREE.MathUtils.lerp(currentIntensity, targetGlitchIntensity, 0.1);

          // Pulse effect
          const pulseValue = 1 + Math.sin(time * params.pulseSpeed) * params.pulseIntensity;
          ghostMaterial.emissiveIntensity = params.emissiveIntensity * pulseValue;

          // Render main scene
          composer.render();
          
          // Render glitch overlay on top
          renderer.autoClear = false;
          renderer.render(glitchScene, glitchCamera);
          renderer.autoClear = true;
        };

        // Window resize
        const handleResize = () => {
          camera.aspect = window.innerWidth / window.innerHeight;
          camera.updateProjectionMatrix();
          renderer.setSize(window.innerWidth, window.innerHeight);
          composer.setSize(window.innerWidth, window.innerHeight);
        };

        window.addEventListener('resize', handleResize);

        // Complete loading and start
        preloader.updateProgress(5);
        preloader.complete(renderer.domElement);

        // Start animation
        animate(0);

        // Cleanup function
        cleanup = () => {
          window.removeEventListener('mousemove', handleMouseMove);
          window.removeEventListener('resize', handleResize);
          
          if (canvasContainerRef.current && renderer.domElement.parentNode) {
            canvasContainerRef.current.removeChild(renderer.domElement);
          }
          
          renderer.dispose();
          ghostGeometry.dispose();
          ghostMaterial.dispose();
          socketGeometry.dispose();
          socketMaterial.dispose();
          eyeGeometry.dispose();
          leftEyeMaterial.dispose();
          rightEyeMaterial.dispose();
          atmosphereGeometry.dispose();
          atmosphereMaterial.dispose();
          glitchGeometry.dispose();
          glitchMaterial.dispose();
        };

      } catch (error) {
        console.error('Error initializing spectral ghost scene:', error);
        setIsLoaded(true); // Show content anyway
        // Make sure preloader completes even if WebGL fails
        if (preloaderRef.current) {
          setTimeout(() => {
            if (preloaderRef.current) {
              preloaderRef.current.classList.add('fade-out');
            }
            if (contentRef.current) {
              contentRef.current.classList.add('fade-in');
            }
          }, 1000);
        }
      }
    };

    initSpectralGhost();

    return () => {
      if (cleanup) {
        cleanup();
      }
    };
  }, []);

  return (
    <section
      ref={ref}
      inert={disabled}
      className={cn(
        'fixed inset-0 mx-auto flex h-svh flex-col items-center justify-center text-center',
        disabled ? 'z-10' : 'z-20'
      )}
    >
      {/* Inject the original CSS styles */}
      <style jsx global>{`
        @import url("https://fonts.googleapis.com/css2?family=Boldonse&display=swap");

        @font-face {
          font-family: "PPSupplyMono";
          src: url("https://assets.codepen.io/7558/PPSupplyMono-Variable.woff2") format("woff2");
          font-weight: 100 900;
          font-style: normal;
        }

        .ghost-loader {
          position: relative;
          width: 64px;
          height: 64px;
          margin: 0 auto 30px;
          display: flex;
          justify-content: center;
          align-items: center;
        }

        .ghost-svg {
          filter: drop-shadow(0 0 20px rgba(255, 255, 255, 0.3));
          animation: ghostFloat 3s ease-in-out infinite;
        }

        .ghost-body {
          fill: white;
          opacity: 0.9;
        }

        .ghost-eye {
          fill: black;
          animation: eyePulse 2s ease-in-out infinite;
          transform-origin: center;
        }

        .left-eye {
          animation-delay: 0s;
        }

        .right-eye {
          animation-delay: 0.1s;
        }

        @keyframes ghostFloat {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-8px);
          }
        }

        @keyframes eyePulse {
          0%, 100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.3);
          }
        }

        .loading-text {
          font-family: "PPSupplyMono", monospace;
          font-size: 12px;
          text-transform: uppercase;
          opacity: 1;
          margin-bottom: 12px;
          animation: textPulse 2s ease-in-out infinite;
        }

        @keyframes textPulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.1;
          }
        }

        .loading-progress {
          width: 96px;
          height: 1px;
          margin: 0 auto;
          border-radius: 1px;
          overflow: hidden;
        }

        .progress-bar {
          height: 100%;
          background: linear-gradient(90deg, #00ff80, #00cc66);
          opacity: 0.1;
          width: 0%;
          transition: width 0.8s ease;
        }

        .content {
          opacity: 0;
          transition: opacity 1.5s ease-in;
        }

        .content.fade-in {
          opacity: 1;
        }

        .quote {
          font-family: "Boldonse", system-ui;
          font-size: 6vw;
          line-height: 1.3;
          font-weight: 400;
          letter-spacing: -0.02em;
          margin-bottom: 5vh;
          text-transform: uppercase;
        }

        .author {
          font-family: "PPSupplyMono", monospace;
          font-size: 12px;
          text-transform: uppercase;
          opacity: 0.7;
          margin-top: 2vh;
        }

        canvas {
          opacity: 0 !important;
          transition: opacity 2s ease-in;
        }

        canvas.fade-in {
          opacity: 1 !important;
        }

        .preloader {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 10000;
          opacity: 1;
          transition: opacity 1s ease-out;
        }

        .preloader.fade-out {
          opacity: 0;
          pointer-events: none;
        }

        .preloader-content {
          text-align: center;
          color: #e0e0e0;
        }
      `}</style>

      {/* Canvas container */}
      <div 
        ref={canvasContainerRef} 
        className="absolute inset-0 w-full h-full"
        style={{
          background: '#000000'
        }}
      />

      {/* Preloader */}
      <div ref={preloaderRef} className="preloader">
        <div className="preloader-content">
          <div className="ghost-loader">
            <svg className="ghost-svg" height="80" viewBox="0 0 512 512" width="80" xmlns="http://www.w3.org/2000/svg">
              <path className="ghost-body" d="m508.374 432.802s-46.6-39.038-79.495-275.781c-8.833-87.68-82.856-156.139-172.879-156.139-90.015 0-164.046 68.458-172.879 156.138-32.895 236.743-79.495 275.782-79.495 275.782-15.107 25.181 20.733 28.178 38.699 27.94 35.254-.478 35.254 40.294 70.516 40.294 35.254 0 35.254-35.261 70.508-35.261s37.396 45.343 72.65 45.343s37.389-45.343 72.651-45.343c35.254 0 35.254 35.261 70.508 35.261s35.27-40.772 70.524-40.294c17.959.238 53.798-2.76 38.692-27.94z" fill="white" />
              <circle className="ghost-eye left-eye" cx="208" cy="225" r="22" fill="black" />
              <circle className="ghost-eye right-eye" cx="297" cy="225" r="22" fill="black" />
            </svg>
          </div>
          <div className="loading-text">Summoning ALICE</div>
          <div className="loading-progress">
            <div className="progress-bar"></div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div ref={contentRef} className="content absolute inset-0 flex flex-col items-center justify-center text-center z-10">
        <div className="quote-container max-w-[90%] overflow-hidden">
          <h1 className="quote text-white">
            ALICE
          </h1>
          <span className="author text-gray-400">Mi Amor</span>
        </div>

        {/* START UI Button */}
        {isLoaded && (
          <Button
            variant="primary"
            size="lg"
            onClick={() => {
              const clickSound = new Audio("/button-click.m4a");
              clickSound.volume = 0.3;
              clickSound.play();
              onStartCall();
            }}
            className="mt-8 px-12 py-4 text-xl font-mono bg-transparent border-2 border-orange-500 text-orange-500 hover:bg-orange-500 hover:text-black rounded-none transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-orange-500/25"
            style={{
              textTransform: 'uppercase',
              letterSpacing: '0.2em',
              filter: 'drop-shadow(0 0 10px rgba(255, 165, 0, 0.5))'
            }}
          >
            START UI
          </Button>
        )}
      </div>

      <footer className="fixed bottom-5 left-0 z-30 flex w-full items-center justify-center">
        <p className="text-orange-400 max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          DM for any Queries:{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://www.instagram.com/07__alone?igsh=OXp5YjU0dnU4bDBq"
            className="text-orange-300 hover:text-orange-200 transition-colors"
          >
            07__alone
          </a>
          .
        </p>
      </footer>
    </section>
  );
};
