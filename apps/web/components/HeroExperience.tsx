"use client";

import { useEffect, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { Stars, OrbitControls } from '@react-three/drei';
import { motion, useScroll, useTransform } from 'framer-motion';
import gsap from 'gsap';
import { OrbitalEarth } from './OrbitalEarth';
import { OrbitalColors, Glassmorphism } from '@/lib/design-system/tokens';
import { OrbitalType } from '@/lib/design-system/typography';

export function HeroExperience({ onEnter }: { onEnter: () => void }) {
    const [loaded, setLoaded] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const { scrollYProgress } = useScroll();

    const earthY = useTransform(scrollYProgress, [0, 0.5], [0, -200]);
    const textY = useTransform(scrollYProgress, [0, 0.3], [0, 100]);
    const opacity = useTransform(scrollYProgress, [0, 0.3], [1, 0]);

    useEffect(() => {
        const tl = gsap.timeline();

        tl.from('.hero-title-char', {
            y: 100,
            opacity: 0,
            rotateX: -90,
            stagger: 0.05,
            duration: 1.2,
            ease: 'power4.out',
        })
            .from('.hero-subtitle', {
                y: 50,
                opacity: 0,
                filter: 'blur(10px)',
                duration: 0.8,
                ease: 'power3.out',
            }, '-=0.6')
            .from('.hero-cta', {
                scale: 0.8,
                opacity: 0,
                duration: 0.6,
                ease: 'back.out(1.7)',
            }, '-=0.4');

        setLoaded(true);
    }, []);

    return (
        <div ref={containerRef} className="relative h-screen w-full overflow-hidden bg-black">
            <motion.div className="absolute inset-0" style={{ y: earthY }}>
                <Canvas camera={{ position: [0, 0, 4], fov: 45 }}>
                    <ambientLight intensity={0.2} />
                    <directionalLight position={[5, 3, 5]} intensity={2} />
                    <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
                    <OrbitalEarth />
                    <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.5} maxPolarAngle={Math.PI / 2} />
                </Canvas>
            </motion.div>

            <motion.div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none" style={{ y: textY, opacity }}>
                <h1 className="hero-title text-center flex flex-wrap justify-center">
                    {'SHADOW LITTER'.split('').map((char, i) => (
                        <span key={i} className="hero-title-char inline-block" style={{
                            fontFamily: OrbitalType.fontFamily.display,
                            fontSize: OrbitalType.sizes.hero,
                            fontWeight: OrbitalType.weights.bold,
                            background: OrbitalType.effects.goldShimmer.background,
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                            textShadow: '0 0 60px rgba(212, 175, 55, 0.3)',
                        }}>
                            {char === ' ' ? '\u00A0' : char}
                        </span>
                    ))}
                </h1>

                <motion.p className="hero-subtitle mt-6 text-center max-w-2xl px-4" style={{
                    fontFamily: OrbitalType.fontFamily.body,
                    fontSize: OrbitalType.sizes.subtitle,
                    color: '#9CA3AF',
                    letterSpacing: '0.2em',
                }}>
                    ORBITAL INTELLIGENCE FOR MUNICIPAL SANITATION
                </motion.p>

                <div className="hero-telemetry mt-12 flex flex-wrap justify-center gap-6 pointer-events-auto">
                    <TelemetryBadge label="SATELLITES ACTIVE" value="3" status="online" />
                    <TelemetryBadge label="LAST PASS" value="2m 34s" status="recent" />
                    <TelemetryBadge label="DETECTIONS TODAY" value="47" status="alert" />
                </div>

                <motion.button
                    onClick={onEnter}
                    className="hero-cta mt-16 pointer-events-auto"
                    whileHover={{ scale: 1.05, boxShadow: '0 0 40px rgba(212, 175, 55, 0.4)' }}
                    whileTap={{ scale: 0.95 }}
                    style={{
                        padding: '1.2rem 3rem',
                        background: 'linear-gradient(135deg, rgba(212, 175, 55, 0.2) 0%, rgba(212, 175, 55, 0.1) 100%)',
                        border: '1px solid rgba(212, 175, 55, 0.5)',
                        borderRadius: '4px',
                        fontFamily: OrbitalType.fontFamily.display,
                        fontSize: OrbitalType.sizes.body,
                        color: OrbitalColors.gold.primary,
                        letterSpacing: '0.2em',
                        backdropFilter: 'blur(10px)',
                    }}>
                    ENTER COMMAND CENTER
                </motion.button>
            </motion.div>
        </div>
    );
}

function TelemetryBadge({ label, value, status }: { label: string, value: string, status: 'online' | 'recent' | 'alert' }) {
    const color = status === 'online' ? OrbitalColors.signal.sentinel : status === 'recent' ? OrbitalColors.gold.primary : OrbitalColors.signal.critical;

    return (
        <motion.div className="flex flex-col items-center gap-1 p-5 rounded-lg w-44" style={Glassmorphism.satellite} whileHover={{ y: -5 }}>
            <div className="text-[10px] uppercase tracking-[0.3em]" style={{ color: '#6B7280', fontFamily: OrbitalType.fontFamily.mono }}>{label}</div>
            <div className="text-2xl font-bold" style={{ color, fontFamily: OrbitalType.fontFamily.display, textShadow: `0 0 20px ${color}40` }}>{value}</div>
            <div className="w-1.5 h-1.5 rounded-full mt-2" style={{ background: color, boxShadow: `0 0 10px ${color}` }} />
        </motion.div>
    );
}
