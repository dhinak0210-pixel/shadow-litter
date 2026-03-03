/**
 * packages/shared-types/src/schema.ts
 * Single source of truth for entire system
 */

export interface SatelliteScene {
    id: string;                          // S2A_20240115T052941_N0509_R105_T44PKT
    constellation: 'SENTINEL_2' | 'LANDSAT_9' | 'PLANET_SCOPE';
    satelliteId: string;                 // S2A, S2B, LC09
    acquisitionTime: string;             // ISO 8601
    cloudCover: number;                  // 0-100
    bbox: [number, number, number, number]; // [minX, minY, maxX, maxY]
    resolution: number;                  // 10, 30, 3 meters
    sizeBytes: number;
    status: 'ARCHIVED' | 'PROCESSING' | 'READY' | 'FAILED';
    bands: ('B02' | 'B03' | 'B04' | 'B08' | 'B11' | 'B12')[];
    downloadUrl?: string;
    cogUrl?: string;                     // Cloud Optimized GeoTIFF
}

export interface Detection {
    id: string;                          // UUID v4
    sceneId: string;                     // Parent satellite scene
    zoneId: string;                      // vaigai_riverbed, etc.

    // Geometry
    geometry: {
        type: 'Polygon';
        coordinates: number[][][];
    };
    centerLat: number;
    centerLon: number;
    areaSqm: number;

    // AI Predictions
    confidence: number;                  // 0-1
    wasteType: 'FRESH_MSW' | 'CONSTRUCTION' | 'CHEMICAL' | 'LEACHATE' | 'LEGACY';
    growthRate?: number;                 // m²/day
    toxicityIndex?: number;              // 0-10

    // Temporal
    firstDetectedAt: string;
    lastVerifiedAt?: string;
    status: 'NEW' | 'VERIFIED' | 'FALSE_POSITIVE' | 'CLEANED' | 'EXPANDING';

    // Provenance
    modelVersion: string;
    processingPipeline: string;

    // Civic Integration
    municipalTicketId?: string;
    alertSent: boolean;
    groundPhotos?: string[];
}

export interface Zone {
    id: string;
    name: string;
    nameTamil: string;
    centerLat: number;
    centerLon: number;
    radiusM: number;
    riskLevel: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    municipalWard: string;
    policeStation: string;
    estimatedPopulation: number;
    lastInspectionDate?: string;
}

// Real-time streaming events
export interface StreamEvent {
    type: 'SCENE_ACQUIRED' | 'DETECTION_CREATED' | 'ALERT_TRIGGERED' | 'MODEL_UPDATED';
    timestamp: string;
    payload: unknown;
    priority: 1 | 2 | 3 | 4 | 5;
}
