/**
 * src/design-system/tokens.ts
 * Cinematic color science for orbital interfaces
 */

export const OrbitalColors = {
    // Void palette - deep space backgrounds
    void: {
        100: '#000000',      // Pure void
        90: '#0A0A0F',       // Near black
        80: '#12121A',       // Deep space
        70: '#1A1A24',       // Satellite panel
        60: '#252532',       // Structural element
        50: '#333344',       // Border subtle
    },

    // Orbital accents - precious metal energy
    gold: {
        primary: '#D4AF37',    // Satellite gold foil
        glow: '#FFD700',       // Solar reflection
        dim: '#8B7355',        // Shadowed gold
        pulse: 'rgba(212, 175, 55, 0.3)', // Ambient halo
    },

    // Data visualization - satellite signal colors
    signal: {
        sentinel: '#00D4AA',   // ESA cyan - healthy
        warning: '#FF6B35',    // Debris orange - caution
        critical: '#FF0040',   // Re-entry red - danger
        neutral: '#6B7280',    // Inactive - gray
        highlight: '#E0E7FF',  // Selection - ice white
    },

    // Waste classification - toxic luminescence
    toxicity: {
        fresh: '#39FF14',      // Neon green - fresh organic
        construction: '#FFA500', // Hazard orange - debris
        chemical: '#BF00FF',   // Purple haze - industrial
        leachate: '#00FFFF',   // Cyan pool - water contamination
    }
};

export const OrbitalMotion = {
    // Physics-based easing - orbital mechanics
    easing: {
        escapeVelocity: [0.22, 1, 0.36, 1],    // Fast out, slow in
        orbitalDecay: [0.33, 1, 0.68, 1],     // Graceful spiral
        zeroGravity: [0.4, 0, 0.2, 1],        // Float and settle
        reEntry: [0.87, 0, 0.13, 1],           // Dramatic arrival
    },

    // Time scales - cinematic timing
    duration: {
        instant: 0.15,        // Micro-interaction
        swift: 0.3,          // UI response
        deliberate: 0.6,     // Content reveal
        cinematic: 1.2,      // Scene transition
        epic: 2.0,           // Hero moment
    },

    // Stagger patterns - constellation reveals
    stagger: {
        rapid: 0.05,         // Data cascade
        wave: 0.1,          // Ripple effect
        orbital: 0.15,      // Planetary alignment
        dramatic: 0.3,      // Sequential focus
    }
};

export const Glassmorphism = {
    // Premium translucent surfaces
    satellite: {
        background: 'rgba(18, 18, 26, 0.7)',
        backdropFilter: 'blur(20px) saturate(180%)',
        border: '1px solid rgba(212, 175, 55, 0.15)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
    },

    hologram: {
        background: 'rgba(0, 212, 170, 0.08)',
        backdropFilter: 'blur(12px)',
        border: '1px solid rgba(0, 212, 170, 0.3)',
        boxShadow: '0 0 20px rgba(0, 212, 170, 0.2), inset 0 0 20px rgba(0, 212, 170, 0.05)',
    },

    warning: {
        background: 'rgba(255, 107, 53, 0.1)',
        backdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 107, 53, 0.4)',
        boxShadow: '0 0 30px rgba(255, 107, 53, 0.3)',
    }
};
