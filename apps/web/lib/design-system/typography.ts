/**
 * src/design-system/typography.ts
 * NASA-inspired, luxury editorial
 */

export const OrbitalType = {
    fontFamily: {
        display: '"Space Grotesk", "Inter", system-ui, sans-serif',
        body: '"Inter", system-ui, sans-serif',
        mono: '"JetBrains Mono", "Fira Code", monospace',
        data: '"Roboto Mono", monospace',
    },

    sizes: {
        hero: 'clamp(4rem, 10vw, 8rem)',      // Command center title
        title: 'clamp(2rem, 5vw, 3.5rem)',    // Section headers
        subtitle: 'clamp(1.25rem, 2vw, 1.75rem)', // Feature titles
        body: 'clamp(0.875rem, 1vw, 1rem)',   // Content
        data: 'clamp(0.75rem, 0.8vw, 0.875rem)', // Telemetry
        micro: '0.625rem',                     // Labels
    },

    weights: {
        light: 300,
        regular: 400,
        medium: 500,
        semibold: 600,
        bold: 700,
    },

    // Special effects
    effects: {
        goldShimmer: {
            background: 'linear-gradient(135deg, #D4AF37 0%, #FFD700 50%, #D4AF37 100%)',
            backgroundSize: '200% 200%',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            animation: 'shimmer 3s ease infinite',
        },

        hologram: {
            textShadow: '0 0 10px rgba(0, 212, 170, 0.5), 0 0 20px rgba(0, 212, 170, 0.3)',
            color: '#00D4AA',
        },

        warningPulse: {
            textShadow: '0 0 10px rgba(255, 0, 64, 0.8)',
            animation: 'pulse 2s ease-in-out infinite',
        }
    }
};
