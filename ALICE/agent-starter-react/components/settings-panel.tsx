'use client';

import { useState, useEffect } from 'react';
import { GearIcon } from '@phosphor-icons/react';
import { cn } from '@/lib/utils';

interface ColorSettings {
  visualizer: string;
  microphone: string;
  camera: string;
  screenShare: string;
  chat: string;
  sayBye: string;
  inputBorder: string;
  text: string;
}

const DEFAULT_COLORS: ColorSettings = {
  visualizer: '#1fd5f9',
  microphone: '#ffffff',
  camera: '#ffffff',
  screenShare: '#ffffff',
  chat: '#ffffff',
  sayBye: '#ff5757',
  inputBorder: '#1fd5f9',
  text: '#ffffff',
};

export function SettingsPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [colors, setColors] = useState<ColorSettings>(DEFAULT_COLORS);

  useEffect(() => {
    // Load saved colors from localStorage
    const savedColors = localStorage.getItem('alice-color-settings');
    if (savedColors) {
      const parsed = JSON.parse(savedColors);
      setColors(parsed);
      applyColors(parsed);
    }
  }, []);

  const applyColors = (colorSettings: ColorSettings) => {
    document.documentElement.style.setProperty('--primary', colorSettings.visualizer);
    document.documentElement.style.setProperty('--alice-mic-color', colorSettings.microphone);
    document.documentElement.style.setProperty('--alice-camera-color', colorSettings.camera);
    document.documentElement.style.setProperty('--alice-screen-color', colorSettings.screenShare);
    document.documentElement.style.setProperty('--alice-chat-color', colorSettings.chat);
    document.documentElement.style.setProperty('--alice-bye-color', colorSettings.sayBye);
    document.documentElement.style.setProperty('--alice-input-border', colorSettings.inputBorder);
    document.documentElement.style.setProperty('--alice-text-color', colorSettings.text);
    localStorage.setItem('alice-color-settings', JSON.stringify(colorSettings));
  };

  const handleColorChange = (key: keyof ColorSettings, value: string) => {
    const newColors = { ...colors, [key]: value };
    setColors(newColors);
    applyColors(newColors);
  };

  const resetToDefaults = () => {
    setColors(DEFAULT_COLORS);
    applyColors(DEFAULT_COLORS);
  };

  const presetColors = [
    { name: 'Cyan', color: '#1fd5f9' },
    { name: 'Orange', color: '#ff6b35' },
    { name: 'Purple', color: '#a855f7' },
    { name: 'Green', color: '#10b981' },
    { name: 'Pink', color: '#ec4899' },
    { name: 'Blue', color: '#3b82f6' },
    { name: 'White', color: '#ffffff' },
    { name: 'Red', color: '#ff5757' },
  ];

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Settings Panel */}
      {isOpen && (
        <div className="mb-2 w-80 max-h-[80vh] overflow-y-auto rounded-lg border border-white/10 bg-black/95 backdrop-blur-sm p-4 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">Color Settings</h3>
            <button
              onClick={resetToDefaults}
              className="text-xs text-cyan-400 hover:text-cyan-300 uppercase tracking-wider"
            >
              Reset
            </button>
          </div>
          
          <div className="space-y-4">
            {/* Audio Visualizer */}
            <ColorControl
              label="Audio Visualizer Circles"
              value={colors.visualizer}
              onChange={(value) => handleColorChange('visualizer', value)}
              presets={presetColors}
            />

            {/* Microphone Icon */}
            <ColorControl
              label="Microphone Icon"
              value={colors.microphone}
              onChange={(value) => handleColorChange('microphone', value)}
              presets={presetColors}
            />

            {/* Camera Icon */}
            <ColorControl
              label="Camera Icon"
              value={colors.camera}
              onChange={(value) => handleColorChange('camera', value)}
              presets={presetColors}
            />

            {/* Screen Share Icon */}
            <ColorControl
              label="Screen Share Icon"
              value={colors.screenShare}
              onChange={(value) => handleColorChange('screenShare', value)}
              presets={presetColors}
            />

            {/* Chat Icon */}
            <ColorControl
              label="Chat Icon"
              value={colors.chat}
              onChange={(value) => handleColorChange('chat', value)}
              presets={presetColors}
            />

            {/* Say Bye Button */}
            <ColorControl
              label="Say Bye Button"
              value={colors.sayBye}
              onChange={(value) => handleColorChange('sayBye', value)}
              presets={presetColors}
            />

            {/* Input Border */}
            <ColorControl
              label="Input Field Border"
              value={colors.inputBorder}
              onChange={(value) => handleColorChange('inputBorder', value)}
              presets={presetColors}
            />

            {/* Text Color */}
            <ColorControl
              label="Text Color"
              value={colors.text}
              onChange={(value) => handleColorChange('text', value)}
              presets={presetColors}
            />
          </div>
        </div>
      )}

      {/* Settings Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'w-12 h-12 rounded-full transition-all duration-300',
          'flex items-center justify-center',
          'border-2',
          isOpen
            ? 'bg-white/10 border-white/30 backdrop-blur-sm'
            : 'bg-black/50 border-white/20 hover:bg-white/10 hover:border-white/30'
        )}
        aria-label="Settings"
      >
        <GearIcon
          size={24}
          weight="bold"
          className={cn(
            'text-white transition-transform duration-300',
            isOpen && 'rotate-90'
          )}
        />
      </button>
    </div>
  );
}

interface ColorControlProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  presets: { name: string; color: string }[];
}

function ColorControl({ label, value, onChange, presets }: ColorControlProps) {
  return (
    <div className="space-y-2 pb-3 border-b border-white/5 last:border-0">
      <label className="block text-xs text-gray-400 font-medium">{label}</label>
      
      {/* Color Picker */}
      <div className="flex items-center gap-2">
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-10 h-10 rounded cursor-pointer border-2 border-white/20"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 bg-white/5 border border-white/10 rounded px-3 py-2 text-white text-xs font-mono"
          placeholder="#ffffff"
        />
      </div>

      {/* Quick Presets */}
      <div className="grid grid-cols-4 gap-1.5">
        {presets.slice(0, 4).map((preset) => (
          <button
            key={preset.name}
            onClick={() => onChange(preset.color)}
            className={cn(
              'h-7 rounded border transition-all',
              value === preset.color
                ? 'border-white scale-105'
                : 'border-white/20 hover:border-white/40'
            )}
            style={{ backgroundColor: preset.color }}
            title={preset.name}
          />
        ))}
      </div>
    </div>
  );
}
