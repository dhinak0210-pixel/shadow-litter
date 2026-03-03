"use client";

import { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { MapControls, useTexture, Html, Billboard, Sphere } from '@react-three/drei';
import * as THREE from 'three';
import { motion, AnimatePresence } from 'framer-motion';
import { OrbitalColors, Glassmorphism } from '@/lib/design-system/tokens';
import { OrbitalType } from '@/lib/design-system/typography';
import { TypewriterStatus } from './luxury/LuxuryComponents';

function MaduraiTerrain() {
    const texture = useTexture('/textures/madurai_satellite_2024.png');
    const elevation = useTexture('/textures/madurai_elevation.png');

    const geometry = useMemo(() => {
        const geo = new THREE.PlaneGeometry(30, 30, 128, 128);
        return geo;
    }, []);

    return (
        <mesh geometry={geometry} rotation={[-Math.PI / 2, 0, 0]}>
            <meshStandardMaterial
                map={texture}
                displacementMap={elevation}
                displacementScale={3}
                roughness={0.9}
                metalness={0.1}
            />
        </mesh>
    );
}

function DetectionMarker({ position, detection, onClick }: { position: [number, number, number], detection: any, onClick: () => void }) {
    const groupRef = useRef<THREE.Group>(null!);
    const [hovered, setHovered] = useState(false);

    useFrame((state) => {
        groupRef.current.position.y = position[1] + Math.sin(state.clock.elapsedTime * 2) * 0.1 + 0.5;
    });

    const colors: any = {
        fresh_dump: OrbitalColors.toxicity.fresh,
        construction: OrbitalColors.toxicity.construction,
        chemical: OrbitalColors.toxicity.chemical,
        leachate: OrbitalColors.toxicity.leachate,
    };

    const color = colors[detection.type] || OrbitalColors.signal.warning;

    return (
        <group ref={groupRef} position={position} onClick={onClick} onPointerOver={() => setHovered(true)} onPointerOut={() => setHovered(false)}>
            <Billboard>
                <Html transform occlude distanceFactor={8}>
                    <motion.div initial={{ opacity: 0, scale: 0 }} animate={{ opacity: 1, scale: 1 }} style={{ width: '180px', transform: hovered ? 'scale(1.1)' : 'scale(1)', transition: 'transform 0.3s' }}>
                        <div style={{ ...Glassmorphism.hologram, padding: '12px', borderRadius: '8px' }}>
                            <div style={{ fontFamily: OrbitalType.fontFamily.mono, fontSize: '10px', color, textTransform: 'uppercase', letterSpacing: '0.1em' }}>{detection.type.replace('_', ' ')}</div>
                            <div style={{ fontFamily: OrbitalType.fontFamily.display, fontSize: '16px', color: '#fff', marginTop: '4px' }}>{detection.area_sqm} m²</div>
                            <div style={{ fontFamily: OrbitalType.fontFamily.mono, fontSize: '9px', color: '#9CA3AF', marginTop: '2px' }}>{detection.confidence}% confidence</div>
                        </div>
                    </motion.div>
                </Html>
            </Billboard>

            <Sphere args={[0.15, 16, 16]}>
                <meshStandardMaterial color={color} emissive={color} emissiveIntensity={3} />
            </Sphere>
            <Sphere args={[0.3, 16, 16]}>
                <meshBasicMaterial color={color} transparent opacity={0.2} />
            </Sphere>
        </group>
    );
}

import { useShadowLitter } from '@/app/providers';

export function OrbitalCommandCenter() {
    const [selected, setSelected] = useState<any>(null);
    const { liveDetections } = useShadowLitter();
    const detections = liveDetections.length > 0 ? liveDetections : [
        { id: 1, position: [5, 2, 8] as [number, number, number], type: 'fresh_dump', area_sqm: 450, confidence: 94.2 },
        { id: 2, position: [-8, 2, 2] as [number, number, number], type: 'construction', area_sqm: 1200, confidence: 87.5 },
        { id: 3, position: [2, 2, -6] as [number, number, number], type: 'leachate', area_sqm: 280, confidence: 91.3 },
    ];

    return (
        <div className="relative w-full h-screen bg-black">
            <Canvas camera={{ position: [20, 20, 20], fov: 50 }}>
                <ambientLight intensity={0.5} />
                <directionalLight position={[10, 20, 10]} intensity={1.5} />
                <MapControls enableDamping dampingFactor={0.05} maxPolarAngle={Math.PI / 2.5} />
                <MaduraiTerrain />
                {detections.map(d => <DetectionMarker key={d.id} position={d.position} detection={d} onClick={() => setSelected(d)} />)}
            </Canvas>

            {/* UI Panels */}
            <div className="absolute inset-0 pointer-events-none p-8 flex flex-col justify-between">
                <div className="flex justify-between items-start pointer-events-auto">
                    <div className="flex flex-col gap-2">
                        <h2 style={{ fontFamily: OrbitalType.fontFamily.display, color: OrbitalColors.gold.primary }} className="text-3xl font-bold tracking-tighter">ORBITAL COMMAND</h2>
                        <div className="flex gap-4">
                            <span className="px-3 py-1 rounded bg-sentinel/10 border border-sentinel/30 text-sentinel text-[10px] font-mono">LIVE FEED ACTIVE</span>
                            <span className="px-3 py-1 rounded bg-white/5 border border-white/10 text-gray-400 text-[10px] font-mono">GLOBAL NORMALIZE</span>
                        </div>
                    </div>

                    {/* GLOBAL SEARCH INPUT */}
                    <div className="relative w-80">
                        <input
                            type="text"
                            placeholder="TARGET NEW CITY (e.g. Bogota)"
                            className="w-full bg-black/50 border border-white/20 text-white p-3 pl-4 rounded outline-none font-mono text-xs focus:border-sentinel transition-colors"
                            onKeyDown={async (e) => {
                                if (e.key === 'Enter') {
                                    const val = e.currentTarget.value;
                                    e.currentTarget.value = 'SCANNING ORBITAL FABRIC...';
                                    try {
                                        const res = await fetch(`http://localhost:8000/api/zones/search/${val}`);
                                        if (res.ok) {
                                            const data = await res.json();
                                            e.currentTarget.value = `${data.utm_zone} | ${data.center_lat.toFixed(2)}°N ${data.center_lon.toFixed(2)}°E`;
                                            // Real implementation would trigger 3D camera fly-to here
                                        } else {
                                            e.currentTarget.value = 'TARGET NOT FOUND';
                                        }
                                    } catch (err) {
                                        e.currentTarget.value = 'API OFFLINE';
                                    }
                                }
                            }}
                        />
                    </div>
                </div>

                <AnimatePresence>
                    {selected && (
                        <motion.div initial={{ x: 400, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 400, opacity: 0 }} className="absolute right-8 top-24 bottom-20 w-96 pointer-events-auto p-6 flex flex-col" style={Glassmorphism.satellite}>
                            <div className="flex justify-between mb-8">
                                <div>
                                    <div className="text-[10px] uppercase font-mono text-gray-500">Detection #{selected.id}</div>
                                    <div className="text-2xl font-bold font-display text-white">ORBITAL HIT</div>
                                </div>
                                <button onClick={() => setSelected(null)} className="text-gray-500 hover:text-white">✕</button>
                            </div>

                            <div className="h-48 bg-white/5 rounded-lg mb-8 border border-white/10 overflow-hidden relative">
                                <div className="absolute inset-0 bg-blue-500/10 flex items-center justify-center text-xs text-gray-500">SATELLITE IMAGE COMPONENT</div>
                                <div className="absolute top-2 left-2 px-2 py-1 bg-black/50 text-[10px] rounded">BEFORE</div>
                                <div className="absolute top-2 right-2 px-2 py-1 bg-sentinel/20 text-[10px] rounded">AFTER</div>
                            </div>

                            <div className="grid grid-cols-2 gap-4 mb-8">
                                <div className="p-4 rounded bg-white/5 border border-white/10">
                                    <div className="text-[10px] text-gray-500 font-mono">AREA</div>
                                    <div className="text-lg font-bold">{selected.area_sqm} m²</div>
                                </div>
                                <div className="p-4 rounded bg-white/5 border border-white/10">
                                    <div className="text-[10px] text-gray-500 font-mono">CONFIDENCE</div>
                                    <div className="text-lg font-bold text-sentinel">{selected.confidence}%</div>
                                </div>
                            </div>

                            <div className="mt-auto space-y-3">
                                <button className="w-full py-3 rounded border border-critical text-critical font-display text-sm hover:bg-critical/10 transition-colors" style={{ color: OrbitalColors.signal.critical, borderColor: OrbitalColors.signal.critical }}>ESCALATE PRIORITY</button>
                                <button className="w-full py-3 rounded bg-white/10 text-white font-display text-sm hover:bg-white/20 transition-colors">GENERATE REPORT</button>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                <div className="flex justify-between items-end pointer-events-auto">
                    <TypewriterStatus
                        messages={[
                            'Global normalization active...',
                            'Monitoring STAC catalogs...',
                            'Awaiting coordinates...',
                        ]}
                    />
                    <div className="flex gap-4">
                        <button className="px-6 py-3 rounded-full bg-gold-primary text-black font-bold text-xs tracking-widest hover:scale-105 transition-transform" style={{ backgroundColor: OrbitalColors.gold.primary }}>LOCK TARGET</button>
                    </div>
                </div>
            </div>
        </div>
    );
}
