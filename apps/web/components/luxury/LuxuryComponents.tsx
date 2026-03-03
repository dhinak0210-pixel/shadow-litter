"use client";

import { useState, useEffect } from 'react';

export function TypewriterStatus({ messages, interval = 3000 }: { messages: string[], interval?: number }) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [displayText, setDisplayText] = useState('');
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        const message = messages[currentIndex];
        const typingSpeed = isDeleting ? 40 : 80;

        const timer = setTimeout(() => {
            if (!isDeleting && displayText === message) {
                setTimeout(() => setIsDeleting(true), interval);
            } else if (isDeleting && displayText === '') {
                setIsDeleting(false);
                setCurrentIndex((prev) => (prev + 1) % messages.length);
            } else {
                const nextText = isDeleting
                    ? message.slice(0, displayText.length - 1)
                    : message.slice(0, displayText.length + 1);
                setDisplayText(nextText);
            }
        }, typingSpeed);

        return () => clearTimeout(timer);
    }, [displayText, isDeleting, currentIndex, messages, interval]);

    return (
        <div className="flex items-center gap-3 font-mono text-[10px] tracking-widest text-[#00D4AA]">
            <div className="w-2 h-2 rounded-full bg-[#00D4AA] animate-pulse" />
            <span>{displayText}</span>
            <span className="w-1.5 h-3 bg-[#00D4AA] animate-[blink_1s_step-end_infinite]" />
        </div>
    );
}

export function ActionButton({ children, variant = 'primary', onClick }: { children: React.ReactNode, variant?: 'primary' | 'warning' | 'gold', onClick?: () => void }) {
    const styles: any = {
        primary: 'border-[#00D4AA] text-[#00D4AA] bg-[#00D4AA]/10',
        warning: 'border-[#FF0040] text-[#FF0040] bg-[#FF0040]/10',
        gold: 'border-[#D4AF37] text-[#D4AF37] bg-[#D4AF37]/10',
    };

    return (
        <button
            onClick={onClick}
            className={`px-6 py-2 border rounded text-[10px] font-bold tracking-widest uppercase transition-all hover:scale-105 active:scale-95 ${styles[variant]}`}
        >
            {children}
        </button>
    );
}
