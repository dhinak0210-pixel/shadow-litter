"use client";

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { useEffect, useState } from 'react';

// ─── GLOBAL STATE STORE ─────────────────────────────────────────

interface Detection {
    id: number;
    type: string;
    area_sqm: number;
    confidence: number;
    position: [number, number, number];
}

interface Satellite {
    id: string;
    orbit: number[];
    health: string;
}

interface ShadowLitterState {
    liveDetections: Detection[];
    activeSatellites: Satellite[];
    systemHealth: { status: string };
    selectedZone: string | null;

    setSelectedZone: (zone: string | null) => void;
    addDetection: (det: Detection) => void;
}

export const useShadowLitter = create<ShadowLitterState>()(
    persist(
        (set) => ({
            liveDetections: [],
            activeSatellites: [],
            systemHealth: { status: 'initializing' },
            selectedZone: null,

            setSelectedZone: (zone) => set({ selectedZone: zone }),
            addDetection: (det) => set((state) => ({
                liveDetections: [det, ...state.liveDetections].slice(0, 100)
            })),
        }),
        {
            name: 'shadow-litter-storage',
        }
    )
);

// ─── PROVIDER COMPONENT ──────────────────────────────────────────

const queryClient = new QueryClient();

export function Providers({ children }: { children: React.ReactNode }) {
    const addDetection = useShadowLitter((s) => s.addDetection);
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        // Asynchronous update to avoid cascading synchronous render lints
        const timer = setTimeout(() => setMounted(true), 0);

        // Minimal WebSocket connection
        const ws = new WebSocket('ws://localhost:8000/ws/live');

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'DETECTION_CREATED') {
                addDetection(data.payload);
            }
        };

        return () => {
            clearTimeout(timer);
            ws.close();
        };
    }, [addDetection]);

    if (!mounted) return null;

    return (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );
}
