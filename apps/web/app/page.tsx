"use client";

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Canvas } from '@react-three/fiber';
import { useShadowLitter } from './providers';

// 3D Components (Previously defined)
import { HeroExperience } from '../components/HeroExperience';
import { OrbitalCommandCenter } from '../components/OrbitalCommandCenter';

export default function Home() {
  const [view, setView] = useState<'hero' | 'command'>('hero');
  const { systemHealth, selectedZone } = useShadowLitter();

  return (
    <main className="min-h-screen bg-black overflow-hidden selection:bg-gold-500/30">
      <AnimatePresence mode="wait">
        {view === 'hero' ? (
          <motion.div
            key="hero"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 1.1, filter: 'blur(20px)' }}
            transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
          >
            <HeroExperience onEnter={() => setView('command')} />
          </motion.div>
        ) : (
          <motion.div
            key="command"
            initial={{ opacity: 0, scale: 0.9, filter: 'blur(20px)' }}
            animate={{ opacity: 1, scale: 1, filter: 'blur(0px)' }}
            transition={{ duration: 1.5, ease: [0.34, 1.56, 0.64, 1] }}
          >
            <OrbitalCommandCenter />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Unified Telemetry HUD overlay */}
      <div className="fixed bottom-4 left-4 z-50 pointer-events-none">
        <div className="flex items-center gap-3 px-3 py-1 bg-black/50 backdrop-blur rounded border border-white/10 text-[10px] uppercase font-mono tracking-widest text-sentinel">
          <div className={`w-1.5 h-1.5 rounded-full ${systemHealth.status === 'healthy' ? 'bg-sentinel' : 'bg-gold-primary'} animate-pulse`} />
          SYSTEM: {systemHealth.status} | {selectedZone || 'ORBITAL SCANNING'}
        </div>
      </div>
    </main>
  );
}
