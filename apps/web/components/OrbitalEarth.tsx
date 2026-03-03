"use client";

import { useRef } from 'react';
import { useFrame, useLoader } from '@react-three/fiber';
import { Float } from '@react-three/drei';
import * as THREE from 'three';

const earthVertexShader = `
  varying vec3 vNormal;
  varying vec2 vUv;
  varying vec3 vPosition;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vUv = uv;
    vPosition = (modelMatrix * vec4(position, 1.0)).xyz;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const earthFragmentShader = `
  uniform sampler2D uDayTexture;
  uniform sampler2D uNightTexture;
  uniform sampler2D uCloudTexture;
  uniform vec3 uSunPosition;
  varying vec3 vNormal;
  varying vec2 vUv;
  varying vec3 vPosition;
  void main() {
    vec3 dayColor = texture2D(uDayTexture, vUv).rgb;
    vec3 nightColor = texture2D(uNightTexture, vUv).rgb;
    vec3 clouds = texture2D(uCloudTexture, vUv).rgb;
    
    vec3 sunDir = normalize(uSunPosition);
    float intensity = dot(vNormal, sunDir);
    
    vec3 color = mix(nightColor, dayColor + clouds * 0.5, smoothstep(-0.2, 0.2, intensity));
    gl_FragColor = vec4(color, 1.0);
  }
`;

const atmosphereVertexShader = `
  varying vec3 vNormal;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.1);
  }
`;

const atmosphereFragmentShader = `
  varying vec3 vNormal;
  void main() {
    float intensity = pow(0.7 - dot(vNormal, vec3(0, 0, 1.0)), 2.0);
    gl_FragColor = vec4(0.3, 0.6, 1.0, 1.0) * intensity;
  }
`;

export function OrbitalEarth() {
    const earthRef = useRef<THREE.Mesh>(null!);
    const satellitesRef = useRef<(THREE.Group | null)[]>([]);

    const [dayTexture, nightTexture, cloudTexture] = useLoader(THREE.TextureLoader, [
        '/textures/earth_day.png',
        '/textures/earth_night.png',
        '/textures/earth_clouds.png'
    ]);

    useFrame((state) => {
        if (earthRef.current) {
            earthRef.current.rotation.y += 0.0005;
        }

        satellitesRef.current.forEach((sat, i) => {
            if (sat) {
                const time = state.clock.elapsedTime;
                const speed = 0.5 + i * 0.1;
                const radius = 1.3 + i * 0.1;

                sat.position.x = Math.cos(time * speed) * radius;
                sat.position.z = Math.sin(time * speed) * radius;
                sat.position.y = Math.sin(time * speed * 0.5) * 0.2;
            }
        });
    });

    return (
        <group>
            {/* Earth sphere with custom shader */}
            <mesh ref={earthRef}>
                <sphereGeometry args={[1, 64, 64]} />
                <shaderMaterial
                    vertexShader={earthVertexShader}
                    fragmentShader={earthFragmentShader}
                    uniforms={{
                        uDayTexture: { value: dayTexture },
                        uNightTexture: { value: nightTexture },
                        uCloudTexture: { value: cloudTexture },
                        uSunPosition: { value: new THREE.Vector3(5, 3, 5) },
                    }}
                />
            </mesh>

            {/* Atmosphere glow */}
            <mesh>
                <sphereGeometry args={[1.1, 32, 32]} />
                <shaderMaterial
                    vertexShader={atmosphereVertexShader}
                    fragmentShader={atmosphereFragmentShader}
                    transparent
                    side={THREE.BackSide}
                    blending={THREE.AdditiveBlending}
                />
            </mesh>

            {/* Sentinel-2 satellites */}
            {['S2A', 'S2B', 'LS9'].map((name, i) => (
                <group key={name} ref={(el) => (satellitesRef.current[i] = el)}>
                    <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
                        <mesh>
                            <boxGeometry args={[0.03, 0.03, 0.06]} />
                            <meshStandardMaterial
                                color={i === 0 ? '#00D4AA' : i === 1 ? '#D4AF37' : '#FF6B35'}
                                emissive={i === 0 ? '#00D4AA' : i === 1 ? '#D4AF37' : '#FF6B35'}
                                emissiveIntensity={2}
                            />
                        </mesh>
                        <mesh position={[-0.05, 0, 0]}>
                            <boxGeometry args={[0.08, 0.001, 0.04]} />
                            <meshStandardMaterial color="#1a1a2e" metalness={0.9} />
                        </mesh>
                        <mesh position={[0.05, 0, 0]}>
                            <boxGeometry args={[0.08, 0.001, 0.04]} />
                            <meshStandardMaterial color="#1a1a2e" metalness={0.9} />
                        </mesh>
                    </Float>
                </group>
            ))}
        </group>
    );
}
